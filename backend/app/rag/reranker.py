"""Rerankers reorder retrieved chunks by relevance to the query.

* LexicalReranker — local fallback blending vector score with keyword
  overlap; catches cases where hashing embeddings are noisy.
* CohereReranker — neural cross-encoder via the Cohere API (COHERE_API_KEY).
"""
from __future__ import annotations

from app.rag.embeddings import TOKEN_RE
from app.rag.vectorstore import ChunkHit

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does",
    "for", "from", "has", "have", "how", "in", "is", "it", "its", "of",
    "on", "or", "that", "the", "this", "to", "was", "what", "when",
    "where", "which", "who", "why", "will", "with",
}


def _norm(token: str) -> str:
    """Crude plural/verb-s stemming so 'provides' matches 'provide'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _content_tokens(text: str) -> set[str]:
    return {
        _norm(t) for t in TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS
    }


class LexicalReranker:
    name = "local/lexical-overlap"

    def rerank(self, query: str, hits: list[ChunkHit]) -> list[ChunkHit]:
        query_tokens = _content_tokens(query)
        if not query_tokens:
            return hits

        rescored: list[ChunkHit] = []
        for hit in hits:
            chunk_tokens = _content_tokens(hit.text)
            overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
            blended = 0.5 * hit.score + 0.5 * overlap
            rescored.append(
                ChunkHit(
                    text=hit.text,
                    score=round(blended, 6),
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    document_title=hit.document_title,
                )
            )
        rescored.sort(key=lambda h: h.score, reverse=True)
        return rescored


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
        reordered: list[ChunkHit] = []
        for result in response.results:
            hit = hits[result.index]
            reordered.append(
                ChunkHit(
                    text=hit.text,
                    score=round(float(result.relevance_score), 6),
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    document_title=hit.document_title,
                )
            )
        return reordered
