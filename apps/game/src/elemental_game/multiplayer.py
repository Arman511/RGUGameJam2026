"""Compatibility exports for the multiplayer network client."""

from elemental_game.networking.client import (
    MATCH_PATH,
    PROTOCOL_VERSION,
    MultiplayerClient,
    MultiplayerError,
)

__all__ = [
    "MATCH_PATH",
    "PROTOCOL_VERSION",
    "MultiplayerClient",
    "MultiplayerError",
]
