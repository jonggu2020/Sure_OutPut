"""
AIOps 서비스
============
3번 모델 서버와 통신. 관리자 전용.
"""

import httpx

from app.core.config import settings


class AIOpsService:

    def __init__(self):
        self.model_url = settings.MODEL_AIOPS_URL

    async def get_resource_status(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.model_url}/status")
            response.raise_for_status()
            return response.json()

    async def get_sandbox_policy(self, sandbox_id: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.model_url}/sandbox-policy",
                json={"sandbox_id": sandbox_id},
            )
            response.raise_for_status()
            return response.json()

    async def get_anomalies(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.model_url}/anomalies")
            response.raise_for_status()
            return response.json()


aiops_service = AIOpsService()
