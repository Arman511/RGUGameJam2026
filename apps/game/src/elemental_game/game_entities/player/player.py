import pygame
from elemental_game import config
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType


class Player:
    SPEED = 165
    STARTING_UNLOCKED_QUADRANTS = frozenset({"top_right"})
    FARM_QUADRANT_UNLOCKS = (
        ("top_left", 10),
        ("bottom_left", 30),
        ("bottom_right", 60),
    )

    def __init__(self, pos=(150, 150), player_type: PlayerType = PlayerType.WATER):
        self.width = 70
        self.height = 70
        self.player_type = player_type
        image = pygame.image.load(player_type.full_image_path).convert_alpha()
        self.image = pygame.transform.scale(image, (self.width, self.height))
        self.pos = pygame.Vector2(pos)  # centre of the player
        self.seeds = {
            seed_type: {"tier1": 0, "tier2": 0, "tier3": 0} for seed_type in SeedType
        }
        self.coins = 5
        self.crops = {}
        self.unlocked_quadrants = set(self.STARTING_UNLOCKED_QUADRANTS)
        self.turret_slots_unlocked = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            (keys[pygame.K_RIGHT] or keys[pygame.K_d])
            - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
            (keys[pygame.K_DOWN] or keys[pygame.K_s])
            - (keys[pygame.K_UP] or keys[pygame.K_w]),
        )
        if move.length() > 0:
            self.pos += (
                move.normalize() * self.SPEED * dt
            )  # normalize: no faster diagonally

    def draw(self, surface):  # placeholder until the sprite is loaded
        surface.blit(self.image, self.image.get_rect(center=self.pos))

    def add_crop(self, crop_type, amount):
        self.crops[crop_type] = self.crops.get(crop_type, 0) + amount

    def add_seed(self, seed_type, tier, amount):
        if seed_type not in self.seeds:
            raise ValueError(f"Invalid seed_type: {seed_type}")
        if tier not in self.seeds[seed_type]:
            raise ValueError(f"Invalid tier: {tier}")
        self.seeds[seed_type][tier] += amount

    def buy_seed(self, seed_type, tier):
        if seed_type not in self.seeds or tier not in (1, 2, 3):
            return False
        if self.coins < tier:
            return False

        self.coins -= tier
        self.add_seed(seed_type, f"tier{tier}", 1)
        return True

    def consume_seed(self, seed_type, tier):
        tier_key = f"tier{tier}"
        if seed_type not in self.seeds or tier_key not in self.seeds[seed_type]:
            return False
        if self.seeds[seed_type][tier_key] <= 0:
            return False

        self.seeds[seed_type][tier_key] -= 1
        return True

    def sell_crop(self, crop_type):
        if self.crops.get(crop_type, 0) <= 0:
            return False

        self.crops[crop_type] -= 1
        self.coins += 3
        return True

    def next_farm_quadrant_unlock(self):
        return next(
            (
                (quadrant, cost)
                for quadrant, cost in self.FARM_QUADRANT_UNLOCKS
                if quadrant not in self.unlocked_quadrants
            ),
            None,
        )

    def buy_next_farm_quadrant(self):
        unlock = self.next_farm_quadrant_unlock()
        if unlock is None:
            return False

        quadrant, cost = unlock
        if self.coins < cost:
            return False

        self.coins -= cost
        self.unlocked_quadrants.add(quadrant)
        return True

    def next_turret_slot_cost(self):
        unlocked = getattr(self, "turret_slots_unlocked", 0)
        if unlocked >= len(config.TURRET_SLOT_UNLOCK_COSTS):
            return None
        return config.TURRET_SLOT_UNLOCK_COSTS[unlocked]

    def buy_turret_slot(self):
        cost = self.next_turret_slot_cost()
        if cost is None or self.coins < cost:
            return False
        self.coins -= cost
        self.turret_slots_unlocked = getattr(self, "turret_slots_unlocked", 0) + 1
        return True

    def reset(self):
        self.seeds = {
            seed_type: {"tier1": 0, "tier2": 0, "tier3": 0} for seed_type in SeedType
        }
        self.coins = 5
        self.crops = {}
        self.unlocked_quadrants = set(self.STARTING_UNLOCKED_QUADRANTS)
        self.turret_slots_unlocked = 0

    def can_afford(self, cost):
        return self.coins >= cost

    def deduct_coins(self, amount):
        if self.coins < amount:
            return False
        self.coins -= amount
        return True
