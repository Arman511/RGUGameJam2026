"""
Defines the farm grid: where crops are planted, grown and harvested

Usage:

farm.plant(0, 0, CropType.FIRE)
farm.update(dt)      # every frame
"""

import pygame
from elemental_game.game_entities.crops.crops import Crop


class Farm:
    TILE_SIZE = 32

    def __init__(self, rows, cols, origin=(0, 0)):
        self.rows = rows
        self.cols = cols
        self.origin = origin  # top-left pixel of the grid
        self.grid = [[None] * cols for _ in range(rows)]

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_empty(self, row, col):
        return self.in_bounds(row, col) and self.grid[row][col] is None

    def get_crop(self, row, col):
        if not self.in_bounds(row, col):
            return None
        return self.grid[row][col]

    def plant(self, row, col, crop_type):
        """Returns the new Crop, or None if the tile is taken or out of bounds."""
        if not self.is_empty(row, col):
            return None
        crop = Crop(crop_type, (row, col))
        self.grid[row][col] = crop
        return crop

    def harvest(self, row, col):
        """Harvests the crop if it's ready and clears the tile. Returns the crop type or None."""
        crop = self.get_crop(row, col)
        if crop is None or not crop.is_ready():
            return None
        self.grid[row][col] = None
        return crop.harvest()

    def tile_rect(self, row, col):
        # return the screen area of the tile as x, y, width, height
        return pygame.Rect(
            self.origin[0] + col * self.TILE_SIZE,
            self.origin[1] + row * self.TILE_SIZE,
            self.TILE_SIZE,
            self.TILE_SIZE,
        )

    def draw(self, surface, font, hovered=None):
        # draw the farm tiles on the screen
        for row in range(self.rows):
            for col in range(self.cols):  # placeholder:
                rect = self.tile_rect(row, col)
                colour = (150, 105, 60) if (row, col) == hovered else (120, 80, 40)
                pygame.draw.rect(surface, colour, rect)
                pygame.draw.rect(surface, (60, 40, 20), rect, 1)

                crop = self.grid[row][col]
                if crop:  # Placeholder: will be replaced with crop image
                    colour = (0, 255, 0) if crop.is_ready() else (255, 255, 255)
                    letter = font.render(crop.crop_type.name[0], True, colour)
                    surface.blit(letter, letter.get_rect(center=rect.center))

    def update(self, dt):
        for row in self.grid:
            for crop in row:
                if crop is not None:
                    crop.growth_timer += dt
                    crop.get_crop_stage()  # updates crop.stage

    def tile_at_pixel(self, x, y):
        """Convert a mouse position to (row, col), or None if outside the grid."""
        col = int((x - self.origin[0]) // self.TILE_SIZE)
        row = int((y - self.origin[1]) // self.TILE_SIZE)
        return (row, col) if self.in_bounds(row, col) else None

    def expand(self, add_rows=0, add_cols=0):
        """Grow the farm to the right (cols) and/or downwards (rows)."""
        for row in self.grid:
            row.extend([None] * add_cols)
        for _ in range(add_rows):
            self.grid.append([None] * (self.cols + add_cols))
        self.rows += add_rows
        self.cols += add_cols
