from elemental_game.types.crop import CropType
import pygame
from elemental_game.types.seed import SeedType


def draw_inventory_hud(surface, hud_font, player):
    panel = pygame.Surface((460, 220), pygame.SRCALPHA)
    panel.fill((25, 28, 35, 225))
    pygame.draw.rect(panel, (225, 225, 225), panel.get_rect(), 2)
    small_font = pygame.font.Font(None, 20)
    panel.blit(
        small_font.render(f"Coins: {player.coins}", True, (255, 230, 120)),
        (12, 8),
    )

    for index, crop_type in enumerate(CropType):
        seeds = player.seeds[SeedType[crop_type.name]]
        crop_count = player.crops.get(crop_type, 0)
        row_y = 40 + index * 28
        panel.blit(
            small_font.render(crop_type.name.title(), True, (255, 255, 255)),
            (12, row_y),
        )
        panel.blit(
            small_font.render(
                f"T1: {seeds['tier1']}   T2: {seeds['tier2']}   T3: {seeds['tier3']}",
                True,
                (255, 255, 255),
            ),
            (105, row_y),
        )
        panel.blit(
            small_font.render(f"Crops:  {crop_count}", True, (255, 255, 255)),
            (330, row_y),
        )
    surface.blit(panel, (10, 48))
