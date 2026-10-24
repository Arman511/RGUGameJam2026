.PHONY: install game compile-game api test lint format serve local-serve

install:
	uv sync --all-packages --all-groups

game:
	uv run --project apps/game python -m elemental_game.main

compile-game:
	uv run --project apps/game --with pyinstaller pyinstaller --noconfirm --clean --onefile --windowed --name ElementalKeep --icon apps/game/src/elemental_game/assets/icon.ico --paths apps/game/src --collect-all elemental_game apps/game/src/elemental_game/main.py

api:
	uv run --project services/api uvicorn elemental_api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

serve:
	docker compose up -d --build

local-serve:
	docker compose -f docker-compose.local.yml up --build
