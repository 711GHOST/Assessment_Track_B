"""Rerankers reorder retrieved chunks by relevance to the query.

* LexicalReranker - local fallback blending normalized retrieval score with
  keyword overlap; scale-invariant so it works on fused (hybrid) candidates.
* FastEmbedReranker - local neural cross-encoder (ONNX, no API key) for a
  real precision boost; enabled when fastembed is installed.
* CohereReranker - hosted neural cross-encoder via the Cohere API.
"""
from __future__ import annotations

import math

from app.rag.text import STOPWORDS, content_tokens, norm  # noqa: F401 (re-exported)
from app.rag.vectorstore import ChunkHit

# Backwards-compatible aliases used elsewhere in the codebase.
_STOPWORDS = STOPWORDS
_content_tokens = content_tokens
_norm = norm


def _rebuilt(hit: ChunkHit, score: float) -> ChunkHit:
    return ChunkHit(
        text=hit.text,
        score=round(score, 6),
        document_id=hit.document_id,
        chunk_index=hit.chunk_index,
        document_title=hit.document_title,
    )


class LexicalReranker:
    name = "local/lexical-hybrid"

    def rerank(self, query: str, hits: list[ChunkHit]) -> list[ChunkHit]:
        if not hits:
            return hits
        query_tokens = content_tokens(query)
        if not query_tokens:
            return hits

        # Min-max normalize incoming scores so candidates coming from
        # different retrieval channels (cosine vs BM25) are comparable.
        raw = [max(0.0, h.score) for h in hits]
        lo, hi = min(raw), max(raw)
        span = (hi - lo) or 1.0

        rescored: list[ChunkHit] = []
        for hit, score in zip(hits, raw):
            norm_sim = (score - lo) / span
            overlap = len(query_tokens & content_tokens(hit.text)) / len(query_tokens)
            rescored.append(_rebuilt(hit, 0.45 * norm_sim + 0.55 * overlap))
        rescored.sort(key=lambda h: h.score, reverse=True)
        return rescored


class FastEmbedReranker:
    name = "local/bge-reranker"

    def __init__(self) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def rerank(self, query: str, hits: list[ChunkHit]) -> list[ChunkHit]:
        if not hits:
            return hits
        logits = list(self._model.rerank(query, [h.text for h in hits]))
        scored = [
            _rebuilt(hit, self._sigmoid(float(logit)))
            for hit, logit in zip(hits, logits)
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored


class CohereReranker:
    name = "cohere/rerank"

    def __init__(self, api_key: str, model: str) -> None:
        import cohere

        self._client = cohere.Client(api_key=api_key)
        self._model = model

    def rerank(self, query: str, hits: list[ChunkHit]) -> list[ChunkHit]:
        if not hits:
            return hits
        response = self._client.rerank(
            query=query,
            documents=[hit.text for hit in hits],
            model=self._model,
            top_n=len(hits),
        )
        return [
            _rebuilt(hits[result.index], float(result.relevance_score))
            for result in response.results
        ]
