from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pygame

from elemental_game import config
from elemental_game.audio import play_background_music
from elemental_game.game_entities.enemies.enemies import EnemyController
from elemental_game.game_entities.enemies.waves import Waves
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.house import House
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.seed_tier_reward import SeedTierReward
from elemental_game.game_entities.shop import ShopMenu
from elemental_game.game_entities.turrets.turrets import TurretSystem
from elemental_game.game_input import GameInputHandler
from elemental_game.types.crop import CropType
from elemental_game.types.player import PlayerType
from elemental_game.types.weather import WeatherTypes


class GameSession:
    def __init__(self, screen: pygame.Surface, player_type: int) -> None:
        self.screen = screen
        self.reset(player_type)
        self.input = GameInputHandler(self)

    def reset(self, player_type: int) -> None:
        farm_width = config.FARM_DIMENSIONS[1] * config.TILE_SIZE
        self.farm = Farm(
            *config.FARM_DIMENSIONS,
            origin=((self.screen.get_width() - farm_width) // 2, config.FARM_HEIGHT),
        )
        self.player = Player(
            player_type=PlayerType(player_type),
            pos=self.farm.tile_rect(0, 5).center,
        )
        self.shop, self.house = ShopMenu(), House(self.screen)
        self.turrets, self.waves = TurretSystem(self.farm), Waves(self.house)
        self.farm.weather_crop_type = self.waves.crop_type
        self.seed_tier_reward: SeedTierReward | None = None
        self.enemies = []
        self.shop_open = self.hud_visible = self.confirm_exit = False
        self.controlling_house_turret = False
        self.run_id, self.run_elapsed, self.enemies_defeated = uuid4().hex, 0.0, 0

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
        self.input.handle_event(event)

    def handle_mouse_event(self, event, quick_action_buttons) -> str | None:
        return self.input.handle_mouse_event(event, quick_action_buttons)

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
        if paused:
            return

        self.farm.update(seconds, grow_crops=self.planting_phase)
        self.shop.update(seconds)
        update = self.waves.update(
            seconds,
            self.screen,
            self.house,
            len(self.enemies),
            extra_enemies=pending_extra_enemies,
            health_multiplier=pending_health_multiplier,
            elemental_biases=pending_elemental_bias,
            weather=pending_weather,
        )
        self.enemies.extend(update.spawned_enemies)
        self.farm.weather_crop_type = self.waves.crop_type

        if update.started_wave is not None:
            if on_wave_started is not None:
                on_wave_started(update.started_wave)
            track = (
                "boss"
                if any(
                    enemy_key in {"boss", "big_boss"}
                    for enemy_key in self.waves.wave_sequence
                )
                else "enemies"
            )
            play_background_music(track, volume=music_volume)
        elif update.completed:
            play_background_music(volume=music_volume)
            if self.wave_number >= 3 and self.wave_number % 3 == 0:
                self.seed_tier_reward = SeedTierReward()

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
