from __future__ import annotations

import pygame

from elemental_game.types.player import PlayerType

from .common import (
    CANCEL_CONFIRM_BUTTON,
    CLEAR_CONFIRM_BUTTON,
    CLEAR_LEADERBOARD_BUTTON,
    HINTS_TOGGLE_BUTTON,
    MENU_FRAME_PANEL,
    MUSIC_SLIDER,
    MUTED_TEXT,
    PLAYER_NEXT_BUTTON,
    PLAYER_PREVIOUS_BUTTON,
    PLAYER_SELECT_PANEL,
    SAVE_SETTINGS_BUTTON,
    SFX_SLIDER,
)
from .context import MenuContext


class SettingsMenuMixin(MenuContext):
    def _handle_settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._close_settings()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(CLEAR_LEADERBOARD_BUTTON).collidepoint(event.pos):
                self.state = "confirm_clear"
                return
            if self.layout.rect(PLAYER_PREVIOUS_BUTTON).collidepoint(event.pos):
                self._change_player_type(-1)
                return
            if self.layout.rect(PLAYER_NEXT_BUTTON).collidepoint(event.pos):
                self._change_player_type(1)
                return
            if self.layout.rect(HINTS_TOGGLE_BUTTON).collidepoint(event.pos):
                self.hints_enabled = not self.hints_enabled
                return
            if self.layout.rect(MUSIC_SLIDER.inflate(0, 18)).collidepoint(event.pos):
                self.dragging_slider = "music_volume"
                self._update_slider(event.pos[0])
            elif self.layout.rect(SFX_SLIDER.inflate(0, 18)).collidepoint(event.pos):
                self.dragging_slider = "sfx_volume"
                self._update_slider(event.pos[0])
            elif self.layout.rect(SAVE_SETTINGS_BUTTON).collidepoint(event.pos):
                self._close_settings()
        elif event.type == pygame.MOUSEMOTION and self.dragging_slider:
            self._update_slider(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and self.dragging_slider:
            self._update_slider(event.pos[0])
            self.dragging_slider = None

    def _close_settings(self) -> None:
        self._save_sound_preferences()
        self.state = "menu"

    def _change_player_type(self, step: int) -> None:
        number = (int(self.player_type) - 1 + step) % len(PlayerType) + 1
        self.player_type = PlayerType(number)

    def _update_slider(self, mouse_x: int) -> None:
        key = self.dragging_slider
        if key is None:
            return
        slider = MUSIC_SLIDER if key == "music_volume" else SFX_SLIDER
        slider = self.layout.rect(slider)
        self.preferences[key] = max(0.0, min(1.0, (mouse_x - slider.x) / slider.width))
        self._apply_sound_preferences()

    def _handle_clear_confirmation_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "settings"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(CLEAR_CONFIRM_BUTTON).collidepoint(event.pos):
                self.store.clear_leaderboard()
                self.notice_message = "Local leaderboard cleared."
                self.state = "settings"
            elif self.layout.rect(CANCEL_CONFIRM_BUTTON).collidepoint(event.pos):
                self.state = "settings"

    def _draw_settings(self) -> None:
        self._draw_panel(MENU_FRAME_PANEL)
        self._draw_panel(pygame.Rect(115, 70, 570, 45))
        self._draw_panel(pygame.Rect(115, 115, 570, 195))
        self._draw_panel(PLAYER_SELECT_PANEL)
        self._draw_title("Settings", 95)
        self._draw_text("Audio", 145, 132, center=False)
        self._draw_text("Music volume", 150, 160, center=False)
        self._draw_slider(MUSIC_SLIDER, self.preferences["music_volume"])

        self._draw_text("SFX volume", 150, 225, center=False)
        self._draw_slider(SFX_SLIDER, self.preferences["sfx_volume"])
        self._draw_text("Gameplay hints", 150, 276, center=False)
        self._draw_button("On" if self.hints_enabled else "Off", HINTS_TOGGLE_BUTTON)

        self._draw_text("Player", 145, 337, center=False)
        self._draw_button("<", PLAYER_PREVIOUS_BUTTON)
        preview = self.player_previews[self.player_type]
        self.screen.blit(
            preview,
            preview.get_rect(
                center=self.layout.point((389, PLAYER_SELECT_PANEL.centery))
            ),
        )
        self._draw_text(
            self.player_type.name.title(), 555, PLAYER_SELECT_PANEL.centery
        )
        self._draw_button(">", PLAYER_NEXT_BUTTON)
        self._draw_button("Clear local leaderboard", CLEAR_LEADERBOARD_BUTTON)
        if self.notice_message:
            self._draw_text(self.notice_message, 400, 465, color=MUTED_TEXT)
        self._draw_button("Save", SAVE_SETTINGS_BUTTON)

    def _draw_clear_confirmation(self) -> None:
        self._draw_panel(pygame.Rect(175, 175, 450, 255))
        self._draw_title("Clear leaderboard?", 210)
        self._draw_text("This permanently removes all local runs.", 400, 275)
        self._draw_button("Clear", CLEAR_CONFIRM_BUTTON)
        self._draw_button("Cancel", CANCEL_CONFIRM_BUTTON)
