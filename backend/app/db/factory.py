"""Choose the storage backend from configuration."""
from __future__ import annotations

from app.core.config import Settings
from app.db.base import Repositories


async def build_repositories(settings: Settings) -> Repositories:
    if settings.mongodb_uri:
        from app.db.mongo import build_mongo_repositories

        return await build_mongo_repositories(settings)

    from app.db.memory import build_memory_repositories

    return build_memory_repositories()
