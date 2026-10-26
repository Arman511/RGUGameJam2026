from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import pygame

from elemental_game import __version__
from elemental_game.api_client import APIClient, AuthClient, CredentialStore
from elemental_game.audio import (
    handle_background_music_end_event,
    initialise_audio,
    play_background_music,
    set_background_music_volume,
)
from elemental_game.config import ASSETS_DIR, IMAGES_DIR
from elemental_game.database import LocalLeaderboardStore
from elemental_game.networking.client import MultiplayerClient
from elemental_game.types.player import PlayerType
from elemental_game.version_check import UpdateInfo, check_for_update

from .common import (
    API_BASE_URL_INPUT,
    BUTTON,
    BUTTON_HOVER,
    JOIN_CODE_RECT,
    LEADERBOARD_FILTER_RECT,
    LOGIN_PASSWORD_RECT,
    LOGIN_USERNAME_RECT,
    MENU_DESIGN_HEIGHT,
    MENU_DESIGN_WIDTH,
    TEXT,
    UPDATE_DOWNLOAD_BUTTON,
    UPDATE_LATER_BUTTON,
    UPDATE_MODAL,
    InputField,
    MenuLayout,
    open_external_page,
)
from .help import HelpMenuMixin
from .leaderboard import LeaderboardMenuMixin
from .login import LoginMenuMixin
from .main_menu import MainMenuMixin
from .multiplayer import MultiplayerMenuMixin
from .settings import SettingsMenuMixin

logger = logging.getLogger(__name__)


