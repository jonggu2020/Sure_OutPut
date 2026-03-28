"""
샌드박스 라우터
==============
일반 사용자: 샌드박스 할당/반환.
관리자: Pool 관리, 리소스 모니터링, 컨테이너 강제 삭제.
내부: 샌드박스 네트워크 에이전트로부터 데이터 수신.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import httpx

from app.core.config import settings
from app.core.security import get_current_user, require_admin
from app.schemas.sandbox import (
    SandboxAssignRequest,
    SandboxAssignResponse,
    PoolStatus,
    PoolConfigUpdate,
    ServerResources,
)
from app.services.sandbox_service import sandbox_service

router = APIRouter()


# ── 일반 사용자 ──

@router.post("/assign", response_model=SandboxAssignResponse)
async def assign_sandbox(
    request: SandboxAssignRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """샌드박스 컨테이너 할당."""
    user_id = current_user.get("sub", "unknown")
    result = await sandbox_service.assign_sandbox(user_id, request.url)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="사용 가능한 샌드박스가 없습니다. 잠시 후 다시 시도해주세요.",
        )

    return result


@router.post("/release/{container_id}")
async def release_sandbox(
    container_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """샌드박스 세션 종료 → 컨테이너 삭제 → Pool 자동 보충."""
    await sandbox_service.release_sandbox(container_id)
    return {"status": "released", "container_id": container_id}


# ── 네트워크 에이전트 데이터 수신 (샌드박스 내부 → Gateway → 2번 모델) ──

@router.post("/network-data")
async def receive_network_data(data: dict):
    """
    샌드박스 네트워크 에이전트가 수집한 트래픽 데이터 수신.
    2번 모델(네트워크 분석)로 포워딩하고 결과를 반환.

    이 엔드포인트는 샌드박스 컨테이너 내부에서 호출됨 (인증 불필요).

    입력 (network_agent.py에서 전송):
    {
        "sandbox_id": "secureops-sandbox-6081",
        "timestamp": 1234567890.0,
        "packet_count": 150,
        "bytes_sent": 24000,
        "bytes_received": 180000,
        "request_frequency": 12.5,
        "unique_domains": 5,
        "dns_query_count": 3,
        "avg_packet_size": 1360.0,
        "protocol_distribution": {"TCP": 0.85, "UDP": 0.15},
        "connection_count": 8,
        "suspicious_ports": 0
    }
    """
    sandbox_id = data.get("sandbox_id", "unknown")

    # 2번 모델 서버로 포워딩
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.MODEL_NETWORK_URL}/predict",
                json={
                    "sandbox_id": sandbox_id,
                    "log_data": data,
                },
            )
            response.raise_for_status()
            result = response.json()

        return {
            "sandbox_id": sandbox_id,
            "is_malicious": result.get("is_malicious", False),
            "confidence": result.get("confidence", 0.0),
            "threat_type": result.get("threat_type"),
            "details": result.get("details"),
        }

    except httpx.ConnectError:
        # 2번 모델 서버가 없을 때 (아직 서용준이 구현 안 했을 때)
        return {
            "sandbox_id": sandbox_id,
            "is_malicious": False,
            "confidence": 0.0,
            "threat_type": None,
            "details": {"note": "네트워크 분석 모델 서버 미연결"},
        }
    except Exception as e:
        return {
            "sandbox_id": sandbox_id,
            "is_malicious": False,
            "confidence": 0.0,
            "threat_type": None,
            "details": {"error": str(e)},
        }


# ── 관리자 전용 ──

@router.get("/pool", response_model=PoolStatus)
async def get_pool_status(
    admin: Annotated[dict, Depends(require_admin)],
):
    """Pool 상태 조회."""
    return sandbox_service.get_pool_status()


@router.put("/pool/config")
async def update_pool_config(
    config: PoolConfigUpdate,
    admin: Annotated[dict, Depends(require_admin)],
):
    """Pool 설정 변경."""
    await sandbox_service.update_pool_config(config)
    return {
        "status": "updated",
        "new_config": {
            "pool_size": config.pool_size,
            "cpu_limit": config.default_cpu_limit,
            "memory_limit": config.default_memory_limit,
        },
    }


@router.delete("/container/{container_id}")
async def force_remove_container(
    container_id: str,
    admin: Annotated[dict, Depends(require_admin)],
):
    """관리자가 특정 컨테이너 강제 삭제."""
    success = await sandbox_service.force_remove_container(container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 컨테이너를 찾을 수 없습니다.",
        )
    return {"status": "removed", "container_id": container_id}


@router.get("/resources", response_model=ServerResources)
async def get_server_resources(
    admin: Annotated[dict, Depends(require_admin)],
):
    """서버 PC 리소스 상태."""
    return sandbox_service.get_server_resources()
