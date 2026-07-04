"""Health and system information."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    pipeline = request.app.state.pipeline
    repos = request.app.state.repos
    return {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
        "providers": {
            **pipeline.provider_info(),
            "database": repos.kind,
        },
    }
