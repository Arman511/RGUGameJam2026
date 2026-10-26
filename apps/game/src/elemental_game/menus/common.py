from __future__ import annotations

import os
import platform
import re
import subprocess
import webbrowser

import pygame

from elemental_game import config

BUTTON = (65, 85, 65)
BUTTON_HOVER = (85, 110, 85)
TEXT = (245, 245, 245)
MUTED_TEXT = (180, 180, 180)
ERROR_TEXT = (255, 130, 130)
MUSIC_SLIDER = pygame.Rect(175, 160, 450, 14)
SFX_SLIDER = pygame.Rect(175, 210, 450, 14)
TURRET_SENSITIVITY_SLIDER = pygame.Rect(175, 305, 450, 14)
API_BASE_URL_INPUT = pygame.Rect(145, 365, 510, 38)
HINTS_TOGGLE_BUTTON = pygame.Rect(520, 238, 110, 36)
PLAYER_SELECT_PANEL = pygame.Rect(115, 425, 570, 65)
PLAYER_PREVIOUS_BUTTON = pygame.Rect(285, PLAYER_SELECT_PANEL.centery - 21, 48, 42)
PLAYER_NEXT_BUTTON = pygame.Rect(445, PLAYER_SELECT_PANEL.centery - 21, 48, 42)
CLEAR_LEADERBOARD_BUTTON = pygame.Rect(170, 500, 460, 40)
SAVE_SETTINGS_BUTTON = pygame.Rect(330, 545, 140, 40)
SETTINGS_PANEL = pygame.Rect(15, 45, 770, 545)
LOGIN_BUTTON = pygame.Rect(205, 340, 120, 48)
REGISTER_BUTTON = pygame.Rect(340, 340, 120, 48)
GUEST_BUTTON = pygame.Rect(475, 340, 120, 48)
PLAY_BUTTON = pygame.Rect(150, 205, 230, 58)
LEADERBOARD_BUTTON = pygame.Rect(420, 205, 230, 58)
SETTINGS_BUTTON = pygame.Rect(150, 295, 230, 58)
HELP_BUTTON = pygame.Rect(420, 295, 230, 58)
SIGN_IN_BUTTON = pygame.Rect(150, 385, 230, 58)
EXIT_BUTTON = pygame.Rect(420, 385, 230, 58)
CREDITS_BUTTON = pygame.Rect(665, 20, 115, 40)
CREDITS_MODAL = pygame.Rect(70, 60, 660, 480)
CREDITS_CLOSE_BUTTON = pygame.Rect(330, 470, 140, 44)
UPDATE_MODAL = pygame.Rect(100, 190, 600, 220)
UPDATE_DOWNLOAD_BUTTON = pygame.Rect(165, 335, 210, 48)
UPDATE_LATER_BUTTON = pygame.Rect(425, 335, 210, 48)
LEADERBOARD_BACK_BUTTON = pygame.Rect(330, 490, 140, 44)
HELP_BACK_BUTTON = pygame.Rect(330, 480, 140, 44)
CLEAR_CONFIRM_BUTTON = pygame.Rect(250, 340, 140, 48)
CANCEL_CONFIRM_BUTTON = pygame.Rect(410, 340, 140, 48)
SINGLE_PLAYER_BUTTON = pygame.Rect(150, 260, 230, 58)
ONLINE_PLAYER_BUTTON = pygame.Rect(420, 260, 230, 58)
HOST_MATCH_BUTTON = pygame.Rect(150, 260, 230, 58)
JOIN_MATCH_BUTTON = pygame.Rect(420, 260, 230, 58)
JOIN_CODE_RECT = pygame.Rect(250, 210, 300, 44)
JOIN_CODE_SUBMIT_BUTTON = pygame.Rect(330, 285, 140, 48)
MULTIPLAYER_BACK_BUTTON = pygame.Rect(330, 390, 140, 44)
CANCEL_HOST_BUTTON = pygame.Rect(330, 410, 140, 44)
LEADERBOARD_FILTER_RECT = pygame.Rect(235, 105, 330, 42)
LOGIN_USERNAME_RECT = pygame.Rect(250, 205, 300, 44)
LOGIN_PASSWORD_RECT = pygame.Rect(250, 265, 300, 44)
MENU_DESIGN_WIDTH = 800
MENU_DESIGN_HEIGHT = 600
MENU_FRAME_PANEL = pygame.Rect(5, 60, 775, 475)
REGISTER_URL = f"{config.ELEMENTAL_KEEP_API_BASE_URL}/register"

RUDE_USERNAME_PATTERN = re.compile(
    rf"\b(?:{'|'.join(re.escape(word) for word in config.RUDE_USERNAME_WORDS)})\b",
    re.IGNORECASE,
)


def censor_username(username: str) -> str:
    return RUDE_USERNAME_PATTERN.sub(
        lambda match: "*" * len(match.group()),
        username,
    )


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


def open_external_page(url: str) -> bool:
    is_wsl = (
        bool(os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"))
        or "microsoft" in platform.release().casefold()
    )
    if not is_wsl:
        try:
            return webbrowser.open(url)
        except (OSError, webbrowser.Error):
            return False

    try:
        subprocess.run(
            ["cmd.exe", "/c", "start", "", url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def open_registration_page(base_url: str | None = None) -> bool:
    register_url = (
        f"{(base_url or config.ELEMENTAL_KEEP_API_BASE_URL).rstrip('/')}/register"
    )
    return open_external_page(register_url)


class InputField:
    def __init__(
        self,
        rect: pygame.Rect,
        *,
        placeholder: str,
        max_length: int,
        secret: bool = False,
        scale: float = 1.0,
        text_input: bool = False,
    ) -> None:
        self.rect = rect
        self.placeholder = placeholder
        self.max_length = max_length
        self.secret = secret
        self.scale = scale
        self.text_input = text_input
        self.value = ""
        self.focused = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif (
                not self.text_input
                and getattr(event, "unicode", "").isprintable()
                and len(self.value) < self.max_length
            ):
                self.value += event.unicode
        elif event.type == pygame.TEXTINPUT and self.focused and self.text_input:
            text = "".join(
                character for character in event.text if character.isprintable()
            )
            self.value = (self.value + text)[: self.max_length]

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
