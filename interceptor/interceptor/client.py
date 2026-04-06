"""
Gateway API 클라이언트
=====================
인터셉터 → Gateway 서버 통신.
로그인, URL 검사, 샌드박스 할당.
"""

import json
import requests
from pathlib import Path


CONFIG_FILE = Path.home() / ".secureops" / "config.json"
DEFAULT_SERVER = "http://123.212.210.230:8000"
DEFAULT_DASHBOARD = "http://123.212.210.230:5173"


class GatewayClient:

    def __init__(self):
        self.base_url = DEFAULT_SERVER
        self.dashboard_url = DEFAULT_DASHBOARD
        self.token = ""
        self._load_config()

    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text())
                self.token = config.get("token", "")
                self.base_url = config.get("base_url", self.base_url)
                self.dashboard_url = config.get("dashboard_url", self.dashboard_url)
            except Exception:
                pass

    def save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({
            "token": self.token,
            "base_url": self.base_url,
            "dashboard_url": self.dashboard_url,
        }))

    def login(self, username: str, password: str) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                self.save_config()
                return True
        except Exception:
            pass
        return False

    def logout(self):
        self.token = ""
        self.save_config()

    def check_url(self, url: str) -> dict | None:
        if not self.token:
            return None
        try:
            r = requests.post(
                f"{self.base_url}/api/phishing/check",
                json={"url": url},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 401:
                self.token = ""
                self.save_config()
        except Exception:
            pass
        return None

    def assign_sandbox(self, url: str) -> dict | None:
        """샌드박스 컨테이너 할당 → noVNC URL 반환."""
        if not self.token:
            return None
        try:
            r = requests.post(
                f"{self.base_url}/api/sandbox/assign",
                json={"url": url},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def is_connected(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def is_logged_in(self) -> bool:
        """토큰이 유효한지 확인."""
        if not self.token:
            return False
        try:
            r = requests.get(
                f"{self.base_url}/api/health",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            return False


gateway_client = GatewayClient()
