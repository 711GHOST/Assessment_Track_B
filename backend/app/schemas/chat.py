"""Request/response models for RAG chat."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list restricting retrieval to specific documents.",
    )


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


class StatsResponse(BaseModel):
    document_count: int
    total_chunks: int
    total_chars: int
    query_count: int
    avg_latency_ms: int
    avg_confidence: int
    helpful_count: int


class Citation(BaseModel):
    index: int
    document_id: str
    document_title: str
    chunk_index: int
    snippet: str
    score: float


class ChatEntryOut(BaseModel):
    id: str
    question: str
    answer: str
    mode: str
    citations: list[Citation]
    latency_ms: int
    confidence: int = 0
    feedback: str | None = None
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    created_at: datetime
