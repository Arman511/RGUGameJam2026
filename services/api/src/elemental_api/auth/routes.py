from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field

from elemental_api.auth.passwords import hash_password, verify_password
from elemental_api.auth.tokens import format_utc, generate_token, token_expiry, token_hash, utc_now
from elemental_api.database.connection import get_db_connection

router = APIRouter(prefix="/api/v1/auth")

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

class AuthResponse(BaseModel):
    token: str
    user: dict[str, Any]

def _normalize_username(value: str) -> str:
    return value.strip().lower()

def _get_user_from_db(connection: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    row = connection.execute(
        "SELECT id, username, normalized_username, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
    }

def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    token_hash_value = token_hash(token)
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT t.user_id, t.expires_at, t.revoked_at, u.username
            FROM auth_tokens t
            INNER JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (token_hash_value,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if row["revoked_at"] is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return _get_user_from_db(connection, row["user_id"])

@router.post("/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
    normalized = _normalize_username(payload.username)
    with get_db_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE normalized_username = ?",
            (normalized,),
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
        user_id = connection.execute(
            "INSERT INTO users(username, normalized_username, password_hash) VALUES (?, ?, ?)",
            (payload.username.strip(), normalized, hash_password(payload.password)),
        ).lastrowid
        connection.commit()
        user = _get_user_from_db(connection, user_id)
    return {"user": user, "message": "registered"}

@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    normalized = _normalize_username(payload.username)
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE normalized_username = ?",
            (normalized,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = generate_token()
        expires_at = format_utc(token_expiry())
        connection.execute(
            "INSERT INTO auth_tokens(user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (row["id"], token_hash(token), expires_at),
        )
        connection.commit()
        return {
            "token": token,
            "user": {"id": row["id"], "username": row["username"]},
        }

@router.get("/me")
def current_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return user

@router.post("/logout")
def logout(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    token = None
    authorization = None
    # A real implementation would receive the token from the Authorization header via dependency injection.
    # This simplified version uses the user context that was already verified and revokes all active tokens.
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT id FROM auth_tokens WHERE user_id = ? AND revoked_at IS NULL",
            (user["id"],),
        ).fetchall()
        for row in rows:
            connection.execute(
                "UPDATE auth_tokens SET revoked_at = ? WHERE id = ?",
                (format_utc(utc_now()), row["id"]),
            )
        connection.commit()
    return {"message": "logged out"}
