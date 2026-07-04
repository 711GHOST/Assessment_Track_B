# Roadmap

## Done (v2.0 rebuild)

- [x] Layered FastAPI backend (routes / schemas / repositories / providers)
- [x] JWT auth: register, login, refresh rotation, logout, bcrypt hashing
- [x] Per-IP rate limiting, security headers, CORS allowlist
- [x] Provider abstraction with zero-key local fallbacks
      (hashing embeddings, lexical rerank, extractive answers, in-memory stores)
- [x] Optional providers: Gemini (LLM + embeddings), Cohere rerank,
      Qdrant vectors, MongoDB persistence
- [x] Per-user tenant isolation for documents and vectors
- [x] Citations with source, chunk, score and snippet
- [x] Answer confidence scoring, AI-suggested questions, answer feedback
- [x] Workspace analytics dashboard (documents, chunks, queries, latency)
- [x] Chat history (persisted, clearable), document-scoped questioning
- [x] React + Vite frontend: auth pages, dashboard, chat with citations
- [x] Animated 3D UI: constellation background, tilt cards, confidence ring,
      typewriter answers, count-up stats, drag-and-drop upload, toasts
- [x] Dark / light theme toggle
- [x] 33-test pytest suite; live end-to-end browser verification
- [x] Dockerfile, render.yaml, vercel.json, deployment guide

## Next up (fill in the blanks)

- [ ] Add `MONGODB_URI` (Atlas free tier) → persistent accounts & history
- [ ] Add `QDRANT_URL` + key → persistent vectors
- [ ] Add `GEMINI_API_KEY` → generative answers (and optionally
      `EMBEDDING_PROVIDER=gemini`)
- [ ] Add `COHERE_API_KEY` → neural reranking
- [ ] Deploy: Render/Northflank + Vercel (see DEPLOYMENT.md)

## Future improvements

- [ ] PDF/DOCX ingestion (server-side parsing, e.g. pypdf + python-docx)
- [ ] Streaming answers (SSE) for perceived latency
- [ ] Conversational memory: rewrite follow-up questions using chat history
- [ ] httpOnly-cookie session option to remove localStorage XSS exposure
- [ ] Retrieval evaluation harness (gold Q/A set, hit-rate + faithfulness
      metrics) run in CI
- [ ] Redis-backed rate limiting for multi-instance deployments
- [ ] Email verification + password reset flow
- [ ] Hybrid retrieval (BM25 + vectors with reciprocal-rank fusion)
- [ ] Admin/usage dashboard: per-user token spend and latency percentiles
- [ ] CI pipeline (GitHub Actions): pytest + frontend build on every push
