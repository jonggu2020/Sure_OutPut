"""
Gateway API 클라이언트
=====================
인터셉터 → Gateway 서버 통신 담당.
"""

import httpx


class GatewayClient:
    """Gateway 서버와의 HTTP 통신."""

    def __init__(self, base_url: str = "http://localhost:8000", token: str = ""):
        self.base_url = base_url
        self.token = token

    async def check_url(self, url: str) -> dict:
        """URL 피싱 검사 요청."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/phishing/check",
                json={"url": url},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            return response.json()

    async def login(self, username: str, password: str) -> str:
        """로그인 → 토큰 발급."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            data = response.json()
            self.token = data["access_token"]
            return self.token


gateway_client = GatewayClient()