class MenuSystem(
    LoginMenuMixin,
    MainMenuMixin,
    MultiplayerMenuMixin,
    HelpMenuMixin,
    LeaderboardMenuMixin,
    SettingsMenuMixin,
):
    layout = MenuLayout(MENU_DESIGN_WIDTH, MENU_DESIGN_HEIGHT)

    def __init__(self, screen: pygame.Surface) -> None:
        initialise_audio()
        self.screen = screen
        self.layout = MenuLayout(*screen.get_size())
        pygame.display.set_caption("Elemental Keep")
        self.clock = pygame.time.Clock()
        menu_font_path = os.path.join(ASSETS_DIR, "font", "pixelfont.ttf")
        self.font = pygame.font.Font(
            menu_font_path, max(1, round(28 * self.layout.scale))
        )
        self.title_font = pygame.font.Font(
            menu_font_path, max(1, round(42 * self.layout.scale))
        )
        self.store = LocalLeaderboardStore()
        self.credentials = CredentialStore()
        self.api_base_url = self.store.api_base_url()
        self.auth = AuthClient(APIClient(base_url=self.api_base_url), self.credentials)
        self.username: str | None = None
        self.state = "login"
        self.running = True
        self.start_game = False  # set when the player presses Play
        self.game_mode = "single"
        self.multiplayer_client: MultiplayerClient | None = None
        self.host_join_timeout_ms: int | None = None
        self.host_join_deadline_ms: int | None = None
        self.error_message = ""
        self.notice_message = ""
        self.leaderboard_rows: list[dict[str, Any]] = []
        self.revealed_usernames: set[str] = set()
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
        self.join_code = InputField(
            self.layout.rect(JOIN_CODE_RECT),
            placeholder="Room code",
            max_length=6,
            scale=self.layout.scale,
        )
        self.preferences = self.store.sound_preferences()
        self.manual_turret_sensitivity = self.store.manual_turret_sensitivity()
        self.api_base_url_input = InputField(
            self.layout.rect(API_BASE_URL_INPUT),
            placeholder="https://example.com",
            max_length=255,
        )
        self.api_base_url_input.value = self.api_base_url
        self.hints_enabled = self.store.hints_enabled()
        self.update_info: UpdateInfo | None = None
        self.update_prompt_open = False
        self.update_open_error = ""
        self.player_type = PlayerType(self.store.player_image_number())
        backgrounds_dir = os.path.join(IMAGES_DIR, "backgrounds")
        self.menu_background = pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(backgrounds_dir, "menu-background.png")
            ).convert(),
            self.screen.get_size(),
        )
        preview_size = max(1, round(48 * self.layout.scale))
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
        self._start_update_check()

    def _start_update_check(self) -> None:
        try:
            update = check_for_update(self.api_base_url, __version__)
        except (httpx.HTTPError, ImportError, TypeError, ValueError) as error:
            logger.warning("Could not check for game updates: %s", error)
            return
        if update is not None:
            self.update_info = update
            self.update_prompt_open = True

    def _apply_sound_preferences(self) -> None:
        if pygame.mixer.get_init() is None:
            return
        set_background_music_volume(self.preferences["music_volume"])
        for channel_number in range(1, pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(channel_number).set_volume(
                self.preferences["sfx_volume"]
            )

    def _save_sound_preferences(self) -> None:
        self.store.save_sound_preferences(
            music_volume=self.preferences["music_volume"],
            sfx_volume=self.preferences["sfx_volume"],
        )
        self.store.save_hints_enabled(self.hints_enabled)
        self.store.save_player_image_number(int(self.player_type))
        self._apply_sound_preferences()

    def run(self) -> bool:
        """Show the menus. Returns True if the player pressed Play,
        False if they closed the window. Can be called again later
        (e.g. Esc in game) and resumes at the main menu."""
        self.running = True
        self.start_game = False
        play_background_music(volume=self.preferences["music_volume"])
        while self.running:
            self.clock.tick(60)
            if self.state == "hosting":
                self._poll_hosting_room()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.state == "settings":
                        self._close_settings()
                    multiplayer_client = getattr(self, "multiplayer_client", None)
                    if multiplayer_client is not None:
                        multiplayer_client.close()
                        self.multiplayer_client = None
                    self.running = False
                    break
                elif handle_background_music_end_event(
                    event, volume=self.preferences["music_volume"]
                ):
                    continue
                else:
                    self._handle_event(event)

                if not self.running:
                    break
            if not self.running:
                break

            self._draw()
            pygame.display.flip()
        return self.start_game

    def _handle_event(self, event: pygame.event.Event) -> None:
        if getattr(self, "update_prompt_open", False):
            self._handle_update_prompt_event(event)
            return
        if self.state == "login":
            self._handle_login_event(event)
        elif self.state == "menu":
            self._handle_menu_event(event)
        elif self.state == "credits":
            self._handle_credits_event(event)
        elif self.state == "leaderboard":
            self._handle_leaderboard_event(event)
        elif self.state == "settings":
            self._handle_settings_event(event)
        elif self.state == "help":
            self._handle_help_event(event)
        elif self.state == "confirm_clear":
            self._handle_clear_confirmation_event(event)
        elif self.state == "mode_select":
            self._handle_mode_select_event(event)
        elif self.state == "online_select":
            self._handle_online_select_event(event)
        elif self.state == "join_room":
            self._handle_join_room_event(event)
        elif self.state == "hosting":
            self._handle_hosting_event(event)

    def _draw(self) -> None:
        self.screen.blit(self.menu_background, (0, 0))
        if self.state == "login":
            self._draw_login()
        elif self.state == "menu":
            self._draw_menu()
        elif self.state == "credits":
            self._draw_credits()
        elif self.state == "leaderboard":
            self._draw_leaderboard()
        elif self.state == "settings":
            self._draw_settings()
        elif self.state == "help":
            self._draw_help()
        elif self.state == "confirm_clear":
            self._draw_clear_confirmation()
        elif self.state == "mode_select":
            self._draw_mode_select()
        elif self.state == "online_select":
            self._draw_online_select()
        elif self.state == "join_room":
            self._draw_join_room()
        elif self.state == "hosting":
            self._draw_hosting()
        self._draw_update_prompt()

    def _handle_update_prompt_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.update_prompt_open = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(UPDATE_LATER_BUTTON).collidepoint(event.pos):
                self.update_prompt_open = False
            elif self.layout.rect(UPDATE_DOWNLOAD_BUTTON).collidepoint(event.pos):
                opened = self.update_info is not None and open_external_page(
                    self.update_info.release_url
                )
                if opened:
                    self.update_prompt_open = False
                else:
                    self.update_open_error = "Could not open the download page."

    def _draw_update_prompt(self) -> None:
        if not getattr(self, "update_prompt_open", False):
            return

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))
        self._draw_panel(UPDATE_MODAL)
        self._draw_title("Update available", 235)
        version = self.update_info.version if self.update_info is not None else ""
        self._draw_text(f"Version {version} is ready to download.", 400, 280)
        self._draw_button("Download update", UPDATE_DOWNLOAD_BUTTON)
        self._draw_button("Later", UPDATE_LATER_BUTTON)
        if self.update_open_error:
            self._draw_text(self.update_open_error, 400, 405, color=(255, 130, 130))

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
        text_font: pygame.font.Font | None = None,
    ) -> None:
        text = (text_font or self.font).render(label, True, color)
        anchor = self.layout.point(
            (center_x if center else x if x is not None else center_x, y)
        )
        position = (
            text.get_rect(center=anchor) if center else text.get_rect(topleft=anchor)
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
        pygame.draw.rect(
            panel, (20, 30, 25, 220), panel.get_rect(), border_radius=radius
        )
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
