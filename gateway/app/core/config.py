"""
설정 관리
========
환경변수를 Pydantic Settings로 관리.
.env 파일 또는 docker-compose 환경변수에서 자동 로드.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 서버 ──
    APP_NAME: str = "SecureOps Gateway"
    DEBUG: bool = False

    # ── DB ──
    DATABASE_URL: str = "postgresql+asyncpg://secureops:secureops@localhost:5432/secureops"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── 모델 서버 URL (Docker 내부 통신) ──
    MODEL_PHISHING_URL: str = "http://model-phishing:8001"
    MODEL_NETWORK_URL: str = "http://model-network:8002"
    MODEL_AIOPS_URL: str = "http://model-aiops:8003"

    # ── CORS ──
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Sandbox ──
    SANDBOX_TIMEOUT_MINUTES: int = 5
    SANDBOX_MAX_PER_USER: int = 1

    class Config:
        env_file = ".env"


settings = Settings()
