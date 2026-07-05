"""Vector stores with per-user isolation.

* InMemoryVectorStore - default; cosine similarity over normalized vectors.
* QdrantVectorStore - activated by QDRANT_URL; payload-filtered by user so
  tenants never see each other's chunks.
"""
from __future__ import annotations

import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.rag.text import bm25_scores, content_tokens_list


@dataclass
class ChunkHit:
    text: str
    score: float
    document_id: str
    chunk_index: int
    document_title: str


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


class VectorStore(ABC):
    name: str

    @abstractmethod
    def upsert(
        self,
        user_id: str,
        document_id: str,
        title: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None: ...

    @abstractmethod
    def search(
        self,
        user_id: str,
        vector: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[ChunkHit]: ...

    @abstractmethod
    def delete_document(self, user_id: str, document_id: str) -> None: ...

    @abstractmethod
    def sample_texts(self, user_id: str, limit: int = 50) -> list[str]: ...

    def keyword_search(
        self,
        user_id: str,
        query: str,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[ChunkHit]:
        """BM25 lexical retrieval. Optional; defaults to none (vector-only)."""
        return []


class InMemoryVectorStore(VectorStore):
    name = "in-memory"

    def __init__(self) -> None:
        self._records: dict[str, list[dict]] = {}

    def upsert(self, user_id, document_id, title, chunks, vectors) -> None:
        records = self._records.setdefault(user_id, [])
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            records.append(
                {
                    "document_id": document_id,
                    "chunk_index": index,
                    "title": title,
                    "text": chunk,
                    "vector": _normalize(vector),
                }
            )

    def search(self, user_id, vector, top_k, document_ids=None) -> list[ChunkHit]:
        records = self._records.get(user_id, [])
        if document_ids:
            allowed = set(document_ids)
            records = [r for r in records if r["document_id"] in allowed]
        query = _normalize(vector)
        scored = [
            (
                sum(q * v for q, v in zip(query, record["vector"])),
                record,
            )
            for record in records
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            ChunkHit(
                text=record["text"],
                score=round(score, 6),
                document_id=record["document_id"],
                chunk_index=record["chunk_index"],
                document_title=record["title"],
            )
            for score, record in scored[:top_k]
        ]

    def delete_document(self, user_id, document_id) -> None:
        records = self._records.get(user_id, [])
        self._records[user_id] = [
            r for r in records if r["document_id"] != document_id
        ]

    def sample_texts(self, user_id, limit=50) -> list[str]:
        return [r["text"] for r in self._records.get(user_id, [])[:limit]]

    def keyword_search(self, user_id, query, top_k, document_ids=None) -> list[ChunkHit]:
        records = self._records.get(user_id, [])
        if document_ids:
            allowed = set(document_ids)
            records = [r for r in records if r["document_id"] in allowed]
        if not records:
            return []
        corpus = [content_tokens_list(r["text"]) for r in records]
        scores = bm25_scores(query, corpus)
        ranked = sorted(
            ((s, r) for s, r in zip(scores, records) if s > 0),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [
            ChunkHit(
                text=record["text"],
                score=round(score, 6),
                document_id=record["document_id"],
                chunk_index=record["chunk_index"],
                document_title=record["title"],
            )
            for score, record in ranked[:top_k]
        ]


class QdrantVectorStore(VectorStore):
    name = "qdrant"

    def __init__(self, url: str, api_key: str, collection: str, dim: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client import models as qm

        self._qm = qm
        self._client = QdrantClient(url=url, api_key=api_key or None)
        # Collection name embeds the dimension so switching embedding
        # providers never mixes incompatible vectors.
        self._collection = f"{collection}_{dim}"
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            )
        # Qdrant requires a payload index on any field used in a filter
        # (per-user isolation + document scoping). Idempotent: safe to call
        # on every startup, including for pre-existing collections.
        self._ensure_payload_index("user_id")
        self._ensure_payload_index("document_id")

    def _ensure_payload_index(self, field: str) -> None:
        try:
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=self._qm.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Index already exists (or a transient race) — safe to ignore.
            pass

    def upsert(self, user_id, document_id, title, chunks, vectors) -> None:
        qm = self._qm
        points = [
            qm.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": index,
                    "title": title,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def _filter(self, user_id: str, document_ids: list[str] | None):
        qm = self._qm
        must = [
            qm.FieldCondition(key="user_id", match=qm.MatchValue(value=user_id))
        ]
        if document_ids:
            must.append(
                qm.FieldCondition(
                    key="document_id", match=qm.MatchAny(any=document_ids)
                )
            )
        return qm.Filter(must=must)

    def search(self, user_id, vector, top_k, document_ids=None) -> list[ChunkHit]:
        # `query_points` is the modern API (the older `.search` was removed in
        # recent qdrant-client releases).
        response = self._client.query_points(
            collection_name=self._collection,
            query=list(vector),
            limit=top_k,
            query_filter=self._filter(user_id, document_ids),
            with_payload=True,
        )
        return [
            ChunkHit(
                text=hit.payload["text"],
                score=round(float(hit.score), 6),
                document_id=hit.payload["document_id"],
                chunk_index=hit.payload["chunk_index"],
                document_title=hit.payload.get("title", "Untitled"),
            )
            for hit in response.points
        ]

    def delete_document(self, user_id, document_id) -> None:
        qm = self._qm
        self._client.delete(
            collection_name=self._collection,
            points_selector=qm.FilterSelector(
                filter=self._filter(user_id, [document_id])
            ),
        )

    def _scroll_records(self, user_id, document_ids=None, limit=500):
        records, _ = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=self._filter(user_id, document_ids),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return records

    def sample_texts(self, user_id, limit=50) -> list[str]:
        return [
            r.payload.get("text", "")
            for r in self._scroll_records(user_id, limit=limit)
        ]

    def keyword_search(self, user_id, query, top_k, document_ids=None) -> list[ChunkHit]:
        # BM25 over the user's chunks (fetched via scroll) so hybrid retrieval
        # also works on Qdrant. Capped for latency; fine for typical corpora.
        records = self._scroll_records(user_id, document_ids, limit=500)
        if not records:
            return []
        corpus = [content_tokens_list(r.payload.get("text", "")) for r in records]
        scores = bm25_scores(query, corpus)
        ranked = sorted(
            ((s, r) for s, r in zip(scores, records) if s > 0),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [
            ChunkHit(
                text=r.payload["text"],
                score=round(s, 6),
                document_id=r.payload["document_id"],
                chunk_index=r.payload["chunk_index"],
                document_title=r.payload.get("title", "Untitled"),
            )
            for s, r in ranked[:top_k]
        ]
