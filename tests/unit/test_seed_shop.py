import pygame
from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.game_entities.farm import CropMenu, Farm
from elemental_game.game_entities.house import House, HouseState
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.seed_tier_reward import SeedTierReward
from elemental_game.game_entities.shop import (
    FertilizerUpgrade,
    HarvestSizeUpgrade,
    HouseUpgrade,
    PlantRadiusUpgrade,
    SellAllCrops,
    ShopMenu,
)
from elemental_game.game_entities.shop.renderer import ShopRenderer
from elemental_game.game_entities.turrets.turrets import ManualTurret
from elemental_game.game_input import GameInputHandler
from elemental_game.gameplay import GameSession
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType


def make_player():
    player = Player.__new__(Player)
    player.player_type = PlayerType.WATER
    player.unlocked_seed_tiers = {seed_type: 3 for seed_type in SeedType}
    player.seeds = {
        seed_type: {"tier1": 0, "tier2": 0, "tier3": 0} for seed_type in SeedType
    }
    player.coins = 5
    player.crops = {}
    player.unlocked_quadrants = {"top_right", "top_left"}
    player.harvest_size = 1
    player.plant_radius = 1
    player.plant_radius_active = 1
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
    farm.pending_plant_tiles = []
    return farm


def test_player_starts_with_five_coins_and_can_buy_tiered_seeds(monkeypatch) -> None:
    surface = pygame.Surface((1, 1), pygame.SRCALPHA)

    class LoadedImage:
        def convert_alpha(self):
            return surface

    monkeypatch.setattr(pygame.image, "load", lambda _: LoadedImage())
    player = Player(player_type=PlayerType.WATER, pos=(0, 0))

    assert player.coins == 5
    assert player.max_unlocked_seed_tier(SeedType.FIRE) == 1
    assert not player.buy_seed(SeedType.FIRE, 2)
    assert player.unlock_next_seed_tier(SeedType.FIRE) == 2
    assert player.unlock_next_seed_tier(SeedType.FIRE) == 3
    assert player.buy_seed(SeedType.FIRE, 3)
    assert player.coins == 1
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


def test_shop_q_and_e_change_seed_tier() -> None:
    player = make_player()
    shop = ShopMenu()

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_e}), player, make_farm()
    )
    assert shop.tier == 2
    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q}), player, make_farm()
    )
    assert shop.tier == 1


def test_shop_buy_quantity_cycles_with_a_d_and_arrows() -> None:
    player = make_player()
    shop = ShopMenu()

    for key, expected_quantity in (
        (pygame.K_d, 10),
        (pygame.K_RIGHT, 100),
        (pygame.K_d, 1),
        (pygame.K_a, 100),
        (pygame.K_LEFT, 10),
        (pygame.K_a, 1),
    ):
        shop.handle_event(
            pygame.event.Event(pygame.KEYDOWN, {"key": key}), player, make_farm()
        )
        assert shop.buy_quantity == expected_quantity


def test_buying_seed_quantity_charges_total_and_adds_all_seeds() -> None:
    player = make_player()
    player.coins = 10
    shop = ShopMenu()
    shop.buy_quantity = 10

    shop._activate_selection(player, make_farm())

    assert player.coins == 0
    assert player.seeds[SeedType.FIRE]["tier1"] == 10


def test_bulk_seed_purchase_requires_full_amount() -> None:
    player = make_player()
    player.coins = 9
    shop = ShopMenu()
    shop.buy_quantity = 10

    shop._activate_selection(player, make_farm())

    assert player.coins == 9
    assert player.seeds[SeedType.FIRE]["tier1"] == 0
    assert "Need 10 coins" in shop.status_message


