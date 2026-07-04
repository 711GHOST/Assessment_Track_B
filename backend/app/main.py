"""Application factory and ASGI entrypoint.

Run locally:   uvicorn app.main:app --reload
In production: uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, documents, health, stats
from app.core.config import get_settings
from app.core.ratelimit import SlidingWindowLimiter
from app.db.factory import build_repositories
from app.rag.pipeline import build_pipeline


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.repos = await build_repositories(settings)
        app.state.pipeline = build_pipeline(settings)
        app.state.limiter = SlidingWindowLimiter()
        yield
        await app.state.repos.close()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    for router in (
        health.router,
        auth.router,
        documents.router,
        chat.router,
        stats.router,
    ):
        app.include_router(router, prefix="/api")

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "service": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
