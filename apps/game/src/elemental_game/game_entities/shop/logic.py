from collections.abc import Sequence

import pygame
from elemental_game.game_entities.farm import Farm
from elemental_game.types.crop import CropType
from elemental_game.types.seed import SeedType
from elemental_game.types.shop import (
    FertilizerUpgrade,
    HarvestSizeUpgrade,
    HouseUpgrade,
    LandUpgrade,
    PlantRadiusUpgrade,
    SellAllCrops,
    TurretSlotUpgrade,
    UpgradeOption,
)

from .renderer import ShopRenderer


class ShopMenu:
    ITEM_H = 30
    FERTILIZER_COST = 10
    STATUS_DURATION = 5.0
    HARVEST_SIZE_UPGRADE_COSTS = (20, 50, 100, 200, 300)
    PLANT_RADIUS_UPGRADE_COSTS = (50, 200)
    MAX_VISIBLE_UPGRADES = 11
    CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_f)
    MODES = ("buy", "upgrade", "sell")
    CROP_TYPES = (
        CropType.FIRE,
        CropType.WATER,
        CropType.LIGHTNING,
        CropType.EARTH,
        CropType.ICE,
        CropType.AIR,
    )

    def __init__(self):
        self.mode = "buy"
        self.selected = 0
        self.tier = 1
        self.selecting_quadrant = False
        self.pending_fertilizer = None
        self._status_message = ""
        self.status_timer = 0.0
        self.scroll_offset = 0

    @property
    def status_message(self) -> str:
        return self._status_message

    @status_message.setter
    def status_message(self, message: str) -> None:
        self._status_message = message
        self.status_timer = self.STATUS_DURATION if message else 0.0

    def clear_status(self) -> None:
        self.status_message = ""

    def update(self, dt: float) -> None:
        if not self._status_message:
            return
        self.status_timer = max(0.0, self.status_timer - dt)
        if self.status_timer == 0:
            self._status_message = ""

    def handle_event(self, event, player, farm, house=None, surface=None):
        if event.type == pygame.MOUSEWHEEL:
            step = -event.y
            if getattr(event, "flipped", False):
                step = -step
            if step:
                if self.selecting_quadrant:
                    quadrants = self._unlocked_quadrants(player)
                    if quadrants:
                        self.selected = (self.selected + step) % len(quadrants)
                else:
                    self._move_selection(step, player, house)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if surface is not None:
                self._handle_mouse_click(event.pos, player, farm, house, surface)
            return
        if event.type != pygame.KEYDOWN:
            return

        if self.selecting_quadrant:
            self._handle_quadrant_selection(event, player, farm)
        elif event.key == pygame.K_TAB:
            step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
            self.mode = self.MODES[
                (self.MODES.index(self.mode) + step) % len(self.MODES)
            ]
            self.selected = 0
            self.scroll_offset = 0
            self.status_message = ""
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._move_selection(-1, player, house)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_selection(1, player, house)
        elif self.mode == "buy" and event.key in (pygame.K_LEFT, pygame.K_a):
            self.tier = (self.tier - 2) % 3 + 1
        elif self.mode == "buy" and event.key in (pygame.K_RIGHT, pygame.K_d):
            self.tier = self.tier % 3 + 1
        elif event.key in self.CONFIRM_KEYS:
            self._activate_selection(player, farm, house)

    def _handle_mouse_click(self, position, player, farm, house, surface) -> None:
        panel = ShopRenderer._panel_rect(surface)
        options = self._visible_options(player, house)
        list_y = ShopRenderer._list_y(self, panel)
        scroll_offset = (
            self.scroll_offset
            if self.mode == "upgrade" and not self.selecting_quadrant
            else 0
        )
        visible_options = options[
            scroll_offset : scroll_offset + self.MAX_VISIBLE_UPGRADES
        ]
        for visible_index, option in enumerate(visible_options):
            row = pygame.Rect(
                panel.x + 16,
                list_y + visible_index * self.ITEM_H,
                panel.width - 32,
                self.ITEM_H,
            )
            if not row.collidepoint(position):
                continue
            self.selected = visible_index + scroll_offset
            if self.selecting_quadrant:
                self._purchase_fertilizer(option, player, farm)
            else:
                self._activate_selection(player, farm, house)
            return

    def _activate_selection(self, player, farm, house=None) -> None:
        options = self._options(player, house)
        if not options:
            self.selected = 0
            if self.mode == "sell":
                self.status_message = "No crops to sell."
            return
        self.selected = min(max(self.selected, 0), len(options) - 1)

        if self.mode == "buy":
            crop_type = self.CROP_TYPES[self.selected]
            player.buy_seed(SeedType[crop_type.name], self.tier)
        elif self.mode == "sell":
            crop_type = options[self.selected]
            if isinstance(crop_type, SellAllCrops):
                sold_count = player.sell_all_crops()
                self.status_message = (
                    f"Sold {sold_count} crops for {sold_count * 3} coins."
                )
            else:
                player.sell_crop(crop_type)
            self.selected = min(
                self.selected,
                max(0, len(self._crop_options(player)) - 1),
            )
        elif self.mode == "upgrade":
            option = options[self.selected]
            if isinstance(option, LandUpgrade):
                if player.buy_next_farm_quadrant():
                    self.status_message = "Farm quadrant unlocked."
                else:
                    self.status_message = "Not enough coins."
            elif isinstance(option, TurretSlotUpgrade):
                if player.buy_turret_slot():
                    self.status_message = "Elemental turret plot unlocked."
                    self.selected = 0
                else:
                    self.status_message = "Not enough coins."
            elif isinstance(option, HouseUpgrade):
                self._purchase_house_upgrade(option, player, house)
            elif isinstance(option, HarvestSizeUpgrade):
                if player.coins < option.cost:
                    self.status_message = "Not enough coins."
                else:
                    player.coins -= option.cost
                    player.harvest_size = option.size
                    self.status_message = (
                        f"Harvest area increased to {option.size}x{option.size}."
                    )
            elif isinstance(option, PlantRadiusUpgrade):
                if player.coins < option.cost:
                    self.status_message = "Not enough coins."
                else:
                    player.coins -= option.cost
                    player.plant_radius = option.radius
                    self.status_message = (
                        f"Plant radius increased to {option.radius}x{option.radius}."
                    )
            elif isinstance(option, FertilizerUpgrade):
                self.pending_fertilizer = option.crop_type
                self._begin_fertilizer_purchase(player, farm)
            else:
                raise ValueError(f"Unsupported upgrade option: {option!r}")

        if self.mode == "upgrade" and not self.selecting_quadrant:
            self.scroll_offset = min(
                self.scroll_offset,
                max(
                    0,
                    len(self._upgrade_options(player, house))
                    - self.MAX_VISIBLE_UPGRADES,
                ),
            )

    def _purchase_house_upgrade(self, option, player, house):
        if house is None:
            raise ValueError("House upgrades require the house instance.")
        if option.key == "repair" and house.health >= house.max_hp:
            self.status_message = "House is already fully repaired."
            return
        if player.coins < option.cost:
            self.status_message = "Not enough coins."
            return

        if option.key in ("turret_damage", "turret_fire_rate"):
            house.turret.upgrade_selection = int(option.key == "turret_fire_rate")
            house.turret.upgrade(player)
            self.status_message = house.turret.status_message
        elif option.key == "max_health":
            player.coins -= option.cost
            house.increase_max_health()
            house.health_upgrade_count += 1
            self.status_message = "House maximum health increased."
        elif option.key == "repair":
            player.coins -= option.cost
            house.repair()
            house.repair_count += 1
            self.status_message = "House repaired."
        else:
            raise ValueError(f"Unsupported house upgrade: {option.key}")

    def _begin_fertilizer_purchase(self, player, farm):
        quadrants = self._unlocked_quadrants(player)
        if len(quadrants) == 1:
            self._purchase_fertilizer(quadrants[0], player, farm)
        elif quadrants:
            self.selecting_quadrant = True
            self.selected = 0
            self.scroll_offset = 0
            self.status_message = ""

    def _handle_quadrant_selection(self, event, player, farm):
        quadrants = self._unlocked_quadrants(player)
        if event.key == pygame.K_ESCAPE:
            self.selecting_quadrant = False
            self.pending_fertilizer = None
            self.selected = 0
            self.scroll_offset = 0
            self.status_message = "Fertilizer purchase cancelled."
        elif event.key in (pygame.K_UP, pygame.K_w) and quadrants:
            self.selected = (self.selected - 1) % len(quadrants)
        elif event.key in (pygame.K_DOWN, pygame.K_s) and quadrants:
            self.selected = (self.selected + 1) % len(quadrants)
        elif event.key in self.CONFIRM_KEYS and quadrants:
            selected = min(max(self.selected, 0), len(quadrants) - 1)
            self._purchase_fertilizer(quadrants[selected], player, farm)

    def _purchase_fertilizer(self, quadrant, player, farm):
        if self.pending_fertilizer is None:
            self.status_message = "Select a fertilizer first."
        elif player.coins < self.FERTILIZER_COST:
            self.status_message = "Not enough coins."
        elif farm.apply_fertilizer(quadrant, self.pending_fertilizer):
            player.coins -= self.FERTILIZER_COST
            self.status_message = (
                f"{self.pending_fertilizer.name.title()} fertilizer applied."
            )
            self.selecting_quadrant = False
            self.pending_fertilizer = None
            self.scroll_offset = 0
        else:
            self.status_message = "Could not apply fertilizer."
        self.selected = 0

    def draw(self, surface, font, player, farm, house=None):
        ShopRenderer.draw(self, surface, font, player, farm, house)

    def _crop_options(self, player) -> list[CropType | SellAllCrops]:
        if self.mode == "buy":
            return list(self.CROP_TYPES)
        crops: list[CropType | SellAllCrops] = [
            crop_type
            for crop_type in self.CROP_TYPES
            if player.crops.get(crop_type, 0) > 0
        ]
        if crops:
            crops.append(SellAllCrops(sum(player.crops.values())))
        return crops

    def _visible_options(self, player, house=None):
        if self.selecting_quadrant:
            return self._unlocked_quadrants(player)
        if self.mode == "upgrade":
            return self._upgrade_options(player, house)
        return self._crop_options(player)

    def _upgrade_options(self, player, house=None) -> list[UpgradeOption]:
        options: list[UpgradeOption] = [
            FertilizerUpgrade(crop_type) for crop_type in self.CROP_TYPES
        ]
        radius_upgrades: list[UpgradeOption] = []
        harvest_size = getattr(player, "harvest_size", 1)
        if harvest_size <= len(self.HARVEST_SIZE_UPGRADE_COSTS):
            radius_upgrades.append(
                HarvestSizeUpgrade(
                    harvest_size + 1,
                    self.HARVEST_SIZE_UPGRADE_COSTS[harvest_size - 1],
                )
            )
        plant_radius = getattr(player, "plant_radius", 1)
        if plant_radius <= len(self.PLANT_RADIUS_UPGRADE_COSTS):
            radius_upgrades.append(
                PlantRadiusUpgrade(
                    plant_radius + 1,
                    self.PLANT_RADIUS_UPGRADE_COSTS[plant_radius - 1],
                )
            )
        options.extend(radius_upgrades)
        unlock = player.next_farm_quadrant_unlock()
        if unlock is not None:
            quadrant, cost = unlock
            options.insert(0, LandUpgrade(quadrant, cost))
        turret_cost = player.next_turret_slot_cost()
        if turret_cost is not None:
            options.append(TurretSlotUpgrade(turret_cost))
        if house is not None:
            options.extend(
                (
                    HouseUpgrade(
                        "turret_damage",
                        "House turret damage",
                        house.turret.next_upgrade_cost,
                    ),
                    HouseUpgrade(
                        "turret_fire_rate",
                        "House turret fire rate",
                        house.turret.next_upgrade_cost,
                    ),
                    HouseUpgrade(
                        "max_health",
                        "Increase house max health",
                        house.next_health_upgrade_cost,
                    ),
                    HouseUpgrade("repair", "Repair house", house.next_repair_cost),
                )
            )
        return options

    def _options(
        self, player, house=None
    ) -> Sequence[CropType | UpgradeOption | SellAllCrops]:
        if self.mode == "upgrade":
            return self._upgrade_options(player, house)
        return self._crop_options(player)

    def _unlocked_quadrants(self, player):
        return [
            quadrant
            for quadrant in Farm.QUADRANTS
            if quadrant in player.unlocked_quadrants
        ]

    def _move_selection(self, step, player, house=None):
        options = self._options(player, house)
        if options:
            self.selected = (self.selected + step) % len(options)
            if self.mode == "upgrade":
                max_offset = max(0, len(options) - self.MAX_VISIBLE_UPGRADES)
                if self.selected < self.scroll_offset:
                    self.scroll_offset = self.selected
                elif self.selected >= self.scroll_offset + self.MAX_VISIBLE_UPGRADES:
                    self.scroll_offset = min(
                        max_offset,
                        self.selected - self.MAX_VISIBLE_UPGRADES + 1,
                    )
        else:
            self.selected = 0
            self.scroll_offset = 0
