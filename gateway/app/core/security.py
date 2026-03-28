"""
인증/보안 유틸
=============
JWT 토큰 생성/검증, 역할(role) 기반 접근 제어.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

security_scheme = HTTPBearer()


def create_access_token(user_id: str, role: str = "user") -> str:
    """JWT 액세스 토큰 생성."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """JWT 토큰 디코딩. 실패 시 HTTPException 발생."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> dict:
    """현재 사용자 정보를 토큰에서 추출."""
    return decode_token(credentials.credentials)


def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """관리자 권한 확인. 3번 모델(AIOps) 라우터에서 사용."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user
