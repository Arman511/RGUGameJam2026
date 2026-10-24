"""
Login, main menu, leaderboard and settings screens.

Usage (from main.py):

    menus = MenuSystem(screen)
    running = menus.run()   # True = player pressed Play, False = window closed
"""

from __future__ import annotations

import os
import platform
import subprocess
import webbrowser
from typing import Any

from elemental_game.types.player import PlayerType
import pygame

from elemental_game.api_client import APIClient, AuthClient, CredentialStore
from elemental_game.api_client.http import APIError, AuthError
from elemental_game.audio import (
    initialise_audio,
    play_background_music,
)
from elemental_game.config import IMAGES_DIR
from elemental_game.database import LocalLeaderboardStore

BUTTON = (65, 85, 65)
BUTTON_HOVER = (85, 110, 85)
TEXT = (245, 245, 245)
MUTED_TEXT = (180, 180, 180)
ERROR_TEXT = (255, 130, 130)
MUSIC_SLIDER = pygame.Rect(175, 185, 450, 14)
SFX_SLIDER = pygame.Rect(175, 250, 450, 14)
PLAYER_PREVIOUS_BUTTON = pygame.Rect(285, 355, 48, 42)
PLAYER_NEXT_BUTTON = pygame.Rect(445, 355, 48, 42)
CLEAR_LEADERBOARD_BUTTON = pygame.Rect(250, 465, 300, 44)
SAVE_SETTINGS_BUTTON = pygame.Rect(330, 540, 140, 44)
LOGIN_BUTTON = pygame.Rect(205, 340, 120, 48)
REGISTER_BUTTON = pygame.Rect(340, 340, 120, 48)
GUEST_BUTTON = pygame.Rect(475, 340, 120, 48)
PLAY_BUTTON = pygame.Rect(250, 190, 300, 54)
LEADERBOARD_BUTTON = pygame.Rect(250, 270, 300, 54)
SETTINGS_BUTTON = pygame.Rect(250, 350, 300, 54)
SIGN_IN_BUTTON = pygame.Rect(250, 430, 300, 54)
EXIT_BUTTON = pygame.Rect(250, 510, 300, 54)
LEADERBOARD_BACK_BUTTON = pygame.Rect(330, 520, 140, 44)
CLEAR_CONFIRM_BUTTON = pygame.Rect(250, 340, 140, 48)
CANCEL_CONFIRM_BUTTON = pygame.Rect(410, 340, 140, 48)
LEADERBOARD_FILTER_RECT = pygame.Rect(265, 105, 330, 42)
LOGIN_USERNAME_RECT = pygame.Rect(250, 205, 300, 44)
LOGIN_PASSWORD_RECT = pygame.Rect(250, 265, 300, 44)
MENU_DESIGN_WIDTH = 800
MENU_DESIGN_HEIGHT = 600
REGISTER_URL = "https://elemental-keep.armandev.co.uk/register"


class MenuLayout:
    def __init__(self, width: int, height: int) -> None:
        self.scale = min(width / MENU_DESIGN_WIDTH, height / MENU_DESIGN_HEIGHT)
        self.offset = (
            round((width - MENU_DESIGN_WIDTH * self.scale) / 2),
            round((height - MENU_DESIGN_HEIGHT * self.scale) / 2),
        )

    def point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (
            round(point[0] * self.scale) + self.offset[0],
            round(point[1] * self.scale) + self.offset[1],
        )

    def rect(self, rect: pygame.Rect) -> pygame.Rect:
        x, y = self.point(rect.topleft)
        right, bottom = self.point(rect.bottomright)
        return pygame.Rect(x, y, right - x, bottom - y)


