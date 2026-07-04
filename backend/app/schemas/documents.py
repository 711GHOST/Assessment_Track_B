"""Request/response models for document management."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=200_000)


class DocumentOut(BaseModel):
    id: str
    title: str
    char_count: int
    chunk_count: int
    created_at: datetime
