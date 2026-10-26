import asyncio
import importlib
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from io import StringIO

import httpx
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
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"


@pytest.mark.parametrize(
    "password",
    ["lowercase1!", "UPPERCASE1!", "NoDigits!!", "NoSymbol123"],
)
def test_registration_rejects_passwords_missing_complexity(password, client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": password},
    )

    assert response.status_code == 422


def test_admin_routes_require_a_configured_token(client, monkeypatch) -> None:
    monkeypatch.delenv("ELEMENTAL_API_ADMIN_TOKEN", raising=False)

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 503
    assert response.json()["detail"] == "Admin endpoints are not configured"


def test_admin_routes_list_users_and_delete_user_records(client, monkeypatch) -> None:
    from elemental_api.database.connection import get_engine
    from elemental_api.database.models import AuthToken, RunRecord, User

    admin_token = "long-random-admin-token"
    monkeypatch.setenv("ELEMENTAL_API_ADMIN_TOKEN", admin_token)
    admin_headers = {"X-Admin-Token": admin_token}
    bad_auth = client.get(
        "/api/v1/admin/users",
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert bad_auth.status_code == 401

    for username in ("alice", "bob"):
        registered = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "S3cretpass!"},
        )
        assert registered.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "S3cretpass!"},
    )
    bearer_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    submitted = client.post(
        "/api/v1/scores",
        headers=bearer_headers,
        json={
            "run_id": "alice-run",
            "time_survived": 64.2,
            "wave_number": 5,
            "enemies_defeated": 14,
        },
    )
    assert submitted.status_code == 200

    users = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert [user["username"] for user in users.json()] == ["alice", "bob"]
    assert "password_hash" not in users.json()[0]

    alice_id = users.json()[0]["id"]
    deleted = client.delete(
        f"/api/v1/admin/users/{alice_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200

    assert client.get("/api/v1/auth/me", headers=bearer_headers).status_code == 401
    assert client.get("/api/v1/leaderboard").json()["scores"] == []
    remaining_users = client.get("/api/v1/admin/users", headers=admin_headers)
    assert [user["username"] for user in remaining_users.json()] == ["bob"]

    with Session(get_engine()) as session:
        assert session.scalar(select(User).where(User.username == "alice")) is None
        assert session.scalars(select(AuthToken)).all() == []
        assert session.scalars(select(RunRecord)).all() == []


def test_pages_link_to_download_page(client) -> None:
    download_page = client.get("/download")
    leaderboard_page = client.get("/")
    registration_page = client.get("/register")

    assert download_page.status_code == 200
    assert "Download the game" in download_page.text
    assert (
        'href="https://github.com/Arman511/RGUGameJam2026/releases"'
        in download_page.text
    )
    assert 'href="/register">Register</a>' in download_page.text
    assert leaderboard_page.status_code == 200
    assert 'href="/download">Download</a>' in leaderboard_page.text
    assert registration_page.status_code == 200
    assert 'href="/download">Download</a>' in registration_page.text


def test_game_version_endpoint_returns_release_details(client, monkeypatch) -> None:
    import elemental_api.main as app_module

    def github_response(*args, **kwargs):
        return httpx.Response(
            200,
            json={"tag_name": "v2.1.0"},
            request=httpx.Request("GET", args[0]),
        )

    _mock_github_request(monkeypatch, app_module, github_response)

    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "v2.1.0",
        "release_url": (
            "https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0"
        ),
    }


def test_game_version_endpoint_reports_github_failure(client, monkeypatch) -> None:
    import elemental_api.main as app_module

    def raise_connection_error(*args, **kwargs):
        raise httpx.ConnectError("GitHub unavailable")

    _mock_github_request(monkeypatch, app_module, raise_connection_error)

    response = client.get("/api/v1/version")

    assert response.status_code == 503


def test_game_version_endpoint_caches_latest_release(client, monkeypatch) -> None:
    import elemental_api.main as app_module

    requests = 0

    def fake_github_request(*args, **kwargs):
        nonlocal requests
        requests += 1
        return httpx.Response(
            200,
            json={"tag_name": "v2.1.0"},
            request=httpx.Request("GET", args[0]),
        )

    _mock_github_request(monkeypatch, app_module, fake_github_request)

    first_response = client.get("/api/v1/version")
    second_response = client.get("/api/v1/version")

    assert first_response.json() == second_response.json()
    assert requests == 1


