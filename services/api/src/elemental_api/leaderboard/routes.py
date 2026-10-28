from __future__ import annotations

import calendar
from datetime import UTC, datetime, time, timedelta
from typing import Annotated, Literal

from elemental_api.auth.routes import get_current_user
from elemental_api.database.connection import get_db
from elemental_api.database.models import RunRecord, User
from elemental_api.schemas import (
    LeaderboardFilters,
    LeaderboardResponse,
    RunResponse,
    RunSubmit,
    RunSubmittedResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1")


def _subtract_months(value: datetime, months: int) -> datetime:
    month_index = value.month - months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str, Query(max_length=128)] = "",
    sort: Literal[
        "time_survived",
        "wave_number",
        "enemies_defeated",
        "username",
    ] = "time_survived",
    direction: Literal["asc", "desc"] = "desc",
    filters: LeaderboardFilters = Depends(),
) -> LeaderboardResponse:
    query = select(RunRecord, User.username).join(User, User.id == RunRecord.user_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    if filters.period == "last_hour":
        query = query.where(RunRecord.submitted_at >= now - timedelta(hours=1))
    elif filters.period == "last_day":
        query = query.where(RunRecord.submitted_at >= now - timedelta(days=1))
    elif filters.period == "last_week":
        query = query.where(RunRecord.submitted_at >= now - timedelta(weeks=1))
    elif filters.period == "last_month":
        query = query.where(RunRecord.submitted_at >= _subtract_months(now, 1))
    elif filters.period == "last_year":
        query = query.where(RunRecord.submitted_at >= _subtract_months(now, 12))
    elif filters.period == "custom":
        assert filters.start_date is not None and filters.end_date is not None
        start = datetime.combine(filters.start_date, time.min)
        end = datetime.combine(filters.end_date + timedelta(days=1), time.min)
        query = query.where(
            RunRecord.submitted_at >= start,
            RunRecord.submitted_at < end,
        )

    normalized_search = search.strip().lower()
    if normalized_search:
        query = query.where(
            func.lower(User.username).contains(normalized_search, autoescape=True)
            | func.lower(RunRecord.run_id).contains(normalized_search, autoescape=True)
        )

    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    sort_column = {
        "time_survived": RunRecord.time_survived,
        "wave_number": RunRecord.wave_number,
        "enemies_defeated": RunRecord.enemies_defeated,
        "username": User.normalized_username,
    }[sort]
    order_by = sort_column.asc() if direction == "asc" else sort_column.desc()
    tie_breakers = (
        (
            RunRecord.time_survived.desc(),
            RunRecord.enemies_defeated.desc(),
            RunRecord.wave_number.desc(),
            RunRecord.submitted_at.desc(),
        )
        if sort == "time_survived"
        else ()
    )
    rows = db.execute(
        query.order_by(order_by, *tie_breakers, RunRecord.id.asc())
        .offset(offset)
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
    return LeaderboardResponse(scores=scores, total=total, offset=offset, limit=limit)


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
