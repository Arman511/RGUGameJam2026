import os
import random
from typing import ClassVar

import pygame
from elemental_game.config import IMAGES_DIR, WINDOW_WIDTH
from elemental_game.game_entities.enemies.enemies import OPPOSING_ELEMENTS
from elemental_game.types.crop import CropType
from elemental_game.types.weather import WeatherTypes

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
    if wave_number % 3 == 0:
        regulars = ["runner"] * max(2, wave_number // 2) + ["brute"] * max(
            2, wave_number // 3
        )
        elites = ["elite_fire", "elite_earth"][: max(1, wave_number // 10)]
        wave = ["boss", *elites, *regulars]
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
