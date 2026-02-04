from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from typing import List, Dict
import os

from dotenv import load_dotenv
load_dotenv()

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),      # for cloud
    api_key=os.getenv("QDRANT_API_KEY")
)

COLLECTION_NAME = "documents"

def initialize_collection():
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,   # must match embedding model
            distance=Distance.COSINE
        )
    )

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

def retrieve_top_k(query_vector: list, top_k: int):
    return qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )

initialize_collection()
