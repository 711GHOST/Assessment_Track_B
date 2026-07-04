"""RAG chat flow tests (local fallback providers)."""
from tests.conftest import LANGCHAIN_DOC


def _upload(auth_client, title="LangChain notes", text=LANGCHAIN_DOC):
    response = auth_client.post("/api/documents", json={"title": title, "text": text})
    assert response.status_code == 201
    return response.json()


def test_query_returns_grounded_answer_with_citations(auth_client):
    _upload(auth_client)
    response = auth_client.post(
        "/api/chat/query", json={"question": "What does LangChain provide?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "chains" in body["answer"].lower()
    assert body["citations"], "expected at least one citation"
    assert body["citations"][0]["document_title"] == "LangChain notes"
    assert body["mode"] == "local/extractive"
    assert body["latency_ms"] >= 0


def test_query_without_documents_is_graceful(auth_client):
    response = auth_client.post("/api/chat/query", json={"question": "Anything?"})
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert "upload" in body["answer"].lower()


def test_unanswerable_question_says_so(auth_client):
    _upload(auth_client)
    response = auth_client.post(
        "/api/chat/query", json={"question": "Who won the 1998 football world cup?"}
    )
    assert response.status_code == 200
    assert "could not find" in response.json()["answer"].lower()


def test_query_scoped_to_selected_documents(auth_client):
    _upload(auth_client)
    other = _upload(
        auth_client,
        title="Cooking",
        text="Pasta is cooked in boiling salted water until al dente.",
    )
    response = auth_client.post(
        "/api/chat/query",
        json={"question": "How is pasta cooked?", "document_ids": [other["id"]]},
    )
    body = response.json()
    assert body["citations"]
    assert all(c["document_id"] == other["id"] for c in body["citations"])


def test_history_persists_and_clears(auth_client):
    _upload(auth_client)
    auth_client.post("/api/chat/query", json={"question": "What is LangChain?"})
    auth_client.post("/api/chat/query", json={"question": "What does it provide?"})

    history = auth_client.get("/api/chat/history").json()
    assert len(history) == 2
    assert history[0]["question"] == "What is LangChain?"

    cleared = auth_client.delete("/api/chat/history")
    assert cleared.status_code == 200
    assert auth_client.get("/api/chat/history").json() == []


def test_users_cannot_see_each_others_documents(client):
    first = client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "full_name": "A", "password": "Secure123"},
    ).json()["access_token"]
    second = client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "full_name": "B", "password": "Secure123"},
    ).json()["access_token"]

    client.post(
        "/api/documents",
        json={"title": "Private", "text": LANGCHAIN_DOC},
        headers={"Authorization": f"Bearer {first}"},
    )
    response = client.post(
        "/api/chat/query",
        json={"question": "What is LangChain?"},
        headers={"Authorization": f"Bearer {second}"},
    )
    assert response.json()["citations"] == []
