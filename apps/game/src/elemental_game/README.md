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
uv run alembic -c apps/game/src/elemental_game/alembic.ini upgrade head
```

Create a new revision with
`uv run alembic -c apps/game/src/elemental_game/alembic.ini revision -m "describe change"`.
Edit the generated revision before use. Do not modify a migration that has
already been applied; add a new revision instead.

Music and SFX volume preferences are stored in the local database and restored
when the game starts. The game leaderboard is local-only and can be filtered by
username; it is ordered by waves reached.

On launch, the game validates an existing API login and otherwise shows a
login screen with a guest skip option. A per-user lock file prevents launching
a second game instance at the same time. Menu, login, settings, and help text
use the bundled pixel font. Play game opens a single-player or
2-player VS choice. Online players can host a room and share its six-character
code, or join a friend's room. During a multiplayer match, press V to open the
attack panel: spend coins to send extra or tougher enemies, or spend a harvested
elemental crop to bias the opponent's next wave or change its weather. Repeated
attacks stack on the opponent's next wave, including extra enemies, increased
health, and elemental bias. A match ends when one house falls; the winner and
loser see the result before both return to the main menu. Online play connects
to `/api/v1/matches` on the configured API server.

The main menu also provides Leaderboard and Settings, plus a Sign in or Sign
out action depending on the current account state. Settings changes are applied
while adjusting the sliders and saved to the local database when Save is
selected or settings are closed.
