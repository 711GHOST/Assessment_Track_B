"""Tests for confidence, suggestions, feedback and stats."""
from tests.conftest import LANGCHAIN_DOC


def _upload(auth_client, title="LangChain notes", text=LANGCHAIN_DOC):
    response = auth_client.post("/api/documents", json={"title": title, "text": text})
    assert response.status_code == 201
    return response.json()


def test_answer_includes_confidence(auth_client):
    _upload(auth_client)
    body = auth_client.post(
        "/api/chat/query", json={"question": "What does LangChain provide?"}
    ).json()
    assert 0 <= body["confidence"] <= 100
    assert body["confidence"] > 0  # a grounded hit should have some confidence


def test_unanswerable_has_zero_confidence(auth_client):
    _upload(auth_client)
    body = auth_client.post(
        "/api/chat/query", json={"question": "Who won the 1998 world cup?"}
    ).json()
    assert body["confidence"] == 0


def test_suggestions_generated_from_documents(auth_client):
    assert auth_client.get("/api/chat/suggestions").json()["suggestions"] == []
    _upload(auth_client)
    suggestions = auth_client.get("/api/chat/suggestions").json()["suggestions"]
    assert len(suggestions) > 0
    assert all(s.endswith((".", "?")) for s in suggestions)


def test_feedback_records_and_validates(auth_client):
    _upload(auth_client)
    entry = auth_client.post(
        "/api/chat/query", json={"question": "What is LangChain?"}
    ).json()

    ok = auth_client.post(f"/api/chat/{entry['id']}/feedback", json={"rating": "up"})
    assert ok.status_code == 200

    bad = auth_client.post(f"/api/chat/{entry['id']}/feedback", json={"rating": "maybe"})
    assert bad.status_code == 422

    missing = auth_client.post("/api/chat/nope/feedback", json={"rating": "up"})
    assert missing.status_code == 404

    history = auth_client.get("/api/chat/history").json()
    assert history[0]["feedback"] == "up"


def test_stats_reflect_activity(auth_client):
    empty = auth_client.get("/api/stats").json()
    assert empty["document_count"] == 0
    assert empty["query_count"] == 0

    _upload(auth_client)
    entry = auth_client.post(
        "/api/chat/query", json={"question": "What does LangChain provide?"}
    ).json()
    auth_client.post(f"/api/chat/{entry['id']}/feedback", json={"rating": "up"})

    stats = auth_client.get("/api/stats").json()
    assert stats["document_count"] == 1
    assert stats["total_chunks"] >= 1
    assert stats["query_count"] == 1
    assert stats["helpful_count"] == 1
    assert stats["avg_confidence"] > 0


def test_feature_endpoints_require_auth(client):
    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/chat/suggestions").status_code == 401
    assert client.post("/api/chat/x/feedback", json={"rating": "up"}).status_code == 401
