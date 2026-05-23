"""
Model 1 Server: HTML 피싱 탐지
==============================
독립 FastAPI 서버. Gateway에서 HTTP로 호출.
/predict → URL 피싱 여부 판정
/health  → 상태 확인 (대시보드 신호등)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import predict
from app.services.predict import prediction_service

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 ML 모델 로딩."""
    prediction_service.load_model()
    yield


app = FastAPI(
    title="SecureOps - Phishing Detection Model",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(predict.router)


@app.get("/health")
async def health():
    """Gateway 헬스체크용."""
    loaded = prediction_service.model is not None
    return {
        "status": "ok" if loaded else "degraded",
        "model": "phishing-html",
        "model_loaded": loaded,
    }