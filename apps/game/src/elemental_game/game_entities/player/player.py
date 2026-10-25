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

    def __init__(self, pos, player_type: PlayerType = PlayerType.WATER):
        self.width = 70
        self.height = 70
        self.player_type = player_type
        image = pygame.image.load(player_type.full_image_path).convert_alpha()
        self.image = pygame.transform.scale(image, (self.width, self.height))
        self.pos = pygame.Vector2(pos)  # centre of the player
        self.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
        self.seeds = {seed_type: {"tier1": 0} for seed_type in SeedType}
        self.seed_sale_coin_thirds = 0
        self.coins = 5
        self.crops = {}
        self.unlocked_quadrants = set(self.STARTING_UNLOCKED_QUADRANTS)
        self.turret_slots_unlocked = 0
        self.harvest_size = 1
        self.plant_radius = 1
        self.plant_radius_active = 1

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
        if isinstance(tier, str) and tier.startswith("tier"):
            tier = int(tier[4:])
        if not isinstance(tier, int) or isinstance(tier, bool) or tier < 1:
            raise ValueError(f"Invalid tier: {tier}")
        tier_key = f"tier{tier}"
        self.seeds[seed_type].setdefault(tier_key, 0)
        self.seeds[seed_type][tier_key] += amount

    @staticmethod
    def seed_tier_cost(tier: int) -> int:
        if not isinstance(tier, int) or isinstance(tier, bool) or tier < 1:
            raise ValueError(f"Invalid tier: {tier}")
        return 2 ** (tier - 1)

    def max_unlocked_seed_tier(self, seed_type: SeedType) -> int:
        return getattr(self, "unlocked_seed_tiers", {}).get(seed_type, 1)

    def unlock_next_seed_tier(self, seed_type: SeedType) -> int:
        if seed_type not in self.seeds:
            raise ValueError(f"Invalid seed_type: {seed_type}")
        next_tier = self.max_unlocked_seed_tier(seed_type) + 1
        self.unlocked_seed_tiers[seed_type] = next_tier
        self.seeds[seed_type].setdefault(f"tier{next_tier}", 0)
        return next_tier

    def buy_seed(self, seed_type, tier, amount=1):
        if (
            seed_type not in self.seeds
            or not isinstance(tier, int)
            or isinstance(tier, bool)
            or tier < 1
            or tier > self.max_unlocked_seed_tier(seed_type)
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount < 1
        ):
            return False
        cost = self.seed_tier_cost(tier) * amount
        if self.coins < cost:
            return False

        self.coins -= cost
        self.add_seed(seed_type, f"tier{tier}", amount)
        return True

    def consume_seed(self, seed_type, tier):
        tier_key = f"tier{tier}"
        if seed_type not in self.seeds or tier_key not in self.seeds[seed_type]:
            return False
        if self.seeds[seed_type][tier_key] <= 0:
            return False

        self.seeds[seed_type][tier_key] -= 1
        return True

    def sell_crop(self, crop_type, amount=1) -> int:
        available = self.crops.get(crop_type, 0)
        if available < amount or amount <= 0:
            return 0

        self.crops[crop_type] -= amount
        self.coins += amount * 3
        return amount

    def sell_all_crops(self) -> int:
        sold_count = sum(self.crops.values())
        if sold_count:
            self.coins += sold_count * 3
            for crop_type in self.crops:
                self.crops[crop_type] = 0
        return sold_count

    def sell_seed(self, seed_type: SeedType, tier: int, amount: int = 1) -> int:
        tier_key = f"tier{tier}"
        if (
            seed_type not in self.seeds
            or not isinstance(tier, int)
            or isinstance(tier, bool)
            or tier < 1
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount < 1
            or self.seeds[seed_type].get(tier_key, 0) < amount
        ):
            return 0

        total_thirds = getattr(
            self, "seed_sale_coin_thirds", 0
        ) + amount * self.seed_tier_cost(tier)
        proceeds, self.seed_sale_coin_thirds = divmod(total_thirds, 3)
        self.seeds[seed_type][tier_key] -= amount
        self.coins += proceeds
        return proceeds

    def seed_sale_proceeds(self, tier: int, amount: int = 1) -> int:
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            return 0
        total_thirds = getattr(
            self, "seed_sale_coin_thirds", 0
        ) + amount * self.seed_tier_cost(tier)
        return total_thirds // 3

    def cycle_plant_radius(self) -> int:
        self.plant_radius_active = (
            self.plant_radius_active % max(1, self.plant_radius) + 1
        )
        return self.plant_radius_active

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
        self.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
        self.seeds = {seed_type: {"tier1": 0} for seed_type in SeedType}
        self.seed_sale_coin_thirds = 0
        self.coins = 5
        self.crops = {}
        self.unlocked_quadrants = set(self.STARTING_UNLOCKED_QUADRANTS)
        self.turret_slots_unlocked = 0
        self.harvest_size = 1
        self.plant_radius = 1
        self.plant_radius_active = 1

    def can_afford(self, cost):
        return self.coins >= cost

    def deduct_coins(self, amount):
        if self.coins < amount:
            return False
        self.coins -= amount
        return True
