import math
from unittest.mock import Mock

import pygame
from elemental_game.game_entities import enemies as enemies_module
from elemental_game.game_entities.enemies import waves as waves_module
from elemental_game.game_entities.enemies import (
    ELITE_SEED_TIER_WEIGHTS,
    ENEMY_DEFS,
    OPPOSING_ELEMENTS,
    REGULAR_SEED_TIER_WEIGHTS,
    EnemyController,
    EnemyState,
    boss_seed_drop,
    load_enemy_images,
    roll_enemy_seed_drop,
    seed_tier_drop_weights,
)
from elemental_game.game_entities.enemies.waves import (
    ENEMY_KEYS_BY_ELEMENT,
    WEATHER_CROP_TYPES,
    Waves,
    build_wave_sequence,
)
from elemental_game.game_entities.house import House
from elemental_game.game_entities.player.player import Player, PlayerType
from elemental_game.game_entities.turrets.turrets import (
    DEFINITION_BY_ELEMENT,
    ELEMENT_RANGE_COLORS,
    ELEMENTAL_TURRET_RANGE,
    PROJECTILE_ASSETS,
    TURRET_DEFS,
    UPGRADE_NAMES,
    ManualTurret,
    TurretInstance,
    TurretProjectile,
    TurretSlot,
    TurretSystem,
    _projectile_image_angle,
)
from elemental_game.screen_rendering.game import _draw_quick_action_button
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.seed import SeedType
from elemental_game.game_types.weather import WeatherTypes


def test_player_types_map_numbers_to_expected_sprite_paths() -> None:
    assert [player_type.image_path for player_type in PlayerType] == [
        "water-player.png",
        "earth-player.png",
        "lightning-player.png",
        "ice-player.png",
        "fire-player.png",
        "air-player.png",
    ]


def test_turret_and_enemy_definitions_have_combat_stats() -> None:
    turret = TURRET_DEFS["flame_turret"]
    enemy = ENEMY_DEFS["swarmer"]
    assert turret.damage > 0
    assert enemy.max_health == 10


def test_ice_and_lightning_enemies_use_their_own_sprites() -> None:
    assert ENEMY_DEFS["ice"].image == "enemy_ice.png"
    assert ENEMY_DEFS["elite_ice"].image == "enemy_ice.png"
    assert ENEMY_DEFS["lightning"].image == "enemy_lightning.png"
    assert ENEMY_DEFS["elite_lightning"].image == "enemy_lightning.png"


def test_regular_elemental_enemy_drops_matching_seed_with_weighted_tier(
    monkeypatch,
) -> None:
    enemy = EnemyState.create("ice", (0, 0))
    calls = []

    def choose_tier(population, *, weights, k):
        calls.append((population, weights, k))
        return ["tier2"]

    monkeypatch.setattr(enemies_module.random, "choices", choose_tier)

    assert roll_enemy_seed_drop(enemy) == (SeedType.ICE, "tier2")
    assert calls == [(["tier1", "tier2", "tier3"], REGULAR_SEED_TIER_WEIGHTS, 1)]


def test_elite_elemental_enemy_uses_elite_tier_weights(monkeypatch) -> None:
    enemy = EnemyState.create("elite_lightning", (0, 0))
    calls = []

    def choose_tier(population, *, weights, k):
        calls.append((population, weights, k))
        return ["tier3"]

    monkeypatch.setattr(enemies_module.random, "choices", choose_tier)

    assert roll_enemy_seed_drop(enemy) == (SeedType.LIGHTNING, "tier3")
    assert calls == [(["tier1", "tier2", "tier3"], ELITE_SEED_TIER_WEIGHTS, 1)]


def test_enemy_seed_drop_never_exceeds_that_element_unlocked_tier(
    monkeypatch,
) -> None:
    enemy = EnemyState.create("ice", (0, 0))
    calls = []

    def choose_tier(population, *, weights, k):
        calls.append((population, weights, k))
        return ["tier2"]

    monkeypatch.setattr(enemies_module.random, "choices", choose_tier)

    assert roll_enemy_seed_drop(enemy, {SeedType.ICE: 2}) == (
        SeedType.ICE,
        "tier2",
    )
    assert calls == [(["tier1", "tier2"], (50, 45), 1)]


def test_enemy_seed_drop_weight_drops_sharply_for_newly_unlocked_tiers() -> None:
    weights = seed_tier_drop_weights(5)

    assert weights == (50, 45, 15, 3.75, 0.9375)
    assert weights[3] < weights[2] / 3
    assert weights[4] < weights[3] / 3


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
    assert build_wave_sequence(2) == ["swarmer"] * 4 + ["brute", "swarmer"]
    assert len(build_wave_sequence(3)) == 7
    assert len(build_wave_sequence(6)) == 11
    assert len(wave) > len(build_wave_sequence(2))
    assert set(wave) <= ENEMY_DEFS.keys()