def _mock_github_request(monkeypatch, app_module, request_handler) -> None:
    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return None

        async def get(self, *args, **kwargs):
            return request_handler(*args, **kwargs)

    monkeypatch.setattr(app_module.httpx, "AsyncClient", MockAsyncClient)


def test_multiplayer_room_relays_actions_and_match_results(client) -> None:
    with client.websocket_connect("/api/v1/matches") as host:
        host.send_json(
            {
                "version": 1,
                "type": "host",
                "payload": {"player_name": "Alice"},
            }
        )
        room_created = host.receive_json()
        room_code = room_created["payload"]["room_code"]

        with client.websocket_connect("/api/v1/matches") as guest:
            guest.send_json(
                {
                    "version": 1,
                    "type": "join",
                    "payload": {"player_name": "Bob", "room_code": room_code},
                }
            )
            host_started = host.receive_json()
            guest_started = guest.receive_json()
            assert host_started["type"] == guest_started["type"] == "match_started"
            assert host_started["payload"]["player_id"] == "player1"
            assert guest_started["payload"]["player_id"] == "player2"

            guest.send_json(
                {
                    "version": 1,
                    "type": "action",
                    "payload": {"action": "change_weather", "element": "FIRE"},
                }
            )
            assert host.receive_json()["type"] == "opponent_action"
            assert guest.receive_json()["type"] == "action_accepted"

            host.send_json(
                {
                    "version": 1,
                    "type": "match_ended",
                    "payload": {"result": "defeat"},
                }
            )
            assert host.receive_json()["payload"]["result"] == "defeat"
            assert guest.receive_json()["payload"]["result"] == "victory"


def test_match_manager_has_configurable_capacity_and_join_timeout(monkeypatch) -> None:
    from elemental_api.matches import (
        DEFAULT_JOIN_TIMEOUT_SECONDS,
        DEFAULT_MATCH_LIMIT,
        MatchManager,
    )

    monkeypatch.delenv("ELEMENTAL_MATCH_LIMIT", raising=False)
    monkeypatch.delenv("ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS", raising=False)
    default_manager = MatchManager()
    assert default_manager.room_limit == 100
    assert default_manager.join_timeout_seconds == 120

    monkeypatch.setenv("ELEMENTAL_MATCH_LIMIT", "7")
    monkeypatch.setenv("ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS", "30")
    manager = MatchManager()

    assert manager.room_limit == 7
    assert manager.join_timeout_seconds == 30
    assert DEFAULT_MATCH_LIMIT == 100
    assert DEFAULT_JOIN_TIMEOUT_SECONDS == 120


def test_multiplayer_config_returns_server_join_timeout(client) -> None:
    from elemental_api.matches import match_manager

    previous_timeout = match_manager.join_timeout_seconds
    try:
        match_manager.join_timeout_seconds = 45
        response = client.get("/api/v1/matches/config")

        assert response.status_code == 200
        assert response.json() == {"join_timeout_seconds": 45}
    finally:
        match_manager.join_timeout_seconds = previous_timeout


def test_match_queue_promotes_next_host_when_a_room_ends(client) -> None:
    from elemental_api.matches import match_manager

    previous_limit = match_manager.room_limit
    match_manager.room_limit = 1
    try:
        with client.websocket_connect("/api/v1/matches") as first_host:
            first_host.send_json(
                {"version": 1, "type": "host", "payload": {"player_name": "First"}}
            )
            first_room = first_host.receive_json()["payload"]["room_code"]
            with client.websocket_connect("/api/v1/matches") as queued_host:
                queued_host.send_json(
                    {"version": 1, "type": "host", "payload": {"player_name": "Next"}}
                )
                assert queued_host.receive_json()["type"] == "queued"
                with client.websocket_connect("/api/v1/matches") as opponent:
                    opponent.send_json(
                        {
                            "version": 1,
                            "type": "join",
                            "payload": {"room_code": first_room},
                        }
                    )
                    first_host.receive_json()
                    opponent.receive_json()
                    first_host.send_json(
                        {
                            "version": 1,
                            "type": "match_ended",
                            "payload": {"result": "defeat"},
                        }
                    )
                    first_host.receive_json()
                    opponent.receive_json()
                    promoted = queued_host.receive_json()
                    assert promoted["type"] == "room_created"
    finally:
        match_manager.room_limit = previous_limit


