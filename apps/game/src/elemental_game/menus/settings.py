from __future__ import annotations

import pygame

from elemental_game.types.player import PlayerType

from .common import (
    API_BASE_URL_INPUT,
    CANCEL_CONFIRM_BUTTON,
    CLEAR_CONFIRM_BUTTON,
    CLEAR_LEADERBOARD_BUTTON,
    MUTED_TEXT,
    SAVE_SETTINGS_BUTTON,
    SETTINGS_PANEL,
)
from .context import MenuContext


class SettingsMenuMixin(MenuContext):
    def _save_modal_setting(self) -> None:
        modal_key = self.settings_modal
        if modal_key is None:
            return

        if modal_key == "api_base_url":
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
                self.error_message = (
                    "API server changed. Sign in again on the new server."
                )
            return

        if modal_key in {"music_volume", "sfx_volume", "hints_enabled"}:
            self._save_sound_preferences()
        if modal_key == "manual_turret_sensitivity":
            self._save_sound_preferences()
            self.store.save_manual_turret_sensitivity(self.manual_turret_sensitivity)
        if modal_key == "player_type":
            self.store.save_player_image_number(int(self.player_type))

    def _close_setting_modal(self) -> None:
        self._save_modal_setting()
        self.api_base_url_input.rect = self.layout.rect(API_BASE_URL_INPUT)
        self.api_base_url_input.focused = False
        self.settings_modal = None

    def _handle_settings_event(self, event: pygame.event.Event) -> None:
        if getattr(self, "settings_modal", None):
            self._handle_settings_modal_event(event)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._close_settings()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            row_buttons = (
                ("music_volume", pygame.Rect(520, 137, 110, 34)),
                ("sfx_volume", pygame.Rect(520, 187, 110, 34)),
                ("hints_enabled", pygame.Rect(520, 237, 110, 34)),
                ("manual_turret_sensitivity", pygame.Rect(520, 287, 110, 34)),
                ("api_base_url", pygame.Rect(520, 337, 110, 34)),
                ("player_type", pygame.Rect(520, 420, 110, 34)),
            )
            for key, rect in row_buttons:
                if self.layout.rect(rect).collidepoint(event.pos):
                    self.settings_modal = key
                    return
            if self.layout.rect(CLEAR_LEADERBOARD_BUTTON).collidepoint(event.pos):
                self.state = "confirm_clear"
                return
            if self.layout.rect(SAVE_SETTINGS_BUTTON).collidepoint(event.pos):
                self._close_settings()

    def _handle_settings_modal_event(self, event: pygame.event.Event) -> None:
        modal_key = self.settings_modal
        if modal_key is None:
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._close_setting_modal()
            return

        if modal_key == "api_base_url":
            self.api_base_url_input.handle_event(event)
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.layout.rect(pygame.Rect(330, 355, 140, 44)).collidepoint(
                    event.pos
                )
            ):
                self._close_setting_modal()
                return
        elif modal_key == "music_volume":
            self._update_modal_slider(
                event, "music_volume", pygame.Rect(180, 245, 440, 14)
            )
        elif modal_key == "sfx_volume":
            self._update_modal_slider(
                event, "sfx_volume", pygame.Rect(180, 245, 440, 14)
            )
        elif modal_key == "manual_turret_sensitivity":
            self._update_modal_slider(
                event,
                "manual_turret_sensitivity",
                pygame.Rect(180, 245, 440, 14),
            )
        elif modal_key == "hints_enabled":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.layout.rect(pygame.Rect(290, 245, 110, 40)).collidepoint(
                    event.pos
                ):
                    self.hints_enabled = True
                elif self.layout.rect(pygame.Rect(405, 245, 110, 40)).collidepoint(
                    event.pos
                ):
                    self.hints_enabled = False
                if self.layout.rect(pygame.Rect(330, 355, 140, 44)).collidepoint(
                    event.pos
                ):
                    self._close_setting_modal()
        elif modal_key == "player_type":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.layout.rect(pygame.Rect(255, 240, 48, 42)).collidepoint(
                    event.pos
                ):
                    self._change_player_type(-1)
                elif self.layout.rect(pygame.Rect(495, 240, 48, 42)).collidepoint(
                    event.pos
                ):
                    self._change_player_type(1)
                elif self.layout.rect(pygame.Rect(330, 355, 140, 44)).collidepoint(
                    event.pos
                ):
                    self._close_setting_modal()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            close_rect = self.layout.rect(pygame.Rect(330, 355, 140, 44))
            if self.settings_modal not in {"api_base_url"} and close_rect.collidepoint(
                event.pos
            ):
                self._close_setting_modal()

    def _update_modal_slider(
        self, event: pygame.event.Event, key: str, rect: pygame.Rect
    ) -> None:
        close_rect = self.layout.rect(pygame.Rect(330, 355, 140, 44))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_rect.collidepoint(event.pos):
                self._close_setting_modal()
                return
            self._set_slider_value(key, event.pos[0], rect)
            self.dragging_slider = key
        elif event.type == pygame.MOUSEMOTION and self.dragging_slider == key:
            self._set_slider_value(key, event.pos[0], rect)
        elif event.type == pygame.MOUSEBUTTONUP and self.dragging_slider == key:
            self._set_slider_value(key, event.pos[0], rect)
            self.dragging_slider = None

    def _set_slider_value(self, key: str, mouse_x: int, rect: pygame.Rect) -> None:
        rect = self.layout.rect(rect)
        value = max(0.0, min(1.0, (mouse_x - rect.x) / rect.width))
        if key == "manual_turret_sensitivity":
            self.manual_turret_sensitivity = value
        else:
            self.preferences[key] = value
            self._apply_sound_preferences()

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
        self._close_setting_modal()
        self.state = "menu"

    def _change_player_type(self, step: int) -> None:
        number = (int(self.player_type) - 1 + step) % len(PlayerType) + 1
        self.player_type = PlayerType(number)

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
        self._draw_title("Settings", 85)
        if self.settings_modal:
            self._draw_settings_modal()
            return

        row_data = (
            ("Music volume", 140, "music_volume"),
            ("SFX volume", 190, "sfx_volume"),
            ("Gameplay hints", 240, "hints_enabled"),
            ("Turret sensitivity", 290, "manual_turret_sensitivity"),
            ("API server", 340, "api_base_url"),
            ("Player", 420, "player_type"),
        )
        for label, y, key in row_data:
            self._draw_text(label, 170, y, center=False)
            self._draw_button("Change", pygame.Rect(520, y - 14, 110, 34))

        self._draw_button("Clear local leaderboard", CLEAR_LEADERBOARD_BUTTON)
        self._draw_button("Save", SAVE_SETTINGS_BUTTON)

    def _draw_settings_modal(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        self._draw_panel(pygame.Rect(150, 130, 500, 300))

        modal_key = self.settings_modal
        if modal_key == "api_base_url":
            self.api_base_url_input.rect = self.layout.rect(
                pygame.Rect(180, 245, 440, 42)
            )
            self._draw_title("API server", 180)
            rect = self.api_base_url_input.rect
            pygame.draw.rect(self.screen, (50, 50, 50), rect)
            border = (
                (170, 210, 170) if self.api_base_url_input.focused else (130, 130, 130)
            )
            pygame.draw.rect(
                self.screen, border, rect, max(1, round(2 * self.layout.scale))
            )
            text = self.api_base_url_input.value or "https://example.com"
            color = (245, 245, 245) if self.api_base_url_input.value else MUTED_TEXT
            rendered = self.font.render(text, True, color)
            available_width = rect.width - round(20 * self.layout.scale)
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
        elif modal_key == "music_volume":
            self._draw_title("Music volume", 180)
            self._draw_slider_with_label("music_volume", 190, 245, 440)
        elif modal_key == "sfx_volume":
            self._draw_title("SFX volume", 180)
            self._draw_slider_with_label("sfx_volume", 190, 245, 440)
        elif modal_key == "hints_enabled":
            self._draw_title("Gameplay hints", 180)
            current = "On" if self.hints_enabled else "Off"
            self._draw_text(f"Current: {current}", 400, 220)
            self._draw_button("On", pygame.Rect(290, 245, 110, 40))
            self._draw_button("Off", pygame.Rect(405, 245, 110, 40))
        elif modal_key == "manual_turret_sensitivity":
            self._draw_title("Turret sensitivity", 180)
            self._draw_slider_with_label(
                "manual_turret_sensitivity",
                190,
                245,
                440,
            )
        elif modal_key == "player_type":
            self._draw_title("Player", 180)
            self._draw_button("<", pygame.Rect(255, 240, 48, 42))
            preview = self.player_previews[self.player_type]
            self.screen.blit(
                preview,
                preview.get_rect(center=self.layout.point((400, 260))),
            )
            self._draw_text(self.player_type.name.title(), 518, 260)
            self._draw_button(">", pygame.Rect(495, 240, 48, 42))

        self._draw_button("Close", pygame.Rect(330, 355, 140, 44))

    def _draw_slider_with_label(
        self, key: str, label_x: int, slider_y: int, slider_width: int
    ) -> None:
        value = (
            self.manual_turret_sensitivity
            if key == "manual_turret_sensitivity"
            else self.preferences[key]
        )
        label = (
            "Turret sensitivity"
            if key == "manual_turret_sensitivity"
            else key.replace("_", " ").title()
        )
        self._draw_text(label, label_x, slider_y - 24, center=False)
        self._draw_text(f"{round(value * 100)}%", 525, slider_y - 24, center=False)
        slider_rect = self.layout.rect(pygame.Rect(180, slider_y, slider_width, 14))
        pygame.draw.rect(self.screen, (85, 85, 85), slider_rect, border_radius=8)
        filled = slider_rect.copy()
        filled.width = round(slider_rect.width * value)
        pygame.draw.rect(self.screen, (110, 175, 110), filled, border_radius=8)
        pygame.draw.circle(
            self.screen,
            (245, 245, 245),
            (slider_rect.x + round(slider_rect.width * value), slider_rect.centery),
            max(1, round(11 * self.layout.scale)),
        )

    def _draw_clear_confirmation(self) -> None:
        self._draw_panel(pygame.Rect(175, 175, 450, 255))
        self._draw_title("Clear leaderboard?", 210)
        self._draw_text("This permanently removes all local runs.", 400, 275)
        self._draw_button("Clear", CLEAR_CONFIRM_BUTTON)
        self._draw_button("Cancel", CANCEL_CONFIRM_BUTTON)
