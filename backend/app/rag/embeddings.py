"""Embedding providers.

* HashingEmbedder - fully local, zero dependencies, deterministic. Uses the
  classic feature-hashing trick (token + bigram features hashed into a fixed
  dimensional space, L2-normalized). Costs nothing and needs no downloads;
  paired with BM25 hybrid retrieval it stays useful offline.
* FastEmbedEmbedder - local *neural* embeddings (BAAI/bge-small-en-v1.5) via
  fastembed/ONNX. No API key; downloads a small quantized model once. This is
  the recommended quality default (EMBEDDING_PROVIDER=auto).
* GeminiEmbedder - hosted neural embeddings via the Gemini API.

All embedders expose `embed(texts)` and `embed_query(text)`; some models
benefit from asymmetric query/passage encoding.
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.rag.text import TOKEN_RE


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbedder:
    name = "local/hashing-tf-384"
    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

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


class FastEmbedEmbedder:
    name = "local/bge-small-en-v1.5"
    dim = 384

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        # bge models use an asymmetric query encoder for better retrieval.
        vec = next(iter(self._model.query_embed(text)))
        return list(map(float, vec))


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

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
