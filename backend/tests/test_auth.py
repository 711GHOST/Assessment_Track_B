"""Authentication flow tests."""
from tests.conftest import REGISTER_PAYLOAD


def test_register_returns_tokens_and_user(client):
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert "password" not in body["user"]


def test_register_duplicate_email_conflict(client):
    assert client.post("/api/auth/register", json=REGISTER_PAYLOAD).status_code == 201
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    weak = {**REGISTER_PAYLOAD, "password": "onlyletters"}
    assert client.post("/api/auth/register", json=weak).status_code == 422
    short = {**REGISTER_PAYLOAD, "password": "a1"}
    assert client.post("/api/auth/register", json=short).status_code == 422


def test_login_success_and_me(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER_PAYLOAD["email"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "Wrong1234"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


def test_refresh_rotates_tokens(client):
    registered = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()
    old_refresh = registered["refresh_token"]

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # The used refresh token must be revoked (rotation).
    reused = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


def test_logout_revokes_refresh_token(client):
    registered = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()
    refresh_token = registered["refresh_token"]

    assert client.post("/api/auth/logout", json={"refresh_token": refresh_token}).status_code == 200
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_login_rate_limited(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    payload = {"email": REGISTER_PAYLOAD["email"], "password": "Wrong1234"}
    statuses = [client.post("/api/auth/login", json=payload).status_code for _ in range(12)]
    assert 429 in statuses
