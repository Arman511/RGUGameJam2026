from __future__ import annotations

import pygame

from elemental_game.types.player import PlayerType

from .common import (
    API_BASE_URL_INPUT,
    CANCEL_CONFIRM_BUTTON,
    CLEAR_CONFIRM_BUTTON,
    CLEAR_LEADERBOARD_BUTTON,
    ERROR_TEXT,
    HINTS_TOGGLE_BUTTON,
    MUSIC_SLIDER,
    MUTED_TEXT,
    PLAYER_NEXT_BUTTON,
    PLAYER_PREVIOUS_BUTTON,
    PLAYER_SELECT_PANEL,
    SAVE_SETTINGS_BUTTON,
    SETTINGS_PANEL,
    SFX_SLIDER,
    TURRET_SENSITIVITY_SLIDER,
)
from .context import MenuContext


class SettingsMenuMixin(MenuContext):
    def _handle_settings_event(self, event: pygame.event.Event) -> None:
        api_input = self.api_base_url_input
        api_input.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if api_input.focused:
                api_input.focused = False
                return
            self._close_settings()
            return
        if event.type == pygame.KEYDOWN and api_input.focused:
            return
        if event.type == pygame.TEXTINPUT and api_input.focused:
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
            if self.layout.rect(API_BASE_URL_INPUT).collidepoint(event.pos):
                return
            if self.layout.rect(MUSIC_SLIDER.inflate(0, 18)).collidepoint(event.pos):
                self.dragging_slider = "music_volume"
                self._update_slider(event.pos[0])
            elif self.layout.rect(SFX_SLIDER.inflate(0, 18)).collidepoint(event.pos):
                self.dragging_slider = "sfx_volume"
                self._update_slider(event.pos[0])
            elif self.layout.rect(
                TURRET_SENSITIVITY_SLIDER.inflate(0, 18)
            ).collidepoint(event.pos):
                self.dragging_slider = "manual_turret_sensitivity"
                self._update_slider(event.pos[0])
            elif self.layout.rect(SAVE_SETTINGS_BUTTON).collidepoint(event.pos):
                self._close_settings()
        elif event.type == pygame.MOUSEMOTION and self.dragging_slider:
            self._update_slider(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and self.dragging_slider:
            self._update_slider(event.pos[0])
            self.dragging_slider = None

    def _close_settings(self) -> None:
        try:
            self.store.save_api_base_url(self.api_base_url_input.value)
        except ValueError as error:
            self.notice_message = str(error)
            return
        server_changed = self.api_base_url != self.store.api_base_url()
        self.api_base_url = self.store.api_base_url()
        self.api_base_url_input.value = self.api_base_url
        self.auth.client.base_url = self.api_base_url
        if server_changed:
            self.credentials.clear_token()
            self.username = None
            self.login_username.value = ""
            self.login_password.value = ""
            self.error_message = "API server changed. Sign in again on the new server."
        self._save_sound_preferences()
        self.store.save_manual_turret_sensitivity(self.manual_turret_sensitivity)
        self.state = "menu"

    def _change_player_type(self, step: int) -> None:
        number = (int(self.player_type) - 1 + step) % len(PlayerType) + 1
        self.player_type = PlayerType(number)

    def _update_slider(self, mouse_x: int) -> None:
        key = self.dragging_slider
        if key is None:
            return
        slider = {
            "music_volume": MUSIC_SLIDER,
            "sfx_volume": SFX_SLIDER,
            "manual_turret_sensitivity": TURRET_SENSITIVITY_SLIDER,
        }[key]
        slider = self.layout.rect(slider)
        value = max(0.0, min(1.0, (mouse_x - slider.x) / slider.width))
        if key == "manual_turret_sensitivity":
            self.manual_turret_sensitivity = value
        else:
            self.preferences[key] = value
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
        self._draw_panel(SETTINGS_PANEL)
        self._draw_panel(pygame.Rect(115, 62, 570, 45))
        self._draw_panel(PLAYER_SELECT_PANEL)
        self._draw_title("Settings", 85)
        self._draw_text("Audio", 145, 122, center=False)
        self._draw_text("Music volume", 150, 143, center=False)
        self._draw_slider(MUSIC_SLIDER, self.preferences["music_volume"])

        self._draw_text("SFX volume", 150, 193, center=False)
        self._draw_slider(SFX_SLIDER, self.preferences["sfx_volume"])
        self._draw_text("Gameplay hints", 150, 253, center=False)
        self._draw_button("On" if self.hints_enabled else "Off", HINTS_TOGGLE_BUTTON)

        self._draw_text("Manual turret movement sensitivity", 150, 282, center=False)
        self._draw_slider(TURRET_SENSITIVITY_SLIDER, self.manual_turret_sensitivity)
        speed = round(30 + self.manual_turret_sensitivity * 240)
        self._draw_text(f"Turn speed: {speed} deg/s", 400, 327)
        self._draw_text("Backend API server URL", 145, 347, center=False)
        self._draw_api_url_input()
        if self.notice_message:
            self._draw_text(self.notice_message, 400, 408, color=ERROR_TEXT)
        else:
            self._draw_text(
                "Use the server root URL; press Backspace to edit.",
                400,
                408,
                color=MUTED_TEXT,
            )

        self._draw_text("Player", 145, 438, center=False)
        self._draw_button("<", PLAYER_PREVIOUS_BUTTON)
        preview = self.player_previews[self.player_type]
        self.screen.blit(
            preview,
            preview.get_rect(
                center=self.layout.point((389, PLAYER_SELECT_PANEL.centery))
            ),
        )
        self._draw_text(self.player_type.name.title(), 555, PLAYER_SELECT_PANEL.centery)
        self._draw_button(">", PLAYER_NEXT_BUTTON)
        self._draw_button("Clear local leaderboard", CLEAR_LEADERBOARD_BUTTON)
        self._draw_button("Save", SAVE_SETTINGS_BUTTON)

    def _draw_api_url_input(self) -> None:
        rect = self.layout.rect(API_BASE_URL_INPUT)
        pygame.draw.rect(self.screen, (50, 50, 50), rect)
        border = (170, 210, 170) if self.api_base_url_input.focused else (130, 130, 130)
        pygame.draw.rect(
            self.screen,
            border,
            rect,
            max(1, round(2 * self.layout.scale)),
        )
        text = self.api_base_url_input.value or "https://example.com"
        color = (245, 245, 245) if self.api_base_url_input.value else MUTED_TEXT
        available_width = rect.width - round(20 * self.layout.scale)
        rendered = self.font.render(text, True, color)
        while text and rendered.get_width() > available_width:
            text = text[1:]
            rendered = self.font.render(text, True, color)
        self.screen.blit(
            rendered,
            (
                rect.x + round(10 * self.layout.scale),
                rect.y + (rect.height - rendered.get_height()) // 2,
            ),
        )

    def _draw_clear_confirmation(self) -> None:
        self._draw_panel(pygame.Rect(175, 175, 450, 255))
        self._draw_title("Clear leaderboard?", 210)
        self._draw_text("This permanently removes all local runs.", 400, 275)
        self._draw_button("Clear", CLEAR_CONFIRM_BUTTON)
        self._draw_button("Cancel", CANCEL_CONFIRM_BUTTON)
