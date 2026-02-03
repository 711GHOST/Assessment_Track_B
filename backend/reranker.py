import cohere
import os
from typing import List, Dict

# Initialize Cohere client
api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key=api_key)

# Function to rerank retrieved documents
def rerank_documents(query: str, documents: List[Dict]) -> List[Dict]:
    document_texts = [doc["text"] for doc in documents]
    response = co.rerank(
        query=query,
        documents=document_texts,
        model="rerank-english-v3.0",
        top_n=len(documents)
    )

    # Combine reranked scores with documents
    for doc, result in zip(documents, response.results):
        doc["score"] = result.relevance_score

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