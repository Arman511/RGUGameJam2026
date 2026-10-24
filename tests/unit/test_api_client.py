from __future__ import annotations

from typing import Any

import httpx
from api_client import APIClient
from api_client import http as http_module
from api_client.models import LocalRunRecord, RunSubmittedResponse


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
        "is_casual": True,
    }
