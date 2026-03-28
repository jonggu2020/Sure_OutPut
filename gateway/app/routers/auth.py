"""
인증 라우터.
로그인/토큰 발급을 처리합니다.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.schemas.user import UserLogin, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """
    로그인하여 JWT 토큰을 발급합니다.
    TODO: 실제 DB 사용자 조회 및 비밀번호 검증 구현
    """
    # 프로토타입: 하드코딩된 사용자로 테스트
    mock_users = {
        "admin": {"password": "admin123", "role": "admin", "user_id": "1"},
        "user": {"password": "user123", "role": "user", "user_id": "2"},
    }

    user = mock_users.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        user_id=user["user_id"],
        role=user["role"],
    )
    return TokenResponse(access_token=token)
