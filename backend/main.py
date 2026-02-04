from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from backend.embedding_chunking import generate_embeddings, chunk_text
from backend.vector_db import add_documents_to_db, retrieve_top_k
from backend.reranker import rerank_documents
import time
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

origins = [
    "https://assessment-track-b-w7o7.vercel.app",  # your frontend
    "http://localhost:3000",  # local dev
    "http://localhost:5173"   # if using Vite
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for testing only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define data models
class Document(BaseModel):
    id: str
    text: str
    metadata: dict

class Query(BaseModel):
    query: str
    top_k: int = 5

class Answer(BaseModel):
    answer: str
    citations: List[str]
    latency: float
    token_estimate: int
    cost_estimate: float

# In-memory storage for demonstration purposes
documents = []

@app.post("/upload")
async def upload_document(doc: Document):
    chunks = chunk_text(doc.text)
    embeddings = generate_embeddings(chunks)

    docs_for_db = []
    for i, chunk in enumerate(chunks):
        docs_for_db.append({
            "id": f"{doc.id}_{i}",
            "text": chunk,
            "vector": embeddings[i],
            "metadata": {"source": doc.id, "chunk": i}
        })

    add_documents_to_db(docs_for_db)
    return {"message": "Document indexed successfully."}

@app.post("/query", response_model=Answer)
async def query_documents(query: Query):
    start = time.time()

    # 1. Embed query
    query_embedding = generate_embeddings([query.query])[0]

    # 2. Retrieve from vector DB
    results = retrieve_top_k(query_embedding, query.top_k)

    retrieved_docs = [
        {"text": hit.payload["text"], "metadata": hit.payload["metadata"]}
        for hit in results
    ]

    # 3. Rerank
    reranked_docs = rerank_documents(query.query, retrieved_docs)

    # 4. Build context
    context = "\n".join([doc["text"] for doc in reranked_docs])

    prompt = f"""
Answer the question ONLY using the context below.
Add inline citations like [1], [2].
If not found, say "I don't know".

Context:
{context}

Question: {query.query}
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    answer = response.text

    latency = round(time.time() - start, 2)

    citations = []
    for i, doc in enumerate(reranked_docs):
        citations.append(f"[{i+1}] Source: {doc['metadata']}")

    return {
        "answer": answer,
        "citations": citations,
        "latency": latency,
        "token_estimate": len(answer.split()) * 2,
        "cost_estimate": 0.0
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}