from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """JWT 토큰 검증 의존성 — 모든 보호된 API에 주입"""
    if not credentials:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("sub") != "dashboard":
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다")