def test_enemy_health_scales_by_wave_and_stacks_with_wave_bonus() -> None:
    def spawned_health(wave_number: int, health_multiplier: float = 1.0) -> int:
        waves = Waves.__new__(Waves)
        waves.wave_elapsed = 0.0
        waves.wave_sequence = ["swarmer"]
        waves.wave_spawned = 0
        waves.wave_number = wave_number
        waves.active_health_multiplier = health_multiplier
        house = Mock()
        house.return_rect.return_value = pygame.Rect(0, 0, 100, 100)
        screen = pygame.Surface((200, 200))

        return waves._spawn_due_enemies(0, screen, house)[0].health

    assert [spawned_health(wave) for wave in (1, 2, 3, 10)] == [10, 11, 12, 17]
    assert spawned_health(2, 1.5) == 16


def test_boss_wave_contains_known_enemy_types() -> None:
    wave = build_wave_sequence(9)
    assert "boss" in wave
    assert "big_boss" in wave
    assert set(wave) <= ENEMY_DEFS.keys()


def test_wave_three_has_the_normal_boss_then_big_bosses_appear_every_three_waves() -> (
    None
):
    assert build_wave_sequence(3)[0] == "boss"
    assert "big_boss" not in build_wave_sequence(3)
    for wave_number in (6, 9, 12):
        assert build_wave_sequence(wave_number)[0] == "boss"
        assert build_wave_sequence(wave_number).count("big_boss") == 1
    assert [build_wave_sequence(wave).count("boss") for wave in (3, 10, 20, 30)] == [
        1,
        1,
        2,
        3,
    ]


def test_bosses_spawn_on_random_sides(monkeypatch) -> None:
    waves = Waves.__new__(Waves)
    waves.wave_elapsed = 0.0
    waves.wave_sequence = ["boss", "big_boss"]
    waves.wave_spawned = 0
    waves.wave_number = 6
    waves.active_health_multiplier = 1.0
    house = Mock()
    house.return_rect.return_value = pygame.Rect(0, 0, 100, 100)
    screen = pygame.Surface((200, 200))
    spawn_positions = iter((-30, screen.get_width() + 30))
    monkeypatch.setattr(
        waves_module.random,
        "choice",
        lambda _positions: next(spawn_positions),
    )

    bosses = waves._spawn_due_enemies(30.0, screen, house)

    assert [boss.pos.x for boss in bosses] == [-30, 230]
    assert [boss.spawn_side for boss in bosses] == ["left", "right"]


def test_big_boss_has_reduced_health_higher_resistance_and_boss_status() -> None:
    normal_boss = EnemyState.create("boss", (0, 0))
    boss = EnemyState.create("big_boss", (0, 0))

    assert normal_boss.max_health == 100
    assert boss.max_health == 270
    assert boss.max_health == 2.7 * ENEMY_DEFS["boss"].max_health
    assert boss.resistance == 0.7
    assert EnemyState.create("boss", (0, 0)).resistance == 0.45
    assert boss.is_boss
    boss.take_damage(10, CropType.FIRE)
    assert boss.health == boss.max_health - 3


def test_boss_resistance_increases_per_boss_wave_and_is_capped() -> None:
    assert math.isclose(
        EnemyState.create("boss", (0, 0), wave_number=6).resistance,
        0.47,
    )
    assert math.isclose(
        EnemyState.create("big_boss", (0, 0), wave_number=6).resistance,
        0.72,
    )
    assert EnemyState.create("boss", (0, 0), wave_number=100).resistance == 0.9
    assert EnemyState.create("big_boss", (0, 0), wave_number=100).resistance == 0.95


def test_bosses_drop_three_seeds_above_player_element_unlock() -> None:
    unlocked_tiers = {SeedType.FIRE: 4}
    assert boss_seed_drop(
        EnemyState.create("boss", (0, 0)), PlayerType.FIRE, unlocked_tiers
    ) == (
        SeedType.FIRE,
        "tier5",
        3,
    )
    assert boss_seed_drop(
        EnemyState.create("big_boss", (0, 0)), PlayerType.FIRE, unlocked_tiers
    ) == (
        SeedType.FIRE,
        "tier6",
        3,
    )


