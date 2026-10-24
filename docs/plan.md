# GitHub Copilot Agent Prompt — Elemental Keep

You are the lead Python game developer and software architect. Work directly in the currently open repository and implement the initial working version of **Elemental Keep**, a 2D elemental farming and tower-defence survival game.

Do not merely explain what should be done or return example snippets. Inspect the repository, create and edit the actual files, run the available checks, fix issues, and leave the repository in a usable state. If a requirement is too large for this first implementation, implement a coherent foundation and document the limitation and next steps.

## 1. Product vision

Elemental Keep is a 2D top-down pixel-art-inspired farming and tower-defence survival game. Players plant elemental crops, harvest resources, construct automatic turrets, repair their farmhouse, and survive increasingly difficult enemy waves.

The core experience is offline single-player. Sign-in is optional and must never be required to launch or play solo. A local leaderboard must work without internet. Online accounts unlock a global leaderboard and, eventually, online two-player PvP.

Tagline: **Farm. Harvest. Defend. Outlast.**

### Core gameplay loop
1. Plant elemental seeds on limited farm plots.
2. Crops grow over time and can be harvested for elemental resources.
3. Spend resources on turrets, upgrades, seeds, and farmhouse repairs.
4. Survive waves of enemies that approach and attack the farmhouse.
5. Lose when farmhouse health reaches zero.
6. Save the run to the local leaderboard and show the final statistics.

### Six elements
- Fire / ember: burning and damage over time.
- Water / droplets: reliable sustained damage; can apply a soaked status.
- Earth / stone: heavy impact, knockback, defensive potential.
- Wind / gale essence: pushes enemies back or slows their advance.
- Ice / frost crystals: slows and can briefly freeze enemies.
- Lightning / charged cores: burst and chain damage.

Keep the element model data-driven where reasonable. Basic elements and turrets must work even if elemental combo effects are not all implemented yet. Potential future synergies: Water + Lightning, Wind + Fire, Water + Ice, Earth + Ice, Wind + Lightning.

### Enemies
Implement at least:
- Swarmer: low health, moves quickly, commonly spawns in groups.
- Brute: slow, high health, deals more farmhouse damage.
- Runner: very fast, fragile, pressures slow-firing defences.
- Elemental boss: high health and a distinct ability or stat profile, appears periodically.

Suggested progression: waves 1–3 basic swarms; 4–6 brutes introduced; 7–9 runners and mixed waves; wave 10 boss; later waves scale difficulty. Exact balance values can be tuned.

### Turrets
Implement automatic targeting of enemies within range, with at least two working turret types in the first playable version and a clear data/model foundation for all six:
- Flame turret: burn or damage over time.
- Water cannon: sustained damage.
- Earth cannon: heavy slow attack and knockback.
- Wind turbine: pushback or slow.
- Ice spire: slow.
- Storm rod: burst damage and optional chaining.

Turrets should target enemies deterministically where practical (for example, nearest eligible enemy, then stable ID as tie-breaker). Implement projectile travel if feasible; instant hit is acceptable for the simplest initial turret if clearly modelled and tested. Do not let visual effects own gameplay logic.

## 2. Non-negotiable requirements

1. **Offline solo gameplay works with no API server and no account.**
2. **The local leaderboard works offline** and persists between launches.
3. The game must not freeze while waiting for HTTP or WebSocket responses.
4. Core game rules must be separated from Pygame rendering.
5. API code must not be imported by the offline game core.
6. Server-side account tokens must be revocable and expire one year after issuance.
7. Never store passwords or raw bearer tokens in server-side database rows or logs.
8. Never commit secrets, live credentials, local databases, generated caches, or virtual environments.
9. Implement real working functionality, not TODO-only modules or fake successful responses.
10. Keep the first implementation understandable and proportionate to a game-jam project. Avoid unnecessary microservices or premature abstractions.

## 3. Technology choices

Use:
- Python 3.12 or newer.
- `uv` workspace for the monorepo.
- Pygame for the desktop game.
- FastAPI + Uvicorn for the online API.
- SQLite for the local leaderboard and the API database, in two independent databases.
- Argon2id via `argon2-cffi` for password hashing.
- `httpx` for API HTTP calls and tests.
- Python standard library `sqlite3` unless a strong reason requires an ORM.
- `pytest` for tests.
- `ruff` for linting/formatting if compatible with the environment.
- `keyring` for client credential storage if it is available and appropriate.

Avoid adding React, a separate JavaScript frontend, PostgreSQL, Redis, or other services for this initial version. The desktop UI is Pygame.

