from __future__ import annotations

import pygame

from elemental_game.audio import play_sfx


class MultiplayerGameOverDialog:
    def __init__(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        result: str,
    ) -> None:
        self.surface = surface
        self.font = font
        self.result = result
        self.done = False
        self.keyboard_dismissal_at = pygame.time.get_ticks() + 500
        if result == "defeat":
            play_sfx("explosion")

    def _panel_rect(self) -> pygame.Rect:
        panel = pygame.Rect(0, 0, min(560, self.surface.get_width() - 40), 230)
        panel.center = self.surface.get_rect().center
        return panel

    def _menu_button_rect(self) -> pygame.Rect:
        panel = self._panel_rect()
        button = pygame.Rect(0, 0, min(300, panel.width - 40), 48)
        button.center = (panel.centerx, panel.y + 184)
        return button

    def handle_event(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_ESCAPE)
            and pygame.time.get_ticks() >= self.keyboard_dismissal_at
        ) or (
            event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
            and event.button == 1
            and self._menu_button_rect().collidepoint(event.pos)
        ):
            self.done = True

    def draw(self) -> None:
        overlay = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.surface.blit(overlay, (0, 0))

        panel = self._panel_rect()
        pygame.draw.rect(self.surface, (44, 48, 57), panel, border_radius=12)
        pygame.draw.rect(self.surface, (225, 225, 225), panel, 2, border_radius=12)
        title = "Congratulations, you won!" if self.result == "victory" else "Game over"
        title_surface = self.font.render(title, True, (255, 230, 120))
        self.surface.blit(
            title_surface, title_surface.get_rect(center=(panel.centerx, panel.y + 70))
        )
        message = "The match has ended."
        message_surface = self.font.render(message, True, (240, 240, 240))
        self.surface.blit(
            message_surface,
            message_surface.get_rect(center=(panel.centerx, panel.y + 118)),
        )
        button = self._menu_button_rect()
        pygame.draw.rect(self.surface, (65, 85, 65), button, border_radius=6)
        pygame.draw.rect(self.surface, (190, 210, 190), button, 2, border_radius=6)
        prompt = self.font.render("Return to main menu", True, (255, 255, 255))
        self.surface.blit(
            prompt,
            prompt.get_rect(center=button.center),
        )
