# Game Core

The local leaderboard schema is managed by Alembic. `LocalLeaderboardStore`
automatically applies pending migrations to its database file when opened.
Pass a username to `submit_run` when saving a run. Use
`AuthClient.username_for_run(guest_username)` to automatically use the signed-in
account name or the guest-provided name when signed out. Pass that same username
to `top_scores` or `personal_best` to show only that player's local runs; omit
it to show the combined leaderboard.

To inspect or apply migrations manually from the repository root:

```sh
uv run alembic -c packages/game_core/alembic.ini history
uv run alembic -c packages/game_core/alembic.ini current
uv run alembic -c packages/game_core/alembic.ini upgrade head
```

Create a new revision with
`uv run alembic -c packages/game_core/alembic.ini revision -m "describe change"`.
Edit the generated revision before use. Do not modify a migration that has
already been applied; add a new revision instead.
