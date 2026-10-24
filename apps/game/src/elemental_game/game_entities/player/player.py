import os
from enum import IntEnum

import pygame
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


class Player:
    SPEED = 165

    def __init__(self, pos=(0, 0), player_type: PlayerType = PlayerType.WATER):
        self.width = 60
        self.height = 60
        self.player_type = player_type
        image = pygame.image.load(player_type.full_image_path).convert_alpha()
        self.image = pygame.transform.scale(image, (self.width, self.height))
        self.pos = pygame.Vector2(pos)  # centre of the player
        self.water_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.fire_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.earth_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.air_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.lightning_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.ice_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.coins = 0
        self.crops = {}

    def update(self, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            keys[pygame.K_RIGHT] - keys[pygame.K_LEFT],
            keys[pygame.K_DOWN] - keys[pygame.K_UP],
        )
        if move.length() > 0:
            self.pos += (
                move.normalize() * self.SPEED * dt
            )  # normalize: no faster diagonally

    def draw(self, surface):  # placeholder until the sprite is loaded
        surface.blit(self.image, self.image.get_rect(center=self.pos))

    def add_crop(self, crop_type, amount):
        self.crops[crop_type] = self.crops.get(crop_type, 0) + amount
