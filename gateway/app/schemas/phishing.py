"""
피싱 탐지 스키마
===============
요청/응답 데이터 형태를 Pydantic 모델로 정의.
라우터와 서비스 모두 이 스키마를 통해서만 데이터를 주고받음.
"""

from pydantic import BaseModel, HttpUrl


class PhishingCheckRequest(BaseModel):
    """사용자가 검사를 요청할 때 보내는 데이터."""
    url: HttpUrl


class PhishingCheckResponse(BaseModel):
    """1차 검사 결과."""
    url: str
    is_phishing: bool
    confidence: float          # 0.0 ~ 1.0
    risk_level: str            # "safe" | "warning" | "danger"
    details: dict | None = None


class SandboxCreateRequest(BaseModel):
    """샌드박스 생성 요청."""
    url: HttpUrl


class SandboxCreateResponse(BaseModel):
    """샌드박스 생성 결과 — noVNC 접속 정보 포함."""
    sandbox_id: str
    novnc_url: str
    expires_at: str | None = None  # AIOps가 동적으로 설정
