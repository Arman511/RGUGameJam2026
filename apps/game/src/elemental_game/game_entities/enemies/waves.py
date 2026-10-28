import math
import os
import random
from dataclasses import dataclass
from typing import ClassVar

import pygame
from elemental_game import config
from elemental_game.config import IMAGES_DIR, WINDOW_WIDTH
from elemental_game.game_entities.enemies import (
    ENEMY_DEFS,
    OPPOSING_ELEMENTS,
    EnemyState,
)
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.weather import WeatherTypes

WEATHER_CROP_TYPES = {
    WeatherTypes.FIRE: CropType.FIRE,
    WeatherTypes.EARTH: CropType.EARTH,
    WeatherTypes.ICE: CropType.ICE,
    WeatherTypes.LIGHTNING: CropType.LIGHTNING,
    WeatherTypes.WATER: CropType.WATER,
    WeatherTypes.WINDS: CropType.AIR,
}
ENEMY_KEYS_BY_ELEMENT = {
    CropType.FIRE: "fire",
    CropType.WATER: "water",
    CropType.LIGHTNING: "lightning",
    CropType.EARTH: "brute",
    CropType.ICE: "ice",
    CropType.AIR: "runner",
}
ENEMY_GROWTH_RATE = 1.08
ENEMY_HEALTH_GROWTH_RATE = 1.06
BOSS_KEYS = frozenset({"boss", "big_boss"})


@dataclass(frozen=True)
class WaveUpdate:
    started_wave: int | None = None
    spawned_enemies: tuple[EnemyState, ...] = ()
    completed: bool = False


