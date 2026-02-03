from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

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
    documents.append(doc)
    return {"message": "Document uploaded successfully."}

@app.post("/query", response_model=Answer)
async def query_documents(query: Query):
    if not documents:
        raise HTTPException(status_code=404, detail="No documents available.")

    # Placeholder for retrieval, reranking, and LLM answering logic
    answer = "This is a placeholder answer."
    citations = [doc.id for doc in documents[:query.top_k]]
    latency = 0.1  # Placeholder latency
    token_estimate = 100  # Placeholder token estimate
    cost_estimate = 0.01  # Placeholder cost estimate

    return Answer(
        answer=answer,
        citations=citations,
        latency=latency,
        token_estimate=token_estimate,
        cost_estimate=cost_estimate
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}