Use asynchronous networking or a worker/thread boundary for network operations so Pygame's render loop stays responsive. Keep database operations short.

## 4. Repository structure

Create a clean monorepo approximately like this. You may add small files where justified, but preserve the package boundaries and do not build every possible future module as an empty placeholder.

elemental-keep/
├── apps/
│   └── game/
│       ├── pyproject.toml
│       └── src/elemental_game/
│           ├── __init__.py
│           ├── main.py
│           ├── settings.py
│           ├── game.py
│           ├── game_loop.py
│           ├── input.py
│           ├── rendering/
│           │   ├── __init__.py
│           │   ├── world.py
│           │   ├── sprites.py
│           │   └── effects.py
│           ├── screens/
│           │   ├── __init__.py
│           │   ├── main_menu.py
│           │   ├── game_screen.py
│           │   ├── login_screen.py
│           │   ├── leaderboard_screen.py
│           │   └── results_screen.py
│           ├── ui/
│           │   ├── __init__.py
│           │   ├── hud.py
│           │   └── build_menu.py
│           ├── persistence/
│           │   ├── __init__.py
│           │   ├── local_database.py
│           │   └── local_leaderboard.py
│           └── assets/
│               └── README.md
├── packages/
│   ├── game_core/
│   │   ├── pyproject.toml
│   │   └── src/game_core/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── elements.py
│   │       ├── resources.py
│   │       ├── crops.py
│   │       ├── farm.py
│   │       ├── enemies.py
│   │       ├── turrets.py
│   │       ├── waves.py
│   │       └── simulation.py
│   └── api_client/
│       ├── pyproject.toml
│       └── src/api_client/
│           ├── __init__.py
│           ├── http.py
│           ├── auth.py
│           └── credentials.py
├── services/
│   └── api/
│       ├── pyproject.toml
│       └── src/elemental_api/
│           ├── __init__.py
│           ├── main.py
│           ├── config.py
│           ├── auth/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── passwords.py
│           │   └── tokens.py
│           ├── leaderboard/
│           │   ├── __init__.py
│           │   └── routes.py
│           └── database/
│               ├── __init__.py
│               ├── connection.py
│               └── schema.sql
├── tests/
│   ├── unit/
│   │   ├── test_farming.py
│   │   ├── test_combat.py
│   │   └── test_waves.py
│   ├── api/
│   │   ├── test_auth.py
│   │   ├── test_tokens.py
│   │   └── test_leaderboard.py
│   └── integration/
│       └── test_offline_game.py
├── docs/
│   ├── game-design.md
│   ├── architecture.md
│   └── multiplayer-protocol.md
├── infra/
│   ├── Dockerfile.api
│   ├── compose.yaml
│   └── Caddyfile.example
├── pyproject.toml
├── .env.example
├── .gitignore
├── Makefile
└── README.md

A module can be omitted if genuinely unnecessary, but do not leave imports pointing to missing modules. Add `__init__.py` where required.

## 5. Monorepo and dependency configuration

Set up a working `uv` workspace with the root project configured as a workspace-only project. Give each member package a valid `pyproject.toml`, package name, `src` layout, dependencies, and entry points as appropriate.

Use sensible distribution names, for example:
- `elemental-game`
- `game-core`
- `api-client`
- `elemental-api`

Configure workspace sources so `elemental-game` depends on the local `game-core` and `api-client` packages. Keep the API independent of Pygame. Make sure these commands work, adjusting package names only consistently with your configuration:

- `uv sync --all-packages`
- `uv run --package elemental-game python -m elemental_game.main`
- `uv run --package elemental-api uvicorn elemental_api.main:app --reload`
- `uv run pytest`

If this environment has no network access and dependency installation fails, still create correct manifests, run all checks possible, and document the exact failure instead of claiming success.

## 6. Game core architecture

Implement a pure-Python simulation in `packages/game_core`. It must not import Pygame, FastAPI, or the API client.

Represent game state explicitly. Use dataclasses, enums, and typed functions where useful. Avoid an unnecessarily elaborate entity-component system.

The simulation should support:
- Starting a run.
- Planting a crop in a valid empty plot.
- Growing crops based on simulation time.
- Harvesting a mature crop and awarding the correct resource.
- Rejecting invalid actions without corrupting state.
- Constructing a turret if the player can afford it and the target tile is valid.
- Spending and adding resources through controlled methods.
- Turrets acquiring targets and attacking.
- Enemy movement and attacks against the farmhouse.
- Wave countdown, spawning, completion, and difficulty scaling.
- Farmhouse damage, repair, defeat and final statistics.
- Deterministic tests using seeded randomness or injected randomness.

