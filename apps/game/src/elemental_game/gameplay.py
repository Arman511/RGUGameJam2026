from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pygame

from elemental_game import config
from elemental_game.audio import play_background_music
from elemental_game.game_entities.enemies.enemies import (
    EnemyController,
)
from elemental_game.game_entities.enemies.waves import Waves
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.house import House
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.shop import ShopMenu
from elemental_game.game_entities.turrets.turrets import TurretSystem
from elemental_game.types.crop import CropType
from elemental_game.types.player import PlayerType
from elemental_game.types.weather import WeatherTypes


class GameSession:
    def __init__(self, screen: pygame.Surface, player_type: int) -> None:
        self.screen = screen
        self.reset(player_type)

    def reset(self, player_type: int) -> None:
        self.farm = Farm(
            *config.FARM_DIMENSIONS,
            origin=(
                (
                    self.screen.get_width()
                    - config.FARM_DIMENSIONS[1] * config.TILE_SIZE
                )
                // 2,
                config.FARM_HEIGHT,
            ),
        )
        self.player = Player(
            player_type=PlayerType(player_type),
            pos=self.farm.tile_rect(0, 5).center,
        )
        self.shop = ShopMenu()
        self.house = House(self.screen)
        self.turrets = TurretSystem(self.farm)
        self.waves = Waves(self.house)
        self.farm.weather_crop_type = self.waves.crop_type
        self.enemies = []
        self.shop_open = False
        self.hud_visible = False
        self.confirm_exit = False
        self.controlling_house_turret = False
        self.run_id = uuid4().hex
        self.run_elapsed = 0.0
        self.enemies_defeated = 0

    @property
    def planting_phase(self) -> bool:
        return self.waves.planting_phase

    @property
    def phase_remaining(self) -> float:
        return self.waves.phase_remaining

    @property
    def wave_number(self) -> int:
        return self.waves.wave_number

    @property
    def game_over(self) -> bool:
        return self.house.health <= 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            if not self.farm.planting:
                self.hud_visible = not self.hud_visible
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_o:
            self.turrets.show_ranges = not self.turrets.show_ranges
        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_r
            and not self.farm.planting
            and not self.shop_open
            and not self.confirm_exit
            and self.turrets.modal_slot is None
            and not self.controlling_house_turret
        ):
            self.player.cycle_plant_radius()
        elif self.turrets.modal_slot is not None:
            self.turrets.handle_event(event, self.player, self.screen)
        elif self.controlling_house_turret and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_f, pygame.K_ESCAPE):
                self.controlling_house_turret = False
        elif self.shop_open and event.type == pygame.KEYDOWN:
            if (
                event.key in (pygame.K_ESCAPE, pygame.K_m)
                and not self.shop.selecting_quadrant
            ):
                self.shop_open = False
                self.shop.clear_status()
            else:
                self.shop.handle_event(
                    event, self.player, self.farm, self.house, self.screen
                )
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            roof = self.house.turret_control_rect()
            if roof.collidepoint(self.player.pos):
                self.controlling_house_turret = True
            elif self.farm.planting or not self.turrets.interact(self.player):
                self.farm.handle_event(event, self.player)
        elif event.type == pygame.KEYDOWN and self.farm.planting:
            self.farm.handle_event(event, self.player)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.confirm_exit = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.shop_open = True
            self.shop.clear_status()
        elif event.type == pygame.KEYDOWN:
            self.farm.handle_event(event, self.player)

    def update(
        self,
        seconds: float,
        *,
        paused: bool,
        music_volume: float,
        pending_extra_enemies: int = 0,
        pending_health_multiplier: float = 1.0,
        pending_elemental_bias: dict[CropType, int] | None = None,
        pending_weather: WeatherTypes | None = None,
        on_wave_started: Callable[[int], None] | None = None,
    ) -> None:
        if not paused and not self.game_over:
            self.run_elapsed += seconds
        if not paused and not self.controlling_house_turret:
            self.player.update(seconds)
        self.farm.update(seconds)
        self.shop.update(seconds)

        if paused:
            return

        wave_update = self.waves.update(
            seconds,
            self.screen,
            self.house,
            len(self.enemies),
            extra_enemies=pending_extra_enemies,
            health_multiplier=pending_health_multiplier,
            elemental_biases=pending_elemental_bias,
            weather=pending_weather,
        )
        self.enemies.extend(wave_update.spawned_enemies)
        self.farm.weather_crop_type = self.waves.crop_type
        if wave_update.started_wave is not None:
            if on_wave_started is not None:
                on_wave_started(wave_update.started_wave)
            play_background_music(
                "boss" if wave_update.started_wave % 3 == 0 else "enemies",
                volume=music_volume,
            )
        elif wave_update.completed:
            play_background_music(volume=music_volume)

        self.enemies, defeated = EnemyController.update(
            seconds,
            self.enemies,
            self.house,
            self.turrets,
            self.player,
            self.screen,
            self.controlling_house_turret,
        )
        self.enemies_defeated += defeated