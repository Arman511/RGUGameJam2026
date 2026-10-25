from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from elemental_game.api_client import APIClient, AuthClient, CredentialStore
from elemental_game.api_client import http as http_module
from elemental_game.api_client.models import LocalRunRecord, RunSubmittedResponse


def test_submit_local_run_maps_local_database_fields(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"status": "ok", "run_id": "local-run"},
            request=httpx.Request("POST", kwargs["url"]),
        )

    monkeypatch.setattr(http_module.httpx, "request", fake_request)
    client = APIClient(token_provider=lambda: "test-token")
    local_record = LocalRunRecord.model_validate(
        {
            "run_id": "local-run",
            "timestamp": "2026-10-24 10:00:00",
            "survival_time": 64.2,
            "final_wave": 5,
            "enemies_defeated": 14,
        }
    )

    response = client.submit_local_run(local_record)

    assert isinstance(response, RunSubmittedResponse)
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["json"] == {
        "run_id": "local-run",
        "time_survived": 64.2,
        "wave_number": 5,
        "enemies_defeated": 14,
    }


def test_multiplayer_client_connects_to_configured_api_server(monkeypatch) -> None:
    import json

    from elemental_game.networking import client as networking_module

    captured: dict[str, Any] = {}

    class FakeConnection:
        def send(self, message: str) -> None:
            captured["message"] = message

    def fake_connect(uri: str, **_kwargs: Any) -> FakeConnection:
        captured["uri"] = uri
        return FakeConnection()

    monkeypatch.setattr(networking_module, "connect", fake_connect)

    networking_module.MultiplayerClient._open(
        "alice",
        "host",
        {},
        base_url="https://staging.example.com:8443",
    )

    assert captured["uri"] == "wss://staging.example.com:8443/api/v1/matches"
    assert json.loads(captured["message"])["payload"]["player_name"] == "alice"


def test_auth_client_uses_active_username_and_guest_name(tmp_path, monkeypatch) -> None:
    from elemental_game.api_client import auth as auth_module

    monkeypatch.setattr(auth_module, "keyring", None)
    credentials = CredentialStore(cache_path=str(tmp_path / "credentials.json"))
    client = APIClient()
    auth = AuthClient(client, credentials)
    current_user = {"id": 1, "username": "alice"}

    def fake_post(path: str, **kwargs: Any) -> dict[str, Any]:
        if path.endswith("/login"):
            return {
                "token": f"token-{current_user['username']}",
                "user": current_user,
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        return {"message": "logged out"}

    monkeypatch.setattr(client, "post", fake_post)
    auth.login("alice", "password")
    assert auth.username_for_run("guest") == "alice"

    current_user = {"id": 2, "username": "bob"}
    auth.login("bob", "password")
    assert auth.username_for_run("guest") == "bob"

    auth.logout()
    assert auth.username_for_run(" guest ") == "guest"


def test_credentials_persist_expiry_and_reject_expired_tokens(
    tmp_path, monkeypatch
) -> None:
    from elemental_game.api_client import auth as auth_module

    monkeypatch.setattr(auth_module, "keyring", None)
    credentials = CredentialStore(cache_path=str(tmp_path / "credentials.json"))
    expiry = datetime.now(UTC) + timedelta(days=1)

    credentials.save_token("valid-token", expiry)
    credentials.save_username("alice")
    assert credentials.load_token() == "valid-token"
    assert credentials.load_username() == "alice"
    assert credentials.token_expired() is False

    credentials.save_token("expired-token", datetime.now(UTC) - timedelta(seconds=1))
    assert credentials.token_expired() is True
    assert credentials.load_token() is None
    assert credentials.load_username() is None


def test_credentials_fall_back_when_keyring_backend_is_unavailable(
    tmp_path, monkeypatch
) -> None:
    import keyring
    from elemental_game.api_client import auth as auth_module

    def keyring_unavailable(*_args: Any) -> None:
        raise keyring.errors.NoKeyringError("no backend available")

    monkeypatch.setattr(auth_module.keyring, "set_password", keyring_unavailable)
    monkeypatch.setattr(auth_module.keyring, "get_password", keyring_unavailable)
    monkeypatch.setattr(auth_module.keyring, "delete_password", keyring_unavailable)
    credentials = CredentialStore(cache_path=str(tmp_path / "credentials.json"))

    credentials.save_token("fallback-token", datetime.now(UTC) + timedelta(days=1))

    assert credentials.load_token() == "fallback-token"

    credentials.clear_token()

    assert credentials.load_token() is None


def test_expired_credentials_handle_missing_keyring_entry(
    tmp_path, monkeypatch
) -> None:
    import keyring
    from elemental_game.api_client import auth as auth_module

    def missing_password(*_args: Any) -> None:
        raise keyring.errors.PasswordDeleteError("elemental-keep")

    monkeypatch.setattr(auth_module.keyring, "delete_password", missing_password)
    credentials = CredentialStore(cache_path=str(tmp_path / "credentials.json"))

    assert credentials.load_token() is None
