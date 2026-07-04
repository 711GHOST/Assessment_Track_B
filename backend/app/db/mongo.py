"""MongoDB persistence built on Motor (async driver).

Activated when MONGODB_URI is set. Collections: users, documents, chats,
refresh_tokens (with a TTL index so expired tokens clean themselves up).
"""
from __future__ import annotations

from datetime import datetime, timezone

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


def _aware(dt: datetime) -> datetime:
    """Mongo returns naive UTC datetimes; normalize them to tz-aware."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class MongoUserRepository(UserRepository):
    def __init__(self, collection) -> None:
        self._col = collection

    async def create(self, user: User) -> User:
        await self._col.insert_one(
            {
                "_id": user.id,
                "email": user.email.lower(),
                "password_hash": user.password_hash,
                "full_name": user.full_name,
                "created_at": user.created_at,
            }
        )
        return user

    @staticmethod
    def _to_user(doc: dict) -> User:
        return User(
            id=doc["_id"],
            email=doc["email"],
            password_hash=doc["password_hash"],
            full_name=doc["full_name"],
            created_at=_aware(doc["created_at"]),
        )

    async def get_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email.lower()})
        return self._to_user(doc) if doc else None

    async def get_by_id(self, user_id: str) -> User | None:
        doc = await self._col.find_one({"_id": user_id})
        return self._to_user(doc) if doc else None


class MongoDocumentRepository(DocumentRepository):
    def __init__(self, collection) -> None:
        self._col = collection

    async def create(self, doc: DocumentRecord) -> DocumentRecord:
        await self._col.insert_one(
            {
                "_id": doc.id,
                "user_id": doc.user_id,
                "title": doc.title,
                "char_count": doc.char_count,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at,
            }
        )
        return doc

    @staticmethod
    def _to_record(doc: dict) -> DocumentRecord:
        return DocumentRecord(
            id=doc["_id"],
            user_id=doc["user_id"],
            title=doc["title"],
            char_count=doc["char_count"],
            chunk_count=doc["chunk_count"],
            created_at=_aware(doc["created_at"]),
        )

    async def list_for_user(self, user_id: str) -> list[DocumentRecord]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [self._to_record(d) for d in await cursor.to_list(length=500)]

    async def get(self, user_id: str, doc_id: str) -> DocumentRecord | None:
        doc = await self._col.find_one({"_id": doc_id, "user_id": user_id})
        return self._to_record(doc) if doc else None

    async def delete(self, user_id: str, doc_id: str) -> bool:
        result = await self._col.delete_one({"_id": doc_id, "user_id": user_id})
        return result.deleted_count > 0


class MongoChatRepository(ChatRepository):
    def __init__(self, collection) -> None:
        self._col = collection

    async def add(self, entry: ChatEntry) -> ChatEntry:
        await self._col.insert_one(
            {
                "_id": entry.id,
                "user_id": entry.user_id,
                "question": entry.question,
                "answer": entry.answer,
                "mode": entry.mode,
                "citations": entry.citations,
                "latency_ms": entry.latency_ms,
                "confidence": entry.confidence,
                "feedback": entry.feedback,
                "created_at": entry.created_at,
            }
        )
        return entry

    @staticmethod
    def _to_entry(doc: dict) -> ChatEntry:
        return ChatEntry(
            id=doc["_id"],
            user_id=doc["user_id"],
            question=doc["question"],
            answer=doc["answer"],
            mode=doc["mode"],
            citations=doc.get("citations", []),
            latency_ms=doc.get("latency_ms", 0),
            confidence=doc.get("confidence", 0),
            feedback=doc.get("feedback"),
            created_at=_aware(doc["created_at"]),
        )

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[ChatEntry]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        entries = [self._to_entry(d) for d in await cursor.to_list(length=limit)]
        return list(reversed(entries))

    async def clear_for_user(self, user_id: str) -> int:
        result = await self._col.delete_many({"user_id": user_id})
        return result.deleted_count

    async def set_feedback(self, user_id: str, entry_id: str, rating: str) -> bool:
        result = await self._col.update_one(
            {"_id": entry_id, "user_id": user_id}, {"$set": {"feedback": rating}}
        )
        return result.matched_count > 0

    async def stats(self, user_id: str) -> dict:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "query_count": {"$sum": 1},
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                    "avg_confidence": {"$avg": "$confidence"},
                    "helpful_count": {
                        "$sum": {"$cond": [{"$eq": ["$feedback", "up"]}, 1, 0]}
                    },
                }
            },
        ]
        docs = await self._col.aggregate(pipeline).to_list(length=1)
        if not docs:
            return {
                "query_count": 0,
                "avg_latency_ms": 0,
                "avg_confidence": 0,
                "helpful_count": 0,
            }
        row = docs[0]
        return {
            "query_count": row["query_count"],
            "avg_latency_ms": round(row.get("avg_latency_ms") or 0),
            "avg_confidence": round(row.get("avg_confidence") or 0),
            "helpful_count": row.get("helpful_count", 0),
        }


class MongoRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, collection) -> None:
        self._col = collection

    async def add(self, record: RefreshTokenRecord) -> None:
        await self._col.insert_one(
            {
                "_id": record.jti,
                "user_id": record.user_id,
                "expires_at": record.expires_at,
                "revoked": record.revoked,
            }
        )

    async def is_active(self, jti: str) -> bool:
        doc = await self._col.find_one({"_id": jti})
        if doc is None or doc.get("revoked"):
            return False
        return _aware(doc["expires_at"]) > utcnow()

    async def revoke(self, jti: str) -> None:
        await self._col.update_one({"_id": jti}, {"$set": {"revoked": True}})

    async def revoke_all_for_user(self, user_id: str) -> None:
        await self._col.update_many({"user_id": user_id}, {"$set": {"revoked": True}})


async def build_mongo_repositories(settings) -> Repositories:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "MONGODB_URI is set but the 'motor' package is not installed. "
            "Run: pip install motor"
        ) from exc

    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    await db.users.create_index("email", unique=True)
    await db.documents.create_index([("user_id", 1), ("created_at", -1)])
    await db.chats.create_index([("user_id", 1), ("created_at", -1)])
    # TTL index: Mongo removes refresh tokens automatically once expired.
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)

    async def close() -> None:
        client.close()

    return Repositories(
        users=MongoUserRepository(db.users),
        documents=MongoDocumentRepository(db.documents),
        chats=MongoChatRepository(db.chats),
        refresh_tokens=MongoRefreshTokenRepository(db.refresh_tokens),
        kind="mongodb",
        close_cb=close,
    )
