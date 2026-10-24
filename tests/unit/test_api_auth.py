import asyncio
import importlib
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from elemental_api.main import (
    ALLOWED_ORIGINS,
    LOCAL_ORIGIN_PATTERN,
    WebSocketOriginMiddleware,
)
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


def test_login_with_wrong_password_returns_unauthorized(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )

    response = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrongpass"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unexpected_error_is_logged_without_exposing_details(
    client
) -> None:
    from elemental_api.auth.routes import get_db

    log_output = StringIO()
    log_handler = logging.StreamHandler(log_output)
    api_logger = logging.getLogger("elemental_api.main")
    api_logger.addHandler(log_handler)

    def fail_database():
        raise RuntimeError("database connection failed")
        yield

    client.app.dependency_overrides[get_db] = fail_database

    try:
        response = TestClient(
            client.app, raise_server_exceptions=False
        ).post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "secretpass"},
        )
    finally:
        api_logger.removeHandler(log_handler)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "database connection failed" not in response.text
    assert "Unhandled exception while handling API request" in log_output.getvalue()
    assert "RuntimeError: database connection failed" in log_output.getvalue()


def test_api_request_logs_method_path_and_status(client) -> None:
    log_output = StringIO()
    log_handler = logging.StreamHandler(log_output)
    api_logger = logging.getLogger("elemental_api.main")
    api_logger.addHandler(log_handler)

    try:
        response = client.get("/api/v1/leaderboard")
    finally:
        api_logger.removeHandler(log_handler)

    assert response.status_code == 200
    assert (
        "API request completed method=GET path=/api/v1/leaderboard status=200"
        in log_output.getvalue()
    )


def test_login_prunes_expired_and_revoked_tokens(client) -> None:
    from elemental_api.database.connection import get_engine
    from elemental_api.database.models import AuthToken, User

    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "secretpass"}
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(get_engine()) as session:
        user = session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        session.add_all(
            [
                AuthToken(
                    user_id=user.id,
                    token_hash="expired-token-hash",
                    expires_at=now - timedelta(days=1),
                ),
                AuthToken(
                    user_id=user.id,
                    token_hash="revoked-token-hash",
                    expires_at=now + timedelta(days=1),
                    revoked_at=now,
                ),
                AuthToken(
                    user_id=user.id,
                    token_hash="active-token-hash",
                    expires_at=now + timedelta(days=1),
                ),
            ]
        )
        session.commit()

    response = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "secretpass"}
    )
    assert response.status_code == 200

    with Session(get_engine()) as session:
        token_hashes = set(session.scalars(select(AuthToken.token_hash)).all())
    assert "active-token-hash" in token_hashes
    assert "expired-token-hash" not in token_hashes
    assert "revoked-token-hash" not in token_hashes
    assert len(token_hashes) == 2


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
        connection.executescript("""
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
            """)

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
    assert "is_casual" not in {
        column["name"]
        for column in inspect(connection_module.get_engine()).get_columns("scores")
    }


def test_auth_and_leaderboard_indexes_are_created(client) -> None:
    from elemental_api.database.connection import get_engine

    indexes = inspect(get_engine())
    auth_indexes = {index["name"] for index in indexes.get_indexes("auth_tokens")}
    score_indexes = {index["name"] for index in indexes.get_indexes("scores")}

    assert {
        "ix_auth_tokens_user_id",
        "ix_auth_tokens_expires_at",
        "ix_auth_tokens_revoked_at",
    } <= auth_indexes
    assert "ix_scores_leaderboard_rank" in score_indexes


def test_leaderboard_page_is_served(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hall of Keepers" in response.text
    assert 'id="search"' in response.text
    assert 'id="theme-toggle"' in response.text
    assert "/static/css/leaderboard.css" in response.text
    assert "/static/js/leaderboard.js" in response.text


def test_registration_page_is_served(client) -> None:
    response = client.get("/register")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Create your account" in response.text
    assert 'id="register-form"' in response.text
    assert "/static/js/register.js" in response.text


def test_leaderboard_static_assets_are_served(client) -> None:
    stylesheet = client.get("/static/css/leaderboard.css")
    script = client.get("/static/js/leaderboard.js")
    register_script = client.get("/static/js/register.js")

    assert stylesheet.status_code == 200
    assert 'data-bs-theme="light"' in stylesheet.text
    assert script.status_code == 200
    assert "REFRESH_INTERVAL = 7000" in script.text
    assert register_script.status_code == 200
    assert "/api/v1/auth/register" in register_script.text


@pytest.mark.parametrize(
    "origin",
    [
        "https://elemental-keep.armandev.co.uk",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],
)
def test_cors_allows_leaderboard_origins(client, origin: str) -> None:
    response = client.options(
        "/api/v1/leaderboard",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://elemental-keep.armandev.co.uk", True),
        ("http://localhost:5173", True),
        ("http://127.0.0.1:8000", True),
        ("https://attacker.example", False),
    ],
)
def test_websocket_origin_policy(origin: str, allowed: bool) -> None:
    forwarded = False
    sent_messages = []

    async def app(scope, receive, send):
        nonlocal forwarded
        forwarded = True
        await send({"type": "websocket.accept"})

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        sent_messages.append(message)

    middleware = WebSocketOriginMiddleware(
        app,
        allowed_origins=ALLOWED_ORIGINS,
        allowed_origin_regex=LOCAL_ORIGIN_PATTERN,
    )
    scope = {
        "type": "websocket",
        "headers": [(b"origin", origin.encode("ascii"))],
    }
    asyncio.run(middleware(scope, receive, send))

    assert forwarded is allowed
    assert sent_messages == (
        [{"type": "websocket.accept"}]
        if allowed
        else [{"type": "websocket.close", "code": 1008}]
    )
