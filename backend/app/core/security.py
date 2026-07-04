"""Password hashing (bcrypt) and JWT creation/verification."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"

# Generated once per process when JWT_SECRET is not configured. Fine for
# development; set JWT_SECRET in production so tokens survive restarts.
_EPHEMERAL_SECRET = secrets.token_urlsafe(48)


def _secret_key() -> str:
    return get_settings().jwt_secret or _EPHEMERAL_SECRET


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    settings = get_settings()
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM), expires_in


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at). The jti is persisted so refresh
    tokens can be revoked and rotated server-side."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_days)
    jti = uuid.uuid4().hex
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM), jti, expires_at


def decode_token(token: str, expected_type: str) -> dict | None:
    """Decode and validate a JWT; returns the payload or None."""
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type or "sub" not in payload:
        return None
    return payload
