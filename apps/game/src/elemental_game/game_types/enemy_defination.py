from dataclasses import dataclass

from elemental_game.game_types.crop import CropType


@dataclass(frozen=True)
class EnemyDefinition:
    """Describe an enemy type and its combat traits."""

    key: str
    name: str
    image: str
    element: CropType | None
    max_health: int
    speed: float
    damage: int
    reward: int
    is_boss: bool = False
    is_elite: bool = False
    knockback_resistance: float = 0.0
    boss_house_damage_percent: int | None = None
    boss_turret_damage_percent: int | None = None
