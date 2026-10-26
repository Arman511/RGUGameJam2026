# Elemental Keep

Elemental Keep is a 2D top-down farming and tower-defence survival game built as a Python monorepo.

## Project overview
- Offline solo gameplay works without any API.
- Local leaderboard results save to the OS app-data directory.
- Optional online leaderboards and account features run through the FastAPI service.

## Download the latest release

Download the latest ready-to-play game build from the
[GitHub Releases page](https://github.com/Arman511/RGUGameJam2026/releases/latest).
Choose the download for your operating system, then open the downloaded game.
The game checks for a newer release when its menu starts and offers a link to
download it; this check runs in the background and is skipped if the API server
is unavailable.
If no build is available for your platform, use the setup instructions below
to run it from source.

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

## How to play

From the main menu, choose **Play game** and select solo or 2-player VS. In
2-player VS, one player hosts a room and shares its six-character code; the
other player joins with that code.

Plant elemental seeds during the 60-second preparation phase, harvest mature
crops, and use five matching crops to build elemental turrets on soil pads.
Defend the house through 30-second enemy waves; bosses appear every fifth wave.
Defeated enemies can drop seeds. Your run is saved to the local leaderboard,
and you can choose to publish it to the online leaderboard when signed in.

The game also has a **Help / Controls** screen in its main menu. Main controls:

- WASD or arrow keys: move
- F: interact, plant, or build
- G: harvest crops
- M: open the shop; Tab and Shift+Tab switch shop tabs
- A/D or arrow keys: choose a seed tier in the shop
- O: show or hide turret ranges
- At the house turret, F to take control, A/D to aim, and Space to fire
- In two-player mode, V opens/closes attacks, Q/E selects a crop, and 1-4 or a
  click on an attack option sends it; Escape closes the panel
- Escape: cancel or go back

Press `H` to toggle the inventory HUD.

## Build a standalone game
```bash
make compile-game
```

The executable is written to `dist/ElementalKeep` (with a `.exe` extension on
Windows). Run this command on the platform you want to build for: PyInstaller
does not cross-compile, so build Windows releases on Windows, macOS releases on
macOS, and Linux releases on Linux.

## Connect the game to an API server

The game uses `https://elemental-keep.armandev.co.uk` by default for online
features. To use another server from a source checkout, create a `.env` file in
the repository root (next to `.env.example`) and set:

```dotenv
ELEMENTAL_KEEP_API_BASE_URL=http://127.0.0.1:8000
```

You can instead set `ELEMENTAL_KEEP_API_BASE_URL` in the environment before
launching the game; when no Settings-menu override has been saved, the
environment variable takes precedence over the `.env` value. Set it to the
base URL of your API server, without an API route suffix. You can also change
the API server in the game's Settings menu; that choice is persisted in the
local game database and applies to account, leaderboard, registration, and
multiplayer features. Changing servers signs the player out to avoid reusing
credentials with a different server. The Settings menu also lets you adjust
house-turret sensitivity. For a downloaded game build, set the environment
variable before launching it to choose the initial default.
## Run the API server locally

Install the project dependencies first with `uv sync --all-packages --all-groups`.
Then start the API from the repository root:

```bash
uv run --project services/api uvicorn elemental_api.main:app --reload --host 127.0.0.1 --port 8000
```

The API is then available at `http://127.0.0.1:8000`; its health check is
`http://127.0.0.1:8000/health`. Alternatively, run `make local-serve` to build
and launch the API in Docker with port 8000 published to your machine. In the
game, set `ELEMENTAL_KEEP_API_BASE_URL` to the API's base URL to use that
server's online services.

For deployment with the production Docker Compose configuration, see
[services/api/README.md](services/api/README.md).

To enable the admin endpoints, run `openssl rand -hex 32` and set
`ELEMENTAL_API_ADMIN_TOKEN` in `.env` to its output before starting Compose.
If the variable is unset or empty, the admin endpoints are disabled and return
HTTP 503.

## Local database and credentials
Local leaderboard data is stored in the OS app-data directory, not in the repository. The API database defaults to `./.local/elemental_api.db` when `ELEMENTAL_API_DB_PATH` is not set. Credential storage uses `keyring` when available; otherwise the client falls back to a private per-user file.

## Tests
```bash
uv run pytest
make coverage
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
