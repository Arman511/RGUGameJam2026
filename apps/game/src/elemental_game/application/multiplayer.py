"""Coordinate multiplayer state that belongs to the active game run."""

import pygame

from elemental_game.application.session import GameSession
from elemental_game.menus import MenuSystem
from elemental_game.networking.attacks import (
    AttackCostTracker,
    send_multiplayer_attack,
)
from elemental_game.networking.client import MultiplayerClient, MultiplayerError
from elemental_game.screen_rendering.game import multiplayer_attack_panel_rect
from elemental_game.screen_rendering.game_over import GameOverDialog
from elemental_game.screen_rendering.multiplayer_game_over import (
    MultiplayerGameOverDialog,
)
from elemental_game.types.crop import CropType
from elemental_game.types.weather import WeatherTypes

GameOverScreen = GameOverDialog | MultiplayerGameOverDialog | None


class MultiplayerController:
    """Keep multiplayer events and attack controls out of the main game loop."""

    def __init__(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        menus: MenuSystem,
        game: GameSession,
    ) -> None:
        self.screen = screen
        self.font = font
        self.menus = menus
        self.client = self._client_from_menu()
        self.panel_open = False
        self.status = ""
        self.pending_extra_enemies = 0
        self.pending_health_multiplier = 1.0
        self.pending_elemental_bias: dict[CropType, int] = {}
        self.pending_weather: WeatherTypes | None = None
        self.selected_element = next(
            (crop for crop, count in game.player.crops.items() if count > 0),
            None,
        )
        self.costs = AttackCostTracker()
        self.result_sent = False
        self.costs.set_phase(game.wave_number, game.planting_phase)

    def reset_run(self, game: GameSession) -> None:
        self.panel_open = False
        self.status = ""
        self.pending_extra_enemies = 0
        self.pending_health_multiplier = 1.0
        self.pending_elemental_bias = {}
        self.pending_weather = None
        self.result_sent = False
        self.costs.reset()
        self.costs.set_phase(game.wave_number, game.planting_phase)

    def notify_wave_started(self, started_wave: int) -> None:
        if self.client is not None:
            try:
                self.client.send_wave(started_wave)
            except MultiplayerError as error:
                self.status = str(error)
        self.pending_extra_enemies = 0
        self.pending_health_multiplier = 1.0
        self.pending_elemental_bias = {}
        self.pending_weather = None

    def poll(self, game_over: GameOverScreen) -> GameOverScreen:
        if self.client is None:
            return game_over
        try:
            for message in self.client.poll():
                payload = message["payload"]
                if message["type"] == "opponent_action":
                    self._apply_opponent_action(payload)
                elif message["type"] == "match_ended":
                    if game_over is None:
                        game_over = MultiplayerGameOverDialog(
                            self.screen, self.font, payload["result"]
                        )
                elif message["type"] == "opponent_disconnected":
                    self.status = "Opponent disconnected."
                    if game_over is None:
                        game_over = MultiplayerGameOverDialog(
                            self.screen, self.font, "defeat"
                        )
                elif message["type"] == "error":
                    self.status = payload["message"]
        except MultiplayerError as error:
            self.status = str(error)
            self.close_connection()
        return game_over

    def finish_match_if_needed(
        self, game: GameSession, game_over: GameOverScreen
    ) -> GameOverScreen:
        if self.client is None or game.house.health > 0 or self.result_sent:
            return game_over
        try:
            self.client.end_match()
        except MultiplayerError as error:
            self.status = str(error)
            game_over = MultiplayerGameOverDialog(self.screen, self.font, "defeat")
        self.result_sent = True
        return game_over

    def handle_mouse_result(
        self,
        event: pygame.event.Event,
        result: str | None,
        game: GameSession,
    ) -> None:
        if result == "attack" and self.client is not None:
            self.panel_open = not self.panel_open
            self._keep_available_element_selected(game)

    def handle_panel_click(self, event: pygame.event.Event, game: GameSession) -> bool:
        if (
            not self.panel_open
            or self.client is None
            or event.type != pygame.MOUSEBUTTONDOWN
            or event.button != 1
            or not multiplayer_attack_panel_rect(self.screen).collidepoint(event.pos)
        ):
            return False
        self._handle_attack_click(event, game)
        return True

    def handle_key_event(self, event: pygame.event.Event, game: GameSession) -> bool:
        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_v
            and self.client is not None
            and game.seed_tier_reward is None
        ):
            self.panel_open = not self.panel_open
            self._keep_available_element_selected(game)
            return True
        if (
            not self.panel_open
            or event.type != pygame.KEYDOWN
            or game.seed_tier_reward is not None
        ):
            return False
        if event.key in (pygame.K_ESCAPE, pygame.K_v):
            self.panel_open = False
        elif event.key in (pygame.K_q, pygame.K_e):
            self._cycle_element(game, -1 if event.key == pygame.K_q else 1)
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            action = {
                pygame.K_1: "extra_enemies",
                pygame.K_2: "tougher_enemies",
                pygame.K_3: "elemental_chance",
                pygame.K_4: "change_weather",
            }[event.key]
            self._send_attack(action, game)
        return True

    def close_connection(self) -> None:
        if self.client is not None:
            self.client.close()
        self.client = None
        self.menus.multiplayer_client = None

    def attach_menu_client(self) -> None:
        self.client = self._client_from_menu()

    def _client_from_menu(self) -> MultiplayerClient | None:
        if self.menus.game_mode == "multiplayer":
            return self.menus.multiplayer_client
        return None

    def _apply_opponent_action(self, payload: dict) -> None:
        action = payload["action"]
        element_name = payload.get("element")
        if action == "extra_enemies":
            self.pending_extra_enemies += 4
            self.status = "Opponent sent extra enemies."
        elif action == "tougher_enemies":
            self.pending_health_multiplier += 0.5
            self.status = "Opponent toughened the next wave."
        elif action in ("elemental_chance", "change_weather"):
            if not isinstance(element_name, str):
                return
            element = CropType.__members__.get(element_name)
            if element is None:
                return
            if action == "elemental_chance":
                self.pending_elemental_bias[element] = (
                    self.pending_elemental_bias.get(element, 0) + 1
                )
                self.status = f"Next wave has more {element_name.lower()} enemies."
            else:
                self.pending_weather = (
                    WeatherTypes.WINDS
                    if element_name == "AIR"
                    else WeatherTypes[element_name]
                )
                self.status = (
                    f"Opponent changed next wave weather to {element_name.lower()}."
                )

    def _keep_available_element_selected(self, game: GameSession) -> None:
        available = self._available_elements(game)
        if self.selected_element not in available:
            self.selected_element = available[0] if available else None

    @staticmethod
    def _available_elements(game: GameSession) -> list[CropType]:
        return [crop for crop, count in game.player.crops.items() if count > 0]

    def _cycle_element(self, game: GameSession, step: int) -> None:
        available = self._available_elements(game)
        if not available:
            return
        current = (
            available.index(self.selected_element)
            if self.selected_element in available
            else 0
        )
        self.selected_element = available[(current + step) % len(available)]

    def _handle_attack_click(
        self,
        event: pygame.event.Event,
        game: GameSession,
    ) -> None:
        panel = multiplayer_attack_panel_rect(self.screen)
        actions = (
            "extra_enemies",
            "tougher_enemies",
            "elemental_chance",
            "change_weather",
        )
        for index, action in enumerate(actions):
            row = pygame.Rect(
                panel.x + 10,
                panel.y + 104 + index * 42,
                panel.width - 20,
                36,
            )
            if row.collidepoint(event.pos):
                self._send_attack(action, game)
                return

    def _send_attack(self, action: str, game: GameSession) -> None:
        self.status = send_multiplayer_attack(
            action,
            self.selected_element,
            game.player,
            self.client,
            self.costs,
        )
