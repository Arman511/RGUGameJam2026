from __future__ import annotations

import pygame

from elemental_game.api_client.http import APIError

from .common import (
    CREDITS_BUTTON,
    CREDITS_CLOSE_BUTTON,
    CREDITS_MODAL,
    ERROR_TEXT,
    EXIT_BUTTON,
    HELP_BUTTON,
    LEADERBOARD_BUTTON,
    MULTIPLAYER_BACK_BUTTON,
    ONLINE_PLAYER_BUTTON,
    PLAY_BUTTON,
    SETTINGS_BUTTON,
    SIGN_IN_BUTTON,
    SINGLE_PLAYER_BUTTON,
)
from .context import MenuContext


class MainMenuMixin(MenuContext):
    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.username is None:
                self.state = "login"
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.layout.rect(CREDITS_BUTTON).collidepoint(event.pos):
            self.state = "credits"
        elif self.layout.rect(PLAY_BUTTON).collidepoint(event.pos):
            self.error_message = ""
            self.state = "mode_select"
        elif self.layout.rect(LEADERBOARD_BUTTON).collidepoint(event.pos):
            self.leaderboard_rows = self.store.top_scores(limit=None)
            self.leaderboard_filter.value = ""
            self.leaderboard_filter.focused = False
            self.leaderboard_scroll = 0
            self.revealed_usernames.clear()
            self.state = "leaderboard"
        elif self.layout.rect(SETTINGS_BUTTON).collidepoint(event.pos):
            self.notice_message = ""
            self.state = "settings"
        elif self.layout.rect(HELP_BUTTON).collidepoint(event.pos):
            self.state = "help"
        elif self.layout.rect(SIGN_IN_BUTTON).collidepoint(event.pos):
            if self.username is None:
                self.error_message = ""
                self.state = "login"
                return
            try:
                self.auth.logout()
            except APIError as error:
                self.error_message = f"Sign out failed: {error}"
                return
            self.username = None
            self.error_message = ""
        elif self.layout.rect(EXIT_BUTTON).collidepoint(event.pos):
            self.start_game = False
            self.running = False

    def _handle_credits_event(self, event: pygame.event.Event) -> None:
        if (
            (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)
            or (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and (
                    self.layout.rect(CREDITS_CLOSE_BUTTON).collidepoint(event.pos)
                    or not self.layout.rect(CREDITS_MODAL).collidepoint(event.pos)
                )
            )
        ):
            self.state = "menu"

    def _handle_mode_select_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "menu"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(SINGLE_PLAYER_BUTTON).collidepoint(event.pos):
                self.game_mode = "single"
                self.state = "menu"
                self.start_game = True
                self.running = False
            elif self.layout.rect(ONLINE_PLAYER_BUTTON).collidepoint(event.pos):
                self.state = "online_select"
            elif self.layout.rect(MULTIPLAYER_BACK_BUTTON).collidepoint(event.pos):
                self.state = "menu"

    def _draw_menu(self) -> None:
        self._draw_panel(pygame.Rect(120, 65, 560, 460))
        self._draw_title("Elemental Keep", 105)
        identity = (
            f"Signed in as {self.username}" if self.username else "Playing as Guest"
        )
        self._draw_text(identity, 400, 150)
        self._draw_button("Play game", PLAY_BUTTON)
        self._draw_button("Leaderboard", LEADERBOARD_BUTTON)
        self._draw_button("Settings", SETTINGS_BUTTON)
        self._draw_button("Help / Controls", HELP_BUTTON)
        self._draw_button(
            "Sign out" if self.username else "Sign in",
            SIGN_IN_BUTTON,
        )
        self._draw_button("Exit", EXIT_BUTTON)
        self._draw_button("Credits", CREDITS_BUTTON)
        if self.error_message:
            self._draw_text(self.error_message, 400, 580, color=ERROR_TEXT)

    def _draw_credits(self) -> None:
        self._draw_menu()
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))
        self._draw_panel(CREDITS_MODAL)
        self._draw_title("Credits", 112)
        credits = (
            "Team: Arman, Hannah and Holly",
            "Music from Pixabay:",
            "benvibrant, desifreemusic,",
            "moonpetalmedia, starostin,",
            "andriig, jonasblakewood, mondamusic",
            "Sound effects from Mixkit.",
            "Sprites by the team, except attack.png,",
            "radar.png and hud.png use emoji images from",
            "Google and Apple.",
        )
        for index, line in enumerate(credits):
            self._draw_text(line, 400, 155 + index * 31)
        self._draw_button("Close", CREDITS_CLOSE_BUTTON)

    def _draw_mode_select(self) -> None:
        self._draw_panel(pygame.Rect(120, 150, 560, 300))
        self._draw_title("Choose a game", 190)
        self._draw_button("Single player", SINGLE_PLAYER_BUTTON)
        self._draw_button("2-player VS", ONLINE_PLAYER_BUTTON)
        self._draw_button("Back", MULTIPLAYER_BACK_BUTTON)
