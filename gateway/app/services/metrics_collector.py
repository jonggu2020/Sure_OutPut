"""
Docker 메트릭 수집기 (Gateway 백그라운드 태스크)
=================================================
Gateway에서 Docker Stats API로 컨테이너 메트릭을 수집하고,
60초 윈도우로 집계하여 WebSocket으로 Model 3에 전달.

이 수집기는 두 가지 일을 한다:
  1. 윈도우를 Model 3로 전송 → 실시간 이상 탐지 추론  (항상 동작)
  2. 윈도우를 CSV로 저장 → Model 3 재학습용 데이터셋   (선택, 기본 OFF)

(2)는 Model 3를 처음 학습시킬 때 데이터를 모으던 일회성 작업이다.
모델이 완성된 현재는 기본적으로 비활성(METRICS_SAVE_CSV=false)이며,
(1) 실시간 추론만 계속 동작한다.
→ 다시 데이터를 모아야 할 일이 생기면 METRICS_SAVE_CSV=true 로 켜면 된다.

사용:
  Gateway main.py의 lifespan에서 시작/중지.
"""

import asyncio
import csv
import json
import logging
import os
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

log = logging.getLogger("metrics_collector")

# ── 설정 ─────────────────────────────────────────────────────────────
POLL_INTERVAL = float(os.environ.get("METRICS_POLL_INTERVAL", "3.0"))
WINDOW_SECONDS = int(os.environ.get("METRICS_WINDOW_SECONDS", "60"))
WINDOW_SLIDE_SECONDS = int(os.environ.get("METRICS_SLIDE_SECONDS", "30"))
CONTAINER_FILTER = os.environ.get("METRICS_CONTAINER_FILTER", "secureops")
DATA_DIR = Path(os.environ.get("METRICS_DATA_DIR", "data"))
COLLECT_ENABLED = os.environ.get("METRICS_COLLECT_ENABLED", "true").lower() == "true"

# 재학습용 CSV 저장 스위치 (기본 OFF).
# - false: 윈도우를 Model 3로 보내 추론만 한다. 디스크에 CSV를 쓰지 않는다.
# - true : 추론에 더해, 윈도우를 재학습 스키마(scenario/label) CSV로도 저장한다.
SAVE_CSV = os.environ.get("METRICS_SAVE_CSV", "false").lower() == "true"

# 재학습 데이터 스키마를 위한 시나리오 및 라벨 환경변수 설정 (CSV 저장 시에만 의미 있음)
SCENARIO_NAME = os.environ.get("METRICS_SCENARIO", "Normal_Realtime")
SCENARIO_LABEL = int(os.environ.get("METRICS_LABEL", "0"))

# 43개 feature 칼럼
FEATURE_COLUMNS = [
    "container_cpu_usage_rate_mean", "container_cpu_usage_rate_std",
    "container_cpu_usage_rate_min", "container_cpu_usage_rate_max",
    "container_cpu_usage_rate_p95", "container_cpu_usage_rate_last",
    "container_memory_usage_bytes_mean", "container_memory_usage_bytes_std",
    "container_memory_usage_bytes_min", "container_memory_usage_bytes_max",
    "container_memory_usage_bytes_p95", "container_memory_usage_bytes_last",
    "container_memory_usage_bytes_slope",
    "container_network_receive_bytes_rate_mean", "container_network_receive_bytes_rate_std",
    "container_network_receive_bytes_rate_min", "container_network_receive_bytes_rate_max",
    "container_network_receive_bytes_rate_p95", "container_network_receive_bytes_rate_last",
    "container_network_receive_bytes_rate_sum", "container_network_receive_bytes_rate_nonzero_ratio",
    "container_network_transmit_bytes_rate_mean", "container_network_transmit_bytes_rate_std",
    "container_network_transmit_bytes_rate_min", "container_network_transmit_bytes_rate_max",
    "container_network_transmit_bytes_rate_p95", "container_network_transmit_bytes_rate_last",
    "container_network_transmit_bytes_rate_sum", "container_network_transmit_bytes_rate_nonzero_ratio",
    "container_disk_read_bytes_rate_mean", "container_disk_read_bytes_rate_std",
    "container_disk_read_bytes_rate_max", "container_disk_read_bytes_rate_p95",
    "container_disk_read_bytes_rate_sum", "container_disk_read_bytes_rate_nonzero_ratio",
    "container_disk_write_bytes_rate_mean", "container_disk_write_bytes_rate_std",
    "container_disk_write_bytes_rate_min", "container_disk_write_bytes_rate_max",
    "container_disk_write_bytes_rate_p95", "container_disk_write_bytes_rate_last",
    "container_disk_write_bytes_rate_sum", "container_disk_write_bytes_rate_nonzero_ratio",
]

