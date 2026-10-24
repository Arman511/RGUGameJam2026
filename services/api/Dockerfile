FROM ghcr.io/astral-sh/uv:alpine AS uv

FROM python:3.12-alpine AS builder

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/api/pyproject.toml services/api/uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY services/api/src ./src
COPY services/api/alembic.ini ./alembic.ini

RUN uv sync --frozen --no-dev

FROM python:3.12-alpine AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ELEMENTAL_API_DISABLE_DOCS=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic.ini /app/alembic.ini

EXPOSE 8000

CMD ["uvicorn", "elemental_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