def test_big_boss_sprite_is_double_the_normal_boss_size(pygame_display) -> None:
    images = load_enemy_images()

    assert images["big_boss"].get_size() == (
        images["boss"].get_width() * 2,
        images["boss"].get_height() * 2,
    )


def test_multiplayer_modifiers_add_enemy_count_and_elemental_bias() -> None:
    baseline = build_wave_sequence(1)

    wave = build_wave_sequence(
        1,
        extra_enemies=2,
        elemental_bias=CropType.FIRE,
    )

    assert len(wave) == len(baseline) + 4
    assert wave.count("fire") == 2


def test_elemental_penalties_stack_across_multiple_attacks() -> None:
    wave = build_wave_sequence(
        1,
        elemental_biases={CropType.FIRE: 3},
        extra_enemies=12,
    )

    assert wave.count("fire") == 6
    assert wave.count("swarmer") == 15


def test_wave_sequence_is_deterministic() -> None:
    assert build_wave_sequence(3) == build_wave_sequence(3)


def test_weather_increases_the_spawn_chance_of_the_counter_element() -> None:
    baseline = build_wave_sequence(2)
    for weather, crop_type in WEATHER_CROP_TYPES.items():
        counter_element = OPPOSING_ELEMENTS[crop_type]
        counter_enemy = ENEMY_KEYS_BY_ELEMENT[counter_element]
        weather_wave = build_wave_sequence(2, weather)

        assert weather_wave.count(counter_enemy) > baseline.count(counter_enemy)


def test_weather_has_a_background_behind_its_icon() -> None:
    waves = Waves.__new__(Waves)
    waves.state = WeatherTypes.FIRE
    waves.dimensions = (55, 55)
    waves.weather_images = {
        WeatherTypes.FIRE: pygame.Surface((55, 55), pygame.SRCALPHA)
    }
    pygame.font.init()
    surface = pygame.Surface((1280, 768))
    font = pygame.font.Font(None, 36)
    waves.draw_weather(surface, font)

    assert surface.get_at((1212, 87))[:3] == (28, 34, 46)


def test_elemental_turrets_cover_every_crop_and_cost_five_matching_crops() -> None:
    assert set(DEFINITION_BY_ELEMENT) == set(CropType)
    assert all(turret.resource_cost == 5 for turret in TURRET_DEFS.values())
    assert len({turret.image for turret in TURRET_DEFS.values()}) == len(CropType)


def test_elemental_damage_matchups_and_neutral_slimes() -> None:
    lightning_enemy = EnemyState(
        key="lightning",
        health=100,
        max_health=100,
        speed=1,
        damage=1,
        reward=1,
    )
    fire_enemy = EnemyState(
        key="fire", health=100, max_health=100, speed=1, damage=1, reward=1
    )
    water_enemy = EnemyState(
        key="water", health=100, max_health=100, speed=1, damage=1, reward=1
    )
    slime = EnemyState(
        key="swarmer", health=100, max_health=100, speed=1, damage=1, reward=1
    )

    lightning_enemy.take_damage(10, CropType.EARTH)
    fire_enemy.take_damage(10, CropType.WATER)
    water_enemy.take_damage(10, CropType.EARTH)
    slime.take_damage(10, CropType.FIRE)

    assert lightning_enemy.health == 85
    assert fire_enemy.health == 85
    assert water_enemy.health == 94
    assert slime.health == 90


def test_turret_does_no_damage_to_same_element_enemies() -> None:
    enemy = EnemyState.create("elite_fire", (0, 0))

    enemy.take_damage(8, CropType.FIRE)

    assert enemy.health == enemy.max_health


def test_elites_are_resistant_and_boss_schedule_is_preserved() -> None:
    elite = EnemyState.create("elite_fire", (0, 0))
    boss = EnemyState.create("boss", (0, 0))

    elite.take_damage(10, CropType.AIR)
    boss.take_damage(10, CropType.FIRE)

    assert elite.health == elite.max_health - 5
    assert boss.health == boss.max_health - 6
    assert build_wave_sequence(3)[0] == "boss"
    assert build_wave_sequence(2)[0] != "boss"
    assert build_wave_sequence(6)[0] == "boss"


def test_turret_plot_unlock_costs_increase_from_ten_to_forty_coins() -> None:
    player = Player.__new__(Player)
    player.coins = 100
    player.turret_slots_unlocked = 0

    for expected_cost in (10, 20, 30, 40):
        assert player.next_turret_slot_cost() == expected_cost
        assert player.buy_turret_slot()

    assert player.turret_slots_unlocked == 4
    assert player.next_turret_slot_cost() is None
    assert player.coins == 100 - sum((10, 20, 30, 40))


