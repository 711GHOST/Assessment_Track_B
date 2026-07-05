"""Central application configuration.

Every value can be overridden through environment variables or a `.env`
file placed in the backend directory. Keys left blank keep the app on its
local, dependency-free fallbacks (in-memory stores + extractive answering)
so the project runs end-to-end without any external service or API key.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    app_name: str = "RAG Application API"
    version: str = "2.1.0"
    environment: str = "development"  # development | production
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Auth / security ---
    jwt_secret: str = ""  # blank -> ephemeral secret generated at startup (dev only)
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # --- Database (users, documents, chat history) ---
    mongodb_uri: str = ""  # blank -> in-memory repositories
    mongodb_db: str = "rag_application"

    # --- Vector store ---
    qdrant_url: str = ""  # blank -> in-memory vector store
    qdrant_api_key: str = ""
    qdrant_collection: str = "rag_chunks"

    # --- Model providers ---
    gemini_api_key: str = ""  # blank -> extractive answers
    gemini_model: str = "gemini-flash-latest"
    # auto -> neural fastembed (BGE-small) if installed, else local hashing.
    # Options: auto | fastembed | local | hashing | gemini
    embedding_provider: str = "auto"
    # auto -> neural fastembed cross-encoder if installed, else lexical.
    # Options: auto | fastembed | local | lexical  (Cohere key overrides all)
    reranker_provider: str = "auto"
    cohere_api_key: str = ""  # blank -> local reranker
    cohere_rerank_model: str = "rerank-english-v3.0"

    # --- RAG tuning ---
    chunk_size_words: int = 200
    chunk_overlap_words: int = 40
    max_document_chars: int = 200_000
    default_top_k: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
