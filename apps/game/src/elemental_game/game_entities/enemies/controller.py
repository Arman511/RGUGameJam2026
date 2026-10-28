"""Advance enemy combat and load enemy artwork."""

from __future__ import annotations

import math
import os
import random

import pygame
from elemental_game.utils import config
from elemental_game.utils.config import IMAGES_DIR
from elemental_game.game_entities.turrets.turrets import TURRET_DEFS, TurretInstance

from .definitions import ENEMY_DEFS, TURRET_MATCHUPS
from .enemy import EnemyState, boss_seed_drop, roll_enemy_seed_drop


class EnemyController:
    """Update enemy movement, attacks, and defeat rewards."""

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
                    nearest_slot = turrets.nearest_turret(
                        enemy.pos,
                        enemy.spawn_side,
                    )
                    enemy.target_turret = (
                        nearest_slot is not None and random.random() < 0.3
                    )
                target_slot = (
                    turrets.nearest_turret(enemy.pos, enemy.spawn_side)
                    if enemy.target_turret
                    else None
                )
            if target_slot is not None and target_slot.turret is not None:
                destination = pygame.Vector2(target_slot.center)
                if enemy.pos.distance_to(destination) <= 44:
                    if enemy.attack_cooldown <= 0:
                        if enemy.is_boss:
                            damage_percent = enemy.definition.boss_turret_damage_percent
                            if damage_percent is None:
                                raise ValueError(
                                    "Boss turret damage percentage is not configured."
                                )
                            damage = math.ceil(
                                TurretInstance.MAX_HEALTH * damage_percent / 100
                            )
                        else:
                            damage = enemy.damage
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
                if enemy.is_boss:
                    damage_percent = enemy.definition.boss_house_damage_percent
                    if damage_percent is None:
                        raise ValueError(
                            "Boss house damage percentage is not configured."
                        )
                    damage = math.ceil(house.max_hp * damage_percent / 100)
                else:
                    damage = enemy.damage
                house.take_damage(damage)
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
            else 82 if definition.is_boss else 48 if definition.is_elite else 42
        )
        images[key] = pygame.transform.smoothscale(image, (size, size))
    return images
