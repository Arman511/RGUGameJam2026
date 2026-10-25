"""
Defines crop attributes and behavior
Usage:

new_emberbloom = Crop(<name or id>, CropType.FIRE, (0, 0))
"""

from enum import Enum
from functools import lru_cache
import os
from elemental_game.config import IMAGES_DIR
from elemental_game.types.crop import CropType
import pygame


class Crop:
    GROWTH_TIME = 5
    VALUE = 3
    WIDTH = 32
    HEIGHT = 32
    CROP_YIELD = 1

    CROP_APPEARANCE = {
        CropType.AIR: os.path.join(IMAGES_DIR, "flower", "air-flower.png"),
        CropType.EARTH: os.path.join(IMAGES_DIR, "flower", "earth-flower.png"),
        CropType.FIRE: os.path.join(IMAGES_DIR, "flower", "fire-flower.png"),
        CropType.ICE: os.path.join(IMAGES_DIR, "flower", "ice-flower.png"),
        CropType.LIGHTNING: os.path.join(IMAGES_DIR, "flower", "lightning-flower.png"),
        CropType.WATER: os.path.join(IMAGES_DIR, "flower", "water-flower.png"),
    }

    def __init__(self, crop_type, pos, tier=1):
        if not isinstance(crop_type, CropType):
            raise TypeError(f"crop_type must be a CropType, got {crop_type!r}")
        if not isinstance(tier, int) or isinstance(tier, bool) or tier < 1:
            raise ValueError(f"tier must be a positive integer, got {tier!r}")
        self.crop_type = crop_type
        self.tier = tier
        self.image = self.CROP_APPEARANCE[crop_type]
        self.pos = pos  # position in farm grid
        self.growth_timer = 0

    def is_ready(self):
        return self.growth_timer >= self.GROWTH_TIME

    def harvest(self):
        # harvest the crop and give user plant
        # return crop_type
        pass

    def get_value(self):
        return self.VALUE

    def set_crop_yield(self, y):
        # may want to change this as game progresses
        pass


@lru_cache(maxsize=None)
def get_crop_icon(crop_type: CropType, size: int) -> pygame.Surface:
    loaded_image = pygame.image.load(Crop.CROP_APPEARANCE[crop_type])
    image = pygame.Surface(loaded_image.get_size(), pygame.SRCALPHA, 32)
    image.blit(loaded_image, (0, 0))
    return pygame.transform.smoothscale(image, (size, size))
