"""Embedding providers.

* HashingEmbedder - fully local, zero dependencies, deterministic. Uses the
  classic feature-hashing trick (token + bigram features hashed into a fixed
  dimensional space, L2-normalized). Quality is below neural embeddings but
  it costs nothing, needs no downloads and keeps the whole pipeline testable
  offline.
* GeminiEmbedder - neural embeddings via the Gemini API. Enabled with
  EMBEDDING_PROVIDER=gemini + GEMINI_API_KEY.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    name = "local/hashing-tf-384"
    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = TOKEN_RE.findall(text.lower())
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm:
            vec = [v / norm for v in vec]
        return vec


class GeminiEmbedder:
    name = "gemini/text-embedding-004"
    dim = 768

    def __init__(self, api_key: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(
            model="text-embedding-004", contents=texts
        )
        return [list(e.values) for e in result.embeddings]
