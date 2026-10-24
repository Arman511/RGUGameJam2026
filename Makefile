.PHONY: install game api test lint format

install:
	uv sync --all-packages --all-groups

game:
	uv run --package elemental-game python -m elemental_game.main

api:
	uv run --package elemental-api uvicorn elemental_api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

serve:
	docker compose up -d --build
