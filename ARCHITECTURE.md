# Architecture & Design Decisions

## Guiding principle: graceful degradation

Every external dependency sits behind an interface with a free, local,
zero-configuration implementation. The app is **fully functional with no
API keys** and upgrades component-by-component as keys are added. This has
three payoffs:

1. **Demo-ability** - anyone can clone and run it in two commands.
2. **Testability** - the entire test suite runs offline and deterministic.
3. **Cost control** - free tiers are only consumed when explicitly enabled.

Provider selection happens once at startup (`app/rag/pipeline.py:build_pipeline`,
`app/db/factory.py:build_repositories`) driven purely by environment
variables. At runtime, if a remote provider call fails, the pipeline
degrades to extractive answering instead of returning a 500.

## Layering

```
api/routes  →  schemas (validation)  →  services (pipeline)  →  db / rag providers
```

- **Routes** are thin: validate, authenticate, delegate, persist.
- **Schemas** (Pydantic v2) enforce input bounds (password policy, document
  size, top_k range) before anything touches business logic.
- **Repositories** (`db/base.py`) isolate storage. The API never imports
  Motor or a dict-store directly - swapping MongoDB in is a config change,
  not a refactor.
- **RAG providers** (`rag/`) are small classes with a shared duck-typed
  interface per role: `Embedder`, `VectorStore`, reranker, answerer.
- Blocking provider calls (Gemini/Cohere/Qdrant SDKs are synchronous) run
  via `run_in_threadpool` so the async event loop stays responsive.

## The RAG pipeline

**Ingestion** - `text → chunk → embed → upsert(user_id namespace)`

- *Chunking*: sentence-aware packing to ~200 words with ~40-word overlap
  (word counts approximate tokens well enough at this scale). Sentences are
  never split mid-way unless a single sentence exceeds the budget.
- *Embeddings (default, `auto`)*: neural **BGE-small-en-v1.5** (384-d) via
  fastembed/ONNX - a genuine sentence-embedding model that matches
  paraphrases (e.g. "vacation" ≈ "paid leave"), no API key. If fastembed
  isn't installed it falls back to **feature hashing** (token + bigram
  features hashed into a 384-d signed space; deterministic, offline; cf.
  scikit-learn's `HashingVectorizer`).
- *Embeddings (hosted)*: Gemini `text-embedding-004` (768-d). The Qdrant
  collection name is namespaced by embedder + dimension so switching
  providers can never mix incompatible vectors.

**Query** - `question → embed → hybrid retrieve → fuse → rerank → answer → cite`

- **Hybrid retrieval**: a dense channel (vector cosine) and a sparse channel
  (**BM25**, Okapi with k1=1.5, b=0.75) each return ~`4 × top_k` candidates.
  BM25 nails exact-keyword matches that embeddings miss; the dense channel
  catches paraphrases. The two lists are merged with **Reciprocal Rank
  Fusion** (`1/(k+rank)`, k=60), then the reranker narrows to `top_k`.
- *Reranker (default, `auto`)*: neural **cross-encoder**
  (ms-marco-MiniLM via fastembed), scored through a sigmoid. Falls back to a
  scale-invariant lexical reranker (min-max normalized retrieval score
  blended 45/55 with stemmed keyword overlap) so it works on fused
  candidates from either channel.
- *Answerer (default)*: extractive - it only quotes, so it cannot
  hallucinate. With a neural embedder it selects sentences by **semantic
  similarity** to the question (cosine ≥ 0.52), so paraphrased questions are
  answered; with the hashing embedder it uses keyword overlap. Returns
  "I could not find…" when nothing clears the bar.
- *Answerer (hosted)*: Gemini with a grounding prompt that requires `[n]`
  citations and mandates an explicit "I could not find…" refusal.
- Citations carry document id/title, chunk index, snippet and score, so
  the UI can show provenance for every answer.

**Derived signals**

- *Confidence (0–100)*: a weighted blend of the top and mean reranked
  scores, damped to zero when the answerer explicitly finds nothing. It is a
  retrieval-strength proxy, not a factuality guarantee - shown as a ring so
  users can gauge how well-grounded a response is.
- *Suggested questions*: generated offline by ranking salient content
  keywords across a sample of the user's chunks and filling question
  templates - deterministic and provider-free (a Gemini key could power
  richer suggestions later).
- *Feedback & analytics*: thumbs up/down persist on the chat entry and feed
  the workspace stats endpoint (query count, average latency, average
  confidence, helpful votes), computed via a Mongo aggregation or an
  in-memory reduction depending on the active backend.

## Multi-tenancy

Every vector is stored with a `user_id`; every search filters on it
(payload filter in Qdrant, dict namespace in memory). Repositories scope
all reads/writes by `user_id`. `tests/test_chat.py::
test_users_cannot_see_each_others_documents` locks this in.

## Security model

| Concern | Measure |
|---|---|
| Password storage | bcrypt (cost-factored, salted); 72-byte input cap enforced in schema |
| Sessions | 30-min JWT access tokens + 7-day refresh tokens |
| Token theft | Refresh rotation: each refresh revokes the used token (server-side jti registry); logout revokes |
| Brute force | Per-IP sliding-window rate limits on login/register/query |
| Account enumeration | Identical error for unknown email vs wrong password |
| Browser attacks | CORS allowlist, `X-Frame-Options: DENY`, `nosniff`, referrer and permissions policies |
| Input abuse | Pydantic bounds everywhere: document ≤ 200k chars, question ≤ 2k, top_k ≤ 10 |

Known trade-offs (documented, acceptable at this scale):

- Tokens live in `localStorage` - simple and works cross-origin
  (Vercel ↔ Render), at the cost of XSS exposure; an httpOnly-cookie flow
  is the hardening path (see TODO).
- The rate limiter is in-process - right-sized for single-instance free
  tiers; Redis would replace it for horizontal scale.

## Frontend

Vite + React 18 (CRA was retired upstream). Plain-JS with a small surface:
one fetch wrapper (`api/client.js`) owning token storage and the
401 → refresh → retry loop; an auth context; three pages. Styling is a
hand-rolled CSS design system (custom properties, no framework) - fast to
load and easy to retheme.

## Testing strategy

- **Unit**: chunking edge cases, embedder determinism/normalization,
  similarity ranking sanity, reranker ordering.
- **API**: full auth lifecycle (register/login/refresh-rotation/logout),
  rate-limit 429s, document CRUD, ingestion → retrieval round-trips,
  tenant isolation, unanswerable-question honesty.
- All tests force blank provider keys, so they exercise exactly what a
  fresh clone runs.
