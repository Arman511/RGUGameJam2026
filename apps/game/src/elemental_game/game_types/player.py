import os
from enum import IntEnum
from elemental_game.config import IMAGES_DIR


class PlayerType(IntEnum):
    WATER = 1
    EARTH = 2
    LIGHTNING = 3
    ICE = 4
    FIRE = 5
    AIR = 6

    @property
    def image_path(self) -> str:
        return f"{self.name.lower()}-player.png"

    @property
    def full_image_path(self) -> str:
        return os.path.join(IMAGES_DIR, "players", self.image_path)
