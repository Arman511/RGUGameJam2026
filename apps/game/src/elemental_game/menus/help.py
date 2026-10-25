from __future__ import annotations

import math

import pygame

from elemental_game.config import FONT_PATH

from .common import HELP_BACK_BUTTON, MENU_FRAME_PANEL
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
        self._draw_panel(MENU_FRAME_PANEL)
        self._draw_title("Controls", 95)
        help_font = pygame.font.Font(FONT_PATH, max(1, round(20 * self.layout.scale)))
        help_items = (
            "Move: WASD / arrow keys",
            "F: interact, plant, or build",
            "Planting: W/S, UP/DOWN, or click a seed",
            "G: harvest crops",
            "Shop: M; tabs: TAB / SHIFT+TAB",
            "Shop selection: W/S, UP/DOWN, or mouse wheel",
            "Buy seeds: Q/E tier; A/D or LEFT/RIGHT quantity (1/10/100)",
            "Turret menu: W/S, arrows, or wheel select; SPACE/ENTER confirm",
            "Turret range display: O",
            "House turret: F at house; A/D aim; SPACE fire; red laser shows aim",
            "Toggle inventory HUD: H",
            "2-player: V attacks; Q/E selects crop; 1-4 sends",
            "ESC: cancel or go back",
        )
        content_width = self.layout.rect(pygame.Rect(60, 0, 680, 1)).width
        help_lines = []
        for item in help_items:
            line = ""
            for word in item.split():
                candidate = f"{line} {word}".strip()
                if line and help_font.size(candidate)[0] > content_width:
                    help_lines.append(line)
                    line = word
                else:
                    line = candidate
            if line:
                help_lines.append(line)
        line_spacing = max(22, math.ceil(help_font.get_linesize() / self.layout.scale))
        for index, line in enumerate(help_lines):
            self._draw_text(
                line,
                400,
                145 + index * line_spacing,
                text_font=help_font,
            )
        self._draw_button("Back", HELP_BACK_BUTTON)