def _open_registration_page() -> bool:
    is_wsl = (
        bool(os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"))
        or "microsoft" in platform.release().casefold()
    )
    if not is_wsl:
        return webbrowser.open(REGISTER_URL)

    try:
        subprocess.run(
            ["cmd.exe", "/c", "start", "", REGISTER_URL],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


class InputField:
    def __init__(
        self,
        rect: pygame.Rect,
        *,
        placeholder: str,
        max_length: int,
        secret: bool = False,
        scale: float = 1.0,
    ) -> None:
        self.rect = rect
        self.placeholder = placeholder
        self.max_length = max_length
        self.secret = secret
        self.scale = scale
        self.value = ""
        self.focused = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.unicode.isprintable() and len(self.value) < self.max_length:
                self.value += event.unicode

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, (50, 50, 50), self.rect)
        border = (170, 210, 170) if self.focused else (130, 130, 130)
        pygame.draw.rect(surface, border, self.rect, max(1, round(2 * self.scale)))
        value = "*" * len(self.value) if self.secret else self.value
        label = value or self.placeholder
        color = TEXT if value else MUTED_TEXT
        surface.blit(
            font.render(label, True, color),
            (
                self.rect.x + round(12 * self.scale),
                self.rect.y + round(10 * self.scale),
            ),
        )


class MenuSystem:
    layout = MenuLayout(MENU_DESIGN_WIDTH, MENU_DESIGN_HEIGHT)

    def __init__(self, screen: pygame.Surface) -> None:
        initialise_audio()
        self.screen = screen
        self.layout = MenuLayout(*screen.get_size())
        pygame.display.set_caption("Elemental Keep")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, max(1, round(28 * self.layout.scale)))
        self.title_font = pygame.font.SysFont(
            None, max(1, round(42 * self.layout.scale))
        )
        self.store = LocalLeaderboardStore()
        self.credentials = CredentialStore()
        self.auth = AuthClient(APIClient(), self.credentials)
        self.username: str | None = None
        self.state = "login"
        self.running = True
        self.start_game = False  # set when the player presses Play
        self.error_message = ""
        self.notice_message = ""
        self.leaderboard_rows: list[dict[str, Any]] = []
        self.leaderboard_scroll = 0
        self.leaderboard_filter = InputField(
            self.layout.rect(LEADERBOARD_FILTER_RECT),
            placeholder="Filter by username",
            max_length=32,
            scale=self.layout.scale,
        )
        self.login_username = InputField(
            self.layout.rect(LOGIN_USERNAME_RECT),
            placeholder="Username",
            max_length=32,
            scale=self.layout.scale,
        )
        self.login_password = InputField(
            self.layout.rect(LOGIN_PASSWORD_RECT),
            placeholder="Password",
            max_length=128,
            secret=True,
            scale=self.layout.scale,
        )
        self.preferences = self.store.sound_preferences()
        self.player_type = PlayerType(self.store.player_image_number())
        backgrounds_dir = os.path.join(IMAGES_DIR, "backgrounds")
        self.menu_background = pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(backgrounds_dir, "menu-background.png")
            ).convert(),
            self.screen.get_size(),
        )
        preview_size = max(1, round(64 * self.layout.scale))
        self.player_previews = {
            player_type: pygame.transform.smoothscale(
                pygame.image.load(player_type.full_image_path).convert_alpha(),
                (preview_size, preview_size),
            )
            for player_type in PlayerType
        }
        self._apply_sound_preferences()
        play_background_music(volume=self.preferences["music_volume"])
        self.dragging_slider: str | None = None
        self._check_existing_login()

    def _check_existing_login(self) -> None:
        if not self.credentials.load_token():
            return
        try:
            user = self.auth.current_user()
        except AuthError as error:
            self.credentials.clear_token()
            self.error_message = (
                f"Your session has expired. Please log in again. ({error})"
            )
            return
        except APIError as error:
            self.error_message = (
                f"Could not verify your login. Log in or skip. ({error})"
            )
            return

        self.username = user.username
        self.credentials.save_username(user.username)
        self.state = "menu"

    def _apply_sound_preferences(self) -> None:
        if pygame.mixer.get_init() is None:
            return
        pygame.mixer.music.set_volume(self.preferences["music_volume"])
        for channel_number in range(pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(channel_number).set_volume(
                self.preferences["sfx_volume"]
            )

    def _save_sound_preferences(self) -> None:
        self.store.save_sound_preferences(
            music_volume=self.preferences["music_volume"],
            sfx_volume=self.preferences["sfx_volume"],
        )
        self.store.save_player_image_number(int(self.player_type))
        self._apply_sound_preferences()

    def run(self) -> bool:
        """Show the menus. Returns True if the player pressed Play,
        False if they closed the window. Can be called again later
        (e.g. Esc in game) and resumes at the main menu."""
        self.running = True
        self.start_game = False
        while self.running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.state == "settings":
                        self._save_sound_preferences()
                    self.running = False
                else:
                    self._handle_event(event)

            self._draw()
            pygame.display.flip()
        return self.start_game

    def _handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "login":
            self._handle_login_event(event)
        elif self.state == "menu":
            self._handle_menu_event(event)
        elif self.state == "leaderboard":
            self._handle_leaderboard_event(event)
        elif self.state == "settings":
            self._handle_settings_event(event)
        elif self.state == "confirm_clear":
            self._handle_clear_confirmation_event(event)

    def _handle_login_event(self, event: pygame.event.Event) -> None:
        self.login_username.handle_event(event)
        self.login_password.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.login_username.focused = not self.login_username.focused
                self.login_password.focused = not self.login_username.focused
            elif event.key == pygame.K_RETURN:
                self._login()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(LOGIN_BUTTON).collidepoint(event.pos):
                self._login()
            elif self.layout.rect(REGISTER_BUTTON).collidepoint(event.pos):
                if not _open_registration_page():
                    self.error_message = "Could not open the registration page."
            elif self.layout.rect(GUEST_BUTTON).collidepoint(event.pos):
                self._continue_as_guest()

    def _login(self) -> None:
        username = self.login_username.value.strip()
        password = self.login_password.value
        if len(username) < 3 or len(password) < 8:
            self.error_message = (
                "Enter a username (at least 3 characters) and password (at least 8)."
            )
            return
        try:
            response = self.auth.login(username, password)
        except APIError as error:
            self.error_message = f"Login failed: {error}"
            return

        self.username = response.user.username
        self.error_message = ""
        self.state = "menu"

    def _continue_as_guest(self) -> None:
        self.username = None
        self.error_message = ""
        self.state = "menu"

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.username is None:
                self.state = "login"
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.layout.rect(PLAY_BUTTON).collidepoint(event.pos):
            self.start_game = True  # hand control back to main.py
            self.running = False
        elif self.layout.rect(LEADERBOARD_BUTTON).collidepoint(event.pos):
            self.leaderboard_rows = self.store.top_scores(limit=None)
            self.leaderboard_filter.value = ""
            self.leaderboard_filter.focused = False
            self.leaderboard_scroll = 0
            self.state = "leaderboard"
        elif self.layout.rect(SETTINGS_BUTTON).collidepoint(event.pos):
            self.notice_message = ""
            self.state = "settings"
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

    def _handle_leaderboard_event(self, event: pygame.event.Event) -> None:
        self.leaderboard_filter.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
            self.leaderboard_scroll = 0
        if event.type == pygame.MOUSEWHEEL:
            self.leaderboard_scroll = max(
                0,
                min(
                    self.leaderboard_scroll - event.y,
                    max(0, len(self._filtered_leaderboard()) - 12),
                ),
            )
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.layout.rect(LEADERBOARD_BACK_BUTTON).collidepoint(event.pos)
        ):
            self.state = "menu"

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

    def _draw(self) -> None:
        self.screen.blit(self.menu_background, (0, 0))
        if self.state == "login":
            self._draw_login()
        elif self.state == "menu":
            self._draw_menu()
        elif self.state == "leaderboard":
            self._draw_leaderboard()
        elif self.state == "settings":
            self._draw_settings()
        elif self.state == "confirm_clear":
            self._draw_clear_confirmation()

    def _draw_login(self) -> None:
        self._draw_panel(pygame.Rect(115, 75, 570, 115))
        self._draw_title("Elemental Keep", 110)
        self._draw_text("Log in to your account, or skip to play as a guest.", 400, 170)
        self.login_username.draw(self.screen, self.font)
        self.login_password.draw(self.screen, self.font)
        self._draw_button("Log in", LOGIN_BUTTON)
        self._draw_button("Register", REGISTER_BUTTON)
        self._draw_button("Skip", GUEST_BUTTON)
        if self.error_message:
            self._draw_text(
                self.error_message, 400, 425, color=ERROR_TEXT, center=False, x=120
            )

    def _draw_menu(self) -> None:
        self._draw_panel(pygame.Rect(180, 65, 440, 110))
        self._draw_title("Elemental Keep", 105)
        identity = (
            f"Signed in as {self.username}" if self.username else "Playing as Guest"
        )
        self._draw_text(identity, 400, 150)
        self._draw_button("Play game", PLAY_BUTTON)
        self._draw_button("Leaderboard", LEADERBOARD_BUTTON)
        self._draw_button("Settings", SETTINGS_BUTTON)
        self._draw_button(
            "Sign out" if self.username else "Sign in",
            SIGN_IN_BUTTON,
        )
        self._draw_button("Exit", EXIT_BUTTON)
        if self.error_message:
            self._draw_text(self.error_message, 400, 580, color=ERROR_TEXT)

    def _draw_leaderboard(self) -> None:
        self._draw_panel(pygame.Rect(125, 30, 550, 480))
        self._draw_title("Local Leaderboard", 50)
        self.leaderboard_filter.draw(self.screen, self.font)
        labels = ("Username", "Waves", "Time (s)", "Enemies")
        columns = (145, 355, 460, 565)
        for label, x in zip(labels, columns, strict=True):
            self._draw_text(label, x, 175, center=False)
        pygame.draw.line(
            self.screen,
            (130, 130, 130),
            self.layout.point((145, 198)),
            self.layout.point((655, 198)),
            max(1, round(self.layout.scale)),
        )

        rows = self._filtered_leaderboard()
        visible_rows = rows[self.leaderboard_scroll : self.leaderboard_scroll + 12]
        for index, row in enumerate(visible_rows):
            y = 220 + index * 24
            values = (
                str(row["username"]),
                str(row["final_wave"]),
                f"{float(row['survival_time']):.1f}",
                str(row["enemies_defeated"]),
            )
            for value, x in zip(values, columns, strict=True):
                self._draw_text(value, x, y, center=False)
        if not rows:
            self._draw_text("No local runs match this filter.", 400, 245)
        elif len(rows) > 12:
            self._draw_text("Scroll to see more runs", 400, 500, color=MUTED_TEXT)
        self._draw_button("Back", LEADERBOARD_BACK_BUTTON)

    def _filtered_leaderboard(self) -> list[dict[str, Any]]:
        query = self.leaderboard_filter.value.casefold().strip()
        return [
            row
            for row in self.leaderboard_rows
            if query in str(row["username"]).casefold()
        ]

    def _draw_settings(self) -> None:
        self._draw_panel(pygame.Rect(115, 30, 570, 65))
        self._draw_panel(pygame.Rect(115, 115, 570, 175))
        self._draw_panel(pygame.Rect(115, 305, 570, 140))
        self._draw_title("Settings", 65)
        self._draw_text("Audio", 145, 132, center=False)
        self._draw_text("Music volume", 150, 160, center=False)
        self._draw_slider(MUSIC_SLIDER, self.preferences["music_volume"])

        self._draw_text("SFX volume", 150, 225, center=False)
        self._draw_slider(SFX_SLIDER, self.preferences["sfx_volume"])

        self._draw_text("Player", 145, 322, center=False)
        self._draw_button("<", PLAYER_PREVIOUS_BUTTON)
        preview = self.player_previews[self.player_type]
        self.screen.blit(
            preview, preview.get_rect(center=self.layout.point((370, 378)))
        )
        self._draw_text(self.player_type.name.title(), 555, 378)
        self._draw_button(">", PLAYER_NEXT_BUTTON)
        self._draw_button("Clear local leaderboard", CLEAR_LEADERBOARD_BUTTON)
        if self.notice_message:
            self._draw_text(self.notice_message, 400, 520, color=MUTED_TEXT)
        self._draw_button("Save", SAVE_SETTINGS_BUTTON)

    def _draw_clear_confirmation(self) -> None:
        self._draw_panel(pygame.Rect(175, 175, 450, 255))
        self._draw_title("Clear leaderboard?", 210)
        self._draw_text("This permanently removes all local runs.", 400, 275)
        self._draw_button("Clear", CLEAR_CONFIRM_BUTTON)
        self._draw_button("Cancel", CANCEL_CONFIRM_BUTTON)

    def _draw_title(self, label: str, y: int) -> None:
        text = self.title_font.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=self.layout.point((400, y))))

    def _draw_text(
        self,
        label: str,
        center_x: int,
        y: int,
        *,
        color: tuple[int, int, int] = TEXT,
        center: bool = True,
        x: int | None = None,
    ) -> None:
        text = self.font.render(label, True, color)
        anchor = self.layout.point(
            (center_x if center else x if x is not None else center_x, y)
        )
        position = (
            text.get_rect(center=anchor)
            if center
            else text.get_rect(topleft=anchor)
        )
        self.screen.blit(text, position)

    def _draw_button(self, label: str, rect: pygame.Rect) -> None:
        rect = self.layout.rect(rect)
        color = BUTTON_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else BUTTON
        radius = max(1, round(5 * self.layout.scale))
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)
        pygame.draw.rect(
            self.screen,
            (155, 175, 155),
            rect,
            max(1, round(self.layout.scale)),
            border_radius=radius,
        )
        text = self.font.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_panel(self, rect: pygame.Rect) -> None:
        rect = self.layout.rect(rect)
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        radius = max(1, round(10 * self.layout.scale))
        pygame.draw.rect(panel, (20, 30, 25, 220), panel.get_rect(), border_radius=radius)
        pygame.draw.rect(
            panel,
            (125, 150, 125, 230),
            panel.get_rect(),
            width=max(1, round(self.layout.scale)),
            border_radius=radius,
        )
        self.screen.blit(panel, rect)

    def _draw_slider(self, rect: pygame.Rect, value: float) -> None:
        rect = self.layout.rect(rect)
        pygame.draw.rect(self.screen, (85, 85, 85), rect, border_radius=8)
        filled = rect.copy()
        filled.width = round(rect.width * value)
        pygame.draw.rect(self.screen, (110, 175, 110), filled, border_radius=8)
        pygame.draw.circle(
            self.screen,
            TEXT,
            (rect.x + round(rect.width * value), rect.centery),
            max(1, round(11 * self.layout.scale)),
        )
