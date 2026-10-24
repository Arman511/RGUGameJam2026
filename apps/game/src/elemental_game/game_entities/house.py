import os
from enum import Enum
from typing import ClassVar

import pygame
from elemental_game.config import FARM_HEIGHT, IMAGES_DIR, WINDOW_WIDTH
from elemental_game.game_entities.turrets.turrets import ManualTurret


class HouseState(Enum):
    FIXED = 1
    BROKEN = 2
    DESTROYED = 3


class House:
    MAX_HP = 100

    APPEARANCE: ClassVar[dict[HouseState, str]] = {
        HouseState.FIXED: os.path.join(IMAGES_DIR, "house", "house.png"),
        HouseState.BROKEN: os.path.join(IMAGES_DIR, "house", "broken-house.png"),
        HouseState.DESTROYED: os.path.join(IMAGES_DIR, "house", "fire-house.png"),
    }

    def __init__(self):
        self.max_hp = 100
        self.health = self.max_hp
        self.state = HouseState.FIXED
        self.dimensions = (250, 200)
        self.turret = ManualTurret()

        self.house_images = {
            house_state: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                self.dimensions,
            )
            for house_state, image in self.APPEARANCE.items()
        }

    def draw(self, surface):
        surface.blit(self.house_images[self.state], self.return_rect())
        self.turret.draw(
            surface, (self.return_rect().centerx, self.return_rect().y + 24)
        )
        if self.health < self.max_hp:
            rect = self.return_rect()
            bar = pygame.Rect(rect.x + 45, rect.y - 12, rect.width - 90, 8)
            pygame.draw.rect(surface, (85, 25, 25), bar)
            pygame.draw.rect(
                surface,
                (80, 220, 90),
                (
                    bar.x,
                    bar.y,
                    bar.width * max(0, self.health) / self.max_hp,
                    bar.height,
                ),
            )

    def take_damage(self, damage):
        self.health = max(0, self.health - damage)
        if self.health == 0:
            self.state = HouseState.DESTROYED
        elif self.health <= self.max_hp // 2:
            self.state = HouseState.BROKEN

    def return_rect(self):
        y = FARM_HEIGHT - 225
        x = (WINDOW_WIDTH - self.dimensions[0]) // 2
        return pygame.Rect(x, y, *self.dimensions)

    def turret_control_rect(self):
        house_rect = self.return_rect()
        return pygame.Rect(
            house_rect.x + 10,
            house_rect.y - 35,
            house_rect.width - 20,
            110,
        )
