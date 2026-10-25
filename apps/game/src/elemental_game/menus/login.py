from __future__ import annotations

import pygame

from elemental_game.api_client.http import APIError, AuthError

from .common import (
    ERROR_TEXT,
    GUEST_BUTTON,
    LOGIN_BUTTON,
    REGISTER_BUTTON,
    open_registration_page,
)
from .context import MenuContext


class LoginMenuMixin(MenuContext):
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
                if not open_registration_page():
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

    def _draw_login(self) -> None:
        self._draw_panel(pygame.Rect(115, 75, 570, 115))
        self._draw_title("Elemental Keep", 110)
        self._draw_text("Log in or skip to play as a guest.", 400, 170)
        self.login_username.draw(self.screen, self.font)
        self.login_password.draw(self.screen, self.font)
        self._draw_button("Log in", LOGIN_BUTTON)
        self._draw_button("Register", REGISTER_BUTTON)
        self._draw_button("Skip", GUEST_BUTTON)
        if self.error_message:
            self._draw_text(
                self.error_message, 400, 425, color=ERROR_TEXT, center=False, x=120
            )
