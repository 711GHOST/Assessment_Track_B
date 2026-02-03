from cohere_rerank import CohereRerank
from typing import List, Dict
import os

# Initialize Gemini Rerank client
api_key = os.getenv("GEMINI_API_KEY")
reranker = CohereRerank(api_key=api_key)

# Function to rerank retrieved documents
def rerank_documents(query: str, documents: List[Dict]) -> List[Dict]:
    rerank_input = {
        "query": query,
        "documents": [doc["text"] for doc in documents]
    }
    reranked = reranker.rerank(**rerank_input)

    # Combine reranked scores with documents
    for doc, score in zip(documents, reranked["scores"]):
        doc["score"] = score

    # Sort documents by score in descending order
    documents.sort(key=lambda x: x["score"], reverse=True)
    return documents

# Example usage
if __name__ == "__main__":
    query = "What is the capital of France?"
    documents = [
        {"text": "Paris is the capital of France.", "metadata": {}},
        {"text": "Berlin is the capital of Germany.", "metadata": {}},
        {"text": "Madrid is the capital of Spain.", "metadata": {}},
    ]
    reranked_docs = rerank_documents(query, documents)
    for doc in reranked_docs:
        print(doc)