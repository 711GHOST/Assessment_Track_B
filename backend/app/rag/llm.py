"""Answer generators.

* ExtractiveAnswerer - local, no API key, no hallucination: quotes the
  sentences most relevant to the question and cites them. With a neural
  embedder it selects sentences by *semantic* similarity (so paraphrased
  questions work); otherwise it falls back to keyword overlap.
* GeminiAnswerer - grounded generation with inline [n] citations via the
  Gemini API (GEMINI_API_KEY).
"""
from __future__ import annotations

import math
import re

from app.rag.text import TOKEN_RE, content_tokens
from app.rag.vectorstore import ChunkHit

NO_ANSWER = (
    "I could not find an answer to that question in your uploaded documents."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Minimum semantic similarity for a sentence to count as an answer.
_SEMANTIC_THRESHOLD = 0.52


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _split_sentences(contexts: list[ChunkHit]) -> tuple[list[str], list[int]]:
    sentences: list[str] = []
    cites: list[int] = []
    for citation_index, hit in enumerate(contexts, start=1):
        for sentence in _SENTENCE_SPLIT.split(hit.text):
            sentence = sentence.strip()
            if len(sentence.split()) >= 3:
                sentences.append(sentence)
                cites.append(citation_index)
    return sentences, cites


class ExtractiveAnswerer:
    name = "local/extractive"

    def __init__(self, embedder=None, semantic: bool = False) -> None:
        # Only use the embedder for sentence selection when it is neural;
        # the hashing embedder has no semantics, so keyword overlap is better.
        self._embedder = embedder if semantic else None

    def answer(self, question: str, contexts: list[ChunkHit]) -> str:
        if self._embedder is not None:
            answer = self._semantic_answer(question, contexts)
            # Fall back to lexical if the semantic pass finds nothing but a
            # keyword match exists (belt and braces).
            if answer != NO_ANSWER:
                return answer
        return self._lexical_answer(question, contexts)

    # -- semantic (neural embedder) ------------------------------------
    def _semantic_answer(self, question: str, contexts: list[ChunkHit]) -> str:
        sentences, cites = _split_sentences(contexts)
        if not sentences:
            return NO_ANSWER
        sentences, cites = sentences[:40], cites[:40]

        query_vec = self._embedder.embed_query(question)
        sentence_vecs = self._embedder.embed(sentences)
        scored = sorted(
            (
                (_cosine(query_vec, vec), sentence, cite)
                for vec, sentence, cite in zip(sentence_vecs, sentences, cites)
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        best = scored[0][0]
        if best < _SEMANTIC_THRESHOLD:
            return NO_ANSWER

        picked: list[tuple[int, str]] = []
        seen: set[str] = set()
        for score, sentence, cite in scored:
            if score < _SEMANTIC_THRESHOLD or score < best - 0.12:
                break
            if sentence in seen:
                continue
            seen.add(sentence)
            picked.append((cite, sentence))
            if len(picked) == 3:
                break
        # Present in reading order for coherence.
        picked.sort(key=lambda item: item[0])
        return " ".join(f"{sentence} [{cite}]" for cite, sentence in picked)

    # -- lexical (keyword overlap) fallback ----------------------------
    def _lexical_answer(self, question: str, contexts: list[ChunkHit]) -> str:
        question_tokens = content_tokens(question)
        if not question_tokens:
            question_tokens = set(TOKEN_RE.findall(question.lower()))

        candidates: list[tuple[float, str, int]] = []
        for citation_index, hit in enumerate(contexts, start=1):
            for sentence in _SENTENCE_SPLIT.split(hit.text):
                sentence = sentence.strip()
                if not sentence:
                    continue
                sentence_tokens = content_tokens(sentence)
                if not sentence_tokens:
                    continue
                overlap = len(question_tokens & sentence_tokens)
                if overlap == 0:
                    continue
                candidates.append(
                    (overlap / len(question_tokens), sentence, citation_index)
                )

        if not candidates:
            return NO_ANSWER

        candidates.sort(key=lambda item: item[0], reverse=True)
        seen: set[str] = set()
        parts: list[str] = []
        for _, sentence, citation_index in candidates:
            if sentence in seen:
                continue
            seen.add(sentence)
            parts.append(f"{sentence} [{citation_index}]")
            if len(parts) == 3:
                break
        return " ".join(parts)


class GeminiAnswerer:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def answer(self, question: str, contexts: list[ChunkHit]) -> str:
        numbered_context = "\n\n".join(
            f"[{i}] (from \"{hit.document_title}\")\n{hit.text}"
            for i, hit in enumerate(contexts, start=1)
        )
        prompt = f"""You are a careful assistant answering strictly from the provided sources.

Rules:
- Answer ONLY using the numbered sources below.
- Add inline citations like [1], [2] after every claim, matching source numbers.
- If the sources do not contain the answer, reply exactly: "{NO_ANSWER}"
- Be concise and factual.

Sources:
{numbered_context}

Question: {question}"""
        response = self._client.models.generate_content(
            model=self._model, contents=prompt
        )
        return (response.text or "").strip() or NO_ANSWER
