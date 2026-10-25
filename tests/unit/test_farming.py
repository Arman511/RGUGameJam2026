import pytest

from elemental_game.game_entities import farm as farm_module
from elemental_game.game_entities.farm import Farm
from elemental_game.types.crop import CropType


@pytest.fixture
def farm(pygame_display, monkeypatch):
    monkeypatch.setattr(farm_module, "play_sfx", lambda *_args: False)
    return Farm(rows=1, cols=2)


def test_planting_on_empty_plot_succeeds(farm) -> None:
    planted_crop = farm.plant(0, 0, CropType.FIRE)

    assert planted_crop is farm.grid[0][0]
    assert planted_crop.crop_type is CropType.FIRE


def test_invalid_planting_leaves_existing_crops_unchanged(farm) -> None:
    planted_crop = farm.plant(0, 0, CropType.FIRE)

    assert farm.plant(0, 0, CropType.WATER) is None
    assert farm.plant(999, 0, CropType.WATER) is None
    with pytest.raises(TypeError):
        farm.plant(0, 1, "unknown_crop")

    assert farm.grid[0][0] is planted_crop
    assert farm.grid[0][1] is None


def test_harvesting_before_maturity_fails(farm) -> None:
    farm.plant(0, 0, CropType.FIRE)

    assert farm.harvest(0, 0) is None
    assert farm.grid[0][0] is not None


def test_harvesting_mature_crop_clears_plot(farm) -> None:
    planted_crop = farm.plant(0, 0, CropType.FIRE)
    farm.update(planted_crop.GROWTH_TIME)

    assert farm.harvest(0, 0) is planted_crop
    assert farm.grid[0][0] is None
