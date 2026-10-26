"""Compatibility exports for multiplayer attack helpers."""

from elemental_game.networking.attacks import (
    ATTACK_BASE_COSTS,
    COIN_ATTACKS,
    CROP_ATTACKS,
    AttackCostTracker,
    send_multiplayer_attack,
)

__all__ = [
    "ATTACK_BASE_COSTS",
    "COIN_ATTACKS",
    "CROP_ATTACKS",
    "AttackCostTracker",
    "send_multiplayer_attack",
]
