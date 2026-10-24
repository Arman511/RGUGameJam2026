from __future__ import annotations

import json
from pathlib import Path

try:
    import keyring
except ImportError:  # pragma: no cover - optional dependency
    keyring = None

from .http import APIClient
from .models import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
)


class CredentialStore:
    def __init__(
        self, app_name: str = "elemental-keep", cache_path: str | None = None
    ) -> None:
        self.app_name = app_name
        self.cache_path = Path(
            cache_path
            or (
                Path.home() / ".local" / "share" / "elemental_keep" / "credentials.json"
            )
        )
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


class AuthClient:
    def __init__(self, client: APIClient, credentials: CredentialStore) -> None:
        self.client = client
        self.credentials = credentials
        self.client.token_provider = credentials.load_token

    def register(self, username: str, password: str) -> RegisterResponse:
        request = RegisterRequest(username=username, password=password)
        response = self.client.post("/api/v1/auth/register", json_body=request)
        return RegisterResponse.model_validate(response)

    def login(self, username: str, password: str) -> AuthResponse:
        request = LoginRequest(username=username, password=password)
        response = self.client.post("/api/v1/auth/login", json_body=request)
        auth_response = AuthResponse.model_validate(response)
        self.credentials.save_token(auth_response.token)
        return auth_response

    def logout(self) -> MessageResponse:
        response = self.client.post("/api/v1/auth/logout")
        self.credentials.clear_token()
        return MessageResponse.model_validate(response)


def keyring_available() -> bool:
    return keyring is not None


def register(client: APIClient, username: str, password: str) -> RegisterResponse:
    request = RegisterRequest(username=username, password=password)
    response = client.post("/api/v1/auth/register", json_body=request)
    return RegisterResponse.model_validate(response)


def login(client: APIClient, username: str, password: str) -> AuthResponse:
    request = LoginRequest(username=username, password=password)
    response = client.post("/api/v1/auth/login", json_body=request)
    return AuthResponse.model_validate(response)


def logout(client: APIClient) -> MessageResponse:
    response = client.post("/api/v1/auth/logout")
    return MessageResponse.model_validate(response)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
