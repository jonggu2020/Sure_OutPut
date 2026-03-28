"""
Model 3 Server: AIOps — Docker 리소스 이상 탐지 + LLM 의사결정
==============================================================
담당: 차인택
독립 FastAPI 서버. 관리자 전용.
Isolation Forest + LSTM 이상 탐지 + Ollama RAG 자동 의사결정.

=== 차인택 작업 가이드 ===

이 서버는 Docker 컨테이너들의 리소스 상태를 모니터링하고,
이상을 탐지하고, 자동으로 대응 조치를 결정합니다.

파이프라인:
  1. Prometheus (http://localhost:9090) → 컨테이너 메트릭 수집
  2. cAdvisor (http://localhost:8085) → Docker 컨테이너 상세 메트릭
  3. Isolation Forest + LSTM → 이상 탐지 (CPU/메모리/네트워크/디스크)
  4. ChromaDB → 과거 조치 이력 벡터 검색 (RAG)
  5. Ollama LLM → 조치 의사결정 (Pool 크기 조정, 컨테이너 종료 등)

데이터 흐름:
  [Prometheus/cAdvisor] → 이 서버가 주기적으로 pull
  → 이상 탐지 모델 실행
  → 이상 발견 시 RAG + LLM으로 조치 결정
  → Gateway /api/sandbox/pool/config 호출하여 자동 조정

해야 할 것:
  1. Prometheus API 연동 (메트릭 수집)
  2. app/services/ 에 이상 탐지 로직 구현 (Isolation Forest + LSTM)
  3. app/ml/ 에 학습된 모델 파일 배치
  4. ChromaDB 연동 (과거 조치 이력 저장/검색)
  5. Ollama 연동 (의사결정 LLM)
  6. 주기적 자동 조정 백그라운드 태스크

사용 가능한 인프라 (docker-compose로 실행됨):
  - Prometheus: http://prometheus:9090 (Docker) / http://localhost:9090 (로컬)
  - cAdvisor: http://cadvisor:8080 (Docker) / http://localhost:8085 (로컬)
  - Ollama: http://ollama:11434 (Docker) / http://localhost:11434 (로컬)
  - ChromaDB: http://chromadb:8000 (Docker) / http://localhost:8004 (로컬)

평가 지표: F1-Score (이상 탐지), RAG 검색 정확도, 응답 Latency
"""

from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import os
import httpx

app = FastAPI(
    title="SecureOps - AIOps Resource Monitor",
    version="0.1.0",
)

# Gateway URL (Pool 자동 조정 시 호출)
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

# Prometheus URL
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")


# ══════════════════════════════════════════════
# 헬스체크
# ══════════════════════════════════════════════

@app.get("/health")
async def health():
    """Gateway 헬스체크용."""
    return {"status": "ok", "model": "aiops-resource"}


# ══════════════════════════════════════════════
# 엔드포인트 1: 리소스 상태 조회
# Gateway /api/aiops/status 에서 호출
# ══════════════════════════════════════════════

class ContainerMetrics(BaseModel):
    """개별 컨테이너 리소스 메트릭."""
    container_name: str
    cpu_percent: float          # CPU 사용률 (%)
    memory_percent: float       # 메모리 사용률 (%)
    memory_usage_mb: float      # 메모리 사용량 (MB)
    network_rx_bytes: int       # 수신 바이트
    network_tx_bytes: int       # 송신 바이트
    disk_read_bytes: int        # 디스크 읽기
    disk_write_bytes: int       # 디스크 쓰기
    is_anomaly: bool            # 이상 여부

class ResourceStatusResponse(BaseModel):
    """전체 리소스 상태 응답."""
    containers: list[ContainerMetrics]
    total_cpu_percent: float
    total_memory_percent: float
    anomaly_count: int
    pool_recommendation: str    # "maintain" | "scale_up" | "scale_down"

