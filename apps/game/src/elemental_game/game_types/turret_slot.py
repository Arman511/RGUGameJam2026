from dataclasses import dataclass
from elemental_game.game_types.turret_instance import TurretInstance


@dataclass
class TurretSlot:
    """Represent one buildable turret position beside the farm."""

    side: str
    index: int
    center: tuple[int, int]
    turret: TurretInstance | None = None