def test_turret_slots_are_outside_both_farm_edges() -> None:
    from types import SimpleNamespace

    player = Player.__new__(Player)
    player.turret_slots_unlocked = 0
    system = TurretSystem.__new__(TurretSystem)
    system.farm = SimpleNamespace(origin=(475, 399), cols=6, rows=6)
    system.slots = []

    system._refresh_slots(player)

    left_edge = system.farm.origin[0]
    right_edge = left_edge + system.farm.cols * 55
    assert all(
        slot.center[0] + 27 < left_edge for slot in system.slots if slot.side == "left"
    )
    assert all(
        slot.center[0] - 27 > right_edge
        for slot in system.slots
        if slot.side == "right"
    )


def test_turret_action_availability_matches_interaction_range() -> None:
    from types import SimpleNamespace

    player = Player.__new__(Player)
    player.turret_slots_unlocked = 0
    player.pos = pygame.Vector2(408, 367)
    system = TurretSystem.__new__(TurretSystem)
    system.farm = SimpleNamespace(origin=(475, 399), cols=6, rows=6)
    system.slots = []
    system.modal_slot = None
    system.modal_selection = 0
    system.status_message = ""

    assert system.can_interact(player)
    assert system.modal_slot is None
    assert system.interact(player)
    assert system.modal_slot is not None

    assert system.toggle_interaction(player)
    assert system.modal_slot is None
    assert system.toggle_interaction(player)
    assert system.modal_slot is not None

    player.pos = pygame.Vector2(0, 0)
    system.close_modal()
    assert not system.can_interact(player)


def test_unlocked_turret_plot_is_added_to_the_map_slots() -> None:
    from types import SimpleNamespace

    player = Player.__new__(Player)
    player.turret_slots_unlocked = 0
    system = TurretSystem.__new__(TurretSystem)
    system.farm = SimpleNamespace(origin=(475, 399), cols=6, rows=6)
    system.slots = []

    system._refresh_slots(player)
    starting_centers = {(slot.side, slot.index): slot.center for slot in system.slots}
    player.turret_slots_unlocked = 4
    system._refresh_slots(player)

    assert len(system.slots) == 10
    assert all(
        slot.center == starting_centers[(slot.side, slot.index)]
        for slot in system.slots
        if slot.index < 3
    )
    assert {
        (slot.side, slot.index): slot.center[1]
        for slot in system.slots
        if slot.index >= 3
    } == {
        ("left", 3): 218,
        ("left", 4): 290,
        ("right", 3): 218,
        ("right", 4): 290,
    }


def test_boss_targets_a_turret_only_when_it_is_closer_than_the_house() -> None:
    system = TurretSystem.__new__(TurretSystem)
    slot = TurretSlot("left", 0, (40, 0), TurretInstance("flame_turret"))
    system.slots = [slot]

    assert system.boss_target((0, 0), (100, 0)) is slot
    assert system.boss_target((0, 0), (30, 0)) is None


def test_boss_damage_reduces_turret_health() -> None:
    system = TurretSystem.__new__(TurretSystem)
    slot = TurretSlot("left", 0, (40, 0), TurretInstance("flame_turret"))

    assert system.damage_slot(slot, 40) is False
    assert slot.turret is not None
    assert slot.turret.health == 60


def test_turret_repair_uses_matching_crop_and_restores_up_to_max_health() -> None:
    system = TurretSystem.__new__(TurretSystem)
    turret = TurretInstance("flame_turret", health=90)
    slot = TurretSlot("right", 0, (0, 0), turret)
    player = Player.__new__(Player)
    player.crops = {CropType.FIRE: 1}
    system.status_message = ""
    system.modal_selection = UPGRADE_NAMES.index("Repair turret")

    system._confirm_selection(player, slot)

    assert turret.health == TurretInstance.MAX_HEALTH
    assert player.crops[CropType.FIRE] == 0

    system._confirm_selection(player, slot)

    assert turret.health == TurretInstance.MAX_HEALTH
    assert player.crops[CropType.FIRE] == 0
    assert system.status_message == "Turret is already at full health."


def test_turret_repair_requires_one_matching_crop() -> None:
    system = TurretSystem.__new__(TurretSystem)
    turret = TurretInstance("flame_turret", health=60)
    slot = TurretSlot("right", 0, (0, 0), turret)
    player = Player.__new__(Player)
    player.crops = {CropType.FIRE: 0}
    system.status_message = ""
    system.modal_selection = UPGRADE_NAMES.index("Repair turret")

    system._confirm_selection(player, slot)

    assert turret.health == 60
    assert player.crops[CropType.FIRE] == 0
    assert system.status_message == "Need 1 fire crops."


