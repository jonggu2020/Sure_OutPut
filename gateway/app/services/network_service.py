"""
네트워크 로그 분석 서비스
========================
2번 모델 서버와 통신.
"""

import httpx

from app.core.config import settings
from app.schemas.network import NetworkAnalysisRequest, NetworkAnalysisResponse


class NetworkService:

    def __init__(self):
        self.model_url = settings.MODEL_NETWORK_URL

    async def analyze(self, request: NetworkAnalysisRequest) -> NetworkAnalysisResponse:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.model_url}/predict",
                json=request.model_dump(),
            )
            response.raise_for_status()
            result = response.json()

        return NetworkAnalysisResponse(
            sandbox_id=request.sandbox_id,
            is_malicious=result.get("is_malicious", False),
            confidence=result.get("confidence", 0.0),
            threat_type=result.get("threat_type"),
            details=result.get("details"),
        )


network_service = NetworkService()
