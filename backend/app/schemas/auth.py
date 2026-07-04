"""Request/response models for authentication."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=80)
    # bcrypt operates on at most 72 bytes, hence the upper bound.
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one digit.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    message: str
