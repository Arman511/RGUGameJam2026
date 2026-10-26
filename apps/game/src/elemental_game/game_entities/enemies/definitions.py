"""Enemy stats and elemental combat matchups."""

from dataclasses import dataclass

from elemental_game.game_entities.crops.crops import CropType

REGULAR_SEED_TIER_WEIGHTS = (50, 45, 15)
ELITE_SEED_TIER_WEIGHTS = (30, 40, 30)


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


ENEMY_DEFS: dict[str, EnemyDefinition] = {
    "swarmer": EnemyDefinition(
        "swarmer", "Slime", "enemy_slime.png", None, 10, 56, 4, 2
    ),
    "brute": EnemyDefinition(
        "brute",
        "Earth Brute",
        "enemy_earth.png",
        CropType.EARTH,
        36,
        30,
        9,
        5,
        knockback_resistance=0.5,
    ),
    "runner": EnemyDefinition(
        "runner", "Air Runner", "enemy_air.png", CropType.AIR, 16, 88, 4, 3
    ),
    "fire": EnemyDefinition(
        "fire", "Fire Wisp", "enemy_fire.png", CropType.FIRE, 22, 48, 6, 4
    ),
    "water": EnemyDefinition(
        "water", "Water Wisp", "enemy_water.png", CropType.WATER, 24, 42, 6, 4
    ),
    "ice": EnemyDefinition(
        "ice", "Ice Wisp", "enemy_ice.png", CropType.ICE, 24, 42, 6, 4
    ),
    "lightning": EnemyDefinition(
        "lightning",
        "Lightning Wisp",
        "enemy_lightning.png",
        CropType.LIGHTNING,
        22,
        52,
        6,
        4,
    ),
    "elite_fire": EnemyDefinition(
        "elite_fire",
        "Elite Fire Wisp",
        "enemy_fire.png",
        CropType.FIRE,
        40,
        44,
        9,
        8,
        is_elite=True,
    ),
    "elite_water": EnemyDefinition(
        "elite_water",
        "Elite Water Wisp",
        "enemy_water.png",
        CropType.WATER,
        42,
        38,
        9,
        8,
        is_elite=True,
    ),
    "elite_earth": EnemyDefinition(
        "elite_earth",
        "Elite Earth Brute",
        "enemy_earth.png",
        CropType.EARTH,
        58,
        28,
        12,
        10,
        is_elite=True,
        knockback_resistance=0.5,
    ),
    "elite_air": EnemyDefinition(
        "elite_air",
        "Elite Air Runner",
        "enemy_air.png",
        CropType.AIR,
        34,
        78,
        8,
        8,
        is_elite=True,
    ),
    "elite_lightning": EnemyDefinition(
        "elite_lightning",
        "Elite Lightning Wisp",
        "enemy_lightning.png",
        CropType.LIGHTNING,
        38,
        48,
        9,
        8,
        is_elite=True,
    ),
    "elite_ice": EnemyDefinition(
        "elite_ice",
        "Elite Ice Wisp",
        "enemy_ice.png",
        CropType.ICE,
        42,
        38,
        9,
        8,
        is_elite=True,
    ),
    "boss": EnemyDefinition(
        "boss",
        "Elemental Boss",
        "finalboss.png",
        None,
        100,
        25,
        20,
        30,
        is_boss=True,
        knockback_resistance=0.75,
        boss_house_damage_percent=10,
        boss_turret_damage_percent=20,
    ),
    "big_boss": EnemyDefinition(
        "big_boss",
        "Elemental Colossus",
        "finalboss.png",
        None,
        300,
        25,
        30,
        60,
        is_boss=True,
        knockback_resistance=0.9,
        boss_house_damage_percent=20,
        boss_turret_damage_percent=30,
    ),
}
OPPOSING_ELEMENTS = {
    CropType.FIRE: CropType.WATER,
    CropType.WATER: CropType.FIRE,
    CropType.EARTH: CropType.LIGHTNING,
    CropType.LIGHTNING: CropType.EARTH,
    CropType.ICE: CropType.AIR,
    CropType.AIR: CropType.ICE,
}
TURRET_MATCHUPS = {
    CropType.FIRE: (CropType.AIR, CropType.WATER),
    CropType.WATER: (CropType.FIRE, CropType.EARTH),
    CropType.EARTH: (CropType.LIGHTNING, CropType.WATER),
    CropType.LIGHTNING: (CropType.WATER, CropType.EARTH),
    CropType.AIR: (CropType.EARTH, CropType.FIRE),
    CropType.ICE: (CropType.AIR, CropType.FIRE),
}
