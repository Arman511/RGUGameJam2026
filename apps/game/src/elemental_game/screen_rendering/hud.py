import os

import pygame

from elemental_game import config
from elemental_game.game_entities.crops.crops import get_crop_icon
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.seed import SeedType
from elemental_game.ui_assets import get_coin_icon


def draw_inventory_hud(surface, player, current_wave: int, enemies_killed: int):
    hud_font = pygame.font.Font(
        os.path.join(config.ASSETS_DIR, "font", "pixelfont.ttf"), 16
    )
    panel = pygame.Surface((460, 270), pygame.SRCALPHA)
    panel.fill((25, 28, 35, 225))
    pygame.draw.rect(panel, (225, 225, 225), panel.get_rect(), 2)
    panel.blit(get_coin_icon(20), (12, 8))
    panel.blit(
        hud_font.render(str(player.coins), True, (255, 230, 120)),
        (38, 8),
    )
    panel.blit(
        hud_font.render(f"Current wave: {current_wave}", True, (255, 255, 255)),
        (12, 32),
    )
    panel.blit(
        hud_font.render(f"Enemies killed: {enemies_killed}", True, (255, 255, 255)),
        (230, 32),
    )

    for index, crop_type in enumerate(CropType):
        crop_count = player.crops.get(crop_type, 0)
        row_y = 70 + index * 28
        row_center_y = row_y + 14
        crop_icon = get_crop_icon(crop_type, 22)
        panel.blit(
            crop_icon,
            crop_icon.get_rect(midleft=(310, row_center_y)),
        )
        row_text = (
            (
                f"{crop_type.name.title()} T"
                f"{getattr(player, 'unlocked_seed_tiers', {}).get(SeedType[crop_type.name], 1)}",
                40,
            ),
            (str(crop_count), 338),
        )
        for text, x in row_text:
            rendered_text = hud_font.render(text, True, (255, 255, 255))
            panel.blit(
                rendered_text,
                rendered_text.get_rect(midleft=(x, row_center_y)),
            )
    surface.blit(panel, (10, 64))
