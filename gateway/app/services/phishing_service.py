"""
피싱 탐지 서비스
===============
라우터에서 호출. 모델 서버와의 HTTP 통신을 담당.
라우터에는 비즈니스 로직을 넣지 않음 — 여기서 처리.
"""

import httpx

from app.core.config import settings
from app.schemas.phishing import (
    PhishingCheckRequest,
    PhishingCheckResponse,
    SandboxCreateRequest,
    SandboxCreateResponse,
)


class PhishingService:
    """1번 모델(HTML 피싱 탐지) 서비스."""

    def __init__(self):
        self.model_url = settings.MODEL_PHISHING_URL

    async def check_url(self, request: PhishingCheckRequest) -> PhishingCheckResponse:
        """
        URL 1차 피싱 검사.
        모델 서버(model-phishing)에 HTTP 요청을 보내고 결과를 반환.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.model_url}/predict",
                json={"url": str(request.url)},
            )
            response.raise_for_status()
            result = response.json()

        confidence = result.get("confidence", 0.0)
        is_phishing = result.get("is_phishing", False)

        return PhishingCheckResponse(
            url=str(request.url),
            is_phishing=is_phishing,
            confidence=confidence,
            risk_level=self._calculate_risk_level(confidence, is_phishing),
            details=result.get("details"),
        )

    async def create_sandbox(self, request: SandboxCreateRequest) -> SandboxCreateResponse:
        """
        샌드박스 Docker 컨테이너 생성.
        TODO: Docker SDK로 컨테이너 생성 + noVNC 연결 설정.
        """
        return SandboxCreateResponse(
            sandbox_id="sandbox-placeholder",
            novnc_url="http://localhost:6080/vnc.html",
            expires_at=None,
        )

    @staticmethod
    def _calculate_risk_level(confidence: float, is_phishing: bool) -> str:
        """신뢰도와 탐지 결과를 기반으로 위험도 레벨 결정."""
        if not is_phishing:
            return "safe"
        if confidence >= 0.8:
            return "danger"
        return "warning"


phishing_service = PhishingService()
