from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
import os
from typing import Any

import httpx
from pydantic import BaseModel
from elemental_game import config

from .models import (
    LeaderboardResponse,
    LocalRunRecord,
    RunSubmission,
    RunSubmittedResponse,
)


class APIError(RuntimeError):
    pass


class AuthError(APIError):
    pass


class ValidationError(APIError):
    pass


@dataclass
class APIClient:
    base_url: str = config.ELEMENTAL_KEEP_API_BASE_URL
    timeout: float = 5.0
    token: str | None = None
    token_provider: Callable[[], str | None] | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self.token_provider() if self.token_provider is not None else self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | BaseModel | None = None,
    ) -> dict[str, Any]:
        if isinstance(json_body, BaseModel):
            json_body = json_body.model_dump(mode="json")
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

    def post(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | BaseModel | None = None,
    ) -> dict[str, Any]:
        return self.request("POST", path, json_body=json_body)

    def submit_run(self, run: RunSubmission) -> RunSubmittedResponse:
        response = self.post("/api/v1/scores", json_body=run)
        return RunSubmittedResponse.model_validate(response)

    def submit_local_run(
        self, run: LocalRunRecord | dict[str, Any]
    ) -> RunSubmittedResponse:
        local_score = (
            run
            if isinstance(run, LocalRunRecord)
            else LocalRunRecord.model_validate(run)
        )
        return self.submit_run(local_score.to_submission())

    def get_leaderboard(self, limit: int = 10) -> LeaderboardResponse:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        response = self.get(f"/api/v1/leaderboard?limit={limit}")
        return LeaderboardResponse.model_validate(response)