@app.get("/status", response_model=ResourceStatusResponse)
async def resource_status():
    """
    전체 Docker 컨테이너 리소스 상태 조회.

    === 차인택: 여기를 Prometheus/cAdvisor 연동으로 교체 ===

    Prometheus 쿼리 예시:
    - CPU: container_cpu_usage_seconds_total{name=~"secureops.*"}
    - 메모리: container_memory_usage_bytes{name=~"secureops.*"}
    - 네트워크: container_network_receive_bytes_total
    """
    # ──────────────────────────────────────────
    # TODO: 차인택 — Prometheus API로 실제 메트릭 수집
    # ──────────────────────────────────────────
    # 예시:
    # metrics = await fetch_prometheus_metrics()
    # for container in metrics:
    #     container.is_anomaly = isolation_forest.predict(container)
    # ──────────────────────────────────────────

    # 더미 응답 (프로토타입)
    return ResourceStatusResponse(
        containers=[
            ContainerMetrics(
                container_name="secureops-sandbox-6081",
                cpu_percent=15.2,
                memory_percent=42.5,
                memory_usage_mb=218.0,
                network_rx_bytes=1024000,
                network_tx_bytes=512000,
                disk_read_bytes=0,
                disk_write_bytes=0,
                is_anomaly=False,
            ),
        ],
        total_cpu_percent=15.2,
        total_memory_percent=42.5,
        anomaly_count=0,
        pool_recommendation="maintain",
    )


# ══════════════════════════════════════════════
# 엔드포인트 2: 이상 탐지 목록
# Gateway /api/aiops/anomalies 에서 호출
# ══════════════════════════════════════════════

class AnomalyInfo(BaseModel):
    """감지된 이상 정보."""
    container_name: str
    anomaly_type: str           # "cpu_spike" | "memory_leak" | "network_flood" | "disk_exhaustion"
    severity: str               # "low" | "medium" | "high" | "critical"
    metric_value: float         # 이상 수치
    threshold: float            # 정상 기준치
    detected_at: float          # 감지 시각 (timestamp)
    recommended_action: str     # LLM이 추천하는 조치

@app.get("/anomalies", response_model=list[AnomalyInfo])
async def anomalies():
    """
    현재 감지된 리소스 이상 목록.

    === 차인택: 여기를 Isolation Forest + LSTM 결과로 교체 ===

    이상 탐지 시나리오 (데이터셋 직접 생성):
    정상 4종:
      - 일반 웹 브라우징
      - 파일 다운로드
      - 영상 스트리밍
      - 다중 탭 사용

    이상 5종:
      - CPU 스파이크 (크립토마이닝)
      - 메모리 릭 (악성 스크립트)
      - 네트워크 플러드 (DDoS/C2)
      - 디스크 과다 쓰기 (랜섬웨어)
      - 복합 이상 (여러 지표 동시 이상)
    """
    # ──────────────────────────────────────────
    # TODO: 차인택 — 이상 탐지 모델 결과 반환
    # ──────────────────────────────────────────

    # 더미 응답 (이상 없음)
    return []


# ══════════════════════════════════════════════
# 엔드포인트 3: 샌드박스 정책 결정
# Gateway /api/aiops/sandbox-policy/{id} 에서 호출
# ══════════════════════════════════════════════

class SandboxPolicyRequest(BaseModel):
    sandbox_id: str

class SandboxPolicyResponse(BaseModel):
    """샌드박스 라이프사이클 정책."""
    sandbox_id: str
    max_lifetime_minutes: int   # 최대 수명 (분)
    action: str                 # "extend" | "terminate" | "scale_down" | "maintain"
    reason: str                 # LLM이 생성한 사유
    pool_size_recommendation: int | None = None  # Pool 크기 조정 추천

