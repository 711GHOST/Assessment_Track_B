"""Authentication routes: register, login, refresh (with rotation), logout, me."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import RefreshTokenRecord, User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
    )


async def _issue_tokens(user: User, repos) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    await repos.refresh_tokens.add(
        RefreshTokenRecord(jti=jti, user_id=user.id, expires_at=expires_at)
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=_user_out(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", limit=10, window_seconds=60))],
)
async def register(payload: RegisterRequest, request: Request) -> TokenResponse:
    repos = request.app.state.repos
    existing = await repos.users.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = User(
        id=uuid.uuid4().hex,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    await repos.users.create(user)
    return await _issue_tokens(user, repos)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("login", limit=10, window_seconds=60))],
)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    repos = request.app.state.repos
    user = await repos.users.get_by_email(payload.email)
    # Same error for unknown email and wrong password: no account enumeration.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    return await _issue_tokens(user, repos)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("refresh", limit=30, window_seconds=60))],
)
async def refresh(payload: RefreshRequest, request: Request) -> TokenResponse:
    repos = request.app.state.repos
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    if claims is None or not await repos.refresh_tokens.is_active(claims["jti"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    user = await repos.users.get_by_id(claims["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    # Rotation: the used refresh token is revoked and a new pair is issued.
    await repos.refresh_tokens.revoke(claims["jti"])
    return await _issue_tokens(user, repos)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshRequest, request: Request) -> MessageResponse:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    if claims is not None:
        await request.app.state.repos.refresh_tokens.revoke(claims["jti"])
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)