Use a fixed simulation timestep, separate from render FPS. Provide a method such as `Simulation.step(dt)` or a fixed-tick update that can be tested without opening a Pygame window. Clamp or otherwise safely handle long frame delays so a window stall does not cause an unbounded catch-up loop.

Define configurable values in `game_core/config.py`, not scattered magic numbers. Keep gameplay state independent from sprite positions where possible; the rendering layer translates model positions into screen coordinates.

Suggested initial game balance, subject to tuning:
- Farmhouse health: 100.
- A small grid of farm plots, for example 3x3.
- Initial resources sufficient to plant at least one crop and build a basic defence.
- Crop growth takes several seconds of simulation time.
- Turrets have range, damage, attack cooldown, cost, and element.
- Enemy damage and movement speed differ by type.
- A short preparation period precedes the first wave.
- Bosses appear at regular intervals starting around wave 10.

Do not overbuild the farming economy before the game is playable. The initial prototype must offer a complete loop from planting to harvesting to building to combat to defeat and results.

## 7. Pygame desktop client

Build a playable window using placeholder shapes and readable text; do not depend on art assets that are not present. Visuals should be clean and consistent, using simple colours, tile outlines, clear UI hierarchy, and distinct shapes/colours for elements, enemies, crops, turrets, and the farmhouse.

### Main menu
Include:
- Play Solo
- Local Leaderboard
- Online / Sign In
- Settings (a basic functional settings screen or a clearly limited settings panel)
- Quit

Play Solo must start immediately without sign-in, a server URL, or a network request. If the API is down, the player must still be able to play solo.

### Game controls
Use intuitive mouse and keyboard controls. Document the actual controls in README and an in-game help panel. A reasonable starting mapping:
- Mouse: select farm plot, place seed/turret, select UI buttons.
- Escape: pause or return to the pause/menu overlay.
- Number keys or visible buttons: select crop/turret type.
- Space or a visible button: continue/start next wave if the design uses manual wave starts.

Implement proper hit testing and visible selected-item state. Don't rely on text labels without actual input handling.

### In-game UI
Display:
- Farmhouse health.
- Current wave and preparation/wave state.
- Survival time.
- Elemental resource counts.
- Selected planting/building mode and its cost.
- Feedback for invalid actions (e.g. not enough resources, occupied plot, wrong tile).
- Pause/restart/menu controls.
- A clear defeat state and result summary.

The game must be playable at a common desktop resolution, resizable if practical, and handle window close cleanly. Use delta time for animation/rendering and a fixed step for simulation.

### Local leaderboard
Save completed runs locally in SQLite in the OS-specific user application-data directory. Never put the database under the repository or working directory by default. Choose a sensible app directory using platform conventions:
- Windows: `%LOCALAPPDATA%` or a suitable per-user application directory.
- macOS: `~/Library/Application Support`.
- Linux: `$XDG_DATA_HOME` or `~/.local/share`.

Create the directory if missing. Use parameterized SQL, schema versioning or safe initialization, indexes where useful, and short transactions. Save run ID, timestamp, survival time, final wave, score, and enemies defeated. Provide a top-scores view and a personal-best summary. If database initialisation fails, show a useful error and avoid silently pretending that a score was saved.

### Run completion
Every completed run is saved locally regardless of account status or internet access. Online score upload is a separate optional action. Do not discard local scores when the user signs in or signs out.

## 8. Optional online account and token implementation

Implement a basic but real account system in the FastAPI service. Solo play must not depend on this being available.

### Registration and login
- Registration accepts a username and password with reasonable length and input validation.
- Normalize usernames for uniqueness, but retain a display username.
- Hash passwords using Argon2id (`argon2-cffi`).
- Return generic authentication errors where appropriate; never reveal stored password hashes.
- Enforce sensible request validation and response schemas.
- Do not log passwords, bearer tokens, or Authorization headers.

### One-year bearer tokens
- Generate at least 32 random bytes with `secrets.token_urlsafe` or equivalent.
- Return the raw token only at issuance.
- Store only a cryptographic hash of the token server-side, not the raw token.
- Store user ID, creation timestamp, expiry timestamp, and revocation timestamp.
- Set expiry to one year after issuance using timezone-aware UTC timestamps.
- Every authenticated request must reject unknown, expired, or revoked tokens.
- Logout revokes the current token.
- Implement `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`, and `/api/v1/auth/logout`.
- Add tests proving expiry and revocation work. Use an injectable clock or controlled timestamps rather than waiting a year in tests.
- Never claim that a token is valid for one year without server-side expiry enforcement.

