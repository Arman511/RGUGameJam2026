from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from elemental_api.auth.routes import router as auth_router
from elemental_api.database.connection import initialize_database
from elemental_api.leaderboard.routes import router as leaderboard_router

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    initialize_database()
    yield


app = FastAPI(title="Elemental Keep API", lifespan=lifespan)


@app.middleware("http")
async def log_api_requests(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    started_at = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "API request completed method=%s path=%s status=%d duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception while handling API request method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


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
def health() -> dict[str, str]:
    return {"status": "ok"}
