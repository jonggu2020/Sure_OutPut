"""
데이터베이스 연결
================
SQLAlchemy async 세션 관리.
라우터/서비스에서 Depends(get_db)로 세션 주입.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """모든 DB 모델의 베이스 클래스."""
    pass


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """요청마다 DB 세션을 생성하고 종료."""
    async with async_session() as session:
        yield session
