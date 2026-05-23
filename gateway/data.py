"""
Gateway 수집 데이터 → 차인택(Model 3) 학습용 스키마 전처리 + 압축
================================================================

Gateway의 metrics_collector.py가 생성한 14개 run 폴더의 CSV를
차인택이 data_collector.py로 수집했던 것과 동일한 최종 스키마로 정리합니다.

차인택 data_collector.py 최종 출력 스키마 (container profile):
  timestamp, container_cpu_usage_rate, container_memory_usage_bytes,
  container_network_receive_bytes_rate, container_network_transmit_bytes_rate,
  container_disk_io_time_rate, label, scenario

Gateway metrics_collector.py 출력 스키마:
  timestamp, container_name, scenario, label, window_start, window_end, row_count,
  + 43개 윈도우 집계 feature (_mean, _std, _min, _max, _p95, _last, _slope, _sum, _nonzero_ratio)

전처리 전략:
  Gateway 데이터는 이미 60초 윈도우 집계된 상태이므로,
  차인택 모델이 직접 소비하는 두 가지 형태를 모두 생성합니다:

  1) windowed/ — 43개 feature 그대로 (윈도우 집계 형태, Model 3 추론용)
  2) timeseries/ — _mean 값을 대표값으로 추출하여 차인택 원본 스키마와 동일하게 변환
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np


# ── 차인택 data_collector.py 원본 스키마 ──
CHARINTAEK_RAW_COLUMNS = [
    "timestamp",
    "container_cpu_usage_rate",
    "container_memory_usage_bytes",
    "container_network_receive_bytes_rate",
    "container_network_transmit_bytes_rate",
    "container_disk_io_time_rate",
    "container_disk_read_bytes_rate",
    "container_disk_write_bytes_rate",
    "label",
    "scenario",
]

# ── Gateway 43개 feature 컬럼 ──
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


def find_csv_files(input_dir: Path) -> list[Path]:
    """Normal_Realtime 하위 run_* 폴더에서 dataset_*.csv 파일 검색."""
    csv_files = sorted(input_dir.rglob("dataset_*.csv"))
    if not csv_files:
        # 단일 파일이 직접 전달된 경우
        csv_files = sorted(input_dir.glob("*.csv"))
    return csv_files


def load_and_merge(csv_files: list[Path]) -> pd.DataFrame:
    """모든 CSV를 로드하고 병합."""
    frames = []
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            # run 폴더 이름에서 출처 추적
            run_name = csv_path.parent.name
            df["source_run"] = run_name
            df["source_file"] = csv_path.name
            frames.append(df)
            print(f"  ✓ {csv_path.relative_to(csv_path.parents[2]) if len(csv_path.parents) > 2 else csv_path.name}: {len(df)} rows")
        except Exception as e:
            print(f"  ✗ {csv_path}: {e}")
    
    if not frames:
        print("[ERROR] CSV 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    merged = pd.concat(frames, ignore_index=True)
    print(f"\n총 병합: {len(merged)} rows from {len(frames)} files")
    return merged


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """기본 전처리: 결측치, 중복 제거, 정렬."""
    original_len = len(df)
    
    # \r 제거 (Windows line ending) — 실제 문자열 컬럼만 처리
    for col in df.columns:
        if df[col].dtype == object and df[col].apply(type).eq(str).all():
            df[col] = df[col].str.strip()
    
    # feature 컬럼 결측치 → 0.0
    existing_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    df[existing_features] = df[existing_features].fillna(0.0)
    
    # 완전 중복 행 제거 (source 컬럼 제외)
    check_cols = [c for c in df.columns if c not in ("source_run", "source_file")]
    df = df.drop_duplicates(subset=check_cols, keep="first")
    
    # timestamp 기준 정렬
    df = df.sort_values(["timestamp", "container_name"]).reset_index(drop=True)
    
    removed = original_len - len(df)
    if removed > 0:
        print(f"중복 제거: {removed}행 제거 → {len(df)}행 유지")
    
    return df


def export_windowed(df: pd.DataFrame, output_dir: Path) -> Path:
    """
    형태 1: 윈도우 집계 형태 (Model 3 추론용)
    43개 feature + timestamp, container_name, scenario, label
    """
    out_dir = output_dir / "windowed"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 출력 컬럼 구성
    meta_cols = ["timestamp", "container_name", "scenario", "label", "window_start", "window_end", "row_count"]
    existing_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    export_cols = meta_cols + existing_features
    
    out_df = df[[c for c in export_cols if c in df.columns]].copy()
    out_path = out_dir / "model3_windowed_features.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\n[windowed] {out_path}: {len(out_df)} rows × {len(out_df.columns)} cols")
    return out_path


def export_timeseries(df: pd.DataFrame, output_dir: Path) -> Path:
    """
    차인택에게 전달했던 원본 스키마와 동일한 10컬럼 CSV 생성.
    
    Gateway _mean → 차인택 원본 컬럼:
      container_cpu_usage_rate_mean     → container_cpu_usage_rate
      container_memory_usage_bytes_mean → container_memory_usage_bytes
      container_network_receive_bytes_rate_mean  → container_network_receive_bytes_rate
      container_network_transmit_bytes_rate_mean → container_network_transmit_bytes_rate
      (Gateway에 없음, Prometheus fs_io_time 메트릭) → container_disk_io_time_rate (빈 값)
      container_disk_read_bytes_rate_mean  → container_disk_read_bytes_rate
      container_disk_write_bytes_rate_mean → container_disk_write_bytes_rate
    """
    out_dir = output_dir / "timeseries"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_df = pd.DataFrame()
    out_df["timestamp"] = df["timestamp"]
    
    # 1:1 매핑
    simple_mapping = {
        "container_cpu_usage_rate_mean": "container_cpu_usage_rate",
        "container_memory_usage_bytes_mean": "container_memory_usage_bytes",
        "container_network_receive_bytes_rate_mean": "container_network_receive_bytes_rate",
        "container_network_transmit_bytes_rate_mean": "container_network_transmit_bytes_rate",
    }
    for src_col, dst_col in simple_mapping.items():
        out_df[dst_col] = df[src_col] if src_col in df.columns else 0.0
    
    # disk_io_time_rate: Prometheus container_fs_io_time_seconds_total 기반 메트릭
    # Gateway Docker Stats에는 이 메트릭이 없으므로 빈 값(원본과 동일한 패턴)
    out_df["container_disk_io_time_rate"] = None
    
    # disk_read, disk_write: 1:1 매핑
    out_df["container_disk_read_bytes_rate"] = df["container_disk_read_bytes_rate_mean"] if "container_disk_read_bytes_rate_mean" in df.columns else 0.0
    out_df["container_disk_write_bytes_rate"] = df["container_disk_write_bytes_rate_mean"] if "container_disk_write_bytes_rate_mean" in df.columns else 0.0
    
    out_df["label"] = df["label"]
    out_df["scenario"] = df["scenario"]
    
    # 차인택 스키마 컬럼 순서 보장
    out_df = out_df[CHARINTAEK_RAW_COLUMNS]
    
    out_path = out_dir / "model3_timeseries_compatible.csv"
    out_df.to_csv(out_path, index=False)
    print(f"[timeseries] {out_path}: {len(out_df)} rows × {len(out_df.columns)} cols")
    return out_path


def print_summary(df: pd.DataFrame):
    """데이터 요약 출력."""
    print("\n" + "=" * 60)
    print("📊 전처리 결과 요약")
    print("=" * 60)
    print(f"총 행 수: {len(df)}")
    print(f"컨테이너: {df['container_name'].nunique()}개 — {', '.join(sorted(df['container_name'].unique()))}")
    print(f"시나리오: {df['scenario'].unique().tolist()}")
    print(f"라벨 분포: {df['label'].value_counts().to_dict()}")
    
    if "source_run" in df.columns:
        print(f"Run 폴더: {df['source_run'].nunique()}개")
    
    # feature 통계
    print("\n주요 feature 범위:")
    key_features = [
        "container_cpu_usage_rate_mean",
        "container_memory_usage_bytes_mean",
        "container_network_receive_bytes_rate_mean",
        "container_network_transmit_bytes_rate_mean",
    ]
    for feat in key_features:
        if feat in df.columns:
            vals = df[feat]
            short_name = feat.replace("container_", "").replace("_mean", "")
            print(f"  {short_name}: min={vals.min():.4f}, mean={vals.mean():.4f}, max={vals.max():.4f}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gateway 수집 데이터 → 차인택 스키마 전처리 + 압축")
    parser.add_argument("--input-dir", required=True, help="Normal_Realtime 폴더 경로 (run_* 하위 폴더 포함)")
    parser.add_argument("--output-dir", default="./model3_preprocessed", help="전처리 결과 출력 디렉토리")
    parser.add_argument("--compress", action="store_true", default=True, help="결과를 zip으로 압축 (기본: True)")
    parser.add_argument("--no-compress", action="store_false", dest="compress")
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🔧 Gateway → Model 3 전처리 시작")
    print("=" * 60)
    print(f"입력: {input_dir}")
    print(f"출력: {output_dir}\n")
    
    # 1) CSV 검색 및 로드
    print("[1/4] CSV 파일 검색 및 로드...")
    csv_files = find_csv_files(input_dir)
    print(f"  발견: {len(csv_files)}개 파일\n")
    df = load_and_merge(csv_files)
    
    # 2) 전처리
    print("\n[2/4] 전처리 (결측치, 중복, 정렬)...")
    df = clean_data(df)
    
    # 3) 두 가지 형태로 내보내기
    print("\n[3/4] 스키마 변환 및 내보내기...")
    windowed_path = export_windowed(df, output_dir)
    timeseries_path = export_timeseries(df, output_dir)
    
    # 요약
    print_summary(df)
    
    # 4) 압축
    if args.compress:
        print(f"\n[4/4] ZIP 압축...")
        zip_name = output_dir.name
        zip_path = shutil.make_archive(
            str(output_dir.parent / zip_name),
            "zip",
            root_dir=str(output_dir.parent),
            base_dir=zip_name,
        )
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"✅ 압축 완료: {zip_path} ({zip_size_mb:.2f} MB)")
    
    print("\n✅ 전처리 완료!")
    print(f"   windowed/  → Model 3 추론용 (43개 feature)")
    print(f"   timeseries/ → 차인택 원본 스키마 호환 (6개 raw metric)")


if __name__ == "__main__":
    main()