# 차인택 ML 모델 재학습 스키마에 맞춘 최종 CSV 컬럼 구성
WINDOW_CSV_COLUMNS = [
    "timestamp", "container_name", "scenario", "label", 
    "window_start", "window_end", "row_count"
] + FEATURE_COLUMNS


# ── Docker Stats 파싱 ────────────────────────────────────────────────

def _parse_size(s: str) -> float:
    s = s.strip()
    units = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3,
             "KB": 1000, "MB": 1000**2, "GB": 1000**3}
    match = re.match(r"([\d.]+)\s*([A-Za-z]+)", s)
    if match:
        return float(match.group(1)) * units.get(match.group(2).upper(), 1)
    return 0.0


def _parse_cpu(s: str) -> float:
    return float(s.strip().replace("%", "")) / 100.0


def collect_docker_stats() -> list[dict]:
    """Docker stats API에서 한 번 수집 (동기, subprocess)."""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream",
             "--format", "{{.Name}}\t{{.ID}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        log.warning("Docker stats 실패: %s", e)
        return []

    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            continue

        name = parts[0]
        if CONTAINER_FILTER and CONTAINER_FILTER not in name.lower():
            continue

        mem_usage = _parse_size(parts[3].split("/")[0].strip())
        net_parts = parts[4].split("/")
        net_rx = _parse_size(net_parts[0].strip()) if len(net_parts) >= 2 else 0
        net_tx = _parse_size(net_parts[1].strip()) if len(net_parts) >= 2 else 0
        block_parts = parts[5].split("/")
        disk_read = _parse_size(block_parts[0].strip()) if len(block_parts) >= 2 else 0
        disk_write = _parse_size(block_parts[1].strip()) if len(block_parts) >= 2 else 0

        rows.append({
            "timestamp": now,
            "container_name": name,
            "cpu_usage_rate": _parse_cpu(parts[2]),
            "memory_usage_bytes": mem_usage,
            "network_receive_bytes_rate": net_rx,
            "network_transmit_bytes_rate": net_tx,
            "disk_read_bytes_rate": disk_read,
            "disk_write_bytes_rate": disk_write,
        })

    return rows


# ── 윈도우 집계 ──────────────────────────────────────────────────────

def compute_window_features(samples: list[dict]) -> dict:
    """원시 샘플 → 43개 feature dict."""
    if not samples:
        return {col: 0.0 for col in FEATURE_COLUMNS}

    metrics = {
        "cpu_usage_rate": [s["cpu_usage_rate"] for s in samples],
        "memory_usage_bytes": [s["memory_usage_bytes"] for s in samples],
        "network_receive_bytes_rate": [s["network_receive_bytes_rate"] for s in samples],
        "network_transmit_bytes_rate": [s["network_transmit_bytes_rate"] for s in samples],
        "disk_read_bytes_rate": [s["disk_read_bytes_rate"] for s in samples],
        "disk_write_bytes_rate": [s["disk_write_bytes_rate"] for s in samples],
    }

    features = {}
    for metric_name, values in metrics.items():
        arr = np.array(values, dtype=float)
        prefix = f"container_{metric_name}"

        features[f"{prefix}_mean"] = float(np.mean(arr))
        features[f"{prefix}_std"] = float(np.std(arr))
        features[f"{prefix}_min"] = float(np.min(arr))
        features[f"{prefix}_max"] = float(np.max(arr))
        features[f"{prefix}_p95"] = float(np.percentile(arr, 95))
        features[f"{prefix}_last"] = float(arr[-1])

        if metric_name == "memory_usage_bytes" and len(arr) > 1:
            x = np.arange(len(arr))
            features[f"{prefix}_slope"] = float(np.polyfit(x, arr, 1)[0])
        elif metric_name == "memory_usage_bytes":
            features[f"{prefix}_slope"] = 0.0

        if metric_name in ("network_receive_bytes_rate", "network_transmit_bytes_rate",
                           "disk_read_bytes_rate", "disk_write_bytes_rate"):
            features[f"{prefix}_sum"] = float(np.sum(arr))
            features[f"{prefix}_nonzero_ratio"] = float(np.count_nonzero(arr) / len(arr))

    return {col: features.get(col, 0.0) for col in FEATURE_COLUMNS}


