"""Player-controlled house turret behavior and visuals."""

from __future__ import annotations

import math
import os

import pygame
from elemental_game.config import IMAGES_DIR, UPGRADE_COST_GROWTH_MULTIPLIER

from .projectiles import ManualProjectile, orient_projectile_image


class ManualTurret:
    """Control the house-mounted turret and its upgrades."""

    UPGRADE_BASE_COST = 10
    FIRE_COOLDOWN = 0.45
    PROJECTILE_SPEED = 800.0
    ROTATION_SPEED = 150.0

    def __init__(self):
        image = pygame.image.load(
            os.path.join(IMAGES_DIR, "turrets", "standard-turret.png")
        ).convert_alpha()
        self.image = pygame.transform.smoothscale(image, (54, 54))
        projectile = pygame.image.load(
            os.path.join(IMAGES_DIR, "turrets", "standard-pellet.png")
        ).convert_alpha()
        self.projectile_image = pygame.transform.scale(projectile, (18, 18))
        self.projectiles: list[ManualProjectile] = []
        self.angle = -90.0
        self.rotation_speed = self.ROTATION_SPEED
        self.cooldown = 0.0
        self.damage_level = 0
        self.fire_rate_level = 0
        self.upgrade_selection = 0
        self.status_message = ""

    def update(
        self,
        dt: float,
        enemies,
        origin,
        rotate_direction: int,
        firing: bool,
        bounds: pygame.Rect | None = None,
    ) -> None:
        rotation_speed = getattr(self, "rotation_speed", self.ROTATION_SPEED)
        self.angle = (self.angle + rotate_direction * rotation_speed * dt) % 360
        self.projectiles = [
            projectile
            for projectile in self.projectiles
            if not projectile.update(dt, enemies, bounds)
        ]
        self.cooldown = max(0.0, self.cooldown - dt)
        if not firing or self.cooldown > 0:
            return
        direction = pygame.Vector2(
            math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle))
        )
        self.projectiles.append(
            ManualProjectile(
                position=pygame.Vector2(origin) - direction * 27,
                direction=direction,
                image=self.projectile_image,
                damage=5 + 5 * self.damage_level,
                speed=self.PROJECTILE_SPEED,
            )
        )
        self.cooldown = max(0.12, self.FIRE_COOLDOWN * (0.82**self.fire_rate_level))

    def upgrade(self, player) -> bool:
        cost = self.next_upgrade_cost
        if player.coins < cost:
            self.status_message = f"Need {cost} coins."
            return False
        player.coins -= cost
        if self.upgrade_selection == 0:
            self.damage_level += 1
            self.status_message = "House turret damage upgraded."
        else:
            self.fire_rate_level += 1
            self.status_message = "House turret fire rate upgraded."
        return True

    @property
    def next_upgrade_cost(self) -> int:
        upgrade_count = self.damage_level + self.fire_rate_level
        return math.ceil(
            self.UPGRADE_BASE_COST * UPGRADE_COST_GROWTH_MULTIPLIER**upgrade_count
        )

    def draw(self, surface, center) -> None:
        rotated = pygame.transform.rotate(self.image, -self.angle - 90)
        surface.blit(rotated, rotated.get_rect(center=center))

    def draw_laser_sight(self, surface: pygame.Surface, center) -> None:
        direction = pygame.Vector2(
            math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle))
        )
        muzzle = pygame.Vector2(center) + direction * 27
        reach = math.hypot(*surface.get_size()) * 2
        endpoint = muzzle + direction * reach
        line = surface.get_rect().clipline(
            (round(muzzle.x), round(muzzle.y)),
            (round(endpoint.x), round(endpoint.y)),
        )
        if not line:
            return
        pygame.draw.line(surface, (255, 0, 0), line[0], line[1], 1)
        pygame.draw.circle(surface, (255, 0, 0), line[1], 5)
        pygame.draw.circle(surface, (255, 230, 230), line[1], 2)

    def draw_projectiles(self, surface) -> None:
        for projectile in self.projectiles:
            image = orient_projectile_image(projectile.image, projectile.direction)
            surface.blit(
                image,
                image.get_rect(center=projectile.position),
            )
