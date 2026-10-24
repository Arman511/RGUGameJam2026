# Elemental Keep API

The API uses SQLAlchemy ORM models and Alembic migrations. On server startup,
the API applies all pending migrations to the configured database.

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
