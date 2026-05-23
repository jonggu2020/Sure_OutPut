"""
헬스체크 라우터
==============
각 모델 서버 + 인프라의 상태를 확인.
대시보드 신호등(녹/주황/적) 데이터 제공.
"""

import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()

# Model 1만 HTTP 헬스체크 (같은 서버에서 실행)
MODEL_SERVERS = [
    {"name": "phishing", "url": settings.MODEL_PHISHING_URL, "admin_only": False},
    # network, aiops는 WebSocket 방식 → 별도 처리
]


@router.get("")
async def health_check():
    """전체 시스템 상태. 대시보드 상태 표시에 사용."""
    statuses = {}

    # Model 1: HTTP 헬스체크
    for server in MODEL_SERVERS:
        statuses[server["name"]] = await _check_server(
            server["url"],
            admin_only=server["admin_only"],
        )

    # Model 2 (Network): WebSocket 연결 상태
    statuses["network"] = _check_network_ws()

    # Model 3 (AIOps): WebSocket 연결 상태
    statuses["aiops"] = _check_aiops_ws()

    return {
        "gateway": "running",
        "models": statuses,
    }


async def _check_server(url: str, admin_only: bool) -> dict:
    """개별 서버 상태 확인 → 녹/주황/적 판정."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")

        if response.status_code == 200:
            status = "green"
        else:
            status = "orange"

    except httpx.ConnectError:
        status = "red"
    except httpx.TimeoutException:
        status = "orange"
    except Exception:
        status = "red"

    return {
        "status": status,
        "admin_only": admin_only,
    }


def _check_network_ws() -> dict:
    """Model 2 (Network) WebSocket 연결 상태 확인."""
    try:
        from app.routers.network import model2
        status = "green" if model2.connected else "red"
    except Exception:
        status = "red"

    return {
        "status": status,
        "admin_only": False,
    }


def _check_aiops_ws() -> dict:
    """Model 3 (AIOps) WebSocket 연결 상태 확인."""
    try:
        from app.routers.aiops import model3
        status = "green" if model3.connected else "red"
    except Exception:
        status = "red"

    return {
        "status": status,
        "admin_only": True,
    }