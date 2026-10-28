from dataclasses import dataclass

from elemental_game.game_types.crop import CropType


@dataclass(frozen=True)
class TurretDefinition:
    """Describe one elemental turret type and its combat stats."""

    key: str
    name: str
    element: CropType
    image: str
    range: float
    fire_rate: float
    damage: int
    slow: float = 0.0
    knockback: float = 0.0

    @property
    def resource_cost(self) -> int:
        return 5
