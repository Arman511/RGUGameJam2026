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

    APPEARANCE = {HouseState.FIXED: os.path.join(IMAGES_DIR, "house", "house.png"),
                  HouseState.BROKEN: os.path.join(IMAGES_DIR, "house", "broken-house.png"),
                  HouseState.DESTROYED: os.path.join(IMAGES_DIR, "house", "fire-house.png")}

    def __init__(self):
        self.max_hp = 100
        self.state = HouseState.FIXED
        self.dimensions = (250, 200)

        self.house_images = {
            house_state: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                self.dimensions,
            )
            for house_state, image in self.APPEARANCE.items()
        }

    def draw(self, surface):
        surface.blit(self.house_images[self.state], self.return_rect())

    def return_rect(self):
        y = FARM_HEIGHT - 225
        x = (WINDOW_WIDTH - self.dimensions[0])//2
        return pygame.Rect(x, y, *self.dimensions)