def test_shop_only_shows_seeds_unlocked_for_the_selected_tier() -> None:
    player = make_player()
    player.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
    player.unlocked_seed_tiers[SeedType.FIRE] = 3
    shop = ShopMenu()

    for _ in range(4):
        shop.handle_event(
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_e}),
            player,
            make_farm(),
        )
    assert shop.tier == 3
    assert shop._visible_options(player) == [CropType.FIRE]

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s}),
        player,
        make_farm(),
    )
    assert shop.selected == 0
    assert shop.tier == 3

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q}), player, make_farm()
    )
    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q}), player, make_farm()
    )
    assert shop.tier == 1
    assert shop._visible_options(player) == list(ShopMenu.CROP_TYPES)


def test_player_seed_tiers_unlock_independently_and_costs_double() -> None:
    player = make_player()
    player.coins = 20
    player.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
    player.unlocked_seed_tiers[SeedType.FIRE] = 4

    assert [player.seed_tier_cost(tier) for tier in range(1, 5)] == [1, 2, 4, 8]
    assert player.buy_seed(SeedType.FIRE, 4)
    assert player.seeds[SeedType.FIRE]["tier4"] == 1
    assert not player.buy_seed(SeedType.WATER, 2)
    assert player.max_unlocked_seed_tier(SeedType.WATER) == 1


def test_boss_reward_unlocks_the_selected_element_only() -> None:
    player = make_player()
    player.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
    reward = SeedTierReward()

    reward.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s}),
        player,
        pygame.Surface((1280, 768)),
    )
    selected = reward.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        pygame.Surface((1280, 768)),
    )

    assert selected is SeedType.WATER
    assert player.max_unlocked_seed_tier(SeedType.WATER) == 2
    assert player.max_unlocked_seed_tier(SeedType.FIRE) == 1


def test_boss_reward_waits_for_manual_turret_exit() -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    reward = Mock()
    game = SimpleNamespace(
        seed_tier_reward=reward,
        controlling_house_turret=True,
        turrets=SimpleNamespace(modal_slot=None),
        shop_open=False,
        farm=SimpleNamespace(planting=False),
        player=object(),
        screen=pygame.Surface((1, 1)),
    )
    handler = GameInputHandler(game)

    handler.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))

    reward.handle_event.assert_not_called()
    assert not game.controlling_house_turret

    handler.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))

    reward.handle_event.assert_called_once()


def test_boss_reward_modal_draws_element_choices(pygame_display) -> None:
    from elemental_game.types.seed import SeedType

    pygame.font.init()
    player = make_player()
    player.unlocked_seed_tiers = {seed_type: 1 for seed_type in SeedType}
    reward = SeedTierReward()

    reward.draw(
        pygame.Surface((1280, 768)),
        pygame.font.Font(None, 22),
        player,
    )


def test_market_mouse_wheel_moves_selection_up_and_down() -> None:
    player = make_player()
    shop = ShopMenu()

    shop.handle_event(
        pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}), player, make_farm()
    )
    assert shop.selected == 1

    shop.handle_event(
        pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1}), player, make_farm()
    )
    assert shop.selected == 0


def test_new_crop_tiers_keep_the_same_growth_duration() -> None:
    tier_one = Crop(CropType.FIRE, (0, 0), tier=1)
    tier_five = Crop(CropType.FIRE, (0, 1), tier=5)

    assert tier_one.GROWTH_TIME == tier_five.GROWTH_TIME


def test_open_market_receives_mouse_wheel_events() -> None:
    from elemental_game.game_entities.turrets.turrets import TurretSystem

    shop = ShopMenu()
    game = GameSession.__new__(GameSession)
    game.turrets = TurretSystem.__new__(TurretSystem)
    game.turrets.modal_slot = None
    game.controlling_house_turret = False
    game.shop_open = True
    game.shop = shop
    game.player = make_player()
    game.farm = make_farm()
    game.house = House.__new__(House)
    game.screen = pygame.Surface((1, 1))
    game.input = GameInputHandler(game)

    event = pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1})
    game.handle_event(event)

    assert shop.selected == 1


def test_market_w_and_s_keys_move_selection() -> None:
    player = make_player()
    shop = ShopMenu()

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s}), player, make_farm()
    )
    assert shop.selected == 1

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w}), player, make_farm()
    )
    assert shop.selected == 0


