from __future__ import annotations

from fastapi import FastAPI

from elemental_api.auth.routes import router as auth_router, get_current_user
from elemental_api.database.connection import initialize_database
from elemental_api.leaderboard.routes import router as leaderboard_router

app = FastAPI(title="Elemental Keep API")
app.include_router(auth_router)
app.include_router(leaderboard_router)

@app.on_event("startup")
def startup() -> None:
    initialize_database()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
