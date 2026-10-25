.PHONY: install game compile-game api test coverage lint format serve local-serve release game-skip-menu

install:
	uv sync --all-packages --all-groups

game:
	uv run --project apps/game python -m elemental_game.main


game-skip-menu:
	uv run --project apps/game python -m elemental_game.main --skip-menu

compile-game:
	uv run --project apps/game --with pyinstaller pyinstaller --noconfirm --clean --onefile --windowed --name ElementalKeep --icon apps/game/src/elemental_game/assets/icon.ico --paths apps/game/src --collect-all elemental_game apps/game/src/elemental_game/main.py

api:
	uv run --project services/api uvicorn elemental_api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

coverage:
	uv run pytest --cov=elemental_game --cov=elemental_api --cov-report=term-missing

lint:
	uv run ruff check .

format:
	uv run ruff format .

serve:
	docker compose up -d --build

local-serve:
	docker compose -f docker-compose.local.yml up --build


release:
	@git fetch origin --tags --force
	@read -p "Enter release tag (e.g. v1.0.0 or ev1.0.0): " tag; \
	if [ -z "$$tag" ]; then \
		echo "Error: tag cannot be empty"; \
		exit 1; \
	fi; \
	case "$$tag" in \
		ev*) expected_branch="experimental" ;; \
		*) expected_branch="main" ;; \
	esac; \
	current_branch=$$(git branch --show-current); \
	if [ "$$current_branch" != "$$expected_branch" ]; then \
		echo "Error: tag '$$tag' requires branch '$$expected_branch', but you're on '$$current_branch'."; \
		exit 1; \
	fi; \
	if git rev-parse -q --verify "refs/tags/$$tag" >/dev/null || \
	   git ls-remote --exit-code --tags origin "refs/tags/$$tag" >/dev/null 2>&1; then \
		echo "Error: tag '$$tag' already exists locally or remotely."; \
		exit 1; \
	fi; \
	git tag "$$tag" && \
	git push origin "$$tag"
