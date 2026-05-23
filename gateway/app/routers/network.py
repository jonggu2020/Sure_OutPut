"""
네트워크 분석 라우터 (WebSocket 방식)
=====================================
Model 2가 WebSocket으로 Gateway에 연결.
샌드박스 network_agent가 보내는 데이터를 Model 2에 전달하여 추론.
"""

import asyncio
import json
import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter()
log = logging.getLogger("network")


# ── WebSocket 연결 관리 ────────────────────────────────────────────

class Model2Connection:
    """Model 2 WebSocket 연결 및 작업 큐 관리."""

    def __init__(self):
        self.websocket: WebSocket | None = None
        self.connected = False
        self._pending: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket):
        async with self._lock:
            self.websocket = ws
            self.connected = True
            log.info("✅ Model 2 연결됨")

    async def unregister(self):
        async with self._lock:
            self.websocket = None
            self.connected = False
            for task_id, future in self._pending.items():
                if not future.done():
                    future.set_exception(Exception("Model 2 연결 끊김"))
            self._pending.clear()
            log.warning("❌ Model 2 연결 해제")

    async def send_task(self, task_type: str, payload: dict, timeout: float = 30.0) -> dict:
        if not self.connected or not self.websocket:
            raise HTTPException(
                status_code=503,
                detail="Model 2가 연결되어 있지 않습니다.",
            )

        task_id = str(uuid.uuid4())
        message = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
        }

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[task_id] = future

        try:
            await self.websocket.send_json(message)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(task_id, None)
            raise HTTPException(
                status_code=504,
                detail=f"Model 2 응답 시간 초과 ({timeout}초)",
            )
        except Exception as e:
            self._pending.pop(task_id, None)
            raise HTTPException(status_code=502, detail=str(e))

    async def receive_result(self, data: dict):
        task_id = data.get("task_id")
        if task_id and task_id in self._pending:
            future = self._pending.pop(task_id)
            if not future.done():
                future.set_result(data.get("result", {}))


# 싱글톤
model2 = Model2Connection()


# ── WebSocket 엔드포인트 (Model 2가 여기로 연결) ───────────────────

@router.websocket("/ws")
async def model2_websocket(ws: WebSocket):
    """Model 2 전용 WebSocket 엔드포인트."""
    await ws.accept()
    await model2.register(ws)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            await model2.receive_result(data)
    except WebSocketDisconnect:
        log.info("Model 2 WebSocket 정상 종료")
    except Exception as e:
        log.error("Model 2 WebSocket 에러: %s", e)
    finally:
        await model2.unregister()


# ── 요청/응답 스키마 ───────────────────────────────────────────────

class NetworkPredictRequest(BaseModel):
    sandbox_id: str
    log_data: dict

class NetworkPredictResponse(BaseModel):
    is_malicious: bool
    confidence: float
    threat_type: str | None = None
    details: dict | None = None


# ── REST 엔드포인트 ────────────────────────────────────────────────

@router.get("/health")
async def network_health():
    """Model 2 연결 상태 확인."""
    return {
        "status": "connected" if model2.connected else "disconnected",
        "model_connected": model2.connected,
    }


@router.post("/predict", response_model=NetworkPredictResponse)
async def network_predict(
    request: NetworkPredictRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """
    네트워크 로그 악성 탐지 — WebSocket으로 Model 2에 전달.
    샌드박스 network_agent → Gateway → Model 2 → 결과 반환.
    """
    result = await model2.send_task(
        task_type="predict",
        payload={
            "sandbox_id": request.sandbox_id,
            "log_data": request.log_data,
        },
    )
    return result


@router.get("/model-info")
async def network_model_info(
    user: Annotated[dict, Depends(get_current_user)],
):
    """Model 2 모델 메타데이터."""
    return await model2.send_task(
        task_type="model_info",
        payload={},
    )