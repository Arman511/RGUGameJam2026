# Architecture

The project is split into a pure game core, a desktop app, an API client, and a FastAPI server.

- `packages/game_core`: deterministic rules, enemy logic, farm logic, and simulation.
- `apps/game`: Pygame rendering and local interaction loop.
- `packages/api_client`: network wrappers and credential handling.
- `services/api`: server-side authentication, leaderboard, and score submission.

This keeps the gameplay rules independent from rendering and API code.
