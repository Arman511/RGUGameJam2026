# Multiplayer protocol

## Match settings

The game reads the room join timeout from `GET /api/v1/matches/config`:

```json
{"join_timeout_seconds": 120.0}
```

The value comes from the webserver's `ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS`
setting (default: 120 seconds). Hosts show a countdown while a room is waiting
for its second player. The countdown starts when the host receives a room; if
the host is queued, it starts when the server promotes the host and creates
their room. If nobody joins before the timeout, the server expires the room and
closes the host connection.

## WebSocket

Matches use `/api/v1/matches`. Every message includes `version: 1`, a `type`,
and a `payload` object. A host sends a `host` handshake; a guest sends a `join`
handshake with the six-character `room_code`. The server responds with
`room_created`, `queued`, or `match_started` as appropriate. A room that does
not receive a second player before the configured timeout sends `room_expired`.

In-match messages relay opponent actions and wave updates. A `match_ended`
message tells each player whether they won or lost.
