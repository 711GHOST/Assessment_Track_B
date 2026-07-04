"""Answer generators.

* ExtractiveAnswerer - local fallback: picks the sentences most relevant to
  the question from the top-ranked chunks and cites them. No API key, no
  hallucination - answers are verbatim from the user's documents.
* GeminiAnswerer - grounded generation with inline [n] citations via the
  Gemini API (GEMINI_API_KEY).
"""
from __future__ import annotations

import re

from app.rag.embeddings import TOKEN_RE
from app.rag.reranker import _content_tokens
from app.rag.vectorstore import ChunkHit

NO_ANSWER = (
    "I could not find an answer to that question in your uploaded documents."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class ExtractiveAnswerer:
    name = "local/extractive"

    def answer(self, question: str, contexts: list[ChunkHit]) -> str:
        question_tokens = _content_tokens(question)
        if not question_tokens:
            question_tokens = set(TOKEN_RE.findall(question.lower()))

        candidates: list[tuple[float, str, int]] = []
        for citation_index, hit in enumerate(contexts, start=1):
            for sentence in _SENTENCE_SPLIT.split(hit.text):
                sentence = sentence.strip()
                if not sentence:
                    continue
                sentence_tokens = _content_tokens(sentence)
                if not sentence_tokens:
                    continue
                overlap = len(question_tokens & sentence_tokens)
                if overlap == 0:
                    continue
                score = overlap / len(question_tokens)
                candidates.append((score, sentence, citation_index))

        if not candidates:
            return NO_ANSWER

        candidates.sort(key=lambda item: item[0], reverse=True)
        seen: set[str] = set()
        parts: list[str] = []
        for score, sentence, citation_index in candidates:
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
