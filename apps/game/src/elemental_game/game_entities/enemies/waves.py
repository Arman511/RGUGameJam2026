import random
from enum import Enum
import os
import pygame
from elemental_game.config import IMAGES_DIR, WINDOW_HEIGHT, WINDOW_WIDTH

class WeatherTypes(Enum):
    FIRE = 1
    EARTH = 2
    ICE = 3
    LIGHTNING = 4
    WATER = 5
    WINDS = 6

class Waves:

    WEATHER = {WeatherTypes.FIRE: os.path.join(IMAGES_DIR, "weather", "weather-fire.png"),
               WeatherTypes.EARTH: os.path.join(IMAGES_DIR, "weather", "weather-earth.png"),
               WeatherTypes.ICE: os.path.join(IMAGES_DIR, "weather", "weather-ice.png"),
               WeatherTypes.LIGHTNING: os.path.join(IMAGES_DIR, "weather", "weather-lightning.png"),
               WeatherTypes.WATER: os.path.join(IMAGES_DIR, "weather", "weather-water.png"),
               WeatherTypes.WINDS: os.path.join(IMAGES_DIR, "weather", "weather-winds.png")}

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