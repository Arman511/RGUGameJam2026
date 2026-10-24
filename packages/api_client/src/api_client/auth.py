from __future__ import annotations

import json
from pathlib import Path

try:
    import keyring
except Exception:  # pragma: no cover - optional dependency
    keyring = None

from .http import APIClient, APIError, AuthError, ValidationError

class CredentialStore:
    def __init__(self, app_name: str = "elemental-keep", cache_path: str | None = None) -> None:
        self.app_name = app_name
        self.cache_path = Path(cache_path or (Path.home() / ".local" / "share" / "elemental_keep" / "credentials.json"))
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def save_token(self, token: str) -> None:
        if keyring is not None:
            keyring.set_password(self.app_name, "api_token", token)
            return
        self.cache_path.write_text(json.dumps({"api_token": token}), encoding="utf-8")

    def load_token(self) -> str | None:
        if keyring is not None:
            token = keyring.get_password(self.app_name, "api_token")
            if token:
                return token
        if self.cache_path.exists():
            try:
                payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (TypeError, ValueError):
                return None
            return payload.get("api_token")
        return None

    def clear_token(self) -> None:
        if keyring is not None:
            try:
                keyring.delete_password(self.app_name, "api_token")
            except keyring.errors.PasswordDeleteError:
                pass
        if self.cache_path.exists():
            try:
                payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (TypeError, ValueError):
                payload = {}
            payload.pop("api_token", None)
            self.cache_path.write_text(json.dumps(payload), encoding="utf-8")

def keyring_available() -> bool:
    return keyring is not None

def register(client: APIClient, username: str, password: str) -> dict[str, object]:
    return client.post(
        "/api/v1/auth/register",
        json_body={"username": username, "password": password},
    )

def login(client: APIClient, username: str, password: str) -> dict[str, object]:
    return client.post(
        "/api/v1/auth/login",
        json_body={"username": username, "password": password},
    )

def logout(client: APIClient) -> dict[str, object]:
    return client.post("/api/v1/auth/logout")

def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
