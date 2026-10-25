from __future__ import annotations

import sqlite3

import pygame
from pydantic import ValidationError as PydanticValidationError

from elemental_game.api_client.http import APIError
from elemental_game.api_client.models import RunSubmission
from elemental_game.audio import play_sfx
from elemental_game.menus import (
    InputField,
    open_registration_page,
)

GAME_OVER_DISPLAY_DELAY_MS = 500


class GameOverDialog:
    def __init__(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        menus,
        *,
        run_id: str,
        survival_time: float,
        final_wave: int,
        enemies_defeated: int,
    ) -> None:
        self.surface = surface
        self.font = font
        self.menus = menus
        self.run_id = run_id
        self.survival_time = survival_time
        self.final_wave = final_wave
        self.enemies_defeated = enemies_defeated
        self.display_at = pygame.time.get_ticks() + GAME_OVER_DISPLAY_DELAY_MS
        self.username = menus.username or "Guest"
        play_sfx("explosion")
        self.status_message = ""
        self.done = False
        self.state = "publish" if menus.username else "username"
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        self.panel = pygame.Rect(0, 0, min(760, surface.get_width() - 40), 430)
        self.panel.center = (center_x, center_y)
        self.username_input = InputField(
            pygame.Rect(center_x - 250, center_y - 10, 500, 48),
            placeholder="Leaderboard username",
            max_length=32,
            text_input=True,
        )
        self.username_input.focused = menus.username is None
        if self.username_input.focused:
            pygame.key.start_text_input()
        self.login_username = InputField(
            pygame.Rect(center_x - 250, center_y - 75, 500, 48),
            placeholder="Account username",
            max_length=32,
        )
        self.login_password = InputField(
            pygame.Rect(center_x - 250, center_y - 15, 500, 48),
            placeholder="Password",
            max_length=128,
            secret=True,
        )
        self.login_username.value = self.username if menus.username is None else ""
        self.local_saved = False
        if menus.username:
            self._save_local(self.username)
        else:
            self._save_local("Guest")

    def _save_local(self, username: str) -> bool:
        try:
            self.menus.store.submit_run(
                self.run_id,
                self.survival_time,
                self.final_wave,
                self.enemies_defeated,
                username=username,
            )
        except (OSError, sqlite3.Error, ValueError) as error:
            self.status_message = f"Could not save run locally: {error}"
            return False
        self.username = username
        self.local_saved = True
        self.status_message = ""
        return True

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.done or pygame.time.get_ticks() < self.display_at:
            return
        if self.state == "published":
            if (
                event.type == pygame.KEYDOWN
                and event.key
                in (
                    pygame.K_ESCAPE,
                    pygame.K_RETURN,
                )
                or (
                    event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
                    and event.button == 1
                    and self._button_rect(1).collidepoint(event.pos)
                )
            ):
                self._finish()
            return
        if self.state == "username":
            self.username_input.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._save_as_guest()
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_RETURN
                or (
                    event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
                    and event.button == 1
                    and self._button_rect(0).collidepoint(event.pos)
                )
            ):
                self._save_guest_username()
            elif (
                event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
                and event.button == 1
                and self._button_rect(1).collidepoint(event.pos)
            ):
                self._save_as_guest()
            return
        if self.state == "login":
            self._handle_login_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_n):
                self._finish()
            elif event.key in (pygame.K_RETURN, pygame.K_y):
                self._publish_or_sign_in()
        elif (
            event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
            and event.button == 1
        ):
            if self._button_rect(0).collidepoint(event.pos):
                self._publish_or_sign_in()
            elif self._button_rect(1).collidepoint(event.pos):
                self._finish()

    def _finish(self) -> None:
        if self.username_input.text_input:
            pygame.key.stop_text_input()
        self.done = True

    def _save_as_guest(self) -> None:
        if self._save_local("Guest"):
            self._finish()

    def _save_guest_username(self) -> None:
        username = self.username_input.value.strip()
        if not username:
            self.status_message = "Enter a username to save this run."
            return
        if self._save_local(username):
            pygame.key.stop_text_input()
            self.login_username.value = username
            self.state = "publish"

    def _publish_or_sign_in(self) -> None:
        if not self.local_saved and not self._save_local(self.username):
            return
        if not self.menus.username:
            self.state = "login"
            self.login_username.focused = True
            self.status_message = "Sign in to publish this locally saved run."
            return
        self._publish()

    def _handle_login_event(self, event: pygame.event.Event) -> None:
        self.login_username.handle_event(event)
        self.login_password.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.login_username.focused = not self.login_username.focused
                self.login_password.focused = not self.login_username.focused
            elif event.key == pygame.K_RETURN:
                self._login_and_publish()
            elif event.key == pygame.K_ESCAPE:
                self.state = "publish"
                self.status_message = ""
        elif (
            event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
            and event.button == 1
        ):
            if self._button_rect(0).collidepoint(event.pos):
                self._login_and_publish()
            elif self._button_rect(1).collidepoint(event.pos):
                if not open_registration_page():
                    self.status_message = "Could not open the registration page."
                else:
                    self.status_message = "Register in your browser, then sign in here."
            elif self._button_rect(2).collidepoint(event.pos):
                self.state = "publish"
                self.status_message = ""

    def _login_and_publish(self) -> None:
        username = self.login_username.value.strip()
        password = self.login_password.value
        if len(username) < 3 or len(password) < 8:
            self.status_message = "Enter an account username and password."
            return
        try:
            response = self.menus.auth.login(username, password)
        except APIError as error:
            self.status_message = f"Sign in failed: {error}"
            return
        self.menus.username = response.user.username
        self._save_local(response.user.username)
        self._publish()

    def _publish(self) -> None:
        run = RunSubmission(
            run_id=self.run_id,
            time_survived=self.survival_time,
            wave_number=self.final_wave,
            enemies_defeated=self.enemies_defeated,
        )
        try:
            self.menus.auth.client.submit_run(run)
        except (APIError, PydanticValidationError) as error:
            self.status_message = f"Run saved locally; publishing failed: {error}"
            return
        self.state = "published"
        self.status_message = "Run published successfully."
        self.done = True

    def draw(self) -> None:
        if pygame.time.get_ticks() < self.display_at:
            return
        overlay = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        self.surface.blit(overlay, (0, 0))
        pygame.draw.rect(self.surface, (38, 43, 51), self.panel)
        pygame.draw.rect(self.surface, (230, 230, 230), self.panel, 2)
        self._draw_text("RUN OVER", self.panel.y + 22, (255, 220, 130))
        self._draw_text(
            f"Wave {self.final_wave}   Time {self.survival_time:.1f}s   "
            f"Enemies defeated {self.enemies_defeated}",
            self.panel.y + 74,
        )
        if self.state == "username":
            self._draw_text(
                "Choose a local name, or keep the Guest entry.",
                self.panel.y + 130,
            )
            self.username_input.draw(self.surface, self.font)
            self._draw_button("Save with name", self._button_rect(0))
            self._draw_button("Finish as Guest", self._button_rect(1))
        elif self.state == "login":
            self._draw_text("Sign in to publish this run online.", self.panel.y + 116)
            self.login_username.draw(self.surface, self.font)
            self.login_password.draw(self.surface, self.font)
            self._draw_button("Sign in & publish", self._button_rect(0))
            self._draw_button("Register", self._button_rect(1))
            self._draw_button("Back", self._button_rect(2))
        elif self.state == "published":
            self._draw_text("Run published successfully.", self.panel.y + 150)
            self._draw_button("Finish", self._button_rect(1))
        else:
            if self.menus.username:
                message = "Publish this run to the online leaderboard?"
            else:
                message = "Run saved locally. Sign in to publish it online."
            self._draw_text(message, self.panel.y + 132)
            self._draw_button(
                "Publish" if self.menus.username else "Sign in & publish",
                self._button_rect(0),
            )
            self._draw_button("Finish", self._button_rect(1))
        if self.status_message:
            self._draw_text(
                self.status_message, self.panel.bottom - 84, (255, 190, 150)
            )

    def _button_rect(self, index: int) -> pygame.Rect:
        width = 220
        height = 48
        spacing = 24
        count = 3 if self.state == "login" else 2
        left = self.panel.centerx - (count * width + (count - 1) * spacing) // 2
        return pygame.Rect(
            left + index * (width + spacing),
            self.panel.bottom - 65,
            width,
            height,
        )

    def _draw_button(self, label: str, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.surface, (65, 85, 65), rect, border_radius=5)
        pygame.draw.rect(self.surface, (155, 175, 155), rect, 1, border_radius=5)
        text = self.font.render(label, True, (245, 245, 245))
        self.surface.blit(text, text.get_rect(center=rect.center))

    def _draw_text(
        self,
        text: str,
        y: int,
        color: tuple[int, int, int] = (245, 245, 245),
    ) -> None:
        rendered = self.font.render(text, True, color)
        if rendered.get_width() > self.panel.width - 40:
            available_width = self.panel.width - 40
            while text and self.font.size(text)[0] > available_width:
                text = text[:-1]
            rendered = self.font.render(text, True, color)
        self.surface.blit(rendered, rendered.get_rect(center=(self.panel.centerx, y)))
