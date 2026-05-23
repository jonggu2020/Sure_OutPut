"""
SecureOps Gateway Server
========================
모든 클라이언트 요청의 진입점.
라우터로 분기하고, 비즈니스 로직은 services 레이어에 위임.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, health, phishing, network, aiops, sandbox
from app.services.sandbox_pool import sandbox_pool
from app.services.metrics_collector import metrics_collector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 로직."""
    # 시작: 샌드박스 Pool 초기화
    await sandbox_pool.initialize()
    # 시작: 메트릭 수집 백그라운드 태스크
    await metrics_collector.start()
    yield
    # 종료: 메트릭 수집 중지
    await metrics_collector.stop()
    # 종료: 샌드박스 Pool 정리
    await sandbox_pool.shutdown()


app = FastAPI(
    title="SecureOps Gateway",
    description="Docker 기반 AI 피싱탐지 자동화 AIOps 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ──────────────────────────────────
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(phishing.router, prefix="/api/phishing", tags=["Phishing"])
app.include_router(network.router, prefix="/api/network", tags=["Network"])
app.include_router(aiops.router, prefix="/api/aiops", tags=["AIOps"])
app.include_router(sandbox.router, prefix="/api/sandbox", tags=["Sandbox"])