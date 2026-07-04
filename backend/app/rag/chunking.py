"""Sentence-aware chunking with word-count budgets and overlap.

Chunks are packed from whole sentences up to `chunk_size` words; each new
chunk is seeded with the trailing sentences of the previous one (~`overlap`
words) so context is preserved across boundaries.
"""
from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s and s.strip()]


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    # Hard-split any single sentence longer than the chunk budget.
    pieces: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= chunk_size:
            pieces.append(sentence)
        else:
            for i in range(0, len(words), chunk_size):
                pieces.append(" ".join(words[i : i + chunk_size]))

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for piece in pieces:
        piece_len = len(piece.split())
        if current and current_len + piece_len > chunk_size and current_len > overlap:
            chunks.append(" ".join(current))
            # Seed the next chunk with trailing sentences for overlap.
            tail: list[str] = []
            tail_len = 0
            for sentence in reversed(current):
                sentence_len = len(sentence.split())
                if tail_len + sentence_len > overlap:
                    break
                tail.insert(0, sentence)
                tail_len += sentence_len
            current, current_len = tail, tail_len
        current.append(piece)
        current_len += piece_len

    if current:
        chunks.append(" ".join(current))
    return chunks
