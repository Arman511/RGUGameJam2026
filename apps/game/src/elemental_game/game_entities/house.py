import math
import os
from enum import Enum
from typing import ClassVar

import pygame
from elemental_game.config import (
    FARM_HEIGHT,
    IMAGES_DIR,
    UPGRADE_COST_GROWTH_MULTIPLIER,
    WINDOW_WIDTH,
)
from elemental_game.game_entities.turrets.turrets import ManualTurret


class HouseState(Enum):
    FIXED = 1
    BROKEN = 2
    DESTROYED = 3


class House:
    MAX_HP = 100
    BAR_SIZE = (250, 24)
    BAR_MARGIN = 20
    BAR_TOP = 32

    APPEARANCE: ClassVar[dict[HouseState, str]] = {
        HouseState.FIXED: os.path.join(IMAGES_DIR, "house", "house.png"),
        HouseState.BROKEN: os.path.join(IMAGES_DIR, "house", "broken-house.png"),
        HouseState.DESTROYED: os.path.join(IMAGES_DIR, "house", "fire-house.png"),
    }

    def __init__(self, surface: pygame.Surface | None = None):
        self.max_hp = self.MAX_HP
        self.health = self.max_hp
        self.health_upgrade_count = 0
        self.repair_count = 0
        self.state = HouseState.FIXED
        self.dimensions = (250, 200)
        self.surface = surface
        self.turret = ManualTurret()

        self.house_images = {
            house_state: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                self.dimensions,
            )
            for house_state, image in self.APPEARANCE.items()
        }

    @property
    def hp(self) -> int:
        return self.health

    def update(self) -> None:
        health = self.hp / self.max_hp * 100
        match health:
            case x if x > 50:
                self.state = HouseState.FIXED
            case x if x > 0:
                self.state = HouseState.BROKEN
            case _:
                self.state = HouseState.DESTROYED

    @hp.setter
    def hp(self, value: int) -> None:
        self.health = max(0, min(self.max_hp, value))
        self.update()

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.house_images[self.state], self.return_rect())
        self.turret.draw(
            surface, (self.return_rect().centerx, self.return_rect().y + 24)
        )
        self.draw_health_bar(surface)

    def draw_health_bar(self, surface: pygame.Surface) -> None:
        width, height = self.BAR_SIZE
        x = surface.get_width() - width - self.BAR_MARGIN
        y = self.BAR_TOP
        ratio = self.health / self.max_hp
        if ratio > 0.5:
            color = (80, 200, 80)
        elif ratio > 0.2:
            color = (230, 180, 50)
        else:
            color = (210, 60, 60)

        pygame.draw.rect(surface, (40, 40, 40), (x, y, width, height))
        pygame.draw.rect(surface, color, (x, y, round(width * ratio), height))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, width, height), 2)

    def take_damage(self, damage_took: int) -> None:
        self.health = max(0, round(self.health - damage_took))
        self.update()

    def increase_max_health(self) -> None:
        self.max_hp = round(self.max_hp * 1.25)
        self.health = round(self.health * 1.25)
        self.update()

    @property
    def next_health_upgrade_cost(self) -> int:
        return math.ceil(25 * UPGRADE_COST_GROWTH_MULTIPLIER**self.health_upgrade_count)

    @property
    def next_repair_cost(self) -> int:
        return math.ceil(10 * UPGRADE_COST_GROWTH_MULTIPLIER**self.repair_count)

    def repair(self) -> None:
        self.health = min(self.max_hp, round(self.health + self.max_hp * 0.25))
        self.update()

    def return_rect(self) -> pygame.Rect:
        y = FARM_HEIGHT - 225
        x = (WINDOW_WIDTH - self.dimensions[0]) // 2
        return pygame.Rect(x, y, *self.dimensions)

    def turret_control_rect(self) -> pygame.Rect:
        house_rect = self.return_rect()
        rooftop_rect = pygame.Rect(
            house_rect.x + 10,
            house_rect.y - 35,
            house_rect.width - 20,
            110,
        )
        return house_rect.union(rooftop_rect)

    def get_hp(self):
        return self.health
