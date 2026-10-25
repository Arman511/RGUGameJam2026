import pygame
from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.game_entities.farm import CropMenu, Farm
from elemental_game.game_entities.house import House, HouseState
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.shop import HouseUpgrade, ShopMenu
from elemental_game.game_entities.turrets.turrets import ManualTurret
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType


def make_player():
    player = Player.__new__(Player)
    player.player_type = PlayerType.WATER
    player.seeds = {
        seed_type: {"tier1": 0, "tier2": 0, "tier3": 0} for seed_type in SeedType
    }
    player.coins = 5
    player.crops = {}
    player.unlocked_quadrants = {"top_right", "top_left"}
    return player


def make_farm(crop=None):
    farm = Farm.__new__(Farm)
    farm.rows = 2
    farm.cols = 2
    farm.origin = (0, 0)
    farm.grid = [[crop, None], [None, None]]
    farm.menu = CropMenu()
    farm.planting = False
    farm.fertilizers = {}
    farm.notice_message = ""
    farm.notice_timer = 0.0
    return farm


def test_player_starts_with_five_coins_and_can_buy_tiered_seeds(monkeypatch) -> None:
    surface = pygame.Surface((1, 1), pygame.SRCALPHA)

    class LoadedImage:
        def convert_alpha(self):
            return surface

    monkeypatch.setattr(pygame.image, "load", lambda _: LoadedImage())
    player = Player(player_type=PlayerType.WATER)

    assert player.coins == 5
    assert player.buy_seed(SeedType.FIRE, 3)
    assert player.coins == 2
    assert player.seeds[SeedType.FIRE]["tier3"] == 1
    assert not player.buy_seed(SeedType.FIRE, 3)


def test_market_space_key_buys_selected_seed() -> None:
    player = make_player()
    shop = ShopMenu()

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}), player, make_farm()
    )

    assert player.coins == 4
    assert player.seeds[SeedType.FIRE]["tier1"] == 1


def test_farm_quadrants_unlock_in_order_and_reset_to_top_right() -> None:
    player = make_player()
    player.unlocked_quadrants = {"top_right"}

    assert player.unlocked_quadrants == {"top_right"}
    assert player.next_farm_quadrant_unlock() == ("top_left", 10)
    assert not player.buy_next_farm_quadrant()

    player.coins = 10
    assert player.buy_next_farm_quadrant()
    assert player.coins == 0
    assert player.unlocked_quadrants == {"top_right", "top_left"}
    assert player.next_farm_quadrant_unlock() == ("bottom_left", 30)

    player.reset()
    assert player.unlocked_quadrants == {"top_right"}


def test_quadrants_split_six_by_six_grid_into_four_three_by_threes() -> None:
    farm = Farm.__new__(Farm)
    farm.rows = 6
    farm.cols = 6

    assert farm.quadrant_at(0, 0) == "top_left"
    assert farm.quadrant_at(0, 3) == "top_right"
    assert farm.quadrant_at(3, 0) == "bottom_left"
    assert farm.quadrant_at(3, 3) == "bottom_right"
    assert farm.quadrant_at(6, 0) is None


def test_fertilizer_doubles_matching_crop_yield_and_expires(monkeypatch) -> None:
    player = make_player()
    player.player_type = PlayerType.FIRE
    crop = Crop(CropType.FIRE, (0, 0), tier=2)
    crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm(crop)
    farm.fertilizers["top_left"] = (CropType.FIRE, 60.0)
    player.pos = pygame.Vector2(25, 25)
    monkeypatch.setattr("elemental_game.game_entities.farm.random.random", lambda: 0.5)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert player.crops[CropType.FIRE] == 4

    farm.fertilizers["top_left"] = (CropType.FIRE, 60.0)
    farm.update(60.0)
    assert "top_left" not in farm.fertilizers


def test_fertilizer_market_selects_a_quadrant_and_charges_coins() -> None:
    player = make_player()
    player.coins = 20
    player.unlocked_quadrants.add("top_left")
    farm = make_farm()
    shop = ShopMenu()
    shop.mode = "upgrade"
    shop.selected = 1

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), player, farm
    )
    assert shop.selecting_quadrant

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), player, farm
    )

    assert not shop.selecting_quadrant
    assert player.coins == 10
    assert farm.fertilizers["top_left"] == (CropType.FIRE, 60.0)


def test_fertilizer_market_applies_directly_when_only_one_quadrant_is_unlocked() -> (
    None
):
    player = make_player()
    player.unlocked_quadrants = {"top_right"}
    player.coins = 15
    farm = make_farm()
    shop = ShopMenu()
    shop.mode = "upgrade"
    shop.selected = 1

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), player, farm
    )

    assert not shop.selecting_quadrant
    assert player.coins == 5
    assert farm.fertilizers["top_right"] == (CropType.FIRE, 60.0)


