"""RAG pipeline orchestration.

Ingestion:  text -> chunk -> embed -> vector store (per-user namespace)
Query:      question -> embed -> retrieve (wide) -> rerank -> answer + citations

Providers are chosen once at startup from configuration; every external
provider degrades gracefully to a local implementation when its key is
missing, and generation falls back to extractive answering if a provider
call fails at runtime.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.rag.chunking import chunk_text
from app.rag.embeddings import FastEmbedEmbedder, GeminiEmbedder, HashingEmbedder
from app.rag.llm import NO_ANSWER, ExtractiveAnswerer, GeminiAnswerer
from app.rag.reranker import (
    _STOPWORDS,
    CohereReranker,
    FastEmbedReranker,
    LexicalReranker,
)
from app.rag.vectorstore import ChunkHit, InMemoryVectorStore, QdrantVectorStore

logger = logging.getLogger(__name__)


def _reciprocal_rank_fusion(
    rankings: list[list[ChunkHit]], limit: int, k: int = 60
) -> list[ChunkHit]:
    """Merge several ranked candidate lists into one via Reciprocal Rank
    Fusion. Each chunk's fused score is the sum of 1/(k+rank) across the
    lists it appears in; the first-seen ChunkHit (with its channel score) is
    kept for downstream reranking."""
    fused: dict[tuple[str, int], float] = {}
    hit_by_key: dict[tuple[str, int], ChunkHit] = {}
    for hits in rankings:
        for rank, hit in enumerate(hits):
            key = (hit.document_id, hit.chunk_index)
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
            hit_by_key.setdefault(key, hit)
    ordered = sorted(fused, key=lambda key: fused[key], reverse=True)
    return [hit_by_key[key] for key in ordered[:limit]]

# Rough public pricing for Gemini Flash, used only for the cost estimate
# shown in the UI (USD per 1M tokens).
_GEMINI_INPUT_PER_M = 0.10
_GEMINI_OUTPUT_PER_M = 0.40


@dataclass
class QueryResult:
    answer: str
    mode: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    retrieved: int = 0
    confidence: int = 0  # 0-100 grounding confidence


class RagPipeline:
    def __init__(self, embedder, store, reranker, answerer, settings: Settings) -> None:
        self.embedder = embedder
        self.store = store
        self.reranker = reranker
        self.answerer = answerer
        self.settings = settings
        self._extractive_fallback = ExtractiveAnswerer()

    # ------------------------------------------------------------------
    def ingest(self, user_id: str, title: str, text: str) -> tuple[str, int]:
        """Chunk, embed and store a document. Returns (document_id, chunks)."""
        document_id = uuid.uuid4().hex
        chunks = chunk_text(
            text,
            chunk_size=self.settings.chunk_size_words,
            overlap=self.settings.chunk_overlap_words,
        )
        if not chunks:
            return document_id, 0
        vectors = self.embedder.embed(chunks)
        self.store.upsert(user_id, document_id, title, chunks, vectors)
        return document_id, len(chunks)

    def delete_document(self, user_id: str, document_id: str) -> None:
        self.store.delete_document(user_id, document_id)

    # ------------------------------------------------------------------
    def query(
        self,
        user_id: str,
        question: str,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> QueryResult:
        started = time.perf_counter()

        # Hybrid retrieval: a dense (vector) channel and a sparse (BM25)
        # channel, fused with Reciprocal Rank Fusion. BM25 catches exact
        # keyword matches that weak embeddings miss; the vector channel
        # catches paraphrases. The reranker then decides final precision.
        wide = max(top_k * 4, 12)
        query_vector = self.embedder.embed_query(question)
        vector_hits = self.store.search(
            user_id, query_vector, top_k=wide, document_ids=document_ids
        )
        try:
            keyword_hits = self.store.keyword_search(
                user_id, question, top_k=wide, document_ids=document_ids
            )
        except Exception:
            logger.exception("Keyword search failed; using vector results only")
            keyword_hits = []
        candidates = _reciprocal_rank_fusion([vector_hits, keyword_hits], limit=wide)

        if not candidates:
            return QueryResult(
                answer=(
                    "You have no indexed documents yet. Upload a document "
                    "first, then ask your question again."
                ),
                mode=self.answerer.name,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        try:
            ranked = self.reranker.rerank(question, candidates)
        except Exception:
            logger.exception("Reranker failed; using vector order")
            ranked = candidates
        contexts = ranked[:top_k]

        mode = self.answerer.name
        try:
            answer = self.answerer.answer(question, contexts)
        except Exception:
            logger.exception("Answerer failed; falling back to extractive mode")
            answer = self._extractive_fallback.answer(question, contexts)
            mode = f"{self._extractive_fallback.name} (fallback)"

        citations = [
            {
                "index": i,
                "document_id": hit.document_id,
                "document_title": hit.document_title,
                "chunk_index": hit.chunk_index,
                "snippet": hit.text[:240],
                "score": hit.score,
            }
            for i, hit in enumerate(contexts, start=1)
        ]

        # Grounding confidence (0-100): how strongly the top contexts match the
        # query, damped to zero when the answerer explicitly found nothing.
        if answer.strip() == NO_ANSWER or not contexts:
            confidence = 0
        else:
            top_score = max(0.0, min(1.0, contexts[0].score))
            mean_score = sum(max(0.0, h.score) for h in contexts) / len(contexts)
            confidence = round((0.7 * top_score + 0.3 * min(1.0, mean_score)) * 100)

        context_words = sum(len(hit.text.split()) for hit in contexts)
        answer_words = len(answer.split())
        token_estimate = int((len(question.split()) + context_words + answer_words) * 1.3)
        cost = 0.0
        if mode.startswith("gemini"):
            input_tokens = (len(question.split()) + context_words) * 1.3
            output_tokens = answer_words * 1.3
            cost = round(
                (input_tokens * _GEMINI_INPUT_PER_M + output_tokens * _GEMINI_OUTPUT_PER_M)
                / 1_000_000,
                8,
            )

        return QueryResult(
            answer=answer,
            mode=mode,
            citations=citations,
            latency_ms=int((time.perf_counter() - started) * 1000),
            token_estimate=token_estimate,
            cost_estimate_usd=cost,
            retrieved=len(candidates),
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    def suggest_questions(self, user_id: str, limit: int = 4) -> list[str]:
        """Generate starter questions from the user's indexed content.

        Offline and deterministic: ranks salient content keywords by frequency
        across a sample of chunks and fills question templates. When a Gemini
        key is configured, richer suggestions could be generated instead.
        """
        try:
            texts = self.store.sample_texts(user_id, limit=60)
        except Exception:
            logger.exception("sample_texts failed; returning no suggestions")
            return []
        if not texts:
            return []

        # Case-insensitive word match so capitalized words keep their first
        # letter (TOKEN_RE is lowercase-only and is used elsewhere for hashing).
        word_re = re.compile(r"[A-Za-z][A-Za-z0-9]+")
        counts: dict[str, int] = {}
        display: dict[str, str] = {}
        for text in texts:
            for original in word_re.findall(text):
                token = original.lower()
                if len(token) < 4 or token in _STOPWORDS:
                    continue
                counts[token] = counts.get(token, 0) + 1
                # Prefer a lowercase display form for common words; keep
                # original casing only for likely proper nouns (all others
                # lower).
                display.setdefault(token, token)

        ranked = sorted(counts, key=lambda t: counts[t], reverse=True)
        templates = [
            "What does the document say about {kw}?",
            "Can you summarize {kw}?",
            "Why is {kw} important?",
            "Explain {kw} in simple terms.",
        ]
        suggestions: list[str] = []
        for i, token in enumerate(ranked[:limit]):
            word = display.get(token, token)
            suggestions.append(templates[i % len(templates)].format(kw=word))
        return suggestions

    def provider_info(self) -> dict[str, str]:
        return {
            "embeddings": self.embedder.name,
            "vector_store": self.store.name,
            "reranker": self.reranker.name,
            "llm": self.answerer.name,
        }


def _build_embedder(settings: Settings):
    """Resolve the embedding provider.

    gemini            -> Gemini API (needs key)
    local | hashing   -> deterministic hashing embedder (no deps)
    fastembed | auto  -> neural BGE-small via fastembed, falling back to
                         hashing if fastembed is unavailable or fails to load
    """
    provider = settings.embedding_provider.lower()
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiEmbedder(settings.gemini_api_key)
    if provider in ("local", "hashing"):
        return HashingEmbedder()
    # "auto" (default) or "fastembed"
    try:
        embedder = FastEmbedEmbedder()
        embedder.embed(["warmup"])  # force model load now, not on first request
        logger.info("Using neural embeddings: %s", embedder.name)
        return embedder
    except Exception:
        logger.warning(
            "fastembed unavailable; using local hashing embeddings. "
            "Install 'fastembed' for higher-quality retrieval.",
            exc_info=True,
        )
        return HashingEmbedder()


def _build_reranker(settings: Settings):
    provider = settings.reranker_provider.lower()
    if settings.cohere_api_key:
        return CohereReranker(settings.cohere_api_key, settings.cohere_rerank_model)
    if provider in ("local", "lexical"):
        return LexicalReranker()
    try:
        reranker = FastEmbedReranker()
        reranker.rerank(
            "warmup", [ChunkHit("warmup text", 0.0, "d", 0, "t")]
        )
        logger.info("Using neural reranker: %s", reranker.name)
        return reranker
    except Exception:
        logger.warning("fastembed reranker unavailable; using lexical reranker.")
        return LexicalReranker()


def build_pipeline(settings: Settings) -> RagPipeline:
    embedder = _build_embedder(settings)

    if settings.qdrant_url:
        # Namespace the collection by embedder so different embedding models
        # (which produce incompatible vectors) never share one collection.
        tag = re.sub(r"[^a-z0-9]+", "_", embedder.name.lower())
        store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection=f"{settings.qdrant_collection}_{tag}",
            dim=embedder.dim,
        )
    else:
        store = InMemoryVectorStore()

    reranker = _build_reranker(settings)

    if settings.gemini_api_key:
        answerer = GeminiAnswerer(settings.gemini_api_key, settings.gemini_model)
    else:
        # Semantic sentence selection only pays off with a neural embedder.
        semantic = not isinstance(embedder, HashingEmbedder)
        answerer = ExtractiveAnswerer(embedder=embedder, semantic=semantic)

    return RagPipeline(embedder, store, reranker, answerer, settings)
