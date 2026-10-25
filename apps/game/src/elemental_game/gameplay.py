from __future__ import annotations

import math
from collections.abc import Callable
from uuid import uuid4

import pygame

from elemental_game import config
from elemental_game.audio import play_background_music
from elemental_game.game_entities.enemies.enemies import (
    EnemyState,
    roll_enemy_seed_drop,
)
from elemental_game.game_entities.enemies.waves import Waves, build_wave_sequence
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
        self.enemies: list[EnemyState] = []
        self.shop_open = False
        self.hud_visible = False
        self.confirm_exit = False
        self.planting_phase = True
        self.phase_remaining = config.PLANTING_PHASE_DURATION
        self.wave_number = 0
        self.wave_sequence: list[str] = []
        self.wave_spawned = 0
        self.wave_elapsed = 0.0
        self.controlling_house_turret = False
        self.run_id = uuid4().hex
        self.run_elapsed = 0.0
        self.enemies_defeated = 0
        self.active_health_multiplier = 1.0

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
        elif self.shop_open and event.type in (pygame.KEYDOWN, pygame.MOUSEWHEEL):
            if (
                event.type == pygame.KEYDOWN
                and event.key in (pygame.K_ESCAPE, pygame.K_m)
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

    @property
    def game_over(self) -> bool:
        return self.house.health <= 0

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

        self.phase_remaining -= seconds
        if self.planting_phase:
            self._start_wave(
                music_volume,
                pending_extra_enemies,
                pending_health_multiplier,
                pending_elemental_bias,
                pending_weather,
                on_wave_started,
            )
        else:
            self._spawn_wave_enemies(seconds)
            if self.phase_remaining <= 0 and not self.enemies:
                self.planting_phase = True
                self.phase_remaining = config.PLANTING_PHASE_DURATION
                play_background_music(volume=music_volume)

        self._update_combat(seconds)

    def _start_wave(
        self,
        music_volume: float,
        extra_enemies: int,
        health_multiplier: float,
        elemental_biases: dict[CropType, int] | None,
        weather: WeatherTypes | None,
        on_wave_started: Callable[[int], None] | None,
    ) -> None:
        if self.phase_remaining > 0:
            return

        self.planting_phase = False
        self.wave_number += 1
        self.waves.new_wave()
        if weather is not None:
            self.waves.state = weather
        self.farm.weather_crop_type = self.waves.crop_type
        self.active_health_multiplier = health_multiplier
        self.wave_sequence = build_wave_sequence(
            self.wave_number,
            self.waves.state,
            extra_enemies=extra_enemies,
            elemental_biases=elemental_biases,
        )
        if on_wave_started is not None:
            on_wave_started(self.wave_number)
        play_background_music(
            "boss" if self.wave_number % 3 == 0 else "enemies",
            volume=music_volume,
        )
        self.wave_spawned = 0
        self.wave_elapsed = 0.0
        self.phase_remaining = config.ENEMY_WAVE_DURATION

    def _spawn_wave_enemies(self, seconds: float) -> None:
        self.wave_elapsed += seconds
        target_spawn_count = min(
            len(self.wave_sequence),
            int(self.wave_elapsed / config.ENEMY_WAVE_DURATION * len(self.wave_sequence))
            + 1,
        )
        while self.wave_spawned < target_spawn_count:
            key = self.wave_sequence[self.wave_spawned]
            spawn_y = min(
                self.screen.get_height() - 55,
                max(
                    80,
                    self.house.return_rect().centery
                    + (self.wave_spawned % 5 - 2) * 65,
                ),
            )
            spawn_x = (
                -30
                if self.wave_spawned % 2 == 0
                else self.screen.get_width() + 30
            )
            enemy = EnemyState.create(key, (spawn_x, spawn_y))
            if self.active_health_multiplier > 1:
                enemy.max_health = math.ceil(
                    enemy.max_health * self.active_health_multiplier
                )
                enemy.health = enemy.max_health
            self.enemies.append(enemy)
            self.wave_spawned += 1

    def _update_combat(self, seconds: float) -> None:
        self.turrets.update(seconds, self.enemies)
        house_turret = self.house.turret
        keys = pygame.key.get_pressed()
        if self.controlling_house_turret:
            rotate_direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
                keys[pygame.K_LEFT] or keys[pygame.K_a]
            )
        else:
            rotate_direction = 0
        house_rect = self.house.return_rect()
        house_turret.update(
            seconds,
            self.enemies,
            (house_rect.centerx, house_rect.y + 24),
            rotate_direction,
            self.controlling_house_turret and keys[pygame.K_SPACE],
            self.screen.get_rect(),
        )

        for enemy in self.enemies:
            if enemy.health <= 0:
                continue
            enemy.update_status_effects(seconds)
            enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - seconds)
            destination = pygame.Vector2(house_rect.center)
            boss_slot = (
                self.turrets.boss_target(enemy.pos, destination)
                if enemy.is_boss
                else None
            )
            if boss_slot is not None:
                destination = pygame.Vector2(boss_slot.center)
                if enemy.pos.distance_to(destination) <= 44:
                    if enemy.attack_cooldown <= 0:
                        self.turrets.damage_slot(boss_slot, enemy.damage * 2)
                        enemy.attack_cooldown = 1.0
                else:
                    enemy.move_towards(destination, seconds)
                continue
            if enemy.pos.distance_to(destination) > 55:
                enemy.move_towards(destination, seconds)
            elif enemy.attack_cooldown <= 0:
                self.house.take_damage(enemy.damage)
                enemy.attack_cooldown = 1.0

        survivors = []
        for enemy in self.enemies:
            if enemy.health <= 0:
                self.player.coins += enemy.reward
                self.enemies_defeated += 1
                seed_amount = math.ceil(config.ENEMY_SEED_DROP_MULTIPLIER)
                if seed_amount > 0:
                    seed_type, seed_tier = roll_enemy_seed_drop(enemy)
                    self.player.add_seed(seed_type, seed_tier, seed_amount)
            else:
                survivors.append(enemy)
        self.enemies = survivors