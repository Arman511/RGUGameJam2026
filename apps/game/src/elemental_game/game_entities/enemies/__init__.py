"""Compatibility exports for the enemy domain and combat controller."""

import random

from .controller import EnemyController, load_enemy_images
from .definitions import (
    ELITE_SEED_TIER_WEIGHTS,
    ENEMY_DEFS,
    OPPOSING_ELEMENTS,
    REGULAR_SEED_TIER_WEIGHTS,
    TURRET_MATCHUPS,
    EnemyDefinition,
)
from .enemy import (
    EnemyState,
    boss_seed_drop,
    roll_enemy_seed_drop,
    seed_tier_drop_weights,
)

__all__ = [
    "ELITE_SEED_TIER_WEIGHTS",
    "ENEMY_DEFS",
    "OPPOSING_ELEMENTS",
    "REGULAR_SEED_TIER_WEIGHTS",
    "TURRET_MATCHUPS",
    "EnemyController",
    "EnemyDefinition",
    "EnemyState",
    "boss_seed_drop",
    "load_enemy_images",
    "random",
    "roll_enemy_seed_drop",
    "seed_tier_drop_weights",
]
