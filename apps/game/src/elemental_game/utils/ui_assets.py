import os
from functools import cache

import pygame

from elemental_game.utils.config import IMAGES_DIR


@cache
def get_coin_icon(size: int) -> pygame.Surface:
    image = pygame.image.load(
        os.path.join(IMAGES_DIR, "settings-and-gameplay", "coin.png")
    )
    icon = pygame.Surface(image.get_size(), pygame.SRCALPHA, 32)
    icon.blit(image, (0, 0))
    return pygame.transform.smoothscale(icon, (size, size))
