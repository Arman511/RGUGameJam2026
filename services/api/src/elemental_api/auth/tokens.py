from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def token_expiry() -> datetime:
    return utc_now() + timedelta(days=365)

def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
