# Elemental Keep API

## Run the server

From the repository root, install dependencies and start a development server:

```sh
uv sync --all-packages --all-groups
uv run --project services/api uvicorn elemental_api.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; check that it is running at
`http://127.0.0.1:8000/health`. The interactive API docs are available at
`/docs` when enabled.

You can also run the API in Docker from the repository root with
`make local-serve`. This builds the local image, publishes port 8000, and keeps
the database in `./.local/elemental_api_data`. Stop it with Ctrl+C. The
deployment-oriented `make serve` command uses `docker-compose.yml` and expects
the external `zoraxy_proxy` Docker network to exist.

To point a game client at this server, set its
`ELEMENTAL_KEEP_API_BASE_URL` to the server's base URL (for example,
`http://127.0.0.1:8000`). See the root [README](../../README.md) for configuring
the game client.

## API overview

The API uses SQLAlchemy ORM models and Alembic migrations. On server startup,
the API applies all pending migrations to the configured database.

The root URL serves the live Jinja2 leaderboard, styled with Bootstrap. The
`/download` page directs players to the latest game release on GitHub, and the
`/register` page lets players create an account using the registration API.
CSS and JavaScript are served from `/static/`; the leaderboard refreshes scores
every seven seconds and supports searching by player/run ID, sorting by score
fields, and switching between light and dark themes. CORS allows
`https://elemental-keep.armandev.co.uk` and local `localhost`/`127.0.0.1`
development origins. WebSocket handshakes use the same origin allowlist. The versioned
`/api/v1/matches` WebSocket endpoint creates six-character rooms, joins the
second player, relays validated match actions and wave status, and broadcasts
the winner when a player reports defeat. Rooms are held in memory and are
removed when a match ends or a player disconnects; active matches do not
survive an API server restart.
`ELEMENTAL_MATCH_LIMIT` controls how many rooms may be hosted at once (default
100). Additional hosts wait in a first-in, first-out queue and receive a room
when a slot opens. `ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS` controls how long a
host room waits for player 2 before it expires (default 120 seconds).

Set `ELEMENTAL_API_DB_PATH` to select the SQLite database file. To inspect or
apply migrations manually from this directory:

```sh
uv run alembic current
uv run alembic upgrade head
uv run alembic history
```

Create a new schema change with `uv run alembic revision -m "describe change"`
and edit the generated revision before deploying it. Never edit a migration
that has already been applied; add a new revision instead.

Score submissions use `time_survived` (seconds) and `wave_number`. The game
client maps its existing local leaderboard fields, `survival_time` and
`final_wave`, to those API fields. Leaderboards rank runs by survival time,
enemies defeated, then wave reached, all descending.
The leaderboard API also supports server-side search by player or run ID,
sorting, and offset-based pagination so the web page loads only the current
result page.

Successful logins remove expired and revoked authentication tokens. Database
indexes support token cleanup, per-user token lookups, and leaderboard ranking.
