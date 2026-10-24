from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ..database.local_database import get_default_data_dir

try:
    import keyring
except ImportError:
    keyring = None

from .http import APIClient
from .models import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)


class CredentialStore:
    def __init__(
        self, app_name: str = "elemental-keep", cache_path: str | None = None
    ) -> None:
        self.app_name = app_name
        self.cache_path = (
            Path(cache_path)
            if cache_path is not None
            else get_default_data_dir() / "credentials.json"
        )
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def save_token(self, token: str, expires_at: datetime) -> None:
        if keyring is not None:
            try:
                keyring.set_password(self.app_name, "api_token", token)
            except keyring.errors.NoKeyringError:
                payload = self._read_cache()
                payload["api_token"] = token
                payload["expires_at"] = expires_at.isoformat()
                self._write_cache(payload)
                return
        payload = self._read_cache()
        if keyring is None:
            payload["api_token"] = token
        payload["expires_at"] = expires_at.isoformat()
        self._write_cache(payload)

    def load_token(self) -> str | None:
        if self.token_expired():
            self.clear_token()
            return None
        if keyring is not None:
            try:
                token = keyring.get_password(self.app_name, "api_token")
            except keyring.errors.NoKeyringError:
                token = None
            if token:
                return token
        token = self._read_cache().get("api_token")
        return token if isinstance(token, str) else None

    def token_expired(self) -> bool:
        expires_at = self._read_cache().get("expires_at")
        if expires_at is None:
            return True
        if not isinstance(expires_at, str):
            return True
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return expiry <= datetime.now(UTC)

    def save_username(self, username: str) -> None:
        payload = self._read_cache()
        payload["username"] = username
        self._write_cache(payload)

    def load_username(self) -> str | None:
        username = self._read_cache().get("username")
        return username if isinstance(username, str) else None

    def _read_cache(self) -> dict[str, object]:
        if not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_cache(self, payload: dict[str, object]) -> None:
        self.cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def clear_token(self) -> None:
        if keyring is not None:
            try:
                keyring.delete_password(self.app_name, "api_token")
            except keyring.errors.NoKeyringError:
                pass
        if self.cache_path.exists():
            try:
                payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (TypeError, ValueError):
                payload = {}
            payload.pop("api_token", None)
            payload.pop("username", None)
            payload.pop("expires_at", None)
            self._write_cache(payload)


class AuthClient:
    def __init__(self, client: APIClient, credentials: CredentialStore) -> None:
        self.client = client
        self.credentials = credentials
        self.client.token_provider = credentials.load_token

    def current_user(self) -> UserResponse:
        response = self.client.get("/api/v1/auth/me")
        return UserResponse.model_validate(response)

    def register(self, username: str, password: str) -> RegisterResponse:
        request = RegisterRequest(username=username, password=password)
        response = self.client.post("/api/v1/auth/register", json_body=request)
        return RegisterResponse.model_validate(response)

    def login(self, username: str, password: str) -> AuthResponse:
        request = LoginRequest(username=username, password=password)
        response = self.client.post("/api/v1/auth/login", json_body=request)
        auth_response = AuthResponse.model_validate(response)
        self.credentials.save_token(auth_response.token, auth_response.expires_at)
        self.credentials.save_username(auth_response.user.username)
        return auth_response

    def logout(self) -> MessageResponse:
        if not self.credentials.load_token():
            print("Not logged in")
            return MessageResponse(message="Not logged in")

        response = self.client.post("/api/v1/auth/logout")
        self.credentials.clear_token()
        return MessageResponse.model_validate(response)

    def username_for_run(self, guest_username: str | None = None) -> str:
        if self.credentials.load_token():
            username = self.credentials.load_username()
            if username is None:
                raise RuntimeError("sign in again to associate runs with your account")
            return username

        if guest_username is None or not guest_username.strip():
            raise ValueError("enter a username to save this run")
        return guest_username.strip()
