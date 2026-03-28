"""
AIOps 라우터
============
관리자 전용. require_admin 의존성으로 권한 체크.
Docker 리소스 모니터링 + 이상 탐지 결과 조회.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.services.aiops_service import aiops_service

router = APIRouter()


@router.get("/status")
async def get_resource_status(
    admin: Annotated[dict, Depends(require_admin)],
):
    """전체 Docker 컨테이너 리소스 상태 조회."""
    return await aiops_service.get_resource_status()


@router.get("/anomalies")
async def get_anomalies(
    admin: Annotated[dict, Depends(require_admin)],
):
    """현재 감지된 리소스 이상 목록."""
    return await aiops_service.get_anomalies()


@router.get("/sandbox-policy/{sandbox_id}")
async def get_sandbox_policy(
    sandbox_id: str,
    admin: Annotated[dict, Depends(require_admin)],
):
    """
    특정 샌드박스의 AIOps 정책 조회.
    리소스 여유 → 수명 연장, 부족 → 조기 종료 등.
    """
    return await aiops_service.get_sandbox_policy(sandbox_id)