def test_w_and_s_keys_move_quadrant_selection() -> None:
    player = make_player()
    shop = ShopMenu()
    shop.mode = "upgrade"
    shop.selecting_quadrant = True

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s}), player, make_farm()
    )
    assert shop.selected == 1

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w}), player, make_farm()
    )
    assert shop.selected == 0


def test_market_mouse_wheel_scrolls_long_upgrade_list(monkeypatch) -> None:
    player = make_player()
    shop = ShopMenu()
    shop.mode = "upgrade"
    monkeypatch.setattr(
        shop, "_options", lambda *args: list(range(15)) if len(args) == 2 else []
    )

    for _ in range(ShopMenu.MAX_VISIBLE_UPGRADES):
        shop.handle_event(
            pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}), player, make_farm()
        )

    assert shop.selected == ShopMenu.MAX_VISIBLE_UPGRADES
    assert shop.scroll_offset == 1

    for _ in range(ShopMenu.MAX_VISIBLE_UPGRADES):
        shop.handle_event(
            pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1}), player, make_farm()
        )

    assert shop.selected == 0
    assert shop.scroll_offset == 0


def test_upgrade_help_only_appears_when_a_fertilizer_is_selected(monkeypatch) -> None:
    player = make_player()
    farm = make_farm()
    shop = ShopMenu()
    shop.mode = "upgrade"
    options = shop._visible_options(player)
    fertilizer_index = next(
        index
        for index, option in enumerate(options)
        if isinstance(option, FertilizerUpgrade)
    )
    non_fertilizer_index = next(
        index
        for index, option in enumerate(options)
        if not isinstance(option, FertilizerUpgrade)
    )
    rendered_text = []

    def capture_text(*args):
        rendered_text.append(args[2])

    monkeypatch.setattr(ShopRenderer, "_draw_fitted", staticmethod(capture_text))
    pygame.font.init()
    surface = pygame.Surface((800, 600))
    font = pygame.font.Font(None, 20)

    shop.selected = fertilizer_index
    shop.draw(surface, font, player, farm)
    assert "W/S or UP/DOWN/SCROLL: Select" in rendered_text
    assert "ENTER/SPACE/F: Buy" in rendered_text
    assert "Matching crops: double yield for 60s." in rendered_text
    assert "Replaces current fertilizer in that quadrant." in rendered_text

    rendered_text.clear()
    shop.selected = non_fertilizer_index
    shop.draw(surface, font, player, farm)
    assert "Matching crops: double yield for 60s." not in rendered_text
    assert "Replaces current fertilizer in that quadrant." not in rendered_text


def test_shop_currency_words_are_rendered_as_coin_icons(monkeypatch) -> None:
    from elemental_game.game_entities.shop import renderer as shop_renderer

    pygame.font.init()
    font_renderer = pygame.font.Font(None, 20)
    rendered_text = []
    coin_sizes = []
    icon = pygame.Surface((20, 20), pygame.SRCALPHA)

    class Font:
        def get_linesize(self):
            return font_renderer.get_linesize()

        def size(self, text):
            return font_renderer.size(text)

        def render(self, text, antialias, color):
            rendered_text.append(text)
            return font_renderer.render(text, antialias, color)

    monkeypatch.setattr(
        shop_renderer, "get_coin_icon", lambda size: coin_sizes.append(size) or icon
    )

    ShopRenderer._draw_fitted(
        pygame.Surface((400, 60)),
        Font(),
        "Market Coins: 10; buy for 5 coins",
        (255, 255, 255),
        (0, 0),
        400,
    )

    assert coin_sizes == [font_renderer.get_linesize()] * 2
    assert not any("coin" in text.lower() for text in rendered_text)


