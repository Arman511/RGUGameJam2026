"""
Defines Enemy class and Enemy type sub classes

Attributes and behaviour specific to the enemy
"""

from abc import ABC, abstractmethod

class Enemy(ABC):
    def __init__(self, id, max_hp, speed, damage, image, width, height, resistance):
        # attributes for enemy creation:
        self.enemy_id = id
        self.max_hp = max_hp
        self.speed = speed
        self.damage = damage # damage the enemy does
        self.image = image # path to assets folder, list
        self.resistance = resistance
        self.width = width
        self.height = height

        # dynamic attributes
        self.pos = (0, 0) # starting pos for now
        self.current_hp = self.max_hp

    def approach_farm(self, destination_coord):
        # function that makes enemy move to farm
        # makes enemy attack things
        pass

    def is_alive(self):
        return self.current_hp > 0

    def take_damage(self, damage_done):
        # change to consider resistance, might end up abstract method
        self.current_hp -= damage_done

    def die(self):
        # enemy is removed from screen
        pass

    @abstractmethod
    def attack(self):
        """Every enemy type must define what happens when it attacks."""


"""
Create new enemy objects with the below classes
"""

class Swarmer(Enemy):
    def __init__(self, id, image): # other stats are fixed
        super().__init__(id, 10, 70, 5, image, 50, 70, None)

    def attack(self):
        pass