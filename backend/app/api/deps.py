"""Shared API dependencies (authentication)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.db.base import User

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_ERROR
    payload = decode_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise _CREDENTIALS_ERROR
    user = await request.app.state.repos.users.get_by_id(payload["sub"])
    if user is None:
        raise _CREDENTIALS_ERROR
    return user
