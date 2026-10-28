import os
import random

import pygame
from elemental_game.utils import config
from elemental_game.utils.audio import play_sfx
from elemental_game.utils.config import IMAGES_DIR, TILE_SIZE
from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.game_types.player import PlayerType
from elemental_game.game_types.seed import SeedType


class Farm:
    TILE_SIZE = 50
    QUADRANTS = (
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
    )
    FERTILIZER_DURATION = 60.0
    FERTILIZER_COLORS = {
        CropType.FIRE: (235, 65, 55),
        CropType.AIR: (245, 245, 245),
        CropType.EARTH: (70, 190, 80),
        CropType.WATER: (65, 145, 240),
        CropType.LIGHTNING: (245, 215, 45),
    }
    FERTILIZER_MARKS = {
        CropType.FIRE: "F",
        CropType.AIR: "A",
        CropType.EARTH: "E",
        CropType.WATER: "W",
        CropType.LIGHTNING: "L",
    }
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
        self.grid: list[list[Crop | None]] = [[None] * cols for _ in range(rows)]
        self.menu = CropMenu()  # one menu, created once
        self.planting = False  # True = menu is drawn and taking input
        self.notice_message = ""
        self.notice_timer = 0.0
        self.weather_crop_type: CropType | None = None
        self.pending_plant_tiles = []

        soil_img = pygame.image.load(
            os.path.join(IMAGES_DIR, "settings-and-gameplay", "soil.png")
        ).convert_alpha()
        seedling_img = pygame.image.load(
            os.path.join(IMAGES_DIR, "settings-and-gameplay", "soil_plant.png")
        ).convert_alpha()
        locked_soil_img = pygame.image.load(
            os.path.join(IMAGES_DIR, "settings-and-gameplay", "locked-soil.png")
        ).convert_alpha()
        self.soil_img = pygame.transform.scale(soil_img, (TILE_SIZE, TILE_SIZE))
        self.seedling_img = pygame.transform.scale(seedling_img, (TILE_SIZE, TILE_SIZE))
        self.locked_soil_img = pygame.transform.scale(
            locked_soil_img, (TILE_SIZE - 2, TILE_SIZE - 2)
        )
        self.fertilizers = {}

        self.flower_imgs = {
            crop_type: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                (TILE_SIZE, TILE_SIZE),
            )
            for crop_type, image in Crop.CROP_APPEARANCE.items()
        }

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_empty(self, row, col):
        return self.in_bounds(row, col) and self.grid[row][col] is None

    def quadrant_at(self, row, col):
        if not self.in_bounds(row, col):
            return None
        vertical = "bottom" if row >= self.rows // 2 else "top"
        horizontal = "right" if col >= self.cols // 2 else "left"
        return f"{vertical}_{horizontal}"

    def get_crop(self, row, col):
        if not self.in_bounds(row, col):
            return None
        return self.grid[row][col]

    def plant(self, row, col, crop_type, tier=1, player=None, play_sound=True):
        """Returns the new Crop, or None if the tile is taken or out of bounds."""
        if not self.is_empty(row, col) or (
            player is not None
            and self.quadrant_at(row, col) not in player.unlocked_quadrants
        ):
            return None
        if play_sound:
            play_sfx("planting")
        crop = Crop(crop_type, (row, col), tier)
        self.grid[row][col] = crop
        return crop

    def harvest(self, row, col, play_sound=True):
        """Harvests a ready crop, clears its tile, and returns the crop or None."""
        crop = self.get_crop(row, col)
        if crop is None or not crop.is_ready():
            return None
        if play_sound:
            play_sfx("harvesting")
        self.grid[row][col] = None
        return crop

    def apply_fertilizer(self, quadrant, crop_type):
        if quadrant not in self.QUADRANTS or crop_type not in self.FERTILIZER_COLORS:
            return False
        self.fertilizers[quadrant] = (crop_type, self.FERTILIZER_DURATION)
        return True

    def tile_rect(self, row, col):
        # return the screen area of the tile as x, y, width, height
        return pygame.Rect(
            self.origin[0] + col * TILE_SIZE,
            self.origin[1] + row * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )

    def draw(self, surface, font, player_pos, player=None):
        for row in range(self.rows):
            for col in range(self.cols):
                rect = self.tile_rect(row, col)
                crop = self.grid[row][col]
                quadrant = self.quadrant_at(row, col)
                unlocked = player is None or quadrant in player.unlocked_quadrants

                if not unlocked:
                    surface.blit(self.locked_soil_img, rect)
                elif crop is None:
                    surface.blit(self.soil_img, rect)
                elif crop.is_ready():
                    surface.blit(self.soil_img, rect)  # ground underneath
                    surface.blit(self.flower_imgs[crop.crop_type], rect)  # its flower
                else:
                    surface.blit(self.seedling_img, rect)

                fertilizer = self.fertilizers.get(quadrant)
                if unlocked and fertilizer is not None:
                    crop_type, remaining = fertilizer
                    if remaining > 0:
                        color = self.FERTILIZER_COLORS[crop_type]
                        marker = pygame.Rect(rect.right - 18, rect.y + 2, 16, 16)
                        pygame.draw.circle(surface, (30, 30, 30), marker.center, 8)
                        pygame.draw.circle(surface, color, marker.center, 6)
                        mark = font.render(
                            self.FERTILIZER_MARKS[crop_type],
                            True,
                            (
                                (25, 25, 25)
                                if crop_type is CropType.AIR
                                else (255, 255, 255)
                            ),
                        )
                        surface.blit(mark, mark.get_rect(center=marker.center))

                if (row, col) == player_pos:
                    if unlocked:
                        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                        pygame.draw.rect(overlay, (87, 0, 72, 95), overlay.get_rect())
                        surface.blit(overlay, rect)

    def update(self, dt, *, grow_crops=True):
        if grow_crops:
            for row in self.grid:
                for crop in row:
                    if crop is not None:
                        crop.growth_timer += dt
        for quadrant, (crop_type, remaining) in list(self.fertilizers.items()):
            remaining -= dt
            if remaining <= 0:
                del self.fertilizers[quadrant]
            else:
                self.fertilizers[quadrant] = (crop_type, remaining)
        if self.notice_timer > 0:
            self.notice_timer = max(0.0, self.notice_timer - dt)

    def tile_at_pixel(self, x, y):
        """Convert a mouse position to (row, col), or None if outside the grid."""
        col = int((x - self.origin[0]) // TILE_SIZE)
        row = int((y - self.origin[1]) // TILE_SIZE)
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
        if self.planting:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, (_, _, _, rect) in enumerate(self.menu.options):
                    if rect.collidepoint(event.pos):
                        self.menu.selected = index
                        self._plant_selection(
                            player, self.menu.selected_crop(), self.menu.tile
                        )
                        self.planting = False
                        break
                return
            if event.type != pygame.KEYDOWN:
                return
            if event.key == pygame.K_ESCAPE:
                self.planting = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.menu.move_selection(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu.move_selection(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._plant_selection(player, self.menu.selected_crop(), self.menu.tile)
                self.planting = False
            return

        # determine if and which tile player is standing on
        if event.type != pygame.KEYDOWN:
            return  # why is there a return statement here do we need this at all
        tile = self.tile_at_pixel(*player.pos)

        if event.key == pygame.K_f and tile:
            crop = self.get_crop(*tile)
            if crop is not None and crop.is_ready():
                self._harvest_area(tile, player)
            elif crop is None and self.quadrant_at(*tile) in player.unlocked_quadrants:
                plant_size = getattr(player, "plant_radius_active", 1)
                self.pending_plant_tiles = self._area_tiles(
                    tile, plant_size, player, empty_only=True
                )
                self.menu.move_to(tile, self.tile_rect(*tile).bottomleft, player)
                if self.menu.options:
                    self.notice_timer = 0.0
                if len(self.menu.options) == 1:
                    self._plant_selection(player, self.menu.selected_crop(), tile)
                    self.planting = False
                else:
                    self.planting = len(self.menu.options) > 1
                if not self.planting and not self.menu.options:
                    self.pending_plant_tiles = []
                    self.notice_message = (
                        "Buy seeds in the market first. Press M to open the market."
                    )
                    self.notice_timer = 2.5
        elif event.key in (pygame.K_g, pygame.K_RETURN) and tile:
            self._harvest_area(tile, player)

    def _plant_selection(self, player, selection, tile):
        if selection is None or tile is None:
            return
        crop_type, tier = selection
        seed_type = SeedType[crop_type.name]
        targets = getattr(self, "pending_plant_tiles", None) or [tile]
        planted_count = 0
        for row, col in targets:
            if player.seeds[seed_type][f"tier{tier}"] <= 0:
                break
            if not player.consume_seed(seed_type, tier):
                break
            planted = self.plant(
                row,
                col,
                crop_type,
                tier,
                player,
                play_sound=planted_count == 0,
            )
            if planted is None:
                player.add_seed(seed_type, f"tier{tier}", 1)
                continue
            planted_count += 1
        self.pending_plant_tiles = []

    def _area_tiles(self, center, size, player, *, empty_only=False):
        row_start = center[0] - (size - 1) // 2
        col_start = center[1] - (size - 1) // 2
        tiles = []
        for row in range(row_start, row_start + size):
            for col in range(col_start, col_start + size):
                if not self.in_bounds(row, col):
                    continue
                if self.quadrant_at(row, col) not in player.unlocked_quadrants:
                    continue
                if empty_only and not self.is_empty(row, col):
                    continue
                tiles.append((row, col))
        return tiles

    def _harvest_area(self, center, player):
        size = max(1, getattr(player, "harvest_size", 1))
        harvested_count = 0
        for row, col in self._area_tiles(center, size, player):
            crop = self.get_crop(row, col)
            if crop is None or not crop.is_ready():
                continue
            self._harvest_for_player(
                row,
                col,
                player,
                play_sound=harvested_count == 0,
            )
            harvested_count += 1

    def _harvest_for_player(self, row, col, player, play_sound=True):
        crop = self.get_crop(row, col)
        if crop is None or not crop.is_ready():
            return
        harvested = self.harvest(row, col, play_sound=play_sound)
        if harvested is None:
            return
        yield_amount = harvested.tier
        if harvested.crop_type is getattr(self, "weather_crop_type", None):
            yield_amount *= 2
        if harvested.crop_type.name == player.player_type.name:
            if random.random() < 0.25:
                yield_amount *= 2
        elif (
            harvested.crop_type is self.OPPOSING_ELEMENTS[player.player_type]
            and random.random() < 0.10
        ):
            yield_amount //= 2
        fertilizer = self.fertilizers.get(self.quadrant_at(row, col))
        if (
            fertilizer is not None
            and fertilizer[0] is harvested.crop_type
            and fertilizer[1] > 0
        ):
            yield_amount *= 2
        player.add_crop(harvested.crop_type, yield_amount)

    def draw_menu(self, surface, font):
        if self.planting:
            self.menu.draw(surface, font)
        elif self.notice_timer > 0:
            banner = font.render(self.notice_message, True, (255, 245, 180))
            background = pygame.Surface(
                (banner.get_width() + 24, banner.get_height() + 16),
                pygame.SRCALPHA,
            )
            background.fill((35, 35, 35, 220))
            background.blit(banner, (12, 8))
            surface.blit(
                background,
                background.get_rect(
                    midtop=(surface.get_width() // 2, surface.get_height() - 70)
                ),
            )


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
            unlocked_tier = getattr(player, "unlocked_seed_tiers", {}).get(seed_type, 1)
            for tier_key, count in sorted(
                player.seeds[seed_type].items(),
                key=lambda item: int(item[0][4:]),
            ):
                tier = int(tier_key[4:])
                if count > 0 and tier <= unlocked_tier:
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
