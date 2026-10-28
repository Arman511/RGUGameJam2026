import pygame

from elemental_game.game_entities.crops.crops import get_crop_icon
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.seed import SeedType


class SeedTierReward:
    ROW_HEIGHT = 42
    PANEL_WIDTH = 470

    def __init__(self) -> None:
        self.selected = 0

    @staticmethod
    def _panel_rect(surface: pygame.Surface) -> pygame.Rect:
        panel = pygame.Rect(
            0,
            0,
            min(SeedTierReward.PANEL_WIDTH, surface.get_width() - 32),
            min(430, surface.get_height() - 32),
        )
        panel.center = surface.get_rect().center
        return panel

    def _row_rect(self, panel: pygame.Rect, index: int) -> pygame.Rect:
        return pygame.Rect(
            panel.x + 18,
            panel.y + 102 + index * self.ROW_HEIGHT,
            panel.width - 36,
            self.ROW_HEIGHT - 4,
        )

    def handle_event(
        self, event: pygame.event.Event, player, surface: pygame.Surface
    ) -> SeedType | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(CropType)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(CropType)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._unlock_selected(player)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            panel = self._panel_rect(surface)
            for index, _ in enumerate(CropType):
                if self._row_rect(panel, index).collidepoint(event.pos):
                    self.selected = index
                    return self._unlock_selected(player)
        return None

    def _unlock_selected(self, player) -> SeedType:
        seed_type = SeedType[tuple(CropType)[self.selected].name]
        player.unlock_next_seed_tier(seed_type)
        return seed_type

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, player) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        panel = self._panel_rect(surface)
        pygame.draw.rect(surface, (38, 43, 54), panel, border_radius=10)
        pygame.draw.rect(surface, (235, 220, 155), panel, 2, border_radius=10)
        title = font.render("BOSS REWARD: UNLOCK A SEED TIER", True, (255, 230, 150))
        surface.blit(title, title.get_rect(midtop=(panel.centerx, panel.y + 20)))
        instructions = font.render(
            "W/S or UP/DOWN, then ENTER (or click)",
            True,
            (230, 230, 230),
        )
        surface.blit(
            instructions,
            instructions.get_rect(midtop=(panel.centerx, panel.y + 62)),
        )

        for index, crop_type in enumerate(CropType):
            row = self._row_rect(panel, index)
            if index == self.selected:
                pygame.draw.rect(surface, (91, 100, 78), row, border_radius=5)
            pygame.draw.rect(surface, (145, 155, 160), row, 1, border_radius=5)
            icon = get_crop_icon(crop_type, 30)
            surface.blit(icon, icon.get_rect(midleft=(row.x + 8, row.centery)))
            tier = player.max_unlocked_seed_tier(SeedType[crop_type.name]) + 1
            label = font.render(
                f"{crop_type.name.title()} seed - unlock Tier {tier}",
                True,
                (255, 255, 255),
            )
            surface.blit(label, label.get_rect(midleft=(row.x + 48, row.centery)))
