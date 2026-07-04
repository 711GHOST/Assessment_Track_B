"""Test fixtures.

Environment variables are forced to blank BEFORE the app is imported so the
suite always runs against the local fallback providers (in-memory DB and
vector store, hashing embeddings, extractive answers) regardless of any
`.env` file on the developer's machine — env vars take precedence over
`.env` in pydantic-settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.update(
    {
        "GEMINI_API_KEY": "",
        "COHERE_API_KEY": "",
        "QDRANT_URL": "",
        "QDRANT_API_KEY": "",
        "MONGODB_URI": "",
        "EMBEDDING_PROVIDER": "local",
        "JWT_SECRET": "test-secret-not-for-production-0123456789abcdef",
        "ENVIRONMENT": "test",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402

LANGCHAIN_DOC = (
    "LangChain is a framework for developing applications powered by large "
    "language models. It provides chains, agents, and memory. Developers use "
    "LangChain to build chatbots, question answering systems, and autonomous "
    "agents. The framework integrates with many vector databases and model "
    "providers."
)

REGISTER_PAYLOAD = {
    "email": "ada@example.com",
    "full_name": "Ada Lovelace",
    "password": "Secure123",
}


@pytest.fixture()
def client():
    """Fresh app (clean in-memory state and rate limits) per test."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client):
    """Client pre-authenticated as a registered user."""
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
