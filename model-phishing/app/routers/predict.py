"""
추론 라우터
==========
Gateway가 POST /predict 로 URL을 보내면 피싱 여부 판정.
실제 추론 로직은 services/predict.py에 위임.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.predict import prediction_service

router = APIRouter()


class PredictRequest(BaseModel):
    url: str


class PredictResponse(BaseModel):
    is_phishing: bool
    confidence: float
    details: dict | None = None


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """URL 피싱 탐지 추론."""
    return await prediction_service.predict(request.url)
