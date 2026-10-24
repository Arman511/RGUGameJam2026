from enum import Enum
import os
from elemental_game.config import IMAGES_DIR, FARM_HEIGHT, WINDOW_WIDTH
import pygame

class HouseState(Enum):
    FIXED = 1
    BROKEN = 2
    DESTROYED = 3

class House:
    MAX_HP = 100

    BAR_SIZE = (250, 24)
    BAR_MARGIN = 20

    APPEARANCE = {HouseState.FIXED: os.path.join(IMAGES_DIR, "house", "house.png"),
                  HouseState.BROKEN: os.path.join(IMAGES_DIR, "house", "broken-house.png"),
                  HouseState.DESTROYED: os.path.join(IMAGES_DIR, "house", "fire-house.png")}

    def __init__(self, surface):
        self.max_hp = 100
        self.state = HouseState.FIXED
        self.dimensions = (250, 200)
        self.surface = surface

        self.house_images = {
            house_state: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                self.dimensions,
            )
            for house_state, image in self.APPEARANCE.items()
        }

        self.hp = self.max_hp

    def draw(self, surface):
        surface.blit(self.house_images[self.state], self.return_rect())
        self.draw_health_bar(surface)

    def draw_health_bar(self, surface):
        width, height = self.BAR_SIZE
        x = WINDOW_WIDTH - width - self.BAR_MARGIN   # top right
        y = self.BAR_MARGIN
        ratio = self.hp / self.max_hp

        if ratio > 0.5:
            colour = (80, 200, 80)
        elif ratio > 0.2:
            colour = (230, 180, 50)
        else:
            colour = (210, 60, 60)

        pygame.draw.rect(surface, (40, 40, 40), (x, y, width, height))               # empty part
        pygame.draw.rect(surface, colour, (x, y, round(width * ratio), height))      # filled part
        pygame.draw.rect(surface, (255, 255, 255), (x, y, width, height), 2)         # border

    def update(self):
        health = self.hp / self.max_hp * 100
        match health:
            case x if x > 50:
                self.state = HouseState.FIXED
            case x if x > 0:
                self.state = HouseState.BROKEN
            case _:
                self.state = HouseState.DESTROYED
        self.draw(self.surface)

    def return_rect(self):
        y = FARM_HEIGHT - 225
        x = (WINDOW_WIDTH - self.dimensions[0])//2
        return pygame.Rect(x, y, *self.dimensions)

    def take_damage(self, damage_took):
        self.hp = max(0, round(self.hp - damage_took))
        self.update()

    def increase_max_health(self):
        self.max_hp = round(self.max_hp * 1.25)
        self.hp = round(self.hp*1.25)
        self.update()

    def repair(self):
        self.hp = min(self.max_hp, round(self.max_hp * 0.25))
        self.update()

    def get_hp(self):
        return self.max_hp