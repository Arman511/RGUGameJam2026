from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

class APIError(RuntimeError):
    pass

class AuthError(APIError):
    pass

class ValidationError(APIError):
    pass

@dataclass
class APIClient:
    base_url: str = "http://127.0.0.1:8000"
    timeout: float = 5.0
    token: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.request(
                method=method.upper(),
                url=f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                headers=self._headers(),
                json=json_body,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise APIError(f"Request failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except json.JSONDecodeError:
                payload = {"detail": response.text}
            detail = payload.get("detail", payload)
            if response.status_code == 401:
                raise AuthError(str(detail))
            if response.status_code == 422:
                raise ValidationError(str(detail))
            raise APIError(str(detail))
        if not response.content:
            return {}
        return response.json()

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(self, path: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", path, json_body=json_body)