def test_buy_shop_controls_have_room_before_seed_list(monkeypatch) -> None:
    rendered = []
    monkeypatch.setattr(
        ShopRenderer,
        "_draw_fitted",
        staticmethod(
            lambda _surface, _font, text, _color, position, _width: rendered.append(
                (text, position)
            )
        ),
    )
    shop = ShopMenu()
    shop._visible_options = lambda *_args: []
    surface = pygame.Surface((800, 600))
    panel = ShopRenderer._panel_rect(surface)

    ShopRenderer.draw(
        shop,
        surface,
        pygame.font.Font(None, 20),
        make_player(),
        make_farm(),
    )

    tier_instruction = next(
        item for item in rendered if item[0] == "Q/E: change seed tier"
    )
    quantity_instruction = next(
        item for item in rendered if item[0] == "A/D or LEFT/RIGHT: change quantity"
    )
    assert quantity_instruction[1][1] > tier_instruction[1][1]
    assert panel.height == 560
    assert ShopRenderer._list_y(shop, panel) > quantity_instruction[1][1]


def test_upgrade_menu_offers_fertilizer_for_every_crop_type() -> None:
    shop = ShopMenu()
    options = shop._upgrade_options(make_player())

    fertilizer_types = {
        option.crop_type for option in options if isinstance(option, FertilizerUpgrade)
    }
    fertilizer_indices = [
        index
        for index, option in enumerate(options)
        if isinstance(option, FertilizerUpgrade)
    ]

    assert fertilizer_types == set(CropType)
    assert fertilizer_indices == list(
        range(fertilizer_indices[0], fertilizer_indices[0] + len(fertilizer_indices))
    )


def test_shift_tab_moves_to_previous_shop_section() -> None:
    player = make_player()
    shop = ShopMenu()

    shop.handle_event(
        pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_TAB, "mod": pygame.KMOD_SHIFT}
        ),
        player,
        make_farm(),
    )

    assert shop.mode == "sell"


def test_market_enter_on_empty_sell_page_does_not_crash() -> None:
    player = make_player()
    shop = ShopMenu()
    shop.mode = "sell"

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        make_farm(),
    )

    assert shop.selected == 0
    assert shop.status_message == "No crops to sell."


def test_market_enter_after_selling_last_crop_does_not_crash() -> None:
    player = make_player()
    player.crops[CropType.FIRE] = 1
    shop = ShopMenu()
    shop.mode = "sell"

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        make_farm(),
    )

    assert player.crops[CropType.FIRE] == 0
    assert player.coins == 8
    assert shop.selected == 0

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        make_farm(),
    )

    assert shop.selected == 0
    assert shop.status_message == "No crops to sell."


def test_sell_all_option_appears_only_with_crops_and_sells_everything() -> None:
    player = make_player()
    shop = ShopMenu()
    shop.mode = "sell"

    assert not any(isinstance(option, SellAllCrops) for option in shop._options(player))

    player.crops = {CropType.FIRE: 2, CropType.WATER: 3}
    options = shop._options(player)
    sell_all_index = next(
        index
        for index, option in enumerate(options)
        if isinstance(option, SellAllCrops)
    )
    sell_all_option = options[sell_all_index]
    assert isinstance(sell_all_option, SellAllCrops)
    assert sell_all_option.count == 5

    shop.selected = sell_all_index
    shop._activate_selection(player, make_farm())

    assert player.crops == {CropType.FIRE: 0, CropType.WATER: 0}
    assert player.coins == 20
    assert not any(isinstance(option, SellAllCrops) for option in shop._options(player))


def test_market_enter_clamps_stale_upgrade_selection() -> None:
    player = make_player()
    player.next_farm_quadrant_unlock = lambda: None
    player.next_turret_slot_cost = lambda: None
    shop = ShopMenu()
    shop.mode = "upgrade"
    shop.selected = 99

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        make_farm(),
    )

    assert not shop.selecting_quadrant
    assert shop.pending_fertilizer is None
    assert shop.selected == len(shop._upgrade_options(player)) - 1
    assert shop.status_message == "Not enough coins."


