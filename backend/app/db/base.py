"""Storage-agnostic entities and repository interfaces.

The API layer only ever talks to these interfaces. Two implementations are
provided: an in-memory store (zero setup, the default) and MongoDB
(activated by setting MONGODB_URI).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------

@dataclass
class User:
    id: str
    email: str
    password_hash: str
    full_name: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class DocumentRecord:
    id: str
    user_id: str
    title: str
    char_count: int
    chunk_count: int
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ChatEntry:
    id: str
    user_id: str
    question: str
    answer: str
    mode: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    confidence: int = 0
    feedback: str | None = None  # "up" | "down" | None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class RefreshTokenRecord:
    jti: str
    user_id: str
    expires_at: datetime
    revoked: bool = False


# --------------------------------------------------------------------------
# Repository interfaces
# --------------------------------------------------------------------------

class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, doc: DocumentRecord) -> DocumentRecord: ...

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[DocumentRecord]: ...

    @abstractmethod
    async def get(self, user_id: str, doc_id: str) -> DocumentRecord | None: ...

    @abstractmethod
    async def delete(self, user_id: str, doc_id: str) -> bool: ...


class ChatRepository(ABC):
    @abstractmethod
    async def add(self, entry: ChatEntry) -> ChatEntry: ...

    @abstractmethod
    async def list_for_user(self, user_id: str, limit: int = 50) -> list[ChatEntry]: ...

    @abstractmethod
    async def clear_for_user(self, user_id: str) -> int: ...

    @abstractmethod
    async def set_feedback(self, user_id: str, entry_id: str, rating: str) -> bool: ...

    @abstractmethod
    async def stats(self, user_id: str) -> dict[str, Any]: ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def add(self, record: RefreshTokenRecord) -> None: ...

    @abstractmethod
    async def is_active(self, jti: str) -> bool: ...

    @abstractmethod
    async def revoke(self, jti: str) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> None: ...


@dataclass
class Repositories:
    users: UserRepository
    documents: DocumentRepository
    chats: ChatRepository
    refresh_tokens: RefreshTokenRepository
    kind: str = "in-memory"
    close_cb: Callable[[], Awaitable[None]] | None = None

    async def close(self) -> None:
        if self.close_cb is not None:
            await self.close_cb()
