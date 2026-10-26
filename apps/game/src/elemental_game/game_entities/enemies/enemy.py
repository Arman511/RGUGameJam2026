"""Enemy state, movement effects, and seed-drop rules."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field

import pygame
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType

from .definitions import (
    ELITE_SEED_TIER_WEIGHTS,
    ENEMY_DEFS,
    OPPOSING_ELEMENTS,
    REGULAR_SEED_TIER_WEIGHTS,
    TURRET_MATCHUPS,
    EnemyDefinition,
)


def seed_tier_drop_weights(max_tier: int, *, elite: bool = False) -> tuple[float, ...]:
    base_weights = ELITE_SEED_TIER_WEIGHTS if elite else REGULAR_SEED_TIER_WEIGHTS
    return tuple(
        (
            base_weights[tier - 1]
            if tier <= len(base_weights)
            else base_weights[-1] * 0.25 ** (tier - len(base_weights))
        )
        for tier in range(1, max_tier + 1)
    )


@dataclass
class EnemyState:
    """Track one enemy's health, movement, and status effects."""

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
    resistance: float = 0.0
    base_speed: float | None = None
    slow_amount: float = 0.0
    target_turret: bool | None = None
    spawn_side: str | None = None

    @classmethod
    def create(cls, key: str, position, *, wave_number: int = 0) -> EnemyState:
        definition = ENEMY_DEFS[key]
        resistance = (
            min(0.95, 0.7 + 0.02 * max(0, wave_number // 3 - 1))
            if key == "big_boss"
            else (
                min(0.9, 0.45 + 0.02 * max(0, wave_number // 3 - 1))
                if definition.is_boss
                else 0.5
                if definition.is_elite
                else 0.0
            )
        )
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
        if element is not None and self.definition.element is element:
            return
        multiplier = 1.0
        if self.resistance > 0:
            multiplier = 1.0 - self.resistance
        elif self.definition.element is not None and element is not None:
            strong_against, weak_against = TURRET_MATCHUPS[element]
            if self.definition.element is strong_against:
                multiplier = 1.5
            elif self.definition.element is weak_against:
                multiplier = 0.6
            elif OPPOSING_ELEMENTS[self.definition.element] is element:
                multiplier = 0.5
        self.health -= max(1, math.ceil(round(damage * multiplier, 10)))

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
            resistance = self.definition.knockback_resistance
            self.pos += vector.normalize() * distance * (1.0 - resistance)

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


def roll_enemy_seed_drop(
    enemy: EnemyState,
    unlocked_tiers: Mapping[SeedType, int] | None = None,
) -> tuple[SeedType, str]:
    element = enemy.definition.element
    if element is None:
        seed_type = random.choice(tuple(SeedType))
    else:
        seed_type = SeedType[element.name]

    base_weights = (
        ELITE_SEED_TIER_WEIGHTS
        if enemy.definition.is_elite
        else REGULAR_SEED_TIER_WEIGHTS
    )
    max_tier = (
        unlocked_tiers.get(seed_type, 1)
        if unlocked_tiers is not None
        else len(base_weights)
    )
    tiers = [f"tier{tier}" for tier in range(1, max_tier + 1)]
    tier_weights = seed_tier_drop_weights(
        max_tier,
        elite=enemy.definition.is_elite,
    )
    tier = random.choices(tiers, weights=tier_weights, k=1)[0]
    return seed_type, tier


def boss_seed_drop(
    enemy: EnemyState,
    player_type: PlayerType,
    unlocked_tiers: Mapping[SeedType, int] | None = None,
) -> tuple[SeedType, str, int]:
    if not enemy.is_boss:
        raise ValueError("Boss seed drops require a boss enemy.")
    seed_type = SeedType[player_type.name]
    tier_offset = 2 if enemy.key == "big_boss" else 1
    tier = (unlocked_tiers or {}).get(seed_type, 1) + tier_offset
    return seed_type, f"tier{tier}", 3
