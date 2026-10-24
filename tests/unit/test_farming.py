from game_core.simulation import Simulation

def test_planting_on_empty_plot_succeeds() -> None:
    sim = Simulation()
    assert sim.plant_crop(0, "ember_root") is True
    assert sim.farm.plots[0].crop is not None

def test_planting_on_occupied_or_invalid_plot_fails_without_charging_resources() -> None:
    sim = Simulation()
    sim.plant_crop(0, "ember_root")
    before = sim.resources.snapshot()
    assert sim.plant_crop(0, "mist_leaf") is False
    assert sim.resources.snapshot() == before
    assert sim.plant_crop(999, "mist_leaf") is False

def test_harvesting_before_maturity_fails() -> None:
    sim = Simulation()
    sim.plant_crop(0, "ember_root")
    assert sim.harvest_crop(0) is False

def test_harvesting_after_maturity_awards_expected_resource() -> None:
    sim = Simulation()
    sim.plant_crop(0, "ember_root")
    sim.advance(10.0)
    assert sim.harvest_crop(0) is True
    assert sim.resources["ember"] >= 10
