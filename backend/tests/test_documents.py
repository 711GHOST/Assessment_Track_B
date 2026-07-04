"""Document management tests."""
from tests.conftest import LANGCHAIN_DOC


def test_documents_require_auth(client):
    assert client.get("/api/documents").status_code == 401
    assert (
        client.post("/api/documents", json={"title": "x", "text": "y"}).status_code
        == 401
    )


def test_create_list_delete_document(auth_client):
    created = auth_client.post(
        "/api/documents", json={"title": "LangChain notes", "text": LANGCHAIN_DOC}
    )
    assert created.status_code == 201, created.text
    doc = created.json()
    assert doc["chunk_count"] >= 1
    assert doc["char_count"] == len(LANGCHAIN_DOC)

    listed = auth_client.get("/api/documents").json()
    assert len(listed) == 1
    assert listed[0]["title"] == "LangChain notes"

    assert auth_client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert auth_client.get("/api/documents").json() == []


def test_delete_missing_document_404(auth_client):
    assert auth_client.delete("/api/documents/does-not-exist").status_code == 404


def test_empty_document_rejected(auth_client):
    response = auth_client.post("/api/documents", json={"title": "empty", "text": "   "})
    assert response.status_code == 422


def test_deleted_document_not_retrievable(auth_client):
    doc = auth_client.post(
        "/api/documents", json={"title": "LangChain notes", "text": LANGCHAIN_DOC}
    ).json()
    auth_client.delete(f"/api/documents/{doc['id']}")

    answer = auth_client.post(
        "/api/chat/query", json={"question": "What is LangChain?"}
    ).json()
    assert answer["citations"] == []
