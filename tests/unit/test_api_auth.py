import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session


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
    response = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"


def test_duplicate_username_is_rejected(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )
    response = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )
    assert response.status_code == 409


def test_login_succeeds_and_returns_token(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "secretpass"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert "token" in payload


def test_protected_routes_require_authentication(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_authenticated_score_submission_saves_time_and_wave(client) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "secretpass"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secretpass"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    submitted = client.post(
        "/api/v1/scores",
        headers=headers,
        json={
            "run_id": "run-1",
            "time_survived": 64.2,
            "wave_number": 5,
            "enemies_defeated": 14,
        },
    )

    assert submitted.status_code == 200
    leaderboard = client.get("/api/v1/leaderboard")
    assert leaderboard.status_code == 200
    entry = leaderboard.json()["scores"][0]
    assert entry["run_id"] == "run-1"
    assert entry["username"] == "alice"
    assert entry["time_survived"] == 64.2
    assert entry["wave_number"] == 5
    assert entry["enemies_defeated"] == 14
    assert entry["submitted_at"]


def test_migration_preserves_legacy_run_data_without_score(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "legacy.db"
    monkeypatch.setenv("ELEMENTAL_API_DB_PATH", str(database_path))
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                normalized_username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                survival_time REAL NOT NULL,
                final_wave INTEGER NOT NULL,
                score INTEGER NOT NULL,
                enemies_defeated INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                is_casual INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, run_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            INSERT INTO users VALUES (1, 'alice', 'alice', 'hash', '2026-10-24T10:00:00Z');
            INSERT INTO scores
                (user_id, run_id, survival_time, final_wave, score, enemies_defeated, submitted_at)
            VALUES (1, 'old-run', 64.2, 5, 1500, 14, '2026-10-24T10:01:00Z');
            """
        )

    import elemental_api.database.connection as connection_module
    from elemental_api.database.models import RunRecord

    connection_module.initialize_database()
    with Session(connection_module.get_engine()) as session:
        run = session.scalar(select(RunRecord).where(RunRecord.run_id == "old-run"))
    assert run is not None
    assert run.time_survived == 64.2
    assert run.wave_number == 5
    assert not {"score", "survival_time", "final_wave"} & {
        column["name"]
        for column in inspect(connection_module.get_engine()).get_columns("scores")
    }
