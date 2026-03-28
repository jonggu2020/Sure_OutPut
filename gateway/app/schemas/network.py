"""
네트워크 로그 분석 스키마
"""

from pydantic import BaseModel


class NetworkAnalysisRequest(BaseModel):
    sandbox_id: str
    log_data: dict


class NetworkAnalysisResponse(BaseModel):
    sandbox_id: str
    is_malicious: bool
    confidence: float
    threat_type: str | None = None
    details: dict | None = None