def test_boss_damage_is_a_percentage_of_house_max_health(monkeypatch) -> None:
    house = Mock()
    house.max_hp = 250
    house.return_rect.return_value = pygame.Rect(-50, -50, 100, 100)
    turrets = Mock()
    turrets.boss_target.return_value = None
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    boss = EnemyState.create("boss", (0, 0))

    EnemyController.update(
        0.1, [boss], house, turrets, Mock(), pygame.Surface((100, 100)), False
    )

    house.take_damage.assert_called_once_with(25)


def test_big_boss_damage_is_a_percentage_of_turret_max_health(monkeypatch) -> None:
    house = Mock()
    house.return_rect.return_value = pygame.Rect(250, -50, 100, 100)
    slot = TurretSlot("left", 0, (40, 0), TurretInstance("flame_turret"))
    turrets = Mock()
    turrets.boss_target.return_value = slot
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    boss = EnemyState.create("big_boss", (0, 0))

    EnemyController.update(
        0.1, [boss], house, turrets, Mock(), pygame.Surface((100, 100)), False
    )

    turrets.damage_slot.assert_called_once_with(
        slot,
        math.ceil(TurretInstance.MAX_HEALTH * 0.3),
    )


def test_regular_enemy_uses_house_or_turret_target_chance(monkeypatch) -> None:
    house = Mock()
    house.return_rect.return_value = pygame.Rect(900, 900, 100, 100)
    turrets = Mock()
    turrets.nearest_turret.return_value = TurretSlot(
        "left", 0, (100, 0), TurretInstance("flame_turret")
    )
    screen = pygame.Surface((1000, 1000))
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    enemy = EnemyState.create("swarmer", (0, 0))

    monkeypatch.setattr(enemies_module.random, "random", lambda: 0.29)
    EnemyController.update(0.1, [enemy], house, turrets, Mock(), screen, False)

    assert enemy.target_turret is True
    assert enemy.pos.y == 0

    enemy = EnemyState.create("swarmer", (0, 0))
    monkeypatch.setattr(enemies_module.random, "random", lambda: 0.3)
    EnemyController.update(0.1, [enemy], house, turrets, Mock(), screen, False)

    assert enemy.target_turret is False
    assert enemy.pos.x > 0
    assert enemy.pos.y > 0


def test_normal_enemies_only_target_turrets_on_their_spawn_side(monkeypatch) -> None:
    house = Mock()
    house.return_rect.return_value = pygame.Rect(900, 900, 100, 100)
    left_turret = TurretSlot("left", 0, (-100, 0), TurretInstance("flame_turret"))
    right_turret = TurretSlot("right", 0, (20, 0), TurretInstance("flame_turret"))
    turrets = TurretSystem.__new__(TurretSystem)
    turrets.slots = [left_turret, right_turret]
    turrets.update = Mock()
    turrets.damage_slot = Mock()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    monkeypatch.setattr(enemies_module.random, "random", lambda: 0.1)

    enemy = EnemyState.create("swarmer", (0, 0))
    enemy.spawn_side = "left"
    EnemyController.update(
        0.1, [enemy], house, turrets, Mock(), pygame.Surface((1000, 1000)), False
    )

    assert enemy.target_turret is True
    assert enemy.pos.x < 0
    turrets.damage_slot.assert_not_called()

    turrets.slots = [right_turret]
    enemy = EnemyState.create("swarmer", (0, 0))
    enemy.spawn_side = "left"
    EnemyController.update(
        0.1, [enemy], house, turrets, Mock(), pygame.Surface((1000, 1000)), False
    )

    assert enemy.target_turret is False
    assert enemy.pos.x > 0
    assert enemy.pos.y > 0


def test_enemy_without_turrets_falls_back_to_house(monkeypatch) -> None:
    house = Mock()
    house.return_rect.return_value = pygame.Rect(-50, -50, 100, 100)
    turrets = Mock()
    turrets.nearest_turret.return_value = None
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    enemy = EnemyState.create("swarmer", (0, 0))

    EnemyController.update(
        0.1, [enemy], house, turrets, Mock(), pygame.Surface((100, 100)), False
    )

    assert enemy.target_turret is False
    house.take_damage.assert_called_once_with(enemy.damage)


