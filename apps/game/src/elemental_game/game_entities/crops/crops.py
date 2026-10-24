"""
Defines crop attributes and behavior
Usage:

new_emberbloom = Crop(<name or id>, CropType.FIRE, (0, 0))
"""

from enum import Enum


class CropType(Enum):
    FIRE = 0
    WATER = 1
    LIGHTNING = 2
    EARTH = 3
    ICE = 4
    WIND = 5


class Crop:
    GROWTH_TIME = 2  # PER STAGE
    VALUE = 3
    WIDTH = 32
    HEIGHT = 32
    CROP_YIELD = 1

    CROP_APPEARANCE = {
        CropType.FIRE: "path to fire plant folder",
        CropType.WATER: "path to water plant folder",
        CropType.LIGHTNING: "path to lightning plant folder",
        CropType.EARTH: "path to earth plant folder",
        CropType.ICE: "path to ice plant folder",
        CropType.WIND: "path to wind plant folder",
    }

    def __init__(self, crop_type, pos):
        if not isinstance(crop_type, CropType):
            raise TypeError(f"crop_type must be a CropType, got {crop_type!r}")
        self.crop_type = crop_type
        self.image = self.CROP_APPEARANCE[crop_type]
        self.pos = pos  # position in farm grid
        self.growth_timer = 0
        self.stage = 0  # how much plant has grown

    def is_ready(self):
        return self.growth_timer >= self.GROWTH_TIME

    def harvest(self):
        # harvest the crop and give user plant
        # return crop_type
        pass

    def get_value(self):
        return self.VALUE

    def get_crop_stage(self):
        # based on time passed since planting, update the stage of the crop
        # return the corresponding appearence png
        pass

    def set_crop_yield(self, y):
        # may want to change this as game progresses
        pass
