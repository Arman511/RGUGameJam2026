"""
Defines the farm grid: where crops are planted, grown and harvested

Usage:

farm.plant(0, 0, CropType.FIRE)
farm.update(dt)      # every frame
"""

import pygame
import random
from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType
from elemental_game.config import IMAGES_DIR
import os


class Farm:
    TILE_SIZE = 50
    OPPOSING_ELEMENTS = {
        PlayerType.FIRE: CropType.WATER,
        PlayerType.WATER: CropType.FIRE,
        PlayerType.EARTH: CropType.LIGHTNING,
        PlayerType.LIGHTNING: CropType.EARTH,
        PlayerType.ICE: CropType.AIR,
        PlayerType.AIR: CropType.ICE,
    }

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

        self.flower_imgs = {
            crop_type: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                (self.TILE_SIZE, self.TILE_SIZE),
            )
            for crop_type, image in Crop.CROP_APPEARANCE.items()
        }

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_empty(self, row, col):
        return self.in_bounds(row, col) and self.grid[row][col] is None

    def get_crop(self, row, col):
        if not self.in_bounds(row, col):
            return None
        return self.grid[row][col]

    def plant(self, row, col, crop_type, tier=1):
        """Returns the new Crop, or None if the tile is taken or out of bounds."""
        if not self.is_empty(row, col):
            return None
        crop = Crop(crop_type, (row, col), tier)
        self.grid[row][col] = crop
        return crop

    def harvest(self, row, col):
        """Harvests a ready crop, clears its tile, and returns the crop or None."""
        crop = self.get_crop(row, col)
        if crop is None or not crop.is_ready():
            return None
        self.grid[row][col] = None
        return crop

    def tile_rect(self, row, col):
        # return the screen area of the tile as x, y, width, height
        return pygame.Rect(
            self.origin[0] + col * self.TILE_SIZE,
            self.origin[1] + row * self.TILE_SIZE,
            self.TILE_SIZE,
            self.TILE_SIZE,
        )

    def draw(self, surface, font, player_pos):
        for row in range(self.rows):
            for col in range(self.cols):
                rect = self.tile_rect(row, col)
                crop = self.grid[row][col]

                if crop is None:
                    surface.blit(self.soil_img, rect)
                elif crop.is_ready():
                    surface.blit(self.soil_img, rect)  # ground underneath
                    surface.blit(self.flower_imgs[crop.crop_type], rect)  # its flower
                else:
                    surface.blit(self.seedling_img, rect)

                if (row, col) == player_pos:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(overlay, (87, 0, 72, 95), overlay.get_rect())
                    surface.blit(overlay, rect)

    def update(self, dt):
        for row in self.grid:
            for crop in row:
                if crop is not None:
                    crop.growth_timer += dt

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
            self.menu.move_to(tile, self.tile_rect(*tile).bottomleft, player)
            self.planting = bool(self.menu.options)
        # if a player does harvest action
        elif event.key == pygame.K_g and tile:
            crop = self.get_crop(*tile)  # determine which crop is on that tile
            if crop is not None and crop.is_ready():
                harvested = self.harvest(*tile)
                yield_amount = harvested.tier
                if harvested.crop_type.name == player.player_type.name:
                    if random.random() < 0.25:
                        yield_amount *= 2
                elif (
                    harvested.crop_type
                    is self.OPPOSING_ELEMENTS[player.player_type]
                    and random.random() < 0.10
                ):
                    yield_amount //= 2
                player.add_crop(harvested.crop_type, yield_amount)

        if self.planting:
            if event.key == pygame.K_ESCAPE:
                self.planting = False
            elif event.key == pygame.K_UP:
                self.menu.move_selection(-1)
            elif event.key == pygame.K_DOWN:
                self.menu.move_selection(1)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                selection = self.menu.selected_crop()
                if selection is not None:
                    crop_type, tier = selection
                    seed_type = SeedType[crop_type.name]
                    if player.consume_seed(seed_type, tier):
                        self.plant(*self.menu.tile, crop_type, tier)
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
        self.options = []

    def move_to(self, tile, pos, player):
        """Point the menu at a tile, place it at pos and reset the selection."""
        self.tile = tile
        self.selected = 0
        self.options = []
        for crop_type in CropType:
            seed_type = SeedType[crop_type.name]
            for tier in (1, 2, 3):
                count = player.seeds[seed_type][f"tier{tier}"]
                if count > 0:
                    rect = pygame.Rect(
                        pos[0],
                        pos[1] + len(self.options) * self.ITEM_H,
                        self.ITEM_W,
                        self.ITEM_H,
                    )
                    self.options.append((crop_type, tier, count, rect))

    def move_selection(self, step):
        if self.options:
            self.selected = (self.selected + step) % len(self.options)

    def selected_crop(self):
        if not self.options:
            return None
        crop_type, tier, _, _ = self.options[self.selected]
        return crop_type, tier

    def draw(self, surface, font):
        if not self.options:
            return

        text_surfaces = [
            font.render(
                f"{crop_type.name.title()} T{tier} ({count})",
                True,
                (255, 255, 255),
            )
            for crop_type, tier, count, _ in self.options
        ]
        menu_width = min(
            surface.get_width(),
            max(self.ITEM_W, max(text.get_width() + 16 for text in text_surfaces)),
        )
        row_height = min(
            self.ITEM_H,
            max(1, surface.get_height() // len(self.options)),
        )
        menu_height = row_height * len(self.options)
        anchor = self.options[0][3]
        menu_x = min(max(0, anchor.x), surface.get_width() - menu_width)
        menu_y = min(max(0, anchor.y), surface.get_height() - menu_height)

        for i, ((_, _, _, rect), text) in enumerate(zip(self.options, text_surfaces)):
            rect.update(menu_x, menu_y + i * row_height, menu_width, row_height)
            colour = (110, 110, 110) if i == self.selected else (60, 60, 60)
            pygame.draw.rect(surface, colour, rect)
            pygame.draw.rect(surface, (200, 200, 200), rect, 1)
            surface.blit(text, text.get_rect(midleft=(rect.x + 8, rect.centery)))