def test_host_room_expires_if_player_two_does_not_join(client) -> None:
    from elemental_api.matches import match_manager

    previous_timeout = match_manager.join_timeout_seconds
    match_manager.join_timeout_seconds = 0.05
    try:
        with client.websocket_connect("/api/v1/matches") as host:
            host.send_json(
                {"version": 1, "type": "host", "payload": {"player_name": "Waiting"}}
            )
            assert host.receive_json()["type"] == "room_created"
            expired = host.receive_json()
            assert expired["type"] == "room_expired"
            assert expired["payload"]["message"] == "Room expired. No player joined."
    finally:
        match_manager.join_timeout_seconds = previous_timeout


def test_duplicate_username_is_rejected(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
    )
    response = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
    )
    assert response.status_code == 409


def test_login_succeeds_and_returns_token(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "S3cretpass!"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert "token" in payload


def test_login_with_wrong_password_returns_unauthorized(client) -> None:
    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
    )

    response = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrongpass"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unexpected_error_is_logged_without_exposing_details(client) -> None:
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
        response = TestClient(client.app, raise_server_exceptions=False).post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "S3cretpass!"},
        )
    finally:
        api_logger.removeHandler(log_handler)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "database connection failed" not in response.text
    assert "Unhandled exception while handling API request" in log_output.getvalue()
    assert "client_ip=testclient" in log_output.getvalue()
    assert "user_agent='testclient'" in log_output.getvalue()
    assert "RuntimeError: database connection failed" in log_output.getvalue()


def test_api_request_logs_method_path_and_status(client) -> None:
    log_output = StringIO()
    log_handler = logging.StreamHandler(log_output)
    api_logger = logging.getLogger("elemental_api.main")
    api_logger.addHandler(log_handler)

    try:
        with TestClient(
            client.app,
            client=("203.0.113.24", 4567),
        ) as identified_client:
            response = identified_client.get(
                "/api/v1/leaderboard",
                headers={"User-Agent": "ElementalKeep/1.2"},
            )
    finally:
        api_logger.removeHandler(log_handler)

    assert response.status_code == 200
    assert (
        "API request completed method=GET path=/api/v1/leaderboard status=200"
        in log_output.getvalue()
    )
    assert "client_ip=203.0.113.24" in log_output.getvalue()
    assert "user_agent='ElementalKeep/1.2'" in log_output.getvalue()


def test_login_prunes_expired_and_revoked_tokens(client) -> None:
    from elemental_api.database.connection import get_engine
    from elemental_api.database.models import AuthToken, User

    client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "S3cretpass!"}
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
        "/api/v1/auth/login", json={"username": "alice", "password": "S3cretpass!"}
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
        json={"username": "alice", "password": "S3cretpass!"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "S3cretpass!"},
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


@pytest.mark.parametrize(
    ("path", "title", "description"),
    [
        (
            "/",
            "Elemental Keep Leaderboard",
            "Live Elemental Keep player leaderboard.",
        ),
        (
            "/register",
            "Create an account · Elemental Keep",
            "Create an Elemental Keep account.",
        ),
        (
            "/download",
            "Download · Elemental Keep",
            "Download Elemental Keep and defend your garden from the elements.",
        ),
    ],
)
def test_public_pages_include_seo_metadata(
    client, path: str, title: str, description: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert f"<title>{title}</title>" in response.text
    assert f'<meta name="description" content="{description}">' in response.text
    assert f'<meta property="og:title" content="{title}">' in response.text
    assert f'<meta property="og:description" content="{description}">' in response.text
    assert '<meta name="twitter:card" content="summary">' in response.text
    assert f'<link rel="canonical" href="http://testserver{path}">' in response.text


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
    assert "Return to the game and sign in" in register_script.text


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
