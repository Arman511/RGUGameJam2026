from __future__ import annotations

import math

import pygame

from elemental_game.api_client.http import APIError
from elemental_game.multiplayer import MultiplayerClient, MultiplayerError

from .common import (
    CANCEL_HOST_BUTTON,
    ERROR_TEXT,
    HOST_MATCH_BUTTON,
    JOIN_CODE_SUBMIT_BUTTON,
    JOIN_MATCH_BUTTON,
    MULTIPLAYER_BACK_BUTTON,
    MUTED_TEXT,
)
from .context import MenuContext


class MultiplayerMenuMixin(MenuContext):
    def _handle_online_select_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "mode_select"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(HOST_MATCH_BUTTON).collidepoint(event.pos):
                self._host_multiplayer_game()
            elif self.layout.rect(JOIN_MATCH_BUTTON).collidepoint(event.pos):
                self.join_code.value = ""
                self.join_code.focused = False
                self.state = "join_room"
            elif self.layout.rect(MULTIPLAYER_BACK_BUTTON).collidepoint(event.pos):
                self.state = "mode_select"

    def _host_multiplayer_game(self) -> None:
        try:
            match_config = self.auth.client.get_match_config()
        except APIError as error:
            self.error_message = f"Could not read multiplayer settings: {error}"
            return
        try:
            self.multiplayer_client = MultiplayerClient.host(self.username or "Guest")
        except MultiplayerError as error:
            self.error_message = str(error)
            return
        self.host_join_timeout_ms = math.ceil(match_config.join_timeout_seconds * 1000)
        self.host_join_deadline_ms = (
            pygame.time.get_ticks() + self.host_join_timeout_ms
            if self.multiplayer_client.room_code is not None
            else None
        )
        self.error_message = ""
        self.state = "hosting"

    def _handle_join_room_event(self, event: pygame.event.Event) -> None:
        self.join_code.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = "online_select"
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._join_multiplayer_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.layout.rect(JOIN_CODE_SUBMIT_BUTTON).collidepoint(event.pos):
                self._join_multiplayer_game()
            elif self.layout.rect(MULTIPLAYER_BACK_BUTTON).collidepoint(event.pos):
                self.state = "online_select"

    def _join_multiplayer_game(self) -> None:
        room_code = self.join_code.value.strip().upper()
        if len(room_code) != 6:
            self.error_message = "Enter the 6-character room code."
            return
        try:
            self.multiplayer_client = MultiplayerClient.join(
                self.username or "Guest", room_code
            )
        except MultiplayerError as error:
            self.error_message = str(error)
            return
        self.game_mode = "multiplayer"
        self.state = "menu"
        self.error_message = ""
        self.start_game = True
        self.running = False

    def _poll_hosting_room(self) -> None:
        if self.multiplayer_client is None:
            self.state = "online_select"
            self.error_message = "Could not connect to the multiplayer room."
            return
        try:
            messages = self.multiplayer_client.poll()
        except MultiplayerError as error:
            self.multiplayer_client.close()
            self.multiplayer_client = None
            self.state = "online_select"
            self.error_message = str(error)
            return
        for message in messages:
            if message["type"] == "match_started":
                self.host_join_deadline_ms = None
                self.game_mode = "multiplayer"
                self.state = "menu"
                self.start_game = True
                self.running = False
            elif message["type"] == "room_created":
                if self.host_join_timeout_ms is not None:
                    self.host_join_deadline_ms = (
                        pygame.time.get_ticks() + self.host_join_timeout_ms
                    )
            elif message["type"] == "room_expired":
                self.multiplayer_client.close()
                self.multiplayer_client = None
                self.host_join_deadline_ms = None
                self.state = "online_select"
                self.error_message = message["payload"]["message"]
                return
            elif message["type"] == "error":
                self.error_message = message["payload"]["message"]
            elif message["type"] == "opponent_disconnected":
                self.error_message = "Your opponent disconnected."

    def _handle_hosting_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.multiplayer_client is not None:
                self.multiplayer_client.close()
                self.multiplayer_client = None
            self.host_join_deadline_ms = None
            self.state = "online_select"
            self.error_message = ""
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.layout.rect(CANCEL_HOST_BUTTON).collidepoint(event.pos)
        ):
            self._handle_hosting_event(
                pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
            )

    def _draw_online_select(self) -> None:
        self._draw_panel(pygame.Rect(120, 150, 560, 300))
        self._draw_title("2-player VS", 190)
        self._draw_button("Host a game", HOST_MATCH_BUTTON)
        self._draw_button("Join with code", JOIN_MATCH_BUTTON)
        self._draw_button("Back", MULTIPLAYER_BACK_BUTTON)
        if self.error_message:
            self._draw_text(self.error_message, 400, 355, color=ERROR_TEXT)

    def _draw_join_room(self) -> None:
        self._draw_panel(pygame.Rect(120, 130, 560, 340))
        self._draw_title("Join a game", 170)
        self._draw_text("Enter the host's 6-character room code.", 400, 205)
        self.join_code.draw(self.screen, self.font)
        self._draw_button("Join", JOIN_CODE_SUBMIT_BUTTON)
        self._draw_button("Back", MULTIPLAYER_BACK_BUTTON)
        if self.error_message:
            self._draw_text(self.error_message, 400, 370, color=ERROR_TEXT)

    def _draw_hosting(self) -> None:
        self._draw_panel(pygame.Rect(120, 130, 560, 340))
        room_code = (
            self.multiplayer_client.room_code
            if self.multiplayer_client is not None
            else "------"
        )
        if room_code is None:
            self._draw_title("Match queue", 175)
            position = (
                self.multiplayer_client.queue_position
                if self.multiplayer_client is not None
                else None
            )
            self._draw_text(f"Queue position: {position or 'updating'}", 400, 270)
            self._draw_text("A match slot will open automatically.", 400, 315)
        else:
            self._draw_title("Waiting for player 2", 175)
            self._draw_text(f"Room code: {room_code}", 400, 270)
            self._draw_text("Share the code with your opponent.", 400, 315)
            if self.host_join_deadline_ms is not None:
                remaining_ms = max(
                    0, self.host_join_deadline_ms - pygame.time.get_ticks()
                )
                remaining_seconds = (remaining_ms + 999) // 1000
                self._draw_text(
                    f"Time remaining: {remaining_seconds}s",
                    400,
                    350,
                    color=MUTED_TEXT,
                )
        self._draw_button("Cancel", CANCEL_HOST_BUTTON)
        if self.error_message:
            self._draw_text(self.error_message, 400, 370, color=ERROR_TEXT)