def test_enemy_damages_turrets_more_when_elementally_strong(monkeypatch) -> None:
    house = Mock()
    house.return_rect.return_value = pygame.Rect(900, 900, 100, 100)
    slot = TurretSlot("left", 0, (40, 0), TurretInstance("wind_turbine"))
    turrets = Mock()
    turrets.nearest_turret.return_value = slot
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: ())
    monkeypatch.setattr(enemies_module.random, "random", lambda: 0.1)
    enemy = EnemyState.create("fire", (0, 0))

    EnemyController.update(
        0.1, [enemy], house, turrets, Mock(), pygame.Surface((100, 100)), False
    )

    turrets.damage_slot.assert_called_once_with(slot, math.ceil(enemy.damage * 1.5))


def test_manual_turret_can_hit_targets_at_unlimited_range() -> None:
    no_target_turret = ManualTurret.__new__(ManualTurret)
    no_target_turret.angle = 0
    no_target_turret.cooldown = 0
    no_target_turret.damage_level = 0
    no_target_turret.fire_rate_level = 0
    no_target_turret.projectiles = []
    no_target_turret.projectile_image = pygame.Surface((18, 18))
    outside_cone = EnemyState.create("swarmer", (0, 5000))
    no_target_turret.update(
        0.01, [outside_cone], (50, 50), 0, True, pygame.Rect(0, 0, 100, 100)
    )
    assert len(no_target_turret.projectiles) == 1
    assert no_target_turret.projectiles[0].position.x < 50
    no_target_turret.update(
        0.2, [outside_cone], (50, 50), 0, False, pygame.Rect(0, 0, 100, 100)
    )
    assert not no_target_turret.projectiles

    turret = ManualTurret.__new__(ManualTurret)
    turret.angle = 0
    turret.cooldown = 0
    turret.damage_level = 0
    turret.fire_rate_level = 0
    turret.projectiles = []
    turret.projectile_image = pygame.Surface((18, 18))
    enemy = EnemyState.create("swarmer", (5000, 0))

    turret.update(0.01, [enemy], (0, 0), 0, True)

    assert enemy.health == enemy.max_health
    assert len(turret.projectiles) == 1
    assert turret.projectiles[0].damage == 5
    assert turret.projectiles[0].image is turret.projectile_image
    slime = EnemyState.create("swarmer", (0, 0))
    slime.take_damage(turret.projectiles[0].damage)
    assert slime.health == 5
    slime.take_damage(turret.projectiles[0].damage)
    assert slime.health == 0
    turret.update(10, [enemy], (0, 0), 0, False)
    assert enemy.health < enemy.max_health


def test_manual_turret_rotation_speed_controls_movement_sensitivity() -> None:
    turret = ManualTurret.__new__(ManualTurret)
    turret.angle = 0.0
    turret.rotation_speed = 90.0
    turret.cooldown = 1.0
    turret.projectiles = []

    turret.update(0.5, [], (0, 0), 1, False)

    assert turret.angle == 45.0


def test_game_loop_applies_saved_manual_turret_sensitivity() -> None:
    from types import SimpleNamespace

    from elemental_game.application.game_loop import GameLoop

    game_loop = GameLoop.__new__(GameLoop)
    turret = SimpleNamespace(rotation_speed=ManualTurret.ROTATION_SPEED)
    game_loop.game = SimpleNamespace(house=SimpleNamespace(turret=turret))
    game_loop.menus = SimpleNamespace(
        store=SimpleNamespace(manual_turret_sensitivity=lambda: 0.75)
    )

    game_loop._apply_manual_turret_sensitivity()

    assert turret.rotation_speed == 210.0


def test_manual_turret_laser_sight_marks_aim_direction() -> None:
    turret = ManualTurret.__new__(ManualTurret)
    turret.angle = 0
    surface = pygame.Surface((100, 100))

    turret.draw_laser_sight(surface, (50, 50))

    assert surface.get_at((77, 50))[:3] == (255, 0, 0)
    assert surface.get_at((23, 50))[:3] == (0, 0, 0)
    assert surface.get_at((99, 50))[:3] == (255, 230, 230)


def test_projectile_sprite_aligns_with_its_direction() -> None:
    assert _projectile_image_angle(pygame.Vector2(0, -1)) == 0
    assert _projectile_image_angle(pygame.Vector2(1, 0)) == -90


def test_elemental_turret_projectile_uses_its_element_sprite_and_hits_on_arrival() -> (
    None
):
    import pygame

    element = CropType.FIRE
    system = TurretSystem.__new__(TurretSystem)
    system.projectiles = []
    system._projectile_images = {
        crop: pygame.Surface((18, 18)) for crop in PROJECTILE_ASSETS
    }
    system.slots = [TurretSlot("left", 0, (0, 0), TurretInstance("flame_turret"))]
    enemy = EnemyState.create("swarmer", (-100, 0))

    system.update(0.01, [enemy])

    assert enemy.health == enemy.max_health
    assert system.projectiles[0].image is system._projectile_images[element]
    assert PROJECTILE_ASSETS[element] == "fire-pellet.png"
    system.update(1, [])
    assert enemy.health < enemy.max_health
    assert not system.projectiles


