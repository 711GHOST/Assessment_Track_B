"""Workspace analytics for the dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.db.base import User
from app.schemas.chat import StatsResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def workspace_stats(
    request: Request, current_user: User = Depends(get_current_user)
) -> StatsResponse:
    repos = request.app.state.repos
    documents = await repos.documents.list_for_user(current_user.id)
    chat_stats = await repos.chats.stats(current_user.id)
    return StatsResponse(
        document_count=len(documents),
        total_chunks=sum(d.chunk_count for d in documents),
        total_chars=sum(d.char_count for d in documents),
        query_count=chat_stats["query_count"],
        avg_latency_ms=chat_stats["avg_latency_ms"],
        avg_confidence=chat_stats["avg_confidence"],
        helpful_count=chat_stats["helpful_count"],
    )
