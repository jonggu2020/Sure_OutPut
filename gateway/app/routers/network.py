"""
네트워크 로그 분석 라우터
========================
샌드박스 내 네트워크 트래픽 분석 요청 처리.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.network import NetworkAnalysisRequest, NetworkAnalysisResponse
from app.services.network_service import network_service

router = APIRouter()


@router.post("/analyze", response_model=NetworkAnalysisResponse)
async def analyze_network(
    request: NetworkAnalysisRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    네트워크 로그 분석.
    샌드박스에서 수집된 네트워크 데이터를 2번 모델로 전송.
    """
    return await network_service.analyze(request)
