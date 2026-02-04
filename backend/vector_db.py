from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from typing import List, Dict
import os

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

COLLECTION_NAME = "documents"

# Ensure collection exists
def initialize_collection():
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vector_size=768,  # Placeholder for embedding size
        distance="Cosine"
    )

# Add documents to the vector database
def add_documents_to_db(documents: List[Dict]):
    points = [
        PointStruct(
            id=doc["id"],
            vector=doc["vector"],
            payload={
                "text": doc["text"],
                "metadata": doc["metadata"]
            }
        )
        for doc in documents
    ]
    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

# Retrieve top-k documents
def retrieve_top_k(query_vector: List[float], top_k: int):
    search_result = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    return search_result

# Initialize the collection on module load
initialize_collection()