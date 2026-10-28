from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

_VERSION_PATTERN = re.compile(r"^(?:ev|v)?(\d+)\.(\d+)\.(\d+)(?:\+dev)?$")


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    release_url: str


def _version_parts(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid game version: {value!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def check_for_update(base_url: str, current_version: str) -> UpdateInfo | None:
    response = httpx.get(
        f"{base_url.rstrip('/')}/api/v1/version",
        timeout=3.0,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("The game server returned invalid version information.")

    latest_version = payload.get("version")
    release_url = payload.get("release_url")
    if not isinstance(latest_version, str) or not isinstance(release_url, str):
        raise TypeError("The game server returned invalid version information.")
    if _version_parts(latest_version) <= _version_parts(current_version):
        return None

    return UpdateInfo(version=latest_version, release_url=release_url)
