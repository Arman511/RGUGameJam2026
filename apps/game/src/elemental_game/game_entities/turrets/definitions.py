"""Turret domain data and upgrade options."""

from dataclasses import dataclass
from typing import ClassVar

from elemental_game.utils.config import ELEMENTAL_TURRET_RANGE
from elemental_game.game_entities.crops.crops import CropType


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


TURRET_DEFS: dict[str, TurretDefinition] = {
    "flame_turret": TurretDefinition(
        "flame_turret",
        "Fire",
        CropType.FIRE,
        "fire-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.8,
        8,
        slow=0.1,
    ),
    "water_cannon": TurretDefinition(
        "water_cannon",
        "Water",
        CropType.WATER,
        "water-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.7,
        7,
        slow=0.15,
    ),
    "earth_cannon": TurretDefinition(
        "earth_cannon",
        "Earth",
        CropType.EARTH,
        "earth-turret.png",
        ELEMENTAL_TURRET_RANGE,
        1.1,
        12,
        knockback=30.0,
    ),
    "wind_turbine": TurretDefinition(
        "wind_turbine",
        "Air",
        CropType.AIR,
        "air-turret.png",
        ELEMENTAL_TURRET_RANGE,
        1.2,
        6,
        slow=0.25,
    ),
    "ice_spire": TurretDefinition(
        "ice_spire",
        "Ice",
        CropType.ICE,
        "ice-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.9,
        5,
        slow=0.35,
    ),
    "storm_rod": TurretDefinition(
        "storm_rod",
        "Lightning",
        CropType.LIGHTNING,
        "lightning-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.6,
        15,
    ),
}
DEFINITION_BY_ELEMENT = {
    definition.element: definition for definition in TURRET_DEFS.values()
}
PROJECTILE_ASSETS = {
    CropType.FIRE: "fire-pellet.png",
    CropType.WATER: "water-pellet.png",
    CropType.EARTH: "earth-pellet.png",
    CropType.AIR: "air-pellet.png",
    CropType.ICE: "ice-pellet.png",
    CropType.LIGHTNING: "lightning-pellet.png",
}
ELEMENT_RANGE_COLORS = {
    CropType.FIRE: (245, 92, 64),
    CropType.WATER: (72, 150, 245),
    CropType.EARTH: (106, 205, 112),
    CropType.AIR: (230, 235, 245),
    CropType.ICE: (102, 220, 235),
    CropType.LIGHTNING: (250, 220, 72),
}
UPGRADE_NAMES = (
    "Fire rate",
    "Damage",
    "Slowdown",
    "Knockback",
    "Attack radius",
    "Attack range",
    "Destroy turret",
)


@dataclass
class TurretSlot:
    """Represent one buildable turret position beside the farm."""

    side: str
    index: int
    center: tuple[int, int]
    turret: TurretInstance | None = None
