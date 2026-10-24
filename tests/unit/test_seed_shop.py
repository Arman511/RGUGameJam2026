import pygame

from elemental_game.game_entities.crops.crops import Crop, CropType
from elemental_game.game_entities.farm import CropMenu, Farm
from elemental_game.game_entities.player.player import Player
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
    return player


def make_farm(crop=None):
    farm = Farm.__new__(Farm)
    farm.rows = 1
    farm.cols = 1
    farm.origin = (0, 0)
    farm.grid = [[crop]]
    farm.menu = CropMenu()
    farm.planting = False
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
    font = pygame.font.Font(None, 28)

    menu.draw(screen, font)

    rect = menu.options[0][3]
    label_width = font.size("Lightning T3 (2)")[0]
    assert rect.right <= screen.get_width()
    assert rect.bottom <= screen.get_height()
    assert label_width + 16 <= rect.width
