from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from elemental_api.auth.passwords import hash_password, verify_password
from elemental_api.auth.tokens import generate_token, token_expiry, token_hash
from elemental_api.database.connection import get_db
from elemental_api.database.models import AuthToken, User
from elemental_api.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/auth")
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenKeyService:
    issue: Callable[[], str] = generate_token
    digest: Callable[[str], str] = token_hash


def get_token_key_service() -> TokenKeyService:
    return TokenKeyService()


def get_bearer_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    bearer_key: Annotated[str, Depends(get_bearer_key)],
    db: Annotated[Session, Depends(get_db)],
    key_service: Annotated[TokenKeyService, Depends(get_token_key_service)],
) -> User:
    token = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == key_service.digest(bearer_key))
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    if token is None or token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expires_at = token.expires_at
    if expires_at.tzinfo is not None:
        expires_at = expires_at.astimezone(UTC).replace(tzinfo=None)
    if now > expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.user


def _normalize_username(value: str) -> str:
    return value.strip().lower()


@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RegisterResponse:
    user = User(
        username=payload.username.strip(),
        normalized_username=_normalize_username(payload.username),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        ) from exc
    return RegisterResponse(
        user=UserResponse.model_validate(user), message="registered"
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    key_service: Annotated[TokenKeyService, Depends(get_token_key_service)],
) -> AuthResponse:
    user = db.scalar(
        select(User).where(
            User.normalized_username == _normalize_username(payload.username)
        )
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    now = datetime.now(UTC).replace(tzinfo=None)
    db.execute(
        delete(AuthToken).where(
            or_(AuthToken.expires_at <= now, AuthToken.revoked_at.is_not(None))
        )
    )
    expires_at = token_expiry().replace(tzinfo=None)
    bearer_key = key_service.issue()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=key_service.digest(bearer_key),
            expires_at=expires_at,
        )
    )
    db.commit()
    return AuthResponse(
        token=bearer_key,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    bearer_key: Annotated[str, Depends(get_bearer_key)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    key_service: Annotated[TokenKeyService, Depends(get_token_key_service)],
) -> MessageResponse:
    token = db.scalar(
        select(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.token_hash == key_service.digest(bearer_key),
        )
    )
    if token is not None:
        token.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    return MessageResponse(message="logged out")


@router.post("/logout_all", response_model=MessageResponse)
def logout_all(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[TokenKeyService, Depends(get_token_key_service)],
) -> MessageResponse:
    tokens = db.scalars(
        select(AuthToken).where(
            AuthToken.user_id == user.id,
        )
    ).all()
    for token in tokens:
        token.revoked_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return MessageResponse(message="logged out all sessions")
