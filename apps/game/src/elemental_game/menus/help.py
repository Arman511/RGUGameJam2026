from __future__ import annotations

import math

import pygame

from .common import HELP_BACK_BUTTON
from .context import MenuContext


class HelpMenuMixin(MenuContext):
    def _handle_help_event(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_ESCAPE
            or event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.layout.rect(HELP_BACK_BUTTON).collidepoint(event.pos)
        ):
            self.state = "menu"

    def _draw_help(self) -> None:
        self._draw_panel(pygame.Rect(100, 45, 600, 510))
        self._draw_title("Controls", 75)
        help_items = (
            "Move: WASD / arrow keys",
            "F: interact, plant, or build",
            "G: harvest crops",
            "Shop: M; tabs: TAB / SHIFT+TAB",
            "Shop seed tier: A/D or arrow keys",
            "Turret range display: O",
            "House turret: F at house; A/D aim; SPACE fire",
            "Toggle inventory HUD: H",
            "2-player: V attacks; Q/E selects crop; 1-4 sends",
            "ESC: cancel or go back",
        )
        content_width = self.layout.rect(pygame.Rect(140, 0, 520, 1)).width
        help_lines = []
        for item in help_items:
            line = ""
            for word in item.split():
                candidate = f"{line} {word}".strip()
                if line and self.font.size(candidate)[0] > content_width:
                    help_lines.append(line)
                    line = word
                else:
                    line = candidate
            if line:
                help_lines.append(line)
        line_spacing = max(30, math.ceil(self.font.get_linesize() / self.layout.scale))
        for index, line in enumerate(help_lines):
            self._draw_text(line, 400, 120 + index * line_spacing)
        self._draw_button("Back", HELP_BACK_BUTTON)