def test_house_upgrades_are_available_in_shop_and_cost_more_after_each_use() -> None:
    from types import SimpleNamespace

    player = SimpleNamespace(
        coins=200,
        next_farm_quadrant_unlock=lambda: None,
        next_turret_slot_cost=lambda: None,
    )
    house = House.__new__(House)
    house.max_hp = 100
    house.health = 50
    house.state = HouseState.BROKEN
    house.health_upgrade_count = 0
    house.repair_count = 0
    house.turret = ManualTurret.__new__(ManualTurret)
    house.turret.damage_level = 0
    house.turret.fire_rate_level = 0
    house.turret.upgrade_selection = 0
    house.turret.status_message = ""
    shop = ShopMenu()
    shop.mode = "upgrade"

    def option_for(key: str) -> HouseUpgrade:
        return next(
            option
            for option in shop._upgrade_options(player, house)
            if isinstance(option, HouseUpgrade) and option.key == key
        )

    shop._purchase_house_upgrade(option_for("turret_damage"), player, house)
    assert house.turret.damage_level == 1
    assert option_for("turret_damage").cost == 20

    shop._purchase_house_upgrade(option_for("max_health"), player, house)
    assert house.max_hp == 125
    assert option_for("max_health").cost == 50

    shop._purchase_house_upgrade(option_for("repair"), player, house)
    assert house.health > 62
    assert option_for("repair").cost == 20


def test_planting_without_seeds_shows_market_reminder() -> None:
    player = make_player()
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert not farm.planting
    assert farm.notice_message == (
        "Buy seeds in the market first. Press M to open the market."
    )
    assert farm.notice_timer > 0


def test_planting_offers_only_owned_seed_tiers_and_consumes_selection() -> None:
    player = make_player()
    player.add_seed(SeedType.FIRE, "tier1", 1)
    player.add_seed(SeedType.FIRE, "tier3", 2)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert farm.planting
    assert [option[:3] for option in farm.menu.options] == [
        (CropType.FIRE, 1, 1),
        (CropType.FIRE, 3, 2),
    ]

    farm.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}), player
    )
    farm.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), player
    )

    planted_crop = farm.grid[0][0]
    assert planted_crop is not None
    assert planted_crop.crop_type is CropType.FIRE
    assert planted_crop.tier == 3
    assert player.seeds[SeedType.FIRE]["tier3"] == 1
    assert not farm.planting


def test_farm_plays_sfx_only_after_successful_planting_and_harvesting(
    monkeypatch,
) -> None:
    events = []
    farm = make_farm()

    monkeypatch.setattr(
        "elemental_game.game_entities.farm.play_sfx",
        lambda name: events.append(("sound", name, farm.grid[0][0])) or True,
    )
    monkeypatch.setattr(
        pygame.time,
        "delay",
        lambda milliseconds: events.append(
            ("delay", milliseconds, farm.grid[0][0])
        ),
    )

    crop = farm.plant(0, 0, CropType.FIRE)
    assert crop is not None
    assert farm.plant(0, 0, CropType.WATER) is None
    assert events == [
        ("sound", "planting", None),
        ("delay", 250, None),
    ]

    crop.growth_timer = crop.GROWTH_TIME
    assert farm.harvest(0, 0) is crop
    assert farm.harvest(0, 0) is None
    assert events == [
        ("sound", "planting", None),
        ("delay", 250, None),
        ("sound", "harvesting", crop),
        ("delay", 250, crop),
    ]


def test_harvest_yield_matches_crop_tier() -> None:
    player = make_player()
    crop = Crop(CropType.ICE, (0, 0), tier=2)
    crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm(crop)
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert farm.grid[0][0] is None
    assert player.crops[CropType.ICE] == 2


def test_matching_element_has_chance_to_double_harvest_yield(monkeypatch) -> None:
    player = make_player()
    player.player_type = PlayerType.FIRE
    crop = Crop(CropType.FIRE, (0, 0), tier=2)
    crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm(crop)
    player.pos = pygame.Vector2(25, 25)
    monkeypatch.setattr("elemental_game.game_entities.farm.random.random", lambda: 0.2)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert player.crops[CropType.FIRE] == 4


def test_opposing_element_has_chance_to_floor_half_harvest_yield(monkeypatch) -> None:
    player = make_player()
    player.player_type = PlayerType.FIRE
    crop = Crop(CropType.WATER, (0, 0), tier=3)
    crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm(crop)
    player.pos = pygame.Vector2(25, 25)
    monkeypatch.setattr("elemental_game.game_entities.farm.random.random", lambda: 0.05)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert player.crops[CropType.WATER] == 1


def test_selling_crop_adds_three_coins_and_removes_one_crop() -> None:
    player = make_player()
    player.coins = 1
    player.add_crop(CropType.WATER, 2)

    assert player.sell_crop(CropType.WATER)
    assert player.coins == 4
    assert player.crops[CropType.WATER] == 1


def test_lightning_planting_option_fits_inside_the_screen() -> None:
    player = make_player()
    player.add_seed(SeedType.LIGHTNING, "tier3", 2)
    menu = CropMenu()
    menu.move_to((0, 0), (280, 570), player)
    screen = pygame.Surface((320, 180))
    pygame.font.init()
    font = pygame.font.Font(None, 28)

    menu.draw(screen, font)

    rect = menu.options[0][3]
    label_width = font.size("Lightning T3 (2)")[0]
    assert rect.right <= screen.get_width()
    assert rect.bottom <= screen.get_height()
    assert label_width + 16 <= rect.width