@app.post("/sandbox-policy", response_model=SandboxPolicyResponse)
async def sandbox_policy(request: SandboxPolicyRequest):
    """
    샌드박스 라이프사이클 정책 결정.

    === 차인택: 여기를 Ollama RAG 기반 자동 의사결정으로 교체 ===

    의사결정 흐름:
    1. 현재 리소스 상태 수집 (Prometheus)
    2. 이상 탐지 모델 실행
    3. ChromaDB에서 유사 상황의 과거 조치 이력 검색 (RAG)
    4. Ollama LLM에 컨텍스트 전달 → 조치 결정

    조치 종류:
    - extend: 리소스 여유 → 샌드박스 수명 연장
    - terminate: 리소스 부족 또는 이상 감지 → 즉시 종료
    - scale_down: 리소스 할당 축소 (CPU/메모리 제한 변경)
    - maintain: 현재 상태 유지

    Ollama 호출 예시:
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "prompt": f"현재 CPU {cpu}%, 메모리 {mem}%. 과거 유사 사례: {rag_results}. 조치를 결정하세요.",
    })
    """
    # ──────────────────────────────────────────
    # TODO: 차인택 — RAG + LLM 의사결정 로직
    # ──────────────────────────────────────────

    # 더미 응답
    return SandboxPolicyResponse(
        sandbox_id=request.sandbox_id,
        max_lifetime_minutes=30,
        action="maintain",
        reason="리소스 상태 정상 — 현재 설정 유지 (더미 응답)",
        pool_size_recommendation=None,
    )


# ══════════════════════════════════════════════
# 엔드포인트 4: Pool 자동 조정 (AIOps 핵심)
# 이 엔드포인트는 내부 백그라운드 태스크에서 주기적으로 실행
# ══════════════════════════════════════════════

@app.post("/auto-adjust")
async def auto_adjust_pool():
    """
    리소스 상태를 분석하고 Gateway의 Pool 크기를 자동 조정.

    === 차인택: 이 로직이 AIOps의 핵심 ===

    흐름:
    1. /status 호출 → 현재 리소스 상태
    2. /anomalies 호출 → 이상 탐지 결과
    3. 결과 기반으로 적정 Pool 크기 결정
    4. Gateway /api/sandbox/pool/config PUT 호출

    예시 규칙 (LLM이 결정하도록 발전):
    - CPU > 80% → Pool 크기 줄임
    - CPU < 30% & 메모리 < 50% → Pool 크기 늘림
    - 이상 감지 → 해당 컨테이너 종료 요청
    """
    # ──────────────────────────────────────────
    # TODO: 차인택 — 자동 조정 로직
    # ──────────────────────────────────────────

    # 더미: 현재 상태 확인 후 Gateway에 Pool 조정 요청
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 예시: Pool 크기를 5로 유지
            response = await client.put(
                f"{GATEWAY_URL}/api/sandbox/pool/config",
                json={"pool_size": 5},
                headers={"Authorization": "Bearer ADMIN_TOKEN_HERE"},  # TODO: 서비스 간 인증
            )
            return {
                "status": "adjusted",
                "new_pool_size": 5,
                "reason": "더미 — 기본값 유지",
            }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


# ══════════════════════════════════════════════
# Prometheus 메트릭 수집 헬퍼 (차인택 참고용)
# ══════════════════════════════════════════════

async def fetch_prometheus_metrics() -> dict:
    """
    Prometheus에서 컨테이너 메트릭을 수집하는 헬퍼 함수.

    === 차인택: 이 함수를 완성해서 사용 ===

    Prometheus API: http://localhost:9090/api/v1/query?query=...

    유용한 PromQL 쿼리:
    - CPU 사용률:
      rate(container_cpu_usage_seconds_total{name=~"secureops.*"}[1m]) * 100

    - 메모리 사용량:
      container_memory_usage_bytes{name=~"secureops.*"}

    - 네트워크 수신:
      rate(container_network_receive_bytes_total{name=~"secureops.*"}[1m])

    - 네트워크 송신:
      rate(container_network_transmit_bytes_total{name=~"secureops.*"}[1m])
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # CPU 쿼리 예시
            response = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={
                    "query": 'rate(container_cpu_usage_seconds_total{name=~"secureops.*"}[1m]) * 100'
                },
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}
