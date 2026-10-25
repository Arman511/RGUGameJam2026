from __future__ import annotations

import pygame


class MultiplayerGameOverDialog:
    DISPLAY_DURATION = 5.0

    def __init__(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        result: str,
    ) -> None:
        self.surface = surface
        self.font = font
        self.result = result
        self.remaining = self.DISPLAY_DURATION
        self.done = False

    def update(self, seconds: float) -> None:
        self.remaining = max(0.0, self.remaining - seconds)
        if self.remaining == 0:
            self.done = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN,
            pygame.K_SPACE,
            pygame.K_ESCAPE,
        ):
            self.done = True

    def draw(self) -> None:
        overlay = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.surface.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, min(560, self.surface.get_width() - 40), 230)
        panel.center = self.surface.get_rect().center
        pygame.draw.rect(self.surface, (44, 48, 57), panel, border_radius=12)
        pygame.draw.rect(self.surface, (225, 225, 225), panel, 2, border_radius=12)
        title = "Congratulations, you won!" if self.result == "victory" else "Game over"
        title_surface = self.font.render(title, True, (255, 230, 120))
        self.surface.blit(
            title_surface, title_surface.get_rect(center=(panel.centerx, panel.y + 70))
        )
        message = "Returning to the main menu..."
        message_surface = self.font.render(message, True, (240, 240, 240))
        self.surface.blit(
            message_surface,
            message_surface.get_rect(center=(panel.centerx, panel.y + 125)),
        )
        prompt = self.font.render("Press ENTER to continue", True, (190, 200, 210))
        self.surface.blit(
            prompt,
            prompt.get_rect(center=(panel.centerx, panel.y + 175)),
        )
