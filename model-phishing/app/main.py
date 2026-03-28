"""
Model 1 Server: HTML 피싱 탐지
==============================
독립 FastAPI 서버. Gateway에서 HTTP로 호출.
/predict → URL 피싱 여부 판정
/health  → 상태 확인 (대시보드 신호등)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 ML 모델 로딩."""
    # TODO: model.pkl 로딩 → app.state.model에 저장
    yield


app = FastAPI(
    title="SecureOps - Phishing Detection Model",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(predict.router)


@app.get("/health")
async def health():
    """Gateway 헬스체크용."""
    return {"status": "ok", "model": "phishing-html"}
