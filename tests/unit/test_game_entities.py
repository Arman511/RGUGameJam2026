from elemental_game.game_entities.enemies.enemies import ENEMY_DEFS, EnemyState
from elemental_game.game_entities.enemies.waves import build_wave_sequence
from elemental_game.game_entities.turrets.turrets import TURRET_DEFS


def test_flame_turret_has_configured_resource_cost() -> None:
    assert TURRET_DEFS["flame_turret"].cost == {"ember": 6, "droplets": 2}


def test_turret_and_enemy_definitions_have_combat_stats() -> None:
    turret = TURRET_DEFS["flame_turret"]
    enemy = ENEMY_DEFS["swarmer"]
    assert turret.damage > 0
    assert enemy.max_health == 10


def test_enemy_movement_stops_at_zero_distance() -> None:
    enemy = EnemyState(
        key="swarmer",
        health=10,
        max_health=10,
        speed=3.0,
        damage=2,
        reward=12,
    )
    enemy.distance = 0.2
    enemy.move(0.1)
    assert enemy.distance == 0.0


def test_wave_sequences_grow_and_use_known_enemies() -> None:
    wave = build_wave_sequence(4)
    assert build_wave_sequence(2) == ["swarmer"] * 4 + ["brute"]
    assert len(wave) > len(build_wave_sequence(2))
    assert set(wave) <= ENEMY_DEFS.keys()


def test_boss_wave_contains_known_enemy_types() -> None:
    wave = build_wave_sequence(10)
    assert wave[0] == "boss"
    assert set(wave) <= ENEMY_DEFS.keys()


def test_wave_sequence_is_deterministic() -> None:
    assert build_wave_sequence(3) == build_wave_sequence(3)
