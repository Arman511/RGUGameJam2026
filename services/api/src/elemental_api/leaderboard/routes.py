from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from elemental_api.auth.routes import get_current_user
from elemental_api.database.connection import get_db_connection

router = APIRouter(prefix="/api/v1")

class ScoreSubmit(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    survival_time: float = Field(ge=0.0, le=86400)
    final_wave: int = Field(ge=1, le=1000)
    score: int = Field(ge=0, le=10000000)
    enemies_defeated: int = Field(ge=0, le=100000)
    is_casual: bool = True

@router.get("/leaderboard")
def leaderboard(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.run_id, u.username, s.survival_time, s.final_wave, s.score, s.enemies_defeated, s.submitted_at
            FROM scores s
            INNER JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC, s.submitted_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"scores": [dict(row) for row in rows]}

@router.post("/scores")
def submit_score(payload: ScoreSubmit, user: dict[str, Any] = None) -> dict[str, Any]:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    with get_db_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM scores WHERE user_id = ? AND run_id = ?",
            (user["id"], payload.run_id),
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run ID already used")
        connection.execute(
            """
            INSERT INTO scores(user_id, run_id, survival_time, final_wave, score, enemies_defeated, is_casual)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user["id"], payload.run_id, payload.survival_time, payload.final_wave, payload.score, payload.enemies_defeated, int(payload.is_casual)),
        )
        connection.commit()
    return {"status": "ok", "run_id": payload.run_id}