def test_market_harvest_area_upgrades_use_the_requested_costs_and_maximum() -> None:
    player = make_player()
    player.coins = 1000
    shop = ShopMenu()
    shop.mode = "upgrade"
    farm = make_farm()

    for expected_size, expected_cost in enumerate((20, 50, 100, 200, 300), start=2):
        option = next(
            option
            for option in shop._upgrade_options(player)
            if isinstance(option, HarvestSizeUpgrade)
        )
        assert option.size == expected_size
        assert option.cost == expected_cost
        shop.selected = shop._upgrade_options(player).index(option)
        shop._activate_selection(player, farm)
        assert player.harvest_size == expected_size

    assert not any(
        isinstance(option, HarvestSizeUpgrade)
        for option in shop._upgrade_options(player)
    )
    assert player.coins == 330


def test_market_plant_radius_upgrades_use_the_requested_costs_and_maximum() -> None:
    player = make_player()
    player.coins = 300
    shop = ShopMenu()
    shop.mode = "upgrade"
    farm = make_farm()

    for expected_radius, expected_cost in ((2, 50), (3, 200)):
        option = next(
            option
            for option in shop._upgrade_options(player)
            if isinstance(option, PlantRadiusUpgrade)
        )
        assert option.radius == expected_radius
        assert option.cost == expected_cost
        shop.selected = shop._upgrade_options(player).index(option)
        shop._activate_selection(player, farm)
        assert player.plant_radius == expected_radius
        assert player.plant_radius_active == expected_radius

    assert not any(
        isinstance(option, PlantRadiusUpgrade)
        for option in shop._upgrade_options(player)
    )
    assert player.coins == 50


def test_plant_radius_button_cycles_only_through_purchased_radii() -> None:
    player = make_player()

    assert player.cycle_plant_radius() == 1
    assert player.plant_radius_active == 1

    player.plant_radius = 2
    assert player.cycle_plant_radius() == 2
    assert player.cycle_plant_radius() == 1

    player.plant_radius = 3
    assert player.cycle_plant_radius() == 2
    assert player.cycle_plant_radius() == 3
    assert player.cycle_plant_radius() == 1


def test_fertilizer_enter_clamps_stale_quadrant_selection() -> None:
    player = make_player()
    player.coins = 20
    farm = make_farm()
    applied_quadrants = []
    farm.apply_fertilizer = lambda quadrant, crop_type: (
        applied_quadrants.append(quadrant) or True
    )
    shop = ShopMenu()
    shop.mode = "upgrade"
    shop.selecting_quadrant = True
    shop.pending_fertilizer = CropType.FIRE
    shop.selected = 99
    last_quadrant = ShopMenu()._unlocked_quadrants(player)[-1]

    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}),
        player,
        farm,
    )

    assert applied_quadrants == [last_quadrant]
    assert player.coins == 10
    assert not shop.selecting_quadrant


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
    assert option_for("turret_damage").cost == 13

    shop._purchase_house_upgrade(option_for("max_health"), player, house)
    assert house.max_hp == 125
    assert option_for("max_health").cost == 32

    shop._purchase_house_upgrade(option_for("repair"), player, house)
    assert house.health > 62
    assert option_for("repair").cost == 13


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


def test_planting_with_multiple_tiers_of_one_crop_type_shows_the_menu() -> None:
    player = make_player()
    player.add_seed(SeedType.FIRE, "tier2", 1)
    player.add_seed(SeedType.FIRE, "tier3", 2)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert farm.planting
    assert [option[:3] for option in farm.menu.options] == [
        (CropType.FIRE, 2, 1),
        (CropType.FIRE, 3, 2),
    ]
    farm.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}), player
    )
    farm.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}), player
    )

    planted_crop = farm.grid[0][0]
    assert not farm.planting
    assert planted_crop is not None
    assert planted_crop.crop_type is CropType.FIRE
    assert planted_crop.tier == 3
    assert player.seeds[SeedType.FIRE]["tier2"] == 1
    assert player.seeds[SeedType.FIRE]["tier3"] == 1


