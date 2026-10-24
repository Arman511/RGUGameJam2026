from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from elemental_api.auth.routes import router as auth_router
from elemental_api.database.connection import initialize_database
from elemental_api.leaderboard.routes import router as leaderboard_router


class HealthResponse(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="Elemental Keep API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(leaderboard_router)


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")
