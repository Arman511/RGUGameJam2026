from dataclasses import dataclass
from typing import ClassVar


@dataclass
class TurretInstance:
    """Track the upgrades and current health of a built turret."""

    MAX_HEALTH: ClassVar[int] = 100
    key: str
    health: int = MAX_HEALTH
    cooldown: float = 0.0
    level: int = 0
    fire_rate_level: int = 0
    damage_level: int = 0
    slow_level: int = 0
    knockback_level: int = 0
    attack_radius_level: int = 0
    attack_range_level: int = 0