def test_planting_menu_includes_unbounded_seed_tiers() -> None:
    player = make_player()
    player.unlocked_seed_tiers[SeedType.FIRE] = 7
    player.add_seed(SeedType.FIRE, "tier7", 1)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert farm.grid[0][0] is not None
    assert farm.grid[0][0].tier == 7


def test_planting_menu_w_and_s_move_selection() -> None:
    player = make_player()
    player.add_seed(SeedType.FIRE, "tier1", 1)
    player.add_seed(SeedType.WATER, "tier1", 1)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)
    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s}), player)
    assert farm.menu.selected == 1
    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w}), player)
    assert farm.menu.selected == 0


def test_clicking_planting_menu_seed_plants_it() -> None:
    player = make_player()
    player.add_seed(SeedType.FIRE, "tier1", 1)
    player.add_seed(SeedType.WATER, "tier1", 1)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)
    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    game = GameSession.__new__(GameSession)
    game.farm = farm
    game.player = player
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": farm.menu.options[1][3].center},
    )
    result = GameInputHandler(game).handle_mouse_event(event, {})

    assert result == "handled"
    assert not farm.planting
    assert farm.grid[0][0] is not None
    assert farm.grid[0][0].crop_type is CropType.WATER
    assert player.seeds[SeedType.WATER]["tier1"] == 0


def test_planting_with_one_crop_and_tier_skips_the_menu() -> None:
    player = make_player()
    player.add_seed(SeedType.FIRE, "tier3", 1)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    planted_crop = farm.grid[0][0]
    assert not farm.planting
    assert planted_crop is not None
    assert planted_crop.crop_type is CropType.FIRE
    assert planted_crop.tier == 3
    assert player.seeds[SeedType.FIRE]["tier3"] == 0


def test_area_planting_at_the_farm_edge_only_uses_eligible_slots(monkeypatch) -> None:
    player = make_player()
    player.unlocked_quadrants = {str(quadrant) for quadrant in Farm.QUADRANTS}
    player.plant_radius = 3
    player.plant_radius_active = 3
    player.add_seed(SeedType.FIRE, "tier1", 3)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)
    monkeypatch.setattr("elemental_game.game_entities.farm.play_sfx", lambda _: False)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert sum(crop is not None for row in farm.grid for crop in row) == 3
    assert player.seeds[SeedType.FIRE]["tier1"] == 0
    assert farm.grid[0][0] is not None
    assert farm.grid[0][1] is not None
    assert farm.grid[1][0] is not None
    assert farm.grid[1][1] is None


def test_area_harvesting_at_the_farm_edge_uses_all_in_bounds_crops(monkeypatch) -> None:
    player = make_player()
    player.unlocked_quadrants = {str(quadrant) for quadrant in Farm.QUADRANTS}
    player.harvest_size = 2
    player.pos = pygame.Vector2(25, 25)
    crops = [Crop(CropType.FIRE, (row, col)) for row in range(2) for col in range(2)]
    for crop in crops:
        crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm()
    farm.grid = [[crops[0], crops[1]], [crops[2], crops[3]]]
    monkeypatch.setattr("elemental_game.game_entities.farm.play_sfx", lambda _: False)
    monkeypatch.setattr("elemental_game.game_entities.farm.random.random", lambda: 0.5)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert all(crop is None for row in farm.grid for crop in row)
    assert player.crops[CropType.FIRE] == 4


def test_planting_with_multiple_crop_types_still_shows_the_menu() -> None:
    player = make_player()
    player.add_seed(SeedType.WATER, "tier2", 1)
    player.add_seed(SeedType.FIRE, "tier1", 1)
    farm = make_farm()
    player.pos = pygame.Vector2(25, 25)

    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)

    assert farm.planting
    assert farm.grid[0][0] is None


def test_shop_status_message_expires_after_five_seconds() -> None:
    shop = ShopMenu()
    shop.status_message = "Elemental turret plot unlocked."

    shop.update(4.9)
    assert shop.status_message == "Elemental turret plot unlocked."

    shop.update(0.1)
    assert shop.status_message == ""


