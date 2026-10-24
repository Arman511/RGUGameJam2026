import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "elemental_api.db"
    monkeypatch.setenv("ELEMENTAL_API_DB_PATH", str(db_path))

    import elemental_api.database.connection as connection_module
    import elemental_api.main as app_module

    importlib.reload(connection_module)
    importlib.reload(app_module)

    with TestClient(app_module.app) as test_client:
        yield test_client


def test_registration_succeeds(client) -> None:
    response = client.post("/api/v1/auth/register", json={"username": "alice", "password": "secretpass"})
    assert response.status_code == 200


def test_duplicate_username_is_rejected(client) -> None:
    client.post("/api/v1/auth/register", json={"username": "alice", "password": "secretpass"})
    response = client.post("/api/v1/auth/register", json={"username": "alice", "password": "secretpass"})
    assert response.status_code == 409


def test_login_succeeds_and_returns_token(client) -> None:
    client.post("/api/v1/auth/register", json={"username": "alice", "password": "secretpass"})
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "secretpass"})
    assert response.status_code == 200
    payload = response.json()
    assert "token" in payload


def test_protected_routes_require_authentication(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