def test_same_element_turret_projectile_does_no_damage_to_matching_elite() -> None:
    system = TurretSystem.__new__(TurretSystem)
    system.projectiles = []
    system._projectile_images = {
        crop: pygame.Surface((18, 18)) for crop in PROJECTILE_ASSETS
    }
    system.slots = [TurretSlot("left", 0, (0, 0), TurretInstance("flame_turret"))]
    enemy = EnemyState.create("elite_fire", (-100, 0))

    system.update(0.01, [enemy])
    system.update(1.0, [])

    assert enemy.health == enemy.max_health


def test_turret_ranges_are_enabled_by_default(pygame_display) -> None:
    system = TurretSystem(None)

    assert system.show_ranges


def test_elemental_projectile_applies_slow_and_knockback_on_impact() -> None:
    enemy = EnemyState.create("swarmer", (100, 0))
    original_speed = enemy.speed
    projectile = TurretProjectile(
        position=pygame.Vector2(0, 0),
        target=enemy,
        image=pygame.Surface((18, 18)),
        damage=5,
        element=CropType.EARTH,
        slow=0.4,
        knockback=30,
        direction=pygame.Vector2(1, 0),
    )

    assert projectile.update(1.0)
    assert enemy.health < enemy.max_health
    assert enemy.speed == original_speed * 0.6
    assert enemy.pos.x == 130

    enemy.update_status_effects(1.0)
    assert enemy.speed == original_speed
    assert enemy.slow_timer == 0


def test_earth_enemies_and_boss_resist_knockback_more() -> None:
    earth_enemies = (
        EnemyState.create("brute", (0, 0)),
        EnemyState.create("elite_earth", (0, 0)),
    )
    boss = EnemyState.create("boss", (0, 0))
    regular_enemy = EnemyState.create("fire", (0, 0))

    for enemy in (*earth_enemies, boss):
        enemy.apply_knockback((1, 0), 40)
    regular_enemy.apply_knockback((1, 0), 40)

    assert [enemy.pos.x for enemy in earth_enemies] == [20, 20]
    assert boss.pos.x == 10
    assert regular_enemy.pos.x == 40


def test_turret_attack_radius_and_range_upgrades_cost_crops_and_take_effect() -> None:
    system = TurretSystem.__new__(TurretSystem)
    turret = TurretInstance("flame_turret")
    slot = TurretSlot("right", 0, (0, 0), turret)
    player = Player.__new__(Player)
    player.crops = {CropType.FIRE: 20}
    system.status_message = ""

    system.modal_selection = UPGRADE_NAMES.index("Attack radius")
    system._confirm_selection(player, slot)
    assert turret.attack_radius_level == 1
    assert player.crops[CropType.FIRE] == 13

    system.modal_selection = UPGRADE_NAMES.index("Attack range")
    system._confirm_selection(player, slot)
    assert turret.attack_range_level == 1
    assert player.crops[CropType.FIRE] == 4


def test_turret_menu_navigation_supports_w_s_and_mouse_wheel() -> None:
    system = TurretSystem.__new__(TurretSystem)
    system.modal_slot = TurretSlot("right", 0, (0, 0), None)
    system.modal_selection = 0
    player = Mock()
    screen = pygame.Surface((100, 100))

    system.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s), player, screen
    )
    assert system.modal_selection == 1

    system.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w), player, screen
    )
    assert system.modal_selection == 0

    system.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), player, screen)
    assert system.modal_selection == 1

    system.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1), player, screen)
    assert system.modal_selection == 0


def test_turret_menu_confirms_purchase_with_space_and_enter() -> None:
    for key in (pygame.K_SPACE, pygame.K_RETURN):
        system = TurretSystem.__new__(TurretSystem)
        slot = TurretSlot("right", 0, (0, 0), None)
        system.modal_slot = slot
        system.modal_selection = 0
        player = Mock()
        player.crops = {
            element: definition.resource_cost
            for element, definition in DEFINITION_BY_ELEMENT.items()
        }

        system.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=key),
            player,
            pygame.Surface((100, 100)),
        )

        assert slot.turret is not None


