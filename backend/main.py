from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware
import time
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

# ---------- YOUR MODULES ----------
from embedding_chunking import chunk_text, generate_embeddings
from vector_db import add_documents_to_db, retrieve_top_k
from reranker import rerank_documents

# ---------- GEMINI (NEW SDK STYLE) ----------
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-flash-latest"

# ---------- FASTAPI ----------
app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://assessment-track-b-w7o7.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- MODELS ----------
class Document(BaseModel):
    id: str
    text: str
    metadata: dict = {}

class Query(BaseModel):
    query: str
    top_k: int = 5

# ---------- ROUTES ----------

@app.post("/upload")
async def upload_document(doc: Document):
    # 1. Chunk text
    chunks = chunk_text(doc.text)

    # 2. Embed chunks
    embeddings = generate_embeddings(chunks)

    # 3. Prepare docs for Qdrant
    docs_for_db = []
    for i, chunk in enumerate(chunks):
        docs_for_db.append({
            "id": str(uuid.uuid4()),   # Qdrant-safe ID
            "text": chunk,
            "vector": embeddings[i],
            "metadata": {
                "source": doc.id,
                "chunk": i
            }
        })

    # 4. Store in vector DB
    add_documents_to_db(docs_for_db)

    return {"message": "Document indexed successfully."}


@app.post("/query")
async def query_documents(query: Query):
    start_time = time.time()

    # 1. Embed query
    query_embedding = generate_embeddings([query.query])[0]

    # 2. Retrieve from Qdrant
    results = retrieve_top_k(query_embedding, query.top_k)

    if not results:
        return {
            "answer": "I don't know.",
            "citations": [],
            "latency": 0.0,
            "token_estimate": 0,
            "cost_estimate": 0.0
        }

    retrieved_docs = [
        {"text": hit.payload["text"], "metadata": hit.payload["metadata"]}
        for hit in results
    ]

    # 3. Rerank
    reranked_docs = rerank_documents(query.query, retrieved_docs)

    # 4. Build context
    context = "\n\n".join([doc["text"] for doc in reranked_docs])

    prompt = f"""
Answer the question ONLY using the context below.
Add inline citations like [1], [2].
If the answer is not in the context, say "I don't know".

Context:
{context}

Question: {query.query}
"""

    # 5. Call Gemini (NEW SDK style – same as your example)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    answer = response.text.strip()

    latency = round(time.time() - start_time, 2)

    # 6. Build citations
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
