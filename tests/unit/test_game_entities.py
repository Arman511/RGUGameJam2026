import pygame
from elemental_game.game_entities.enemies import enemies as enemies_module
from elemental_game.game_entities.enemies.enemies import (
    ELITE_SEED_TIER_WEIGHTS,
    ENEMY_DEFS,
    OPPOSING_ELEMENTS,
    REGULAR_SEED_TIER_WEIGHTS,
    EnemyState,
    roll_enemy_seed_drop,
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
from elemental_game.types.crop import CropType
from elemental_game.types.seed import SeedType
from elemental_game.types.weather import WeatherTypes


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
    assert calls == [(("tier1", "tier2", "tier3"), REGULAR_SEED_TIER_WEIGHTS, 1)]


def test_elite_elemental_enemy_uses_elite_tier_weights(monkeypatch) -> None:
    enemy = EnemyState.create("elite_lightning", (0, 0))
    calls = []

    def choose_tier(population, *, weights, k):
        calls.append((population, weights, k))
        return ["tier3"]

    monkeypatch.setattr(enemies_module.random, "choices", choose_tier)

    assert roll_enemy_seed_drop(enemy) == (SeedType.LIGHTNING, "tier3")
    assert calls == [(("tier1", "tier2", "tier3"), ELITE_SEED_TIER_WEIGHTS, 1)]


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
    wave = build_wave_sequence(9)
    assert wave[0] == "boss"
    assert set(wave) <= ENEMY_DEFS.keys()


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


def test_elites_are_resistant_and_bosses_appear_every_third_wave() -> None:
    elite = EnemyState.create("elite_fire", (0, 0))
    boss = EnemyState.create("boss", (0, 0))

    elite.take_damage(10, CropType.AIR)
    boss.take_damage(10, CropType.FIRE)

    assert elite.health == elite.max_health - 5
    assert boss.health == boss.max_health - 5
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
        ("left", 3): 238,
        ("left", 4): 310,
        ("right", 3): 238,
        ("right", 4): 310,
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
    assert turret.projectiles[0].image is turret.projectile_image
    turret.update(10, [enemy], (0, 0), 0, False)
    assert enemy.health < enemy.max_health


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
    assert player.crops[CropType.FIRE] == 15

    system.modal_selection = UPGRADE_NAMES.index("Attack range")
    system._confirm_selection(player, slot)
    assert turret.attack_range_level == 1
    assert player.crops[CropType.FIRE] == 5


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

    assert all(f"{name} (x0)" in " ".join(rendered_text) for name in UPGRADE_NAMES[:-1])
    assert all("have 8" in text for text in rendered_text if "Fire rate" in text)


def test_inventory_hud_includes_wave_and_enemy_kill_count(monkeypatch) -> None:
    from types import SimpleNamespace

    from elemental_game.screen_rendering import hud
    from elemental_game.types.seed import SeedType

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

    assert "Current wave: 7" in rendered
    assert "Enemies killed: 14" in rendered


def test_house_roof_includes_the_mounted_turret_standing_area() -> None:
    house = House.__new__(House)
    house.dimensions = (250, 200)
    rect = house.turret_control_rect()

    assert rect.collidepoint(house.return_rect().centerx, house.return_rect().y + 20)
    assert rect.collidepoint(house.return_rect().center)


def test_elemental_turret_range_is_increased() -> None:
    assert ELEMENTAL_TURRET_RANGE > 190
