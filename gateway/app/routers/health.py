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

MODEL_SERVERS = [
    {"name": "phishing", "url": settings.MODEL_PHISHING_URL, "admin_only": False},
    {"name": "network", "url": settings.MODEL_NETWORK_URL, "admin_only": False},
    {"name": "aiops", "url": settings.MODEL_AIOPS_URL, "admin_only": True},
]


@router.get("")
async def health_check():
    """전체 시스템 상태. 대시보드 상태 표시에 사용."""
    statuses = {}

    for server in MODEL_SERVERS:
        statuses[server["name"]] = await _check_server(
            server["url"],
            admin_only=server["admin_only"],
        )

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
