"""In-memory repositories — the zero-setup default.

Data lives for the lifetime of the process. Perfect for local development,
demos and tests; set MONGODB_URI to switch to persistent storage.
"""
from __future__ import annotations

from app.db.base import (
    ChatEntry,
    ChatRepository,
    DocumentRecord,
    DocumentRepository,
    RefreshTokenRecord,
    RefreshTokenRepository,
    Repositories,
    User,
    UserRepository,
    utcnow,
)


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, str] = {}

    async def create(self, user: User) -> User:
        self._by_id[user.id] = user
        self._by_email[user.email.lower()] = user.id
        return user

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._by_email.get(email.lower())
        return self._by_id.get(user_id) if user_id else None

    async def get_by_id(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._docs: dict[str, DocumentRecord] = {}

    async def create(self, doc: DocumentRecord) -> DocumentRecord:
        self._docs[doc.id] = doc
        return doc

    async def list_for_user(self, user_id: str) -> list[DocumentRecord]:
        docs = [d for d in self._docs.values() if d.user_id == user_id]
        return sorted(docs, key=lambda d: d.created_at, reverse=True)

    async def get(self, user_id: str, doc_id: str) -> DocumentRecord | None:
        doc = self._docs.get(doc_id)
        return doc if doc and doc.user_id == user_id else None

    async def delete(self, user_id: str, doc_id: str) -> bool:
        doc = self._docs.get(doc_id)
        if doc and doc.user_id == user_id:
            del self._docs[doc_id]
            return True
        return False


class InMemoryChatRepository(ChatRepository):
    def __init__(self) -> None:
        self._entries: list[ChatEntry] = []

    async def add(self, entry: ChatEntry) -> ChatEntry:
        self._entries.append(entry)
        return entry

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[ChatEntry]:
        entries = [e for e in self._entries if e.user_id == user_id]
        return entries[-limit:]

    async def clear_for_user(self, user_id: str) -> int:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.user_id != user_id]
        return before - len(self._entries)

    async def set_feedback(self, user_id: str, entry_id: str, rating: str) -> bool:
        for entry in self._entries:
            if entry.id == entry_id and entry.user_id == user_id:
                entry.feedback = rating
                return True
        return False

    async def stats(self, user_id: str) -> dict:
        entries = [e for e in self._entries if e.user_id == user_id]
        latencies = [e.latency_ms for e in entries]
        confidences = [e.confidence for e in entries if e.confidence]
        return {
            "query_count": len(entries),
            "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "avg_confidence": round(sum(confidences) / len(confidences)) if confidences else 0,
            "helpful_count": sum(1 for e in entries if e.feedback == "up"),
        }


class InMemoryRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self._records: dict[str, RefreshTokenRecord] = {}

    async def add(self, record: RefreshTokenRecord) -> None:
        self._records[record.jti] = record

    async def is_active(self, jti: str) -> bool:
        record = self._records.get(jti)
        if record is None or record.revoked:
            return False
        return record.expires_at > utcnow()

    async def revoke(self, jti: str) -> None:
        record = self._records.get(jti)
        if record:
            record.revoked = True

    async def revoke_all_for_user(self, user_id: str) -> None:
        for record in self._records.values():
            if record.user_id == user_id:
                record.revoked = True


def build_memory_repositories() -> Repositories:
    return Repositories(
        users=InMemoryUserRepository(),
        documents=InMemoryDocumentRepository(),
        chats=InMemoryChatRepository(),
        refresh_tokens=InMemoryRefreshTokenRepository(),
        kind="in-memory",
    )