def test_reopening_shop_can_clear_previous_status_message() -> None:
    shop = ShopMenu()
    shop.status_message = "Elemental turret plot unlocked."

    shop.clear_status()

    assert shop.status_message == ""


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
        lambda milliseconds: events.append(("delay", milliseconds, farm.grid[0][0])),
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


def test_enemy_phase_pauses_crop_growth_but_counts_down_fertilizer() -> None:
    crop = Crop(CropType.FIRE, (0, 0))
    farm = make_farm(crop)
    farm.fertilizers["top_left"] = (CropType.FIRE, 60.0)

    farm.update(5.0, grow_crops=False)

    assert crop.growth_timer == 0
    assert farm.fertilizers["top_left"] == (CropType.FIRE, 55.0)


def test_game_only_advances_crop_growth_during_planting_phase(monkeypatch) -> None:
    from types import SimpleNamespace

    from elemental_game import gameplay as gameplay_module

    growth_settings = []
    update_result = SimpleNamespace(
        spawned_enemies=[], started_wave=None, completed=False
    )
    game = GameSession.__new__(GameSession)
    game.house = SimpleNamespace(health=100)
    game.player = SimpleNamespace(update=lambda _seconds: None)
    game.farm = SimpleNamespace(
        update=lambda _seconds, *, grow_crops: growth_settings.append(grow_crops),
        weather_crop_type=None,
    )
    game.shop = SimpleNamespace(update=lambda _seconds: None)
    game.waves = SimpleNamespace(
        planting_phase=False,
        crop_type=CropType.FIRE,
        update=lambda *_args, **_kwargs: update_result,
    )
    game.screen = pygame.Surface((1, 1))
    game.enemies = []
    game.turrets = object()
    game.controlling_house_turret = False
    game.run_elapsed = 0.0
    game.enemies_defeated = 0
    monkeypatch.setattr(
        gameplay_module.EnemyController,
        "update",
        lambda *_args: ([], 0),
    )

    game.update(1.0, paused=False, music_volume=1.0)
    game.waves.planting_phase = True
    game.update(1.0, paused=False, music_volume=1.0)

    assert growth_settings == [False, True]


def test_open_planting_menu_only_pauses_during_planting_phase() -> None:
    from types import SimpleNamespace

    game = GameSession.__new__(GameSession)
    game.shop_open = False
    game.confirm_exit = False
    game.farm = SimpleNamespace(planting=True)
    game.waves = SimpleNamespace(planting_phase=False)
    game.turrets = SimpleNamespace(modal_slot=None)

    assert not game.single_player_menu_paused

    game.waves.planting_phase = True

    assert game.single_player_menu_paused


