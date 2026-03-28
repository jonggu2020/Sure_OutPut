"""
피싱 탐지 라우터
===============
HTTP 요청/응답만 처리. 로직은 phishing_service에 위임.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.security import get_current_user
from app.schemas.phishing import (
    PhishingCheckRequest,
    PhishingCheckResponse,
    SandboxCreateRequest,
    SandboxCreateResponse,
)
from app.services.phishing_service import phishing_service

router = APIRouter()


@router.post("/check", response_model=PhishingCheckResponse)
async def check_url(
    request: PhishingCheckRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    URL 1차 피싱 검사.
    인터셉터가 이 엔드포인트로 URL을 전송.
    """
    return await phishing_service.check_url(request)


@router.post("/sandbox", response_model=SandboxCreateResponse)
async def create_sandbox(
    request: SandboxCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    샌드박스 모드 실행.
    Docker 컨테이너 생성 → noVNC 접속 URL 반환.
    """
    return await phishing_service.create_sandbox(request)


@router.websocket("/ws/sandbox/{sandbox_id}")
async def sandbox_realtime(websocket: WebSocket, sandbox_id: str):
    """
    샌드박스 실시간 감시 WebSocket.
    샌드박스 내 이벤트(클릭, 페이지 이동) 발생 시:
    1. Model 1 재검사
    2. Model 2 네트워크 분석
    3. 결과를 클라이언트에 실시간 push
    """
    await websocket.accept()

    try:
        while True:
            # 샌드박스 컨테이너에서 이벤트 수신
            data = await websocket.receive_json()

            event_type = data.get("event_type")  # "click", "navigate", "form_submit"
            event_url = data.get("url", "")

            # 1번 모델: HTML 재검사
            phishing_result = None
            if event_url:
                phishing_result = await phishing_service.check_url(
                    PhishingCheckRequest(url=event_url)
                )

            # TODO: 2번 모델 네트워크 분석도 여기서 호출

            # 결과를 클라이언트에 실시간 전송
            await websocket.send_json({
                "sandbox_id": sandbox_id,
                "event_type": event_type,
                "phishing": phishing_result.model_dump() if phishing_result else None,
                "network": None,  # TODO: 2번 모델 결과
            })

    except WebSocketDisconnect:
        # TODO: 연결 끊김 → 타임아웃 카운트 시작 (AIOps가 관리)
        pass
