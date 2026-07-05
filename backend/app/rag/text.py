"""Shared text utilities: tokenization, stopwords, light stemming, BM25.

Kept in its own module so both the reranker and the vector stores can use
them without importing each other (which would be circular).
"""
from __future__ import annotations

import math
import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does",
    "for", "from", "has", "have", "how", "in", "is", "it", "its", "of",
    "on", "or", "that", "the", "this", "to", "was", "what", "when",
    "where", "which", "who", "why", "will", "with",
}


def norm(token: str) -> str:
    """Crude plural/verb-s stemming so 'provides' matches 'provide'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def content_tokens_list(text: str) -> list[str]:
    """Ordered content tokens with repetition (for term frequencies)."""
    return [norm(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def content_tokens(text: str) -> set[str]:
    """Unique content tokens (stopwords removed, lightly stemmed)."""
    return set(content_tokens_list(text))


def bm25_scores(query: str, documents: list[list[str]]) -> list[float]:
    """Okapi BM25 relevance of `query` against each pre-tokenized document.

    Returns one score per document (0.0 when nothing matches). Standard
    parameters k1=1.5, b=0.75.
    """
    n = len(documents)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in documents) / n or 1.0

    df: dict[str, int] = {}
    for doc in documents:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    q_terms = set(content_tokens_list(query))
    k1, b = 1.5, 0.75
    scores: list[float] = []
    for doc in documents:
        if not doc:
            scores.append(0.0)
            continue
        dl = len(doc)
        tf: dict[str, int] = {}
        for term in doc:
            tf[term] = tf.get(term, 0) + 1
        score = 0.0
        for term in q_terms:
            freq = tf.get(term)
            if not freq:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (freq * (k1 + 1)) / (
                freq + k1 * (1 - b + b * dl / avgdl)
            )
        scores.append(score)
    return scores
