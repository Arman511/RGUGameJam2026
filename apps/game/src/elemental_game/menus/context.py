from __future__ import annotations

from typing import Any, Protocol

import pygame

from elemental_game.api_client import AuthClient, CredentialStore
from elemental_game.database import LocalLeaderboardStore
from elemental_game.multiplayer import MultiplayerClient
from elemental_game.types.player import PlayerType

from .common import InputField, MenuLayout


class MenuContext(Protocol):
    auth: AuthClient
    credentials: CredentialStore
    error_message: str
    font: pygame.font.Font
    game_mode: str
    hints_enabled: bool
    host_join_deadline_ms: int | None
    host_join_timeout_ms: int | None
    layout: MenuLayout
    leaderboard_filter: InputField
    leaderboard_rows: list[dict[str, Any]]
    leaderboard_scroll: int
    login_password: InputField
    login_username: InputField
    multiplayer_client: MultiplayerClient | None
    notice_message: str
    player_previews: dict[PlayerType, pygame.Surface]
    player_type: PlayerType
    preferences: dict[str, float]
    revealed_usernames: set[str]
    running: bool
    screen: pygame.Surface
    start_game: bool
    state: str
    store: LocalLeaderboardStore
    title_font: pygame.font.Font
    username: str | None
    join_code: InputField

    def _apply_sound_preferences(self) -> None: ...

    def _change_player_type(self, step: int) -> None: ...

    def _close_settings(self) -> None: ...

    def _continue_as_guest(self) -> None: ...

    def _draw_button(self, label: str, rect: pygame.Rect) -> None: ...

    def _draw_credits(self) -> None: ...

    def _draw_panel(self, rect: pygame.Rect) -> None: ...

    def _draw_slider(self, rect: pygame.Rect, value: float) -> None: ...

    def _draw_text(
        self,
        label: str,
        center_x: int,
        y: int,
        *,
        color: tuple[int, int, int] = (245, 245, 245),
        center: bool = True,
        x: int | None = None,
    ) -> None: ...

    def _draw_title(self, label: str, y: int) -> None: ...

    def _filtered_leaderboard(self) -> list[dict[str, Any]]: ...

    def _handle_hosting_event(self, event: pygame.event.Event) -> None: ...

    def _save_sound_preferences(self) -> None: ...

    def _host_multiplayer_game(self) -> None: ...

    def _join_multiplayer_game(self) -> None: ...

    def _login(self) -> None: ...

    def _update_slider(self, mouse_x: int) -> None: ...
