from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self, image, width, height):
        # attributes for player creation:
        self.image = image  # path to assets folder, list
        self.width = width
        self.height = height
        self.pos = (0, 0)
