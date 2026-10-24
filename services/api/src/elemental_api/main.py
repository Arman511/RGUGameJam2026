from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from elemental_api.auth.routes import router as auth_router
from elemental_api.database.connection import initialize_database
from elemental_api.leaderboard.routes import router as leaderboard_router

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "template"))
ALLOWED_ORIGINS = [
    "https://elemental-keep.armandev.co.uk",
    "http://localhost",
    "https://localhost",
]
LOCAL_ORIGIN_PATTERN = r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?"


class WebSocketOriginMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        allowed_origins: list[str],
        allowed_origin_regex: str,
    ) -> None:
        self.app = app
        self.allowed_origins = set(allowed_origins)
        self.allowed_origin_pattern = re.compile(allowed_origin_regex)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return

        origin_bytes = dict(scope["headers"]).get(b"origin")
        if origin_bytes is not None:
            origin = origin_bytes.decode("latin-1")
            if (
                origin not in self.allowed_origins
                and self.allowed_origin_pattern.fullmatch(origin) is None
            ):
                await send({"type": "websocket.close", "code": 1008})
                return

        await self.app(scope, receive, send)


class HealthResponse(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    initialize_database()
    yield


app = FastAPI(title="Elemental Keep API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=LOCAL_ORIGIN_PATTERN,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(
    WebSocketOriginMiddleware,
    allowed_origins=ALLOWED_ORIGINS,
    allowed_origin_regex=LOCAL_ORIGIN_PATTERN,
)
app.mount(
    "/static",
    StaticFiles(directory=PACKAGE_DIR / "static"),
    name="static",
)
app.include_router(auth_router)
app.include_router(leaderboard_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def leaderboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"page_title": "Elemental Keep Leaderboard"},
    )


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
def registration_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"page_title": "Create an account · Elemental Keep"},
    )


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")
