# Elemental Keep

Elemental Keep is a 2D top-down farming and tower-defence survival game built as a Python monorepo.

## Project overview
- Offline solo gameplay works without any API.
- Local leaderboard results save to the OS app-data directory.
- Optional online leaderboards and account features run through the FastAPI service.
- Game rules live in the pure-Python `game-core` package so rendering and networking stay decoupled.

## Requirements
- Python 3.12+
- uv

## Setup
```bash
uv sync --all-packages --all-groups
```

## Run the solo game
```bash
uv run --project apps/game python -m elemental_game.main
```

Start directly in the game, using a saved login when available or playing as a
guest otherwise:
```bash
uv run --project apps/game python -m elemental_game.main --skip-menu
```

## Build a standalone game
```bash
make compile-game
```

The executable is written to `dist/ElementalKeep` (with a `.exe` extension on
Windows). Run this command on the platform you want to build for: PyInstaller
does not cross-compile, so build Windows releases on Windows, macOS releases on
macOS, and Linux releases on Linux.

## Enviroment variables (Game)
- ELEMENTAL_KEEP_API_BASE_URL - Set this to change the games backendend server for global leaderboard

## Run the API locally
```bash
uv run --project services/api uvicorn elemental_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Controls
- Left click: interact with farm plots and UI
- 1-6: select crop or turret types
- Space: start next wave / continue
- Escape: pause

## Local database and credentials
Local leaderboard data is stored in the OS app-data directory, not in the repository. The API database defaults to `./.local/elemental_api.db` when `ELEMENTAL_API_DB_PATH` is not set. Credential storage uses `keyring` when available; otherwise the client falls back to a private per-user file.

## Tests
```bash
uv run pytest
uv run ruff check .
```

## Licenses
The project is licensed under the [MIT License](LICENSE). Audio tracks are
covered by their respective licenses. Background music is stored as Ogg Vorbis
for Pygame playback; the normal playlist randomly selects a track and advances
when it ends. Enemy and boss tracks remain separate looping tracks.

- `background.ogg` — Pixabay, andriig — [license certificate](licenses/background-license.txt)
- `boss.ogg` — Pixabay, jonasblakewood — [license certificate](licenses/boss-license.txt)
- `enemies.ogg` — Pixabay, mondamusic — [license certificate](licenses/enemies-license.txt)
- `farm-and-tavern.ogg` — Pixabay, benvibrant
- `cinematic-rural-folk.ogg` — Pixabay, desifreemusic
- `autumn-farm-folk.ogg` — Pixabay, moonpetalmedia
- `starostin-folk.ogg` — Pixabay, starostin — [license certificate](licenses/starostin-folk-license.txt)

The Pixabay [License Summary](https://pixabay.com/service/license-summary/)
applies to Pixabay music.