# ── 수집기 클래스 ────────────────────────────────────────────────────

class MetricsCollector:
    """Gateway 백그라운드 메트릭 수집기."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._buffers: dict[str, list] = defaultdict(list)
        self._windows_written = 0
        self._csv_path: Path | None = None
        self._last_window_time = 0.0
        self._last_summary_time = 0.0  # 10분 단위 콘솔 출력을 위한 타이머 변수 추가

    async def start(self):
        """백그라운드 수집 시작. CSV 저장은 SAVE_CSV가 켜져 있을 때만 준비."""
        if not COLLECT_ENABLED:
            log.info("메트릭 수집 비활성화 (METRICS_COLLECT_ENABLED=false)")
            return

        # 재학습용 CSV 저장이 켜진 경우에만 폴더 구조 + CSV 헤더를 준비한다.
        # 꺼져 있으면 디스크에 아무것도 만들지 않고 추론 전용으로 동작한다.
        if SAVE_CSV:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

            # 예: data/Normal_Realtime/run_01_20260515T123414Z/
            run_dir = DATA_DIR / SCENARIO_NAME / f"run_01_{timestamp_str}"
            run_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            self._csv_path = run_dir / f"dataset_{date_str}.csv"

            with open(self._csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=WINDOW_CSV_COLUMNS)
                writer.writeheader()
        else:
            self._csv_path = None

        self._running = True
        self._last_window_time = time.time()
        self._last_summary_time = time.time()  # 타이머 초기화
        self._task = asyncio.create_task(self._collect_loop())

        if SAVE_CSV:
            log.info("📊 메트릭 수집 시작 (추론 + CSV 저장) → %s (시나리오: %s, 라벨: %d)",
                     self._csv_path, SCENARIO_NAME, SCENARIO_LABEL)
        else:
            log.info("📊 메트릭 수집 시작 (추론 전용 — CSV 저장 OFF). "
                     "재학습 데이터가 필요하면 METRICS_SAVE_CSV=true 로 켜세요.")

    async def stop(self):
        """수집 중지."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if SAVE_CSV:
            log.info("📊 메트릭 수집 종료 (윈도우 %d개 저장)", self._windows_written)
        else:
            log.info("📊 메트릭 수집 종료 (추론 전용 모드)")

    def _print_summary(self):
        """10분 주기 콘솔 요약. CSV 저장 모드 여부에 따라 내용이 다르다."""
        if SAVE_CSV and self._csv_path is not None:
            base_dir = DATA_DIR / SCENARIO_NAME
            dataset_files = list(base_dir.rglob("dataset_*.csv")) if base_dir.exists() else []
            total_runs = len(dataset_files)

            total_cumulative_rows = 0
            for file_path in dataset_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = sum(1 for _ in f)
                        if lines > 1:
                            total_cumulative_rows += (lines - 1)
                except Exception:
                    pass

            log.info("==================================================")
            log.info("📊 [10분 주기 - 실시간 수집 진행 상황 요약]")
            log.info("▶ 현재 시나리오: %s (라벨: %d)", SCENARIO_NAME, SCENARIO_LABEL)
            log.info("▶ 현재 세션에 기록된 윈도우 수: %d 개", self._windows_written)
            log.info("▶ 누적 생성된 폴더(Run) 개수: %d 개", total_runs)
            log.info("▶ 현재 시나리오의 전체 누적 데이터: 총 %d 개", total_cumulative_rows)
            log.info("==================================================")
        else:
            # 추론 전용 모드: 디스크 누적이 없으므로 처리량만 가볍게 보고한다.
            log.info("==================================================")
            log.info("📊 [10분 주기 - 추론 전용 모드]")
            log.info("▶ 현재 세션에 처리한 윈도우 수: %d 개", self._windows_written)
            log.info("==================================================")

    async def _collect_loop(self):
        """메인 수집 루프."""
        while self._running:
            try:
                # Docker stats 수집 (blocking → run_in_executor)
                loop = asyncio.get_event_loop()
                samples = await loop.run_in_executor(None, collect_docker_stats)

                now = time.time()

                if samples:
                    for s in samples:
                        s["_time"] = now
                        self._buffers[s["container_name"]].append(s)

                # 윈도우 생성 체크
                if now - self._last_window_time >= WINDOW_SLIDE_SECONDS:
                    await self._create_windows(now)
                    self._last_window_time = now

                    # 오래된 샘플 정리
                    cutoff = now - (WINDOW_SECONDS * 2)
                    for name in list(self._buffers.keys()):
                        self._buffers[name] = [
                            s for s in self._buffers[name] if s["_time"] >= cutoff
                        ]

                # 10분(600초) 콘솔 출력 타이머 체크
                if now - self._last_summary_time >= 600:
                    self._print_summary()
                    self._last_summary_time = now

            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("수집 루프 에러: %s", e)

            await asyncio.sleep(POLL_INTERVAL)

    async def _create_windows(self, now: float):
        """현재 버퍼에서 윈도우를 생성한다.

        - Model 3 전송(추론)은 항상 수행한다.
        - CSV 저장은 SAVE_CSV가 켜져 있을 때만 수행한다.
        """
        window_end = now
        window_start = now - WINDOW_SECONDS

        for container_name, container_samples in self._buffers.items():
            window_samples = [
                s for s in container_samples
                if s["_time"] >= window_start and s["_time"] <= window_end
            ]

            if len(window_samples) < 3:
                continue

            features = compute_window_features(window_samples)

            # ── 재학습용 CSV 저장 (선택) ──
            if SAVE_CSV and self._csv_path is not None:
                row = {
                    "timestamp": datetime.fromtimestamp(window_end, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "container_name": container_name,
                    "scenario": SCENARIO_NAME,
                    "label": SCENARIO_LABEL,
                    "window_start": datetime.fromtimestamp(window_start, tz=timezone.utc).isoformat(),
                    "window_end": datetime.fromtimestamp(window_end, tz=timezone.utc).isoformat(),
                    "row_count": len(window_samples),
                }
                row.update(features)

                with open(self._csv_path, "a", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=WINDOW_CSV_COLUMNS)
                    writer.writerow(row)

            self._windows_written += 1

            # ── Model 3 실시간 추론 (항상 수행) ──
            try:
                from app.routers.aiops import model3
                if model3.connected:
                    result = await model3.send_task(
                        task_type="predict",
                        payload={
                            "features": features,
                            "threshold_policy": "best_f1",
                        },
                        timeout=10.0,
                    )
                    is_anomaly = result.get("is_anomaly", False)
                    score = result.get("anomaly_score", 0)

                    if is_anomaly:
                        log.warning(
                            "🔴 이상 감지: %s (score: %.4f)",
                            container_name, score,
                        )
                    else:
                        log.info(
                            "🟢 정상: %s (score: %.4f, 윈도우 #%d)",
                            container_name, score, self._windows_written,
                        )
            except Exception as e:
                log.debug("Model 3 전송 실패 (수집은 계속): %s", e)

    @property
    def stats(self) -> dict:
        """현재 수집 상태."""
        return {
            "running": self._running,
            "save_csv": SAVE_CSV,
            "windows_written": self._windows_written,
            "csv_path": str(self._csv_path) if self._csv_path else None,
            "active_containers": list(self._buffers.keys()),
        }


# 싱글톤
metrics_collector = MetricsCollector()