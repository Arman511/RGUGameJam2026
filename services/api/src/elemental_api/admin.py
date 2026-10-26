from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from elemental_api.database.connection import get_db
from elemental_api.database.models import AuthToken, RunRecord, User
from elemental_api.schemas import MessageResponse, UserResponse

ADMIN_TOKEN_ENV = "ELEMENTAL_API_ADMIN_TOKEN"


def require_admin_token(
    token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    expected_token = os.environ.get(ADMIN_TOKEN_ENV)
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are not configured",
        )
    if token is None or not secrets.compare_digest(
        token.encode("utf-8"), expected_token.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )


router = APIRouter(
    prefix="/api/v1/admin",
    dependencies=[Depends(require_admin_token)],
)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[UserResponse]:
    users = db.scalars(select(User).order_by(User.id).offset(offset).limit(limit)).all()
    return [UserResponse.model_validate(user) for user in users]


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
    db.execute(delete(RunRecord).where(RunRecord.user_id == user_id))
    db.delete(user)
    db.commit()
    return MessageResponse(message="User and associated records deleted")
