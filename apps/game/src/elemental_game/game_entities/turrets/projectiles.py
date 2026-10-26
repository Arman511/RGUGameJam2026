"""Projectile state and movement shared by automated and manual turrets."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import pygame
from elemental_game.game_entities.crops.crops import CropType


class ProjectileTarget(Protocol):
    """Describe the damage and movement effects a projectile can apply."""

    health: int
    pos: pygame.Vector2

    def take_damage(self, damage: int, element: CropType | None = None) -> None: ...

    def apply_slow(self, amount: float) -> None: ...

    def apply_knockback(self, direction, distance: float) -> None: ...
@dataclass
class TurretProjectile:
    """Move a turret shot toward its selected enemy."""

    position: pygame.Vector2
    target: ProjectileTarget
    image: pygame.Surface
    damage: int
    element: CropType | None
    slow: float = 0.0
    knockback: float = 0.0
    direction: pygame.Vector2 | None = None
    speed: float = 500.0

    def update(self, dt: float) -> bool:
        if self.target.health <= 0:
            return True
        offset = pygame.Vector2(self.target.pos) - self.position
        distance = offset.length()
        travel = self.speed * dt
        if distance <= travel:
            self.position = pygame.Vector2(self.target.pos)
            self.target.take_damage(self.damage, self.element)
            self.target.apply_slow(self.slow)
            if self.knockback and self.direction is not None:
                self.target.apply_knockback(self.direction, self.knockback)
            return True
        if distance:
            self.position += offset * (travel / distance)
        return False
@dataclass
class ManualProjectile:
    """Move a player-fired shot and detect its first enemy hit."""

    position: pygame.Vector2
    direction: pygame.Vector2
    image: pygame.Surface
    damage: int
    speed: float = 800.0
    hit_radius: float = 20.0

    def update(self, dt: float, enemies, bounds: pygame.Rect | None) -> bool:
        movement = self.direction * (self.speed * dt)
        start = pygame.Vector2(self.position)
        self.position += movement
        movement_length_squared = movement.length_squared()
        if movement_length_squared:
            candidates = []
            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                progress = max(
                    0.0,
                    min(
                        1.0,
                        (pygame.Vector2(enemy.pos) - start).dot(movement)
                        / movement_length_squared,
                    ),
                )
                closest = start + movement * progress
                if closest.distance_to(enemy.pos) <= self.hit_radius:
                    candidates.append((progress, enemy))
            if candidates:
                _, target = min(candidates, key=lambda candidate: candidate[0])
                target.take_damage(self.damage)
                return True
        return bounds is not None and not bounds.collidepoint(self.position)
def _projectile_image_angle(direction: pygame.Vector2) -> float:
    direction_angle = math.degrees(math.atan2(direction.y, direction.x))
    return -direction_angle - 90
def orient_projectile_image(
    image: pygame.Surface, direction: pygame.Vector2
) -> pygame.Surface:
    if not direction.length_squared():
        return image
    return pygame.transform.rotate(image, _projectile_image_angle(direction))
