from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self, image, width, height):
        # attributes for player creation:
        self.image = image  # path to assets folder, list
        self.width = width
        self.height = height
        self.pos = (0, 0)
        self.water_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.fire_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.earth_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.air_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.lightning_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.ice_seed = {"tier1": 0, "tier2": 0, "tier3": 0}
        self.coins = 0