Client credential storage:
- Prefer OS credential storage through `keyring` where it works.
- If a fallback is needed, use a private per-user app-data file with restrictive permissions, never the repo. Document the security tradeoff.
- Never store passwords to automate future login.
- Automatically reuse a saved token for online features when it remains valid.
- If the token expires, keep solo play and local leaderboard available; prompt for sign-in only when an online feature is requested.
- Logout calls the server to revoke the token when reachable and removes the local token. If offline, remove the local token and clearly explain that server-side revocation could not be confirmed.
- Avoid printing tokens in debug output.

### API database
Use a persistent, configurable SQLite path. Do not assume a relative database path inside the repository for production. Provide a development default that is obvious and safe, and allow configuration through environment variables.

Create tables for users, auth_tokens, and scores with:
- Appropriate primary keys and foreign keys.
- Unique normalized username.
- Unique token hash.
- Indexes for token lookup and leaderboard sorting.
- UTC timestamps.
- Foreign keys enabled on every database connection.
- WAL mode where suitable.
- Parameterized SQL and short transactions.

Use a database connection helper that is safe for FastAPI's execution model. Avoid sharing a single SQLite connection across unrelated concurrent requests. Ensure schema initialisation is explicit and reliable.

## 9. Global leaderboard and score integrity

Implement:
- `GET /api/v1/leaderboard` for paginated or bounded top scores.
- `POST /api/v1/scores` for authenticated score submissions.
- A client-side view for online leaderboard if feasible without compromising offline functionality.

Store at least username/display name, survival time, final wave, score and submission time. Validate types, ranges, request size, and sensible maximums. Enforce unique run IDs per user to prevent accidental duplicate submissions.

Important limitation: a basic client-reported offline score is not cheat-proof. Treat uploaded offline scores as casual/unverified. Do not claim anti-cheat security that does not exist. The future PvP implementation should record results based on server simulation. Make this distinction clear in the docs and UI if score verification status is displayed.

## 10. Online multiplayer foundation

Online PvP is a future phase, but structure the code so it can be added without redesigning the game core.

For this initial implementation:
- Create a documented WebSocket protocol design in `docs/multiplayer-protocol.md`.
- Define versioned JSON messages and validation for join, ready, action, state update, error and match-ended events.
- Require authenticated match membership for actual WebSocket connections.
- Never accept a user-supplied user ID as proof of identity.
- Prefer an authentication message immediately after WebSocket connection or another supported secure mechanism; do not put long-lived bearer tokens into URLs where they can be logged.
- Validate all player actions on the server, including resource costs and match membership.
- Document server-authoritative simulation and reconnect behaviour.

If time allows after the playable game, implement the minimal private-match creation/join foundation. Do not create fake PvP buttons that report success without doing anything. If PvP is not implemented, show it as unavailable/coming soon and document it honestly. The rest of the game must still work.

## 11. API client and graceful degradation

Create a small API client package with:
- Configurable API base URL.
- HTTP methods for registration, login, current user, logout, leaderboard retrieval and score submission.
- Explicit timeout values.
- Clear typed exceptions or result objects for network failures, authentication failures and validation errors.
- Bearer-token handling that never logs secrets.
- No blocking HTTP calls on the Pygame main thread.
- Unit tests using `httpx` mock transports or FastAPI's test client where appropriate.

The desktop application must distinguish:
- Not signed in.
- Signed in.
- Offline/unreachable server.
- Expired/revoked session.
- Online feature not implemented yet.

Never treat network failure as proof that a token has expired. Keep local functionality usable.

## 12. Tests

Write meaningful automated tests; do not just test imports.

### Game-core tests
- Planting on an empty plot succeeds.
- Planting on an occupied or invalid plot fails without charging resources.
- Harvesting before maturity fails.
- Harvesting after maturity awards the expected resource.
- Insufficient resources prevent construction.
- Turret attacks reduce enemy health under valid conditions.
- Enemies move and damage the farmhouse when they reach it.
- Wave progression and scaling work.
- Farmhouse defeat ends the run.
- Simulation tests are deterministic when seeded.

### Local persistence tests
- Database initialises and creates the expected tables.
- Completed runs persist and can be queried after reconnecting.
- Leaderboard sorting and limits work.
- Duplicate run IDs are handled safely.
- Tests use temporary directories/databases, never the user's real app-data database.

### API tests
- Registration succeeds with valid input.
- Duplicate normalized usernames are rejected.
- Passwords are hashed and not stored as plaintext.
- Login succeeds with correct credentials and fails with incorrect credentials.
- Raw token is not stored in the database.
- Valid token authenticates.
- Expired and revoked tokens are rejected.
- Logout revokes a token.
- Unauthenticated requests to protected endpoints fail.
- Public leaderboard works without a token.
- Score input validation and duplicate-run protection work.

