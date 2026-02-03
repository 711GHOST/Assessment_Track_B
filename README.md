# Mini RAG Application

## Overview
This is a Mini Retrieval-Augmented Generation (RAG) application built with the following tech stack:
- **Backend**: FastAPI
- **Frontend**: React
- **Vector Database**: Qdrant
- **Embeddings**: Gemmini or Cohere
- **Reranker**: Cohere Rerank

The application allows users to upload documents, query them, and receive grounded answers with inline citations.

---

## Architecture
![Architecture Diagram](architecture-diagram-placeholder.png)

1. **Document Upload**: Users upload or paste text, which is chunked and stored in the vector database.
2. **Query Flow**: Queries retrieve top-k documents, rerank them, and generate answers using an LLM.
3. **Frontend**: Displays answers, citations, latency, token estimates, and cost estimates.

---

## Chunking Parameters
- **Chunk Size**: 1000 tokens
- **Overlap**: 150 tokens
- **Strategy**: Text is tokenized, split into overlapping chunks, and converted back to strings.

---

## Retriever Configuration
- **Vector Database**: Qdrant
- **Distance Metric**: Cosine similarity
- **Embedding Size**: 768 (using `sentence-transformers/all-MiniLM-L6-v2`)

---

## Reranker
- **Provider**: Cohere Rerank
- **API Key**: Required in `.env` file

---

## Providers Used
- **Embeddings**: Gemini or Cohere
- **Reranker**: Cohere
- **Vector Database**: Qdrant

---

## Quickstart

### Backend
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend
1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the React app:
   ```bash
   npm start
   ```

---

## Deployment
- **Hosting**: Render, Vercel, or Hugging Face Spaces
- **Environment Variables**: Store API keys in `.env` file

---

## Tradeoffs/Remarks
- **Latency**: Using hosted services may introduce latency.
- **Cost**: Gemini and Cohere APIs incur usage costs.
- **Scalability**: Suitable for small-scale applications; may require optimization for large datasets.

---

## .env Example
```
GEMINI_API_KEY=your-gemini-api-key
COHERE_API_KEY=your-cohere-api-key
QDRANT_HOST=localhost
QDRANT_PORT=6333
```