"""Run the frame loop and delegate focused work to game subsystems."""

import pygame

from elemental_game.application.multiplayer import MultiplayerController
from elemental_game.application.session import GameSession
from elemental_game.audio import handle_background_music_end_event
from elemental_game.game_entities.enemies import load_enemy_images
from elemental_game.menus import MenuSystem
from elemental_game.screen_rendering.game import GameScreenRenderer
from elemental_game.screen_rendering.game_over import GameOverDialog
from elemental_game.screen_rendering.multiplayer_game_over import (
    MultiplayerGameOverDialog,
)


class GameLoop:
    """Own frame timing, event routing, and rendering for a single game run."""

    def __init__(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        clock: pygame.time.Clock,
        menus: MenuSystem,
    ) -> None:
        self.screen = screen
        self.font = font
        self.clock = clock
        self.menus = menus
        self.game = GameSession(screen, menus.store.player_image_number())
        self._apply_manual_turret_sensitivity()
        self.enemy_images = load_enemy_images()
        self.renderer = GameScreenRenderer(screen, font, self.enemy_images)
        self.multiplayer = MultiplayerController(screen, font, menus, self.game)
        self.game_over: GameOverDialog | MultiplayerGameOverDialog | None = None
        self.running = True

    def run(self) -> None:
        self.clock.tick()
        while self.running:
            self._show_single_player_game_over()
            seconds = self.clock.tick(60) / 1000
            self.game_over = self.multiplayer.poll(self.game_over)
            self.game_over = self.multiplayer.finish_match_if_needed(
                self.game, self.game_over
            )
            tile = self.game.farm.tile_at_pixel(*self.game.player.pos)
            self.multiplayer.costs.set_phase(
                self.game.wave_number, self.game.planting_phase
            )
            self._handle_events()
            if not self.running:
                break
            self._update(seconds)
            self._draw(tile)
        self.multiplayer.close_connection()

    def _show_single_player_game_over(self) -> None:
        if (
            self.game.house.health <= 0
            and self.game_over is None
            and self.multiplayer.client is None
        ):
            self.game_over = GameOverDialog(
                self.screen,
                self.font,
                self.menus,
                run_id=self.game.run_id,
                survival_time=self.game.run_elapsed,
                final_wave=self.game.wave_number,
                enemies_defeated=self.game.enemies_defeated,
            )

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if handle_background_music_end_event(
                event, volume=self.menus.preferences["music_volume"]
            ):
                continue
            if (
                self.game_over is None
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                self._handle_mouse_click(event)
                continue
            if self.game.confirm_exit and event.type == pygame.KEYDOWN:
                self._handle_exit_confirmation(event)
                continue
            if self.game_over is not None:
                self._handle_game_over_event(event)
                if not self.running:
                    return
                continue
            if self.multiplayer.handle_key_event(event, self.game):
                continue
            self.game.handle_event(event)

    def _handle_mouse_click(self, event: pygame.event.Event) -> None:
        if (
            self.game.seed_tier_reward is None
            and not self.game.shop_open
            and self.multiplayer.handle_panel_click(event, self.game)
        ):
            return
        result = self.game.handle_mouse_event(event, self.renderer.quick_action_buttons)
        self.multiplayer.handle_mouse_result(event, result, self.game)

    def _handle_exit_confirmation(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_y, pygame.K_RETURN):
            self.game.confirm_exit = False
            self._return_to_menu()
        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
            self.game.confirm_exit = False

    def _handle_game_over_event(self, event: pygame.event.Event) -> None:
        if self.game_over is None:
            return
        self.game_over.handle_event(event)
        if self.game_over.done:
            self.game_over = None
            self._return_to_menu()

    def _return_to_menu(self) -> None:
        self.multiplayer.close_connection()
        self.running = self.menus.run()
        if self.running:
            self.multiplayer.attach_menu_client()
            self._reset_run()
        self.clock.tick()

    def _reset_run(self) -> None:
        self.game.reset(self.menus.store.player_image_number())
        self._apply_manual_turret_sensitivity()
        self.game_over = None
        self.multiplayer.reset_run(self.game)

    def _apply_manual_turret_sensitivity(self) -> None:
        sensitivity = self.menus.store.manual_turret_sensitivity()
        self.game.house.turret.rotation_speed = 30.0 + sensitivity * 240.0

    def _update(self, seconds: float) -> None:
        paused = (
            (self.multiplayer.client is None and self.game.single_player_menu_paused)
            or self.game.seed_tier_reward is not None
            or self.game.house.health <= 0
            or self.game_over is not None
        )
        self.game.update(
            seconds,
            paused=paused,
            music_volume=self.menus.preferences["music_volume"],
            pending_extra_enemies=self.multiplayer.pending_extra_enemies,
            pending_health_multiplier=self.multiplayer.pending_health_multiplier,
            pending_elemental_bias=self.multiplayer.pending_elemental_bias,
            pending_weather=self.multiplayer.pending_weather,
            on_wave_started=self.multiplayer.notify_wave_started,
        )

    def _draw(self, tile: tuple[int, int] | None) -> None:
        self.renderer.draw(
            farm=self.game.farm,
            player=self.game.player,
            house=self.game.house,
            turrets=self.game.turrets,
            waves=self.game.waves,
            enemies=self.game.enemies,
            enemy_images=self.enemy_images,
            tile=tile,
            planting_phase=self.game.planting_phase,
            phase_remaining=self.game.phase_remaining,
            wave_number=self.game.wave_number,
            enemies_defeated=self.game.enemies_defeated,
            controlling_house_turret=self.game.controlling_house_turret,
            multiplayer=self.multiplayer.client,
            multiplayer_status=self.multiplayer.status,
            hud_visible=self.game.hud_visible,
            hints_enabled=self.menus.hints_enabled,
            multiplayer_panel_open=self.multiplayer.panel_open,
            selected_attack_element=self.multiplayer.selected_element,
            shop_open=self.game.shop_open,
            shop=self.game.shop,
            confirm_exit=self.game.confirm_exit,
            game_over_dialog=self.game_over,
            attack_costs=self.multiplayer.costs.costs(),
            seed_tier_reward=self.game.seed_tier_reward,
        )
        pygame.display.flip()
