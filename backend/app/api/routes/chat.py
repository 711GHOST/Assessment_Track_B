"""RAG chat routes: ask questions, suggestions, feedback, history."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.db.base import ChatEntry, User
from app.schemas.auth import MessageResponse
from app.schemas.chat import (
    ChatEntryOut,
    FeedbackRequest,
    QueryRequest,
    SuggestionsResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _to_out(entry: ChatEntry, token_estimate: int = 0, cost: float = 0.0) -> ChatEntryOut:
    return ChatEntryOut(
        id=entry.id,
        question=entry.question,
        answer=entry.answer,
        mode=entry.mode,
        citations=entry.citations,
        latency_ms=entry.latency_ms,
        confidence=entry.confidence,
        feedback=entry.feedback,
        token_estimate=token_estimate,
        cost_estimate_usd=cost,
        created_at=entry.created_at,
    )


@router.post(
    "/query",
    response_model=ChatEntryOut,
    dependencies=[Depends(rate_limit("query", limit=30, window_seconds=60))],
)
async def query(
    payload: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ChatEntryOut:
    pipeline = request.app.state.pipeline
    result = await run_in_threadpool(
        pipeline.query,
        current_user.id,
        payload.question.strip(),
        payload.top_k,
        payload.document_ids,
    )

    entry = ChatEntry(
        id=uuid.uuid4().hex,
        user_id=current_user.id,
        question=payload.question.strip(),
        answer=result.answer,
        mode=result.mode,
        citations=result.citations,
        latency_ms=result.latency_ms,
        confidence=result.confidence,
    )
    await request.app.state.repos.chats.add(entry)
    return _to_out(entry, result.token_estimate, result.cost_estimate_usd)


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(
    request: Request, current_user: User = Depends(get_current_user)
) -> SuggestionsResponse:
    pipeline = request.app.state.pipeline
    items = await run_in_threadpool(pipeline.suggest_questions, current_user.id, 4)
    return SuggestionsResponse(suggestions=items)


@router.post("/{entry_id}/feedback", response_model=MessageResponse)
async def feedback(
    entry_id: str,
    payload: FeedbackRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    updated = await request.app.state.repos.chats.set_feedback(
        current_user.id, entry_id, payload.rating
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    return MessageResponse(message="Thanks for the feedback.")


@router.get("/history", response_model=list[ChatEntryOut])
async def history(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChatEntryOut]:
    entries = await request.app.state.repos.chats.list_for_user(
        current_user.id, limit=limit
    )
    return [_to_out(e) for e in entries]


@router.delete("/history", response_model=MessageResponse)
async def clear_history(
    request: Request, current_user: User = Depends(get_current_user)
) -> MessageResponse:
    removed = await request.app.state.repos.chats.clear_for_user(current_user.id)
    return MessageResponse(message=f"Cleared {removed} messages.")
