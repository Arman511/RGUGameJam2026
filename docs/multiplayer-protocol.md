# Multiplayer protocol draft

This document describes the initial versioned protocol for future online matches.

## Version
All messages include a `version` integer and a `type` field.

## Example message schema
```json
{"version": 1, "type": "join", "payload": {"match_id": "abc123"}}
```

## Message types
- `join`
- `ready`
- `action`
- `state_update`
- `error`
- `match_ended`

Server responsibilities include validation, authoritative simulation, match membership checks, and reconnect handling.
The initial implementation keeps PvP unavailable and documents it as future work.
