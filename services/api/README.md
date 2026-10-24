# Elemental Keep API

The API uses SQLAlchemy ORM models and Alembic migrations. On server startup,
the API applies all pending migrations to the configured database.

The root URL serves the live Jinja2 leaderboard, styled with Bootstrap. The
`/download` page directs players to the latest game release on GitHub, and the
`/register` page lets players create an account using the registration API.
CSS and JavaScript are served from `/static/`; the leaderboard refreshes scores
every seven seconds and supports searching by player/run ID, sorting by score
fields, and switching between light and dark themes. CORS allows
`https://elemental-keep.armandev.co.uk` and local `localhost`/`127.0.0.1`
development origins. WebSocket handshakes use the same origin allowlist for
the planned multiplayer feature.

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
