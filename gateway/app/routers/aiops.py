"""
AIOps 라우터 (WebSocket 방식)
==============================
관리자 전용. Model 3가 WebSocket으로 Gateway에 연결.
Gateway는 관리자 요청이 오면 WebSocket을 통해 Model 3에 작업을 전송.

흐름:
  1. Model 3 (별도 PC) → Gateway WebSocket 연결 (/api/aiops/ws)
  2. 관리자가 /api/aiops/predict 호출
  3. Gateway → WebSocket으로 Model 3에 작업 전송
  4. Model 3 → 추론 결과를 WebSocket으로 반환
  5. Gateway → 관리자에게 응답

별도 PC에서 포트포워딩 불필요 — Model 3이 먼저 연결하니까.
"""

import asyncio
import json
import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.core.security import require_admin

router = APIRouter()
log = logging.getLogger("aiops")


# ── WebSocket 연결 관리 ────────────────────────────────────────────

class Model3Connection:
    """Model 3 WebSocket 연결 및 작업 큐 관리."""

    def __init__(self):
        self.websocket: WebSocket | None = None
        self.connected = False
        self._pending: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket):
        """Model 3가 연결되면 등록."""
        async with self._lock:
            self.websocket = ws
            self.connected = True
            log.info("✅ Model 3 연결됨")

    async def unregister(self):
        """연결 해제."""
        async with self._lock:
            self.websocket = None
            self.connected = False
            # 대기 중인 작업 전부 에러 처리
            for task_id, future in self._pending.items():
                if not future.done():
                    future.set_exception(
                        Exception("Model 3 연결 끊김")
                    )
            self._pending.clear()
            log.warning("❌ Model 3 연결 해제")

    async def send_task(self, task_type: str, payload: dict, timeout: float = 30.0) -> dict:
        """Model 3에 작업을 전송하고 결과를 대기."""
        if not self.connected or not self.websocket:
            raise HTTPException(
                status_code=503,
                detail="Model 3가 연결되어 있지 않습니다.",
            )

        task_id = str(uuid.uuid4())
        message = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
        }

        # Future 생성 — 결과가 올 때까지 대기할 객체
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
                detail=f"Model 3 응답 시간 초과 ({timeout}초)",
            )
        except Exception as e:
            self._pending.pop(task_id, None)
            raise HTTPException(status_code=502, detail=str(e))

    async def receive_result(self, data: dict):
        """Model 3로부터 결과를 받아 대기 중인 Future에 전달."""
        task_id = data.get("task_id")
        if task_id and task_id in self._pending:
            future = self._pending.pop(task_id)
            if not future.done():
                future.set_result(data.get("result", {}))


# 싱글톤 인스턴스
model3 = Model3Connection()


# ── WebSocket 엔드포인트 (Model 3가 여기로 연결) ───────────────────

@router.websocket("/ws")
async def model3_websocket(ws: WebSocket):
    """
    Model 3 전용 WebSocket 엔드포인트.
    Model 3이 시작되면 이 엔드포인트에 연결을 유지.
    """
    await ws.accept()
    await model3.register(ws)

    try:
        while True:
            # Model 3로부터 결과 수신 대기
            raw = await ws.receive_text()
            data = json.loads(raw)
            await model3.receive_result(data)
    except WebSocketDisconnect:
        log.info("Model 3 WebSocket 정상 종료")
    except Exception as e:
        log.error("Model 3 WebSocket 에러: %s", e)
    finally:
        await model3.unregister()


# ── 요청/응답 스키마 ───────────────────────────────────────────────

class PredictRequest(BaseModel):
    features: dict[str, float]
    threshold_policy: str = "best_f1"

class BatchPredictRequest(BaseModel):
    windows: list[dict[str, float]]
    threshold_policy: str = "best_f1"


# ── REST 엔드포인트 (관리자 → Gateway → Model 3) ──────────────────

@router.get("/health")
async def aiops_health(
    admin: Annotated[dict, Depends(require_admin)],
):
    """Model 3 연결 상태 확인."""
    return {
        "status": "connected" if model3.connected else "disconnected",
        "model_connected": model3.connected,
    }


@router.post("/predict")
async def aiops_predict(
    request: PredictRequest,
    admin: Annotated[dict, Depends(require_admin)],
):
    """단일 윈도우 이상 탐지 — WebSocket으로 Model 3에 전달."""
    return await model3.send_task(
        task_type="predict",
        payload={
            "features": request.features,
            "threshold_policy": request.threshold_policy,
        },
    )


@router.post("/predict/batch")
async def aiops_predict_batch(
    request: BatchPredictRequest,
    admin: Annotated[dict, Depends(require_admin)],
):
    """다중 윈도우 일괄 이상 탐지."""
    return await model3.send_task(
        task_type="predict_batch",
        payload={
            "windows": request.windows,
            "threshold_policy": request.threshold_policy,
        },
        timeout=60.0,
    )


@router.get("/model-info")
async def aiops_model_info(
    admin: Annotated[dict, Depends(require_admin)],
):
    """Model 3 모델 메타데이터 조회."""
    return await model3.send_task(
        task_type="model_info",
        payload={},
    )