### Integration tests
- Core solo run can start, advance and finish without an API.
- Local score storage does not require authentication.
- API unavailable does not prevent main menu/solo gameplay.
- No test launches an interactive Pygame window unless it explicitly uses a headless/dummy video driver.

## 13. Documentation and operations

Write a useful `README.md` that includes:
- Project overview and current feature status.
- Requirements and setup.
- Exact install and run commands.
- How to run solo offline.
- Actual keyboard/mouse controls.
- How to run the API locally.
- Environment variables.
- Where local database and credentials are stored.
- How local and global leaderboards differ.
- How to run tests and linting.
- What is implemented versus planned.

Create `.env.example` with non-secret example values only. Add `.gitignore` rules for:
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.env` and secret files
- SQLite database files and journal/WAL/SHM files
- build/distribution artifacts
- IDE and OS clutter

Create `docs/game-design.md` with the gameplay rules and `docs/architecture.md` with package boundaries and data flows. In `docs/multiplayer-protocol.md`, document a versioned JSON protocol and which validations are server responsibilities.

Create a `Makefile` with practical targets such as `install`, `game`, `api`, `test`, `lint`, and `format`. Ensure commands match the actual workspace configuration.

Provide a minimal API Dockerfile and Compose file only if they are correct and useful. Use a persistent volume for the server SQLite database. Do not hardcode production secrets. Include a reverse-proxy HTTPS example only if it is correctly configured and clearly marked as an example.

## 14. Code quality and design constraints

- Type hints for public functions and core data structures.
- Use clear names and focused modules.
- Use dataclasses/enums where helpful.
- Keep rendering, simulation, persistence and network code separated.
- Avoid giant files, circular imports, hidden global state, and excessive abstractions.
- Avoid magic numbers; centralise tunable gameplay values.
- Handle expected failures with clear messages.
- Do not swallow exceptions silently.
- Do not include secrets or bearer tokens in logs or error messages.
- Do not write to repository-root data files at runtime.
- Use UTC timestamps for server-side records.
- Make randomness injectable or seedable for tests.
- Ensure API database schema is created on startup or via a clear initialization command.
- No `pass`-only placeholder implementations for advertised features.
- Do not claim that optional multiplayer is complete if only a protocol document exists.
- Do not generate art assets using external services; simple placeholder graphics are enough.

## 15. Implementation sequence

Follow this order and keep the repository runnable after each stage:

1. Inspect the current repository and existing instructions. Preserve useful existing work.
2. Set up the `uv` workspace and member package manifests.
3. Implement the pure-Python game core and unit tests.
4. Implement local SQLite persistence and tests.
5. Build the Pygame menu, playable solo loop, HUD, mouse interactions, pause/defeat screens and local leaderboard.
6. Run the game headlessly where possible and run core tests.
7. Implement the FastAPI database, registration/login, one-year tokens, logout, leaderboard and score endpoints.
8. Add API tests and client-side API/credential foundations.
9. Write documentation, environment example, `.gitignore`, Makefile and deployment scaffolding.
10. Run `uv sync --all-packages`, `uv run pytest`, and lint/format checks if dependencies are available. Fix the actual errors.
11. Review the resulting tree for broken imports, missing files, incorrect commands, secrets, runtime data in the repository, and misleading feature claims.
12. Finish with a concise report of what was created, commands that were actually tested, any test results, and limitations or next steps.

Do not stop after presenting a plan. Make changes directly in the workspace.

## 16. Acceptance criteria

The initial code is acceptable only if all applicable items below are true:

- The workspace structure and package manifests are valid.
- The Pygame application opens into a menu.
- A player can start a solo run without signing in or running the API.
- The player can plant, grow and harvest crops, collect resources, build working defences, fight enemies and lose.
- A completed run is saved to local SQLite and appears in the local leaderboard after restarting the application.
- No local database is written into the repository by default.
- The API can run separately and has functional registration, login, current-user, logout and public leaderboard endpoints.
- Tokens expire after one year and revoked/expired tokens are rejected.
- Passwords and raw tokens are not stored in plaintext server-side.
- Tests cover core rules, local persistence and authentication.
- README commands reflect the actual files and package names.
- Optional online functionality does not compromise offline solo play.
- Incomplete features are clearly documented and never represented as working.

Start by inspecting the repository, then implement the project in the order above. Make reasonable decisions without asking me to approve every small choice. If you encounter a real blocker, complete the other independent work and explain the blocker precisely.
