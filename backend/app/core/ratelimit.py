"""Tiny in-process sliding-window rate limiter.

Sufficient for a single-instance deployment (Render/Northflank free tier).
Swap for a Redis-backed limiter when scaling horizontally.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
            )
        hits.append(now)


def rate_limit(scope: str, limit: int, window_seconds: float):
    """FastAPI dependency limiting requests per client IP for a route group."""

    async def dependency(request: Request) -> None:
        limiter: SlidingWindowLimiter = request.app.state.limiter
        client = request.client.host if request.client else "anonymous"
        limiter.check(f"{scope}:{client}", limit, window_seconds)

    return dependency
