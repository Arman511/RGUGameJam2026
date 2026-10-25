import os
import random
from typing import ClassVar

import pygame
from elemental_game.config import IMAGES_DIR, WINDOW_WIDTH
from elemental_game.types.weather import WeatherTypes


def build_wave_sequence(wave_number: int) -> list[str]:
    if wave_number < 1:
        raise ValueError("wave_number must be positive")
    if wave_number % 5 == 0:
        regulars = ["runner"] * max(2, wave_number // 2) + ["brute"] * max(
            2, wave_number // 3
        )
        elites = ["elite_fire", "elite_earth"][: max(1, wave_number // 10)]
        return ["boss", *elites, *regulars]
    if wave_number == 1:
        return ["swarmer", "swarmer", "swarmer"]
    if wave_number == 2:
        return ["swarmer"] * 4 + ["brute"] * 1
    swarmers = max(2, 7 - wave_number)
    runners = 2 + wave_number
    brutes = 1 + wave_number // 2
    wave = ["swarmer"] * swarmers + ["runner"] * runners + ["brute"] * brutes
    if wave_number >= 3:
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

    def draw_weather(self, surface):
        y = 60
        x = (WINDOW_WIDTH - self.dimensions[0]) - 40
        surface.blit(self.weather_images[self.state], (x, y))

    def new_wave(self):
        self.state = self.get_weather()
