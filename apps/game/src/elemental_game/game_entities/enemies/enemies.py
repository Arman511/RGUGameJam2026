from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field

import pygame
from elemental_game.config import IMAGES_DIR
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.types.seed import SeedType

REGULAR_SEED_TIER_WEIGHTS = (50, 45, 15)
ELITE_SEED_TIER_WEIGHTS = (30, 40, 30)
SEED_TIERS = ("tier1", "tier2", "tier3")


@dataclass(frozen=True)
class EnemyDefinition:
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


ENEMY_DEFS: dict[str, EnemyDefinition] = {
    "swarmer": EnemyDefinition(
        "swarmer", "Slime", "enemy_slime.png", None, 10, 56, 4, 2
    ),
    "brute": EnemyDefinition(
        "brute", "Earth Brute", "enemy_earth.png", CropType.EARTH, 36, 30, 9, 5
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
        "boss", "Elemental Boss", "finalboss.png", None, 200, 25, 20, 30, is_boss=True
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


@dataclass
class EnemyState:
    key: str
    health: int
    max_health: int
    speed: float
    damage: int
    reward: int
    pos: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    distance: float = 0.0
    attack_cooldown: float = 0.0
    slow_timer: float = 0.0
    resistance: float = 1.0
    base_speed: float | None = None
    slow_amount: float = 0.0

    @classmethod
    def create(cls, key: str, position) -> EnemyState:
        definition = ENEMY_DEFS[key]
        resistance = 0.45 if definition.is_boss else 0.5 if definition.is_elite else 1.0
        return cls(
            key=key,
            health=definition.max_health,
            max_health=definition.max_health,
            speed=definition.speed,
            damage=definition.damage,
            reward=definition.reward,
            pos=pygame.Vector2(position),
            distance=1000.0,
            resistance=resistance,
            base_speed=definition.speed,
        )

    @property
    def definition(self) -> EnemyDefinition:
        return ENEMY_DEFS[self.key]

    @property
    def is_boss(self) -> bool:
        return self.definition.is_boss

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, damage: float, element: CropType | None = None) -> None:
        multiplier = 1.0
        if element is not None and self.resistance < 1:
            multiplier = self.resistance
        elif self.definition.element is not None and element is not None:
            strong_against, weak_against = TURRET_MATCHUPS[element]
            if self.definition.element is strong_against:
                multiplier = 1.5
            elif self.definition.element is weak_against:
                multiplier = 0.6
            elif OPPOSING_ELEMENTS[self.definition.element] is element:
                multiplier = 0.5
        self.health -= max(1, math.ceil(damage * multiplier))

    def apply_slow(self, amount: float) -> None:
        if amount <= 0:
            return
        if self.base_speed is None:
            self.base_speed = self.speed
        self.slow_amount = max(self.slow_amount, min(0.7, amount))
        self.slow_timer = max(self.slow_timer, 1.0)
        self.speed = max(8.0, self.base_speed * (1.0 - self.slow_amount))

    def apply_knockback(self, direction, distance: float) -> None:
        vector = pygame.Vector2(direction)
        if distance > 0 and vector.length_squared() > 0:
            self.pos += vector.normalize() * distance

    def update_status_effects(self, dt: float) -> None:
        if self.slow_timer <= 0:
            return
        self.slow_timer = max(0.0, self.slow_timer - dt)
        if self.slow_timer == 0:
            if self.base_speed is not None:
                self.speed = self.base_speed
            self.slow_amount = 0.0

    def move(self, dt: float) -> None:
        self.distance = max(0.0, self.distance - self.speed * dt)

    def move_towards(self, destination, dt: float) -> bool:
        target = pygame.Vector2(destination)
        offset = target - self.pos
        distance = offset.length()
        if distance <= 1:
            return True
        step = min(distance, self.speed * dt)
        self.pos += offset.normalize() * step
        self.distance = max(0.0, self.distance - step)
        return distance <= step + 1

    def draw(self, surface, images) -> None:
        image = images[self.key]
        rect = image.get_rect(center=self.pos)
        surface.blit(image, rect)
        bar = pygame.Rect(rect.x, rect.y - 7, rect.width, 4)
        pygame.draw.rect(surface, (85, 25, 25), bar)
        pygame.draw.rect(
            surface,
            (80, 220, 90),
            (
                bar.x,
                bar.y,
                bar.width * max(0, self.health) / self.max_health,
                bar.height,
            ),
        )


def roll_enemy_seed_drop(enemy: EnemyState) -> tuple[SeedType, str]:
    element = enemy.definition.element
    if element is None:
        return random.choice(tuple(SeedType)), "tier1"

    weights = (
        ELITE_SEED_TIER_WEIGHTS
        if enemy.definition.is_elite
        else REGULAR_SEED_TIER_WEIGHTS
    )
    tier = random.choices(SEED_TIERS, weights=weights, k=1)[0]
    return SeedType[element.name], tier


def load_enemy_images() -> dict[str, pygame.Surface]:
    images = {}
    for key, definition in ENEMY_DEFS.items():
        image = pygame.image.load(
            os.path.join(IMAGES_DIR, "enemy", definition.image)
        ).convert_alpha()
        size = 82 if definition.is_boss else 48 if definition.is_elite else 42
        images[key] = pygame.transform.smoothscale(image, (size, size))
    return images
