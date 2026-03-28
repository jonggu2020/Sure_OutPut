"""
Model 2 Server: 네트워크 로그 분석
==================================
담당: 서용준
독립 FastAPI 서버. Gateway에서 HTTP로 호출.
CIC-Bell-DNS 2021 데이터셋 기반 XGBoost/LightGBM.

=== 서용준 작업 가이드 ===

이 서버는 샌드박스 컨테이너에서 자동 수집된 네트워크 트래픽 데이터를
받아서 악성 여부를 판별합니다.

데이터 흐름:
  [샌드박스 Docker] → network_agent.py가 5초마다 수집
  → [Gateway /api/sandbox/network-data] → 이 서버 /predict로 포워딩

해야 할 것:
  1. app/services/ 에 추론 로직 구현
  2. app/ml/ 에 학습된 모델 파일 배치
  3. /predict 엔드포인트에서 실제 모델 추론으로 교체
  4. 평가 지표: Recall, F1-Score, ROC-AUC
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="SecureOps - Network Log Analysis Model",
    version="0.1.0",
)


# ── 입력 스키마 (Gateway에서 이 형태로 전송됨) ──

class PredictRequest(BaseModel):
    sandbox_id: str
    log_data: dict
    """
    log_data 필드 상세 (network_agent.py에서 수집):
    {
        "sandbox_id": "secureops-sandbox-6081",   # 샌드박스 식별자
        "timestamp": 1234567890.0,                # 수집 시각 (Unix timestamp)
        "packet_count": 150,                      # 수집 기간 내 패킷 수
        "bytes_sent": 24000,                      # 송신 바이트
        "bytes_received": 180000,                 # 수신 바이트
        "request_frequency": 12.5,                # 초당 요청 수
        "unique_domains": 5,                      # 접속한 고유 도메인(IP) 수
        "dns_query_count": 3,                     # DNS 쿼리 수
        "avg_packet_size": 1360.0,                # 평균 패킷 크기 (bytes)
        "protocol_distribution": {                # 프로토콜별 비율
            "TCP": 0.85,
            "UDP": 0.15
        },
        "connection_count": 8,                    # 활성 연결 수
        "suspicious_ports": 0                     # 비표준 포트 접속 수 (80,443,53,8080,8443 외)
    }
    """


# ── 출력 스키마 (Gateway가 이 형태를 기대함) ──

class PredictResponse(BaseModel):
    is_malicious: bool       # 악성 여부
    confidence: float        # 0.0 ~ 1.0
    threat_type: str | None  # "phishing" | "malware" | "c2" | "data_exfil" | None
    details: dict | None     # 추가 정보 (feature importance 등)


@app.get("/health")
async def health():
    """Gateway 헬스체크용."""
    return {"status": "ok", "model": "network-log"}


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    네트워크 로그 기반 악성 트래픽 탐지.

    === 서용준: 여기를 실제 모델 추론으로 교체 ===

    참고할 피처 (log_data에서 추출):
    - packet_count, bytes_sent, bytes_received → 트래픽 볼륨
    - request_frequency → 요청 빈도 (높으면 DDoS/스캐닝 의심)
    - unique_domains → 다수 도메인 접속 (C2 통신 의심)
    - dns_query_count → DNS 터널링 탐지
    - avg_packet_size → 비정상 패킷 크기
    - suspicious_ports → 비표준 포트 사용 (백도어 의심)
    - protocol_distribution → TCP/UDP 비율 이상

    모델 후보: XGBoost, LightGBM (CIC-Bell-DNS 2021 학습)
    """
    log = request.log_data

    # ──────────────────────────────────────────
    # TODO: 서용준 — 아래를 실제 모델 추론으로 교체
    # ──────────────────────────────────────────
    # 예시:
    # features = extract_features(log)
    # prediction = model.predict(features)
    # probability = model.predict_proba(features)
    # ──────────────────────────────────────────

    # 더미 응답 (프로토타입)
    # suspicious_ports > 0 이면 의심으로 판단 (임시 규칙)
    suspicious = log.get("suspicious_ports", 0)
    high_frequency = log.get("request_frequency", 0) > 50

    if suspicious > 3 or high_frequency:
        return PredictResponse(
            is_malicious=True,
            confidence=0.75,
            threat_type="suspicious_activity",
            details={
                "reason": f"비표준 포트 {suspicious}개 감지" if suspicious > 3
                          else f"높은 요청 빈도 ({log.get('request_frequency', 0)}/초)",
                "note": "더미 규칙 기반 판단 — 실제 모델로 교체 필요",
            },
        )

    return PredictResponse(
        is_malicious=False,
        confidence=0.05,
        threat_type=None,
        details={
            "packet_count": log.get("packet_count", 0),
            "connection_count": log.get("connection_count", 0),
            "note": "더미 응답 — 실제 모델로 교체 필요",
        },
    )
