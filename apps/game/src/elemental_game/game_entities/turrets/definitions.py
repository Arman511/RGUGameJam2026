"""Turret domain data and upgrade options."""

from dataclasses import dataclass
from typing import ClassVar

from elemental_game.game_types.turret_definition import TurretDefinition
from elemental_game.utils.config import ELEMENTAL_TURRET_RANGE
from elemental_game.game_entities.crops.crops import CropType

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
    "Repair turret",
    "Destroy turret",
)
