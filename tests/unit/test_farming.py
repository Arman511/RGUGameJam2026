from elemental_game.farm import Farm


def test_planting_on_empty_plot_succeeds() -> None:
    farm = Farm()
    assert farm.plant(0, "ember_root") is True
    assert farm.plots[0].crop is not None


def test_invalid_planting_leaves_existing_crops_unchanged() -> None:
    farm = Farm()
    assert farm.plant(0, "ember_root") is True
    planted_crop = farm.plots[0].crop
    assert farm.plant(0, "mist_leaf") is False
    assert farm.plant(999, "mist_leaf") is False
    assert farm.plant(1, "unknown_crop") is False
    assert farm.plots[0].crop is planted_crop
    assert farm.plots[1].crop is None


def test_harvesting_before_maturity_fails() -> None:
    farm = Farm()
    assert farm.plant(0, "ember_root") is True
    assert farm.harvest(0) is None


def test_harvesting_mature_crop_clears_plot() -> None:
    farm = Farm()
    assert farm.plant(0, "ember_root") is True
    farm.tick(4.0)
    assert farm.harvest(0) == "ember_root"
    assert farm.plots[0].crop is None