def build_wave_sequence(
    wave_number: int,
    weather: WeatherTypes | None = None,
    *,
    extra_enemies: int = 0,
    elemental_bias: CropType | None = None,
    elemental_biases: dict[CropType, int] | None = None,
) -> list[str]:
    if wave_number < 1:
        raise ValueError("wave_number must be positive")
    if extra_enemies < 0:
        raise ValueError("extra_enemies cannot be negative")
    if wave_number >= 3:
        normal_bosses = ["boss"] * max(1, wave_number // 10)
        big_bosses = ["big_boss"] if wave_number > 3 and wave_number % 3 == 0 else []
        regulars = ["runner"] * max(2, wave_number // 2) + ["brute"] * max(
            2, wave_number // 3
        )
        elites = ["elite_fire", "elite_earth"][: max(1, wave_number // 10)]
        wave = [*normal_bosses, *big_bosses, *elites, *regulars]
    elif wave_number == 1:
        wave = ["swarmer", "swarmer", "swarmer"]
    elif wave_number == 2:
        wave = ["swarmer"] * 4 + ["brute"]
    else:
        swarmers = max(2, 7 - wave_number)
        runners = 2 + wave_number
        brutes = 1 + wave_number // 2
        wave = ["swarmer"] * swarmers + ["runner"] * runners + ["brute"] * brutes
        elite_types = (
            "elite_fire",
            "elite_water",
            "elite_earth",
            "elite_air",
            "elite_lightning",
        )

        wave.extend(
            [elite_types[(wave_number - 3) % len(elite_types)]] * (1 + wave_number // 4)
        )
    bosses = [enemy for enemy in wave if enemy in BOSS_KEYS]
    non_boss_enemies = [enemy for enemy in wave if enemy not in BOSS_KEYS]
    target_count = math.ceil(
        len(non_boss_enemies) * ENEMY_GROWTH_RATE ** (wave_number - 1)
    )
    if non_boss_enemies:
        wave = bosses + [
            non_boss_enemies[index % len(non_boss_enemies)]
            for index in range(target_count)
        ]
    if weather is not None:
        crop_type = WEATHER_CROP_TYPES[weather]
        counter_element = OPPOSING_ELEMENTS[crop_type]
        counter_enemy = ENEMY_KEYS_BY_ELEMENT[counter_element]
        wave.extend([counter_enemy] * max(1, len(wave) // 3))
    bias_counts = dict(elemental_biases or {})
    if elemental_bias is not None:
        bias_counts[elemental_bias] = bias_counts.get(elemental_bias, 0) + 1
    elemental_enemy_count = max(1, (len(wave) + 1) // 2)
    for element, count in bias_counts.items():
        if (
            element not in ENEMY_KEYS_BY_ELEMENT
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise ValueError("elemental_biases must contain valid elements and counts.")
        wave.extend([ENEMY_KEYS_BY_ELEMENT[element]] * elemental_enemy_count * count)
    wave.extend(["swarmer"] * extra_enemies)
    return wave


class Waves:
    WEATHER: ClassVar[dict[WeatherTypes, str]] = {
        WeatherTypes.FIRE: os.path.join(IMAGES_DIR, "weather", "weather-fire.png"),
        WeatherTypes.EARTH: os.path.join(IMAGES_DIR, "weather", "weather-earth.png"),
        WeatherTypes.ICE: os.path.join(IMAGES_DIR, "weather", "weather-ice.png"),
        WeatherTypes.LIGHTNING: os.path.join(
            IMAGES_DIR, "weather", "weather-lightning.png"
        ),
        WeatherTypes.WATER: os.path.join(IMAGES_DIR, "weather", "weather-water.png"),
        WeatherTypes.WINDS: os.path.join(IMAGES_DIR, "weather", "weather-winds.png"),
    }

    def __init__(self, house):
        self.state = self.get_weather()
        self.alive = house.get_hp() > 0
        self.planting_phase = True
        self.phase_remaining = config.PLANTING_PHASE_DURATION
        self.wave_number = 0
        self.wave_sequence: list[str] = []
        self.wave_spawned = 0
        self.wave_elapsed = 0.0
        self.active_health_multiplier = 1.0

        self.dimensions = (55, 55)
        self.weather_images = {
            weather_state: pygame.transform.scale(
                pygame.image.load(image).convert_alpha(),
                self.dimensions,
            )
            for weather_state, image in self.WEATHER.items()
        }

    def get_weather(self):
        return random.choice(list(WeatherTypes))

    @property
    def crop_type(self) -> CropType:
        return WEATHER_CROP_TYPES[self.state]

    def draw_weather(self, surface, font):
        y = 72
        x = (WINDOW_WIDTH - self.dimensions[0]) - 28
        image = self.weather_images[self.state]
        image_rect = image.get_rect(topleft=(x, y))
        background_rect = image_rect.inflate(12, 12)
        pygame.draw.rect(surface, (28, 34, 46), background_rect, border_radius=8)
        pygame.draw.rect(surface, (210, 220, 235), background_rect, 1, border_radius=8)
        surface.blit(image, image_rect)

        label = font.render("Weather Forecast", True, (0, 0, 0))
        surface.blit(
            label,
            label.get_rect(
                midright=(background_rect.left - 10, background_rect.centery)
            ),
        )

    def new_wave(self):
        self.state = self.get_weather()

    def update(
        self,
        seconds: float,
        screen: pygame.Surface,
        house,
        enemy_count: int,
        *,
        extra_enemies: int = 0,
        health_multiplier: float = 1.0,
        elemental_biases: dict[CropType, int] | None = None,
        weather: WeatherTypes | None = None,
    ) -> WaveUpdate:
        self.phase_remaining -= seconds
        if self.planting_phase:
            return self._start_wave(
                extra_enemies,
                health_multiplier,
                elemental_biases,
                weather,
            )

        spawned_enemies = self._spawn_due_enemies(seconds, screen, house)
        completed = (
            self.phase_remaining <= 0 and enemy_count + len(spawned_enemies) == 0
        )
        if completed:
            self.planting_phase = True
            self.phase_remaining = config.PLANTING_PHASE_DURATION
        return WaveUpdate(spawned_enemies=tuple(spawned_enemies), completed=completed)

    def _start_wave(
        self,
        extra_enemies: int,
        health_multiplier: float,
        elemental_biases: dict[CropType, int] | None,
        weather: WeatherTypes | None,
    ) -> WaveUpdate:
        if self.phase_remaining > 0:
            return WaveUpdate()

        self.planting_phase = False
        self.wave_number += 1
        self.new_wave()
        if weather is not None:
            self.state = weather
        self.active_health_multiplier = health_multiplier
        self.wave_sequence = build_wave_sequence(
            self.wave_number,
            self.state,
            extra_enemies=extra_enemies,
            elemental_biases=elemental_biases,
        )
        self.wave_spawned = 0
        self.wave_elapsed = 0.0
        self.phase_remaining = config.ENEMY_WAVE_DURATION
        return WaveUpdate(started_wave=self.wave_number)

    def _spawn_due_enemies(
        self,
        seconds: float,
        screen: pygame.Surface,
        house,
    ) -> list[EnemyState]:
        self.wave_elapsed += seconds
        target_spawn_count = min(
            len(self.wave_sequence),
            int(
                self.wave_elapsed / config.ENEMY_WAVE_DURATION * len(self.wave_sequence)
            )
            + 1,
        )
        house_center_y = house.return_rect().centery
        spawned_enemies = []
        while self.wave_spawned < target_spawn_count:
            spawn_y = min(
                screen.get_height() - 55,
                max(80, house_center_y + (self.wave_spawned % 5 - 2) * 65),
            )
            enemy_key = self.wave_sequence[self.wave_spawned]
            if ENEMY_DEFS[enemy_key].is_boss:
                spawn_x = random.choice((-30, screen.get_width() + 30))
            else:
                spawn_x = -30 if self.wave_spawned % 2 == 0 else screen.get_width() + 30
            enemy = EnemyState.create(
                enemy_key,
                (spawn_x, spawn_y),
                wave_number=self.wave_number,
            )
            enemy.spawn_side = "left" if spawn_x < 0 else "right"
            health_multiplier = self.active_health_multiplier * (
                ENEMY_HEALTH_GROWTH_RATE ** (self.wave_number - 1)
            )
            if health_multiplier > 1:
                enemy.max_health = math.ceil(enemy.max_health * health_multiplier)
                enemy.health = enemy.max_health
            spawned_enemies.append(enemy)
            self.wave_spawned += 1
        return spawned_enemies
