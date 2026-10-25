from __future__ import annotations

import math
import os
import random
from collections.abc import Mapping
from dataclasses import dataclass, field

import pygame
from elemental_game import config
from elemental_game.config import IMAGES_DIR
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.game_entities.turrets.turrets import TURRET_DEFS
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType

REGULAR_SEED_TIER_WEIGHTS = (50, 45, 15)
ELITE_SEED_TIER_WEIGHTS = (30, 40, 30)


def seed_tier_drop_weights(max_tier: int, *, elite: bool = False) -> tuple[float, ...]:
    base_weights = ELITE_SEED_TIER_WEIGHTS if elite else REGULAR_SEED_TIER_WEIGHTS
    return tuple(
        base_weights[tier - 1]
        if tier <= len(base_weights)
        else base_weights[-1] * 0.25 ** (tier - len(base_weights))
        for tier in range(1, max_tier + 1)
    )


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
    knockback_resistance: float = 0.0


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
        200,
        25,
        20,
        30,
        is_boss=True,
        knockback_resistance=0.75,
    ),
    "big_boss": EnemyDefinition(
        "big_boss",
        "Elemental Colossus",
        "finalboss.png",
        None,
        600,
        25,
        30,
        60,
        is_boss=True,
        knockback_resistance=0.9,
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
    resistance: float = 0.0
    base_speed: float | None = None
    slow_amount: float = 0.0
    target_turret: bool | None = None

    @classmethod
    def create(cls, key: str, position, *, wave_number: int = 0) -> EnemyState:
        definition = ENEMY_DEFS[key]
        resistance = (
            min(0.95, 0.75 + 0.02 * max(0, wave_number // 3 - 1))
            if key == "big_boss"
            else min(0.9, 0.5 + 0.02 * max(0, wave_number // 3 - 1))
            if definition.is_boss
            else 0.5
            if definition.is_elite
            else 0.0
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


class EnemyController:
    @staticmethod
    def update(
        seconds: float,
        enemies: list[EnemyState],
        house,
        turrets,
        player,
        screen: pygame.Surface,
        controlling_house_turret: bool,
    ) -> tuple[list[EnemyState], int]:
        turrets.update(seconds, enemies)
        keys = pygame.key.get_pressed()
        rotate_direction = (
            int(keys[pygame.K_RIGHT] or keys[pygame.K_d])
            - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
            if controlling_house_turret
            else 0
        )
        house_rect = house.return_rect()
        house.turret.update(
            seconds,
            enemies,
            (house_rect.centerx, house_rect.y + 24),
            rotate_direction,
            controlling_house_turret and keys[pygame.K_SPACE],
            screen.get_rect(),
        )

        for enemy in enemies:
            if enemy.health <= 0:
                continue
            enemy.update_status_effects(seconds)
            enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - seconds)
            destination = pygame.Vector2(house_rect.center)
            if enemy.is_boss:
                target_slot = turrets.boss_target(enemy.pos, destination)
            else:
                if enemy.target_turret is None:
                    nearest_slot = turrets.nearest_turret(enemy.pos)
                    enemy.target_turret = (
                        nearest_slot is not None and random.random() < 0.3
                    )
                target_slot = (
                    turrets.nearest_turret(enemy.pos) if enemy.target_turret else None
                )
            if target_slot is not None and target_slot.turret is not None:
                destination = pygame.Vector2(target_slot.center)
                if enemy.pos.distance_to(destination) <= 44:
                    if enemy.attack_cooldown <= 0:
                        damage = enemy.damage * 2 if enemy.is_boss else enemy.damage
                        enemy_element = enemy.definition.element
                        turret_element = TURRET_DEFS[target_slot.turret.key].element
                        if (
                            not enemy.is_boss
                            and enemy_element is not None
                            and TURRET_MATCHUPS[enemy_element][0] is turret_element
                        ):
                            damage = math.ceil(damage * 1.5)
                        turrets.damage_slot(target_slot, damage)
                        enemy.attack_cooldown = 1.0
                else:
                    enemy.move_towards(destination, seconds)
                continue
            if enemy.pos.distance_to(destination) > 55:
                enemy.move_towards(destination, seconds)
            elif enemy.attack_cooldown <= 0:
                house.take_damage(enemy.damage)
                enemy.attack_cooldown = 1.0

        survivors = []
        defeated = 0
        for enemy in enemies:
            if enemy.health <= 0:
                player.coins += enemy.reward
                defeated += 1
                if enemy.is_boss:
                    seed_type, seed_tier, seed_amount = boss_seed_drop(
                        enemy,
                        player.player_type,
                        getattr(player, "unlocked_seed_tiers", None),
                    )
                    player.add_seed(seed_type, seed_tier, seed_amount)
                else:
                    seed_amount = math.ceil(config.ENEMY_SEED_DROP_MULTIPLIER)
                    if seed_amount > 0:
                        seed_type, seed_tier = roll_enemy_seed_drop(
                            enemy, getattr(player, "unlocked_seed_tiers", None)
                        )
                        player.add_seed(seed_type, seed_tier, seed_amount)
            else:
                survivors.append(enemy)
        return survivors, defeated


def load_enemy_images() -> dict[str, pygame.Surface]:
    images = {}
    for key, definition in ENEMY_DEFS.items():
        image = pygame.image.load(
            os.path.join(IMAGES_DIR, "enemy", definition.image)
        ).convert_alpha()
        size = (
            164
            if key == "big_boss"
            else 82
            if definition.is_boss
            else 48
            if definition.is_elite
            else 42
        )
        images[key] = pygame.transform.smoothscale(image, (size, size))
    return images
