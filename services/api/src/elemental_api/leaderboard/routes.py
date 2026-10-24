from __future__ import annotations

from typing import Annotated

from elemental_api.auth.routes import get_current_user
from elemental_api.database.connection import get_db
from elemental_api.database.models import RunRecord, User
from elemental_api.schemas import (
    LeaderboardResponse,
    RunResponse,
    RunSubmit,
    RunSubmittedResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1")


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> LeaderboardResponse:
    rows = db.execute(
        select(RunRecord, User.username)
        .join(User, User.id == RunRecord.user_id)
        .order_by(
            RunRecord.time_survived.desc(),
            RunRecord.enemies_defeated.desc(),
            RunRecord.wave_number.desc(),
            RunRecord.submitted_at.desc(),
        )
        .limit(limit)
    )
    scores = [
        RunResponse(
            run_id=run.run_id,
            username=username,
            time_survived=run.time_survived,
            wave_number=run.wave_number,
            enemies_defeated=run.enemies_defeated,
            submitted_at=run.submitted_at,
        )
        for run, username in rows
    ]
    return LeaderboardResponse(scores=scores)


@router.post("/scores", response_model=RunSubmittedResponse)
def submit_run(
    payload: RunSubmit,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RunSubmittedResponse:
    run = RunRecord(
        user_id=user.id,
        **payload.model_dump(),
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Run ID already used"
        ) from exc
    return RunSubmittedResponse(run_id=run.run_id)
