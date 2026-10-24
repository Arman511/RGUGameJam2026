import os

import pygame

from elemental_game.settings import SPRITES_DIR

class Player():
    SPEED = 165
    def __init__(self, pos=(0, 0)):
        self.width = 60
        self.height = 60
        image = pygame.image.load(os.path.join(SPRITES_DIR, "player1.png")).convert_alpha()
        self.image = pygame.transform.scale(image, (self.width, self.height))
        self.pos = pygame.Vector2(pos)  # centre of the player
        self.water_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.fire_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.earth_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.air_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.lightning_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.ice_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.coins = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            keys[pygame.K_RIGHT] - keys[pygame.K_LEFT],
            keys[pygame.K_DOWN] - keys[pygame.K_UP],
        )
        if move.length() > 0:
            self.pos += move.normalize() * self.SPEED * dt  # normalize: no faster diagonally

    def draw(self, surface):  # placeholder until the sprite is loaded
        surface.blit(self.image, self.image.get_rect(center=self.pos))