def test_upgraded_turret_attacks_targets_in_extended_radius_and_range() -> None:
    for enemy_position, upgrade_field in (
        ((0, 80), "attack_radius_level"),
        ((230, 0), "attack_range_level"),
    ):
        system = TurretSystem.__new__(TurretSystem)
        turret = TurretInstance("flame_turret")
        setattr(turret, upgrade_field, 1)
        system.slots = [TurretSlot("right", 0, (0, 0), turret)]
        system.projectiles = []
        system._projectile_images = {CropType.FIRE: pygame.Surface((18, 18))}
        enemy = EnemyState.create("swarmer", enemy_position)

        system.update(0.01, [enemy])

        assert len(system.projectiles) == 1


def test_turret_attack_overlay_is_filled_and_uses_element_color() -> None:
    system = TurretSystem.__new__(TurretSystem)
    overlay = pygame.Surface((500, 500), pygame.SRCALPHA)
    slot = TurretSlot("right", 0, (100, 250), TurretInstance("flame_turret"))

    system._draw_range(overlay, slot)

    assert overlay.get_at((200, 250)) == (*ELEMENT_RANGE_COLORS[CropType.FIRE], 58)
    assert overlay.get_at((200, 250)).a > 50


def test_turret_quick_action_uses_the_same_background_as_other_buttons() -> None:
    surface = pygame.Surface((80, 80))
    background = (67, 86, 69)

    _draw_quick_action_button(
        surface,
        pygame.Rect(10, 10, 56, 56),
        pygame.Surface((1, 1)),
        enabled=True,
        hovered=False,
    )

    assert surface.get_at((15, 15))[:3] == background


def test_disabled_turret_quick_action_keeps_a_yellow_border() -> None:
    surface = pygame.Surface((80, 80))
    background = (65, 65, 65)
    border = (255, 225, 100)

    _draw_quick_action_button(
        surface,
        pygame.Rect(10, 10, 56, 56),
        pygame.Surface((1, 1)),
        enabled=False,
        hovered=False,
        border_color=border,
        border_width=1,
    )

    assert surface.get_at((15, 15))[:3] == background
    assert surface.get_at((38, 10))[:3] == border
    assert surface.get_at((38, 11))[:3] == background


def test_turret_upgrade_menu_displays_current_upgrade_levels() -> None:
    rendered_text = []

    class Font:
        def render(self, text, *_args):
            rendered_text.append(text)
            return pygame.Surface((1, 1), pygame.SRCALPHA)

    system = TurretSystem.__new__(TurretSystem)
    system.modal_slot = TurretSlot("right", 0, (0, 0), TurretInstance("flame_turret"))
    system.modal_selection = 0
    system.status_message = ""
    from types import SimpleNamespace

    system._draw_modal(
        pygame.Surface((1280, 768)),
        Font(),
        SimpleNamespace(crops={CropType.FIRE: 8}),
    )

    assert all(f"{name} (x0)" in " ".join(rendered_text) for name in UPGRADE_NAMES[:6])
    assert all("have 8" in text for text in rendered_text if "Fire rate" in text)
    assert any("Repair turret (+25 health)" in text for text in rendered_text)


def test_inventory_hud_includes_wave_and_enemy_kill_count(monkeypatch) -> None:
    from types import SimpleNamespace

    from elemental_game.screen_rendering import hud
    from elemental_game.game_types.seed import SeedType

    rendered = []

    class Font:
        def render(self, text, *_args):
            rendered.append(text)
            return pygame.Surface((1, 1), pygame.SRCALPHA)

    monkeypatch.setattr(hud.pygame.font, "Font", lambda *_args: Font())
    player = SimpleNamespace(
        coins=10,
        seeds={
            SeedType[crop.name]: {"tier1": 0, "tier2": 0, "tier3": 0}
            for crop in CropType
        },
        crops={},
    )

    hud.draw_inventory_hud(pygame.Surface((800, 600)), player, 7, 14)

    assert "Coins: 10" not in rendered
    assert "10" in rendered
    assert "Fire T1" in rendered
    assert "Current wave: 7" in rendered
    assert "Enemies killed: 14" in rendered
    assert not any(text.startswith("T1:") for text in rendered)


def test_house_roof_includes_the_mounted_turret_standing_area() -> None:
    house = House.__new__(House)
    house.dimensions = (250, 200)
    rect = house.turret_control_rect()

    assert rect.collidepoint(house.return_rect().centerx, house.return_rect().y + 20)
    assert rect.collidepoint(house.return_rect().center)


def test_elemental_turret_range_is_increased() -> None:
    assert ELEMENTAL_TURRET_RANGE > 190