def test_player_does_not_move_with_plant_selector_open_during_enemy_phase(
    monkeypatch,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from elemental_game import gameplay as gameplay_module

    update_result = SimpleNamespace(
        spawned_enemies=[], started_wave=None, completed=False
    )
    game = GameSession.__new__(GameSession)
    game.house = SimpleNamespace(health=100)
    game.player = Mock()
    game.farm = SimpleNamespace(
        planting=True,
        update=lambda *_args, **_kwargs: None,
        weather_crop_type=None,
    )
    game.waves = SimpleNamespace(
        planting_phase=False,
        update=lambda *_args, **_kwargs: update_result,
        crop_type=CropType.FIRE,
    )
    game.shop_open = False
    game.shop = SimpleNamespace(update=lambda *_args: None)
    game.confirm_exit = False
    game.turrets = SimpleNamespace(modal_slot=None)
    game.seed_tier_reward = None
    game.controlling_house_turret = False
    game.run_elapsed = 0.0
    game.enemies = []
    game.enemies_defeated = 0
    game.screen = pygame.Surface((1, 1))
    monkeypatch.setattr(
        gameplay_module.EnemyController,
        "update",
        lambda *_args: ([], 0),
    )

    game.update(
        0.1,
        paused=False,
        music_volume=1.0,
    )

    game.player.update.assert_not_called()


def test_paused_game_does_not_advance_fertilizer_timers() -> None:
    from types import SimpleNamespace

    game = GameSession.__new__(GameSession)
    game.house = SimpleNamespace(health=100)
    game.player = make_player()
    game.farm = make_farm()
    game.farm.fertilizers["top_left"] = (CropType.FIRE, 60.0)
    game.shop = ShopMenu()
    game.controlling_house_turret = False

    game.update(5.0, paused=True, music_volume=1.0)

    assert game.farm.fertilizers["top_left"] == (CropType.FIRE, 60.0)


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


def test_weather_guarantees_double_yield_for_matching_crop(monkeypatch) -> None:
    player = make_player()
    player.player_type = PlayerType.WATER
    crop = Crop(CropType.FIRE, (0, 0), tier=2)
    crop.growth_timer = crop.GROWTH_TIME
    farm = make_farm(crop)
    farm.weather_crop_type = CropType.FIRE
    player.pos = pygame.Vector2(25, 25)
    monkeypatch.setattr("elemental_game.game_entities.farm.random.random", lambda: 0.9)

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


def test_selling_crop_rejects_batch_larger_than_inventory() -> None:
    player = make_player()
    player.coins = 1
    player.add_crop(CropType.WATER, 4)

    assert player.sell_crop(CropType.WATER, 10) == 0
    assert player.coins == 1
    assert player.crops[CropType.WATER] == 4


def test_shop_rejects_selected_quantity_larger_than_inventory() -> None:
    player = make_player()
    player.coins = 1
    player.add_crop(CropType.WATER, 4)
    shop = ShopMenu()
    shop.mode = "sell"
    shop.sell_quantity = 10
    shop.selected = 0

    shop._activate_selection(player, make_farm())

    assert player.coins == 1
    assert player.crops[CropType.WATER] == 4
    assert shop.status_message == "Not enough Water crops (4 available)."


def test_sell_filter_cycles_crops_seeds_all_by_key_and_click() -> None:
    player = make_player()
    player.add_crop(CropType.FIRE, 1)
    player.add_seed(SeedType.WATER, "tier1", 2)
    shop = ShopMenu()
    shop.mode = "sell"

    assert shop.sell_filter == "crops"
    shop.handle_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_u}),
        player,
        make_farm(),
    )
    assert shop.sell_filter == "seeds"
    assert [(item.seed_type, item.tier) for item in shop._visible_options(player)] == [
        (SeedType.WATER, 1)
    ]

    surface = pygame.Surface((800, 600))
    filter_rect = ShopRenderer._sell_filter_rect(ShopRenderer._panel_rect(surface))
    shop.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": filter_rect.center}
        ),
        player,
        make_farm(),
        surface=surface,
    )
    assert shop.sell_filter == "all"
    options = shop._visible_options(player)
    assert CropType.FIRE in options
    assert any(getattr(item, "seed_type", None) is SeedType.WATER for item in options)


def test_selling_three_tier_one_seeds_pays_one_coin_across_sales() -> None:
    player = make_player()
    player.coins = 0
    player.add_seed(SeedType.FIRE, "tier1", 3)

    assert player.sell_seed(SeedType.FIRE, 1) == 0
    assert player.sell_seed(SeedType.FIRE, 1) == 0
    assert player.sell_seed(SeedType.FIRE, 1) == 1
    assert player.coins == 1
    assert player.seeds[SeedType.FIRE]["tier1"] == 0


def test_selling_seed_quantity_uses_tier_buy_price_for_payout() -> None:
    player = make_player()
    player.coins = 0
    player.add_seed(SeedType.FIRE, "tier3", 10)
    shop = ShopMenu()
    shop.mode = "sell"
    shop.sell_filter = "seeds"
    shop.sell_quantity = 10
    shop.selected = 0

    shop._activate_selection(player, make_farm())

    assert player.coins == 13
    assert player.seeds[SeedType.FIRE]["tier3"] == 0
    assert "for 13 coins" in shop.status_message


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
