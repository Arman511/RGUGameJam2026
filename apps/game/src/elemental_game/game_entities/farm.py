"""
Defines the farm grid: where crops are planted, grown and harvested

Usage:

farm.plant(0, 0, CropType.FIRE)
farm.update(dt)      # every frame
"""

import pygame
from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.config import IMAGES_DIR
import os


class Farm:
    TILE_SIZE = 50

    def __init__(self, rows, cols, origin=(0, 0)):
        self.rows = rows
        self.cols = cols
        self.origin = origin  # top-left pixel of the grid
        self.grid = [[None] * cols for _ in range(rows)]
        self.menu = CropMenu()  # one menu, created once
        self.planting = False  # True = menu is drawn and taking input

        soil_img = pygame.image.load(
            os.path.join(IMAGES_DIR, "settings-and-gameplay", "soil.png")
        ).convert_alpha()
        seedling_img = pygame.image.load(
            os.path.join(IMAGES_DIR, "settings-and-gameplay", "soil_plant.png")
        ).convert_alpha()
        self.soil_img = pygame.transform.scale(
            soil_img, (self.TILE_SIZE, self.TILE_SIZE)
        )
        self.seedling_img = pygame.transform.scale(
            seedling_img, (self.TILE_SIZE, self.TILE_SIZE)
        )

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
        for row in range(self.rows):
            for col in range(self.cols):
                rect = self.tile_rect(row, col)
                surface.blit(self.soil_img, rect)

                crop = self.grid[row][col]
                if crop:
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

    def handle_event(self, event, player):
        # determine if and which tile player is standing on
        if event.type != pygame.KEYDOWN:
            return  # why is there a return statement here do we need this at all
        tile = self.tile_at_pixel(*player.pos)

        # if a player does farm action
        if event.key == pygame.K_f and tile and self.is_empty(*tile):
            self.menu.move_to(
                tile, self.tile_rect(*tile).bottomleft
            )  # position the menu
            self.planting = True
        # if a player does harvest action
        elif event.key == pygame.K_h and tile:
            crop = self.get_crop(*tile)  # determine which crop is on that tile
            if crop is not None and crop.is_ready():
                self.harvest(*tile)  # player gains some crop
                player.add_crop(crop.crop_type, crop.CROP_YIELD)

        if self.planting:
            if event.key == pygame.K_UP:
                self.menu.move_selection(-1)
            elif event.key == pygame.K_DOWN:
                self.menu.move_selection(1)
            elif event.key == pygame.K_RETURN:
                self.plant(*self.menu.tile, self.menu.selected_type())
                self.planting = False

    def draw_menu(self, surface, font):
        if self.planting:  # good
            self.menu.draw(surface, font)


class CropMenu:
    """Popup listing the plant types."""

    ITEM_W, ITEM_H = 120, 30

    def __init__(self):
        self.tile = None  # tile the menu is currently open for
        self.selected = 0  # index of the highlighted option
        self.options = [
            (crop_type, pygame.Rect(0, 0, self.ITEM_W, self.ITEM_H))
            for crop_type in CropType
        ]

    def move_to(self, tile, pos):
        """Point the menu at a tile, place it at pos and reset the selection."""
        self.tile = tile
        self.selected = 0
        for i, (_, rect) in enumerate(self.options):
            rect.topleft = (pos[0], pos[1] + i * self.ITEM_H)

    def move_selection(self, step):
        self.selected = (self.selected + step) % len(self.options)  # wraps around

    def selected_type(self):
        return self.options[self.selected][0]

    def draw(self, surface, font):
        for i, (crop_type, rect) in enumerate(self.options):
            colour = (110, 110, 110) if i == self.selected else (60, 60, 60)
            pygame.draw.rect(surface, colour, rect)
            pygame.draw.rect(surface, (200, 200, 200), rect, 1)
            text = font.render(crop_type.name.title(), True, (255, 255, 255))
            surface.blit(text, text.get_rect(midleft=(rect.x + 8, rect.centery)))
