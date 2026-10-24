from game_core.simulation import Simulation

def test_insufficient_resources_prevent_construction() -> None:
    sim = Simulation()
    sim.resources["ember"] = 0
    assert sim.build_turret("flame_turret", 0) is False

def test_turret_attacks_reduce_enemy_health() -> None:
    sim = Simulation()
    sim._spawn_enemy("swarmer")
    sim.turrets[0] = type("T", (), {"key": "flame_turret", "cooldown": 0.0, "last_target_id": None})()
    sim.enemies[0].distance = 30.0
    sim.advance(0.5)
    assert sim.enemies[0].health < 10

def test_enemies_damage_the_farmhouse_when_reaching_it() -> None:
    sim = Simulation()
    sim._spawn_enemy("swarmer")
    sim.enemies[0].distance = 0.0
    sim.advance(0.1)
    assert sim.farmhouse_health < 30

def test_wave_progression_and_scaling_work() -> None:
    sim = Simulation()
    sim.start_wave(2)
    assert sim.wave_number == 2
    assert len(sim.wave_queue) > 0

def test_farmhouse_defeat_ends_the_run() -> None:
    sim = Simulation()
    sim.farmhouse_health = 0
    sim.advance(0.1)
    assert sim.game_over is True

def test_deterministic_seeded_simulation() -> None:
    sim1 = Simulation(seed=7)
    sim2 = Simulation(seed=7)
    sim1.start_wave(3)
    sim2.start_wave(3)
    assert len(sim1.wave_queue) == len(sim2.wave_queue)
