import argparse
import atexit
import math
import os
import sys
from collections.abc import Sequence
from uuid import uuid4

import pygame

from elemental_game import config
from elemental_game.audio import play_background_music
from elemental_game.game_entities.enemies.enemies import (
    EnemyState,
    load_enemy_images,
    roll_enemy_seed_drop,
)
from elemental_game.game_entities.enemies.waves import Waves, build_wave_sequence
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.house import House
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.shop import ShopMenu
from elemental_game.game_entities.turrets.turrets import TurretSystem
from elemental_game.instance_lock import GameInstanceLock
from elemental_game.menus import MenuSystem
from elemental_game.multiplayer import MultiplayerError
from elemental_game.screen_rendering.exit_confirmation import draw_exit_confirmation
from elemental_game.screen_rendering.game_over import GameOverDialog
from elemental_game.screen_rendering.hud import draw_inventory_hud
from elemental_game.screen_rendering.multiplayer_game_over import (
    MultiplayerGameOverDialog,
)
from elemental_game.types.crop import CropType
from elemental_game.types.player import PlayerType
from elemental_game.types.weather import WeatherTypes
from elemental_game.game_entities.house import HouseState

MULTIPLAYER_COIN_COSTS = {"extra_enemies": 6, "tougher_enemies": 8}
_game_instance_lock = GameInstanceLock()
try:
    if not _game_instance_lock.acquire():
        print("Elemental Keep is already running.", file=sys.stderr)
        raise SystemExit(0)
except OSError as error:
    print(f"Could not create the game instance lock: {error}", file=sys.stderr)
    raise SystemExit(1) from error
atexit.register(_game_instance_lock.release)

# Initialise pygame attributes and use a larger audio buffer to reduce
# underruns on slower audio backends such as WSL.
pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=4096)
pygame.init()
pygame.display.set_icon(pygame.image.load(os.path.join(config.ASSETS_DIR, "icon.ico")))
screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(os.path.join(config.ASSETS_DIR, "font", "pixelfont.ttf"), 22)
game_background = pygame.transform.smoothscale(
    pygame.image.load(
        os.path.join(config.IMAGES_DIR, "backgrounds", "background.png")
    ).convert(),
    screen.get_size(),
)


# login / main menu / leaderboard / settings (menus.py)
# returns True when they press Play, False if they close the window
def _create_game(screen, player_type):
    farm = Farm(
        *config.FARM_DIMENSIONS,
        origin=(
            (screen.get_width() - config.FARM_DIMENSIONS[1] * config.TILE_SIZE) // 2,
            config.FARM_HEIGHT,
        ),
    )
    player = Player(player_type=PlayerType(player_type), pos=farm.tile_rect(0, 3).center)
    return farm, player


def _draw_quick_action_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    icon: pygame.Surface,
    *,
    enabled: bool,
    hovered: bool,
) -> None:
    background = (67, 86, 69) if enabled else (65, 65, 65)
    border = (225, 230, 215) if enabled and hovered else (145, 150, 145)
    pygame.draw.rect(surface, background, rect, border_radius=9)
    pygame.draw.rect(surface, border, rect, 2, border_radius=9)
    max_icon_width = rect.width - 14
    max_icon_height = rect.height - 14
    scale = min(
        max_icon_width / icon.get_width(),
        max_icon_height / icon.get_height(),
        1.0,
    )
    if scale < 1:
        icon = pygame.transform.smoothscale(
            icon,
            (
                max(1, round(icon.get_width() * scale)),
                max(1, round(icon.get_height() * scale)),
            ),
        )
    icon_rect = icon.get_rect(center=rect.center)
    surface.blit(icon, icon_rect)
    if not enabled:
        overlay = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        overlay.fill((75, 75, 75, 155))
        surface.blit(overlay, icon_rect)


def _draw_quick_action_tooltip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    button_rect: pygame.Rect,
    label: str,
) -> None:
    text = font.render(label, True, (255, 255, 255))
    tooltip = pygame.Rect(
        0,
        0,
        text.get_width() + 20,
        text.get_height() + 12,
    )
    tooltip.midbottom = (button_rect.centerx, button_rect.top - 8)
    tooltip.clamp_ip(surface.get_rect())
    pygame.draw.rect(surface, (30, 35, 42), tooltip, border_radius=5)
    pygame.draw.rect(surface, (190, 200, 210), tooltip, 1, border_radius=5)
    surface.blit(text, text.get_rect(center=tooltip.center))


def _multiplayer_attack_panel_rect(surface: pygame.Surface) -> pygame.Rect:
    panel = pygame.Rect(665, 170, 470, 300)
    panel.clamp_ip(surface.get_rect())
    return panel


def _send_multiplayer_attack(action, selected_attack_element, player, multiplayer):
    element = (
        selected_attack_element
        if action in {"elemental_chance", "change_weather"}
        else None
    )
    if action in {"elemental_chance", "change_weather"} and (
        element is None or player.crops.get(element, 0) <= 0
    ):
        return "Harvest an elemental crop first."
    if action in MULTIPLAYER_COIN_COSTS and player.coins < MULTIPLAYER_COIN_COSTS[action]:
        return "Not enough coins for that attack."
    if multiplayer is None:
        return "Multiplayer attacks are unavailable."
    try:
        multiplayer.send_action(
            action, element.name if element is not None else None
        )
    except MultiplayerError as error:
        return str(error)

    if action in MULTIPLAYER_COIN_COSTS:
        player.deduct_coins(MULTIPLAYER_COIN_COSTS[action])
    elif element is not None:
        player.crops[element] -= 1
    return "Attack sent for the next wave."


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play Elemental Keep.")
    parser.add_argument(
        "--skip-menu",
        action="store_true",
        help="Start the game immediately, using a saved login or playing as a guest.",
    )
    args = parser.parse_args(argv)

    menus = MenuSystem(screen)
    if args.skip_menu:
        if menus.username is None:
            menus._continue_as_guest()
        running = True
    else:
        running = menus.run()

    if not running:
        _game_instance_lock.release()
        pygame.quit()
        return

    multiplayer = menus.multiplayer_client if menus.game_mode == "multiplayer" else None
    quick_action_size = 56
    quick_action_y = screen.get_height() - quick_action_size - 18
    quick_action_buttons = {
        "store": pygame.Rect(16, quick_action_y, quick_action_size, quick_action_size),
        "hud": pygame.Rect(78, quick_action_y, quick_action_size, quick_action_size),
        "turret": pygame.Rect(
            140, quick_action_y, quick_action_size, quick_action_size
        ),
        "attack": pygame.Rect(
            202, quick_action_y, quick_action_size, quick_action_size
        ),
    }
    quick_action_icons = {
        "store": pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(
                    config.IMAGES_DIR, "settings-and-gameplay", "store-icon.png"
                )
            ).convert_alpha(),
            (42, 42),
        ),
        "hud": pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(config.IMAGES_DIR, "settings-and-gameplay", "hud.png")
            ).convert_alpha(),
            (42, 42),
        ),
        "turret": pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(config.IMAGES_DIR, "turrets", "standard-turret.png")
            ).convert_alpha(),
            (42, 42),
        ),
        "attack": pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(config.IMAGES_DIR, "settings-and-gameplay", "attack.png")
            ).convert_alpha(),
            (42, 42),
        ),
    }
    farm, player = _create_game(screen, menus.store.player_image_number())
    shop = ShopMenu()
    house = House(screen)
    turrets = TurretSystem(farm)
    enemy_images = load_enemy_images()
    phase_icons = {
        "planting": pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(
                    config.IMAGES_DIR, "settings-and-gameplay", "soil_plant.png"
                )
            ).convert_alpha(),
            (48, 48),
        ),
        "enemy": pygame.transform.smoothscale(enemy_images["swarmer"], (48, 48)),
    }
    enemy_marker_background = pygame.Surface((60, 60), pygame.SRCALPHA)
    pygame.draw.rect(
        enemy_marker_background,
        (24, 32, 46, 185),
        enemy_marker_background.get_rect(),
        border_radius=9,
    )
    pygame.draw.rect(
        enemy_marker_background,
        (145, 165, 190, 190),
        enemy_marker_background.get_rect(),
        1,
        border_radius=9,
    )
    waves = Waves(house)
    farm.weather_crop_type = waves.crop_type
    shop_open = False
    hud_visible = False
    confirm_exit = False
    planting_phase = True
    phase_remaining = config.PLANTING_PHASE_DURATION
    wave_number = 0
    wave_sequence = []
    wave_spawned = 0
    wave_elapsed = 0.0
    enemies = []
    controlling_house_turret = False
    run_id = uuid4().hex
    run_elapsed = 0.0
    enemies_defeated = 0
    game_over_dialog = None
    multiplayer_panel_open = False
    multiplayer_status = ""
    pending_extra_enemies = 0
    pending_health_multiplier = 1.0
    active_health_multiplier = 1.0
    pending_elemental_bias: dict[CropType, int] = {}
    pending_weather: WeatherTypes | None = None
    selected_attack_element: CropType | None = next(
        (crop for crop, count in player.crops.items() if count > 0),
        None,
    )
    multiplayer_result_sent = False

    clock.tick()
    while running:
        if house.health <= 0 and game_over_dialog is None and multiplayer is None:
            game_over_dialog = GameOverDialog(
                screen,
                font,
                menus,
                run_id=run_id,
                survival_time=run_elapsed,
                final_wave=wave_number,
                enemies_defeated=enemies_defeated,
            )
        seconds = clock.tick(60) / 1000  # seconds since last frame
        if multiplayer is not None:
            try:
                for message in multiplayer.poll():
                    payload = message["payload"]
                    if message["type"] == "opponent_action":
                        action = payload["action"]
                        element_name = payload.get("element")
                        if action == "extra_enemies":
                            pending_extra_enemies += 4
                            multiplayer_status = "Opponent sent extra enemies."
                        elif action == "tougher_enemies":
                            pending_health_multiplier += 0.5
                            multiplayer_status = "Opponent toughened the next wave."
                        elif (
                            action == "elemental_chance"
                            and element_name in CropType.__members__
                        ):
                            element = CropType[element_name]
                            pending_elemental_bias[element] = (
                                pending_elemental_bias.get(element, 0) + 1
                            )
                            multiplayer_status = (
                                f"Next wave has more {element_name.lower()} enemies."
                            )
                        elif (
                            action == "change_weather"
                            and element_name in CropType.__members__
                        ):
                            pending_weather = (
                                WeatherTypes.WINDS
                                if element_name == "AIR"
                                else WeatherTypes[element_name]
                            )
                            multiplayer_status = f"Opponent changed next wave weather to {element_name.lower()}."
                    elif message["type"] == "match_ended":
                        if game_over_dialog is None:
                            game_over_dialog = MultiplayerGameOverDialog(
                                screen, font, payload["result"]
                            )
                    elif message["type"] == "opponent_disconnected":
                        multiplayer_status = "Opponent disconnected."
                        if game_over_dialog is None:
                            game_over_dialog = MultiplayerGameOverDialog(
                                screen, font, "defeat"
                            )
                    elif message["type"] == "error":
                        multiplayer_status = payload["message"]
            except MultiplayerError as error:
                multiplayer_status = str(error)
                multiplayer.close()
                multiplayer = None
                menus.multiplayer_client = None
        if (
            multiplayer is not None
            and house.health <= 0
            and not multiplayer_result_sent
        ):
            try:
                multiplayer.end_match()
            except MultiplayerError as error:
                multiplayer_status = str(error)
                game_over_dialog = MultiplayerGameOverDialog(screen, font, "defeat")
            multiplayer_result_sent = True
        tile = farm.tile_at_pixel(*player.pos)  # tile the player is standing on

        # Handle keyboard and mouse inputs.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif (
                game_over_dialog is None
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                clicked_action = next(
                    (
                        action
                        for action, rect in quick_action_buttons.items()
                        if rect.collidepoint(event.pos)
                    ),
                    None,
                )
                if clicked_action is not None:
                    actions_enabled = (
                        not confirm_exit
                        and not farm.planting
                        and turrets.modal_slot is None
                        and not controlling_house_turret
                        and game_over_dialog is None
                        and house.health > 0
                    )
                    if actions_enabled:
                        if clicked_action == "store":
                            shop_open = not shop_open
                            shop.clear_status()
                        elif clicked_action == "hud":
                            hud_visible = not hud_visible
                        elif clicked_action == "turret" and turrets.can_interact(
                            player
                        ):
                            turrets.interact(player)
                        elif clicked_action == "attack" and multiplayer is not None:
                            multiplayer_panel_open = not multiplayer_panel_open
                            available = [
                                crop
                                for crop, count in player.crops.items()
                                if count > 0
                            ]
                            if selected_attack_element not in available:
                                selected_attack_element = (
                                    available[0] if available else None
                                )
                    continue
                if shop_open:
                    shop.handle_event(event, player, farm, house, screen)
                    continue
                if turrets.modal_slot is not None:
                    turrets.handle_event(event, player, screen)
                    continue
                if multiplayer_panel_open:
                    panel = _multiplayer_attack_panel_rect(screen)
                    attack_actions = (
                        "extra_enemies",
                        "tougher_enemies",
                        "elemental_chance",
                        "change_weather",
                    )
                    for index, action in enumerate(attack_actions, start=2):
                        row = pygame.Rect(
                            panel.x + 10,
                            panel.y + 25 + index * 42,
                            panel.width - 20,
                            42,
                        )
                        if row.collidepoint(event.pos):
                            multiplayer_status = _send_multiplayer_attack(
                                action,
                                selected_attack_element,
                                player,
                                multiplayer,
                            )
                            break
                continue
            elif confirm_exit and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    confirm_exit = False
                    if multiplayer is not None:
                        multiplayer.close()
                        multiplayer = None
                        menus.multiplayer_client = None
                    running = menus.run()
                    if running:
                        multiplayer = (
                            menus.multiplayer_client
                            if menus.game_mode == "multiplayer"
                            else None
                        )
                        farm, player = _create_game(
                            screen, menus.store.player_image_number()
                        )
                        shop = ShopMenu()
                        house = House(screen)
                        turrets = TurretSystem(farm)
                        enemies = []
                        planting_phase = True
                        phase_remaining = config.PLANTING_PHASE_DURATION
                        wave_number = 0
                        wave_sequence = []
                        wave_spawned = 0
                        wave_elapsed = 0.0
                        controlling_house_turret = False
                        run_id = uuid4().hex
                        run_elapsed = 0.0
                        enemies_defeated = 0
                        game_over_dialog = None
                        waves = Waves(house)
                        farm.weather_crop_type = waves.crop_type
                        shop_open = False
                        hud_visible = False
                        multiplayer_panel_open = False
                        multiplayer_status = ""
                        pending_extra_enemies = 0
                        pending_health_multiplier = 1.0
                        active_health_multiplier = 1.0
                        pending_elemental_bias = {}
                        pending_weather = None
                        multiplayer_result_sent = False
                    clock.tick()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    confirm_exit = False
            elif game_over_dialog is not None:
                game_over_dialog.handle_event(event)
                if game_over_dialog.done:
                    if multiplayer is not None:
                        multiplayer.close()
                        multiplayer = None
                        menus.multiplayer_client = None
                    game_over_dialog = None
                    running = menus.run()
                    if running:
                        multiplayer = (
                            menus.multiplayer_client
                            if menus.game_mode == "multiplayer"
                            else None
                        )
                        farm, player = _create_game(
                            screen, menus.store.player_image_number()
                        )
                        shop = ShopMenu()
                        house = House(screen)
                        turrets = TurretSystem(farm)
                        enemies = []
                        planting_phase = True
                        phase_remaining = config.PLANTING_PHASE_DURATION
                        wave_number = 0
                        wave_sequence = []
                        wave_spawned = 0
                        wave_elapsed = 0.0
                        controlling_house_turret = False
                        run_id = uuid4().hex
                        run_elapsed = 0.0
                        enemies_defeated = 0
                        waves = Waves(house)
                        farm.weather_crop_type = waves.crop_type
                        shop_open = False
                        hud_visible = False
                        multiplayer_panel_open = False
                        multiplayer_status = ""
                        pending_extra_enemies = 0
                        pending_health_multiplier = 1.0
                        active_health_multiplier = 1.0
                        pending_elemental_bias = {}
                        pending_weather = None
                        multiplayer_result_sent = False
                    clock.tick()
                    if not running:
                        break
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_v
                and multiplayer is not None
                and game_over_dialog is None
            ):
                multiplayer_panel_open = not multiplayer_panel_open
                available = [crop for crop, count in player.crops.items() if count > 0]
                if selected_attack_element not in available:
                    selected_attack_element = available[0] if available else None
            elif multiplayer_panel_open and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_v):
                    multiplayer_panel_open = False
                elif event.key in (pygame.K_q, pygame.K_e):
                    available = [
                        crop for crop, count in player.crops.items() if count > 0
                    ]
                    if available:
                        current = (
                            available.index(selected_attack_element)
                            if selected_attack_element in available
                            else 0
                        )
                        step = -1 if event.key == pygame.K_q else 1
                        selected_attack_element = available[
                            (current + step) % len(available)
                        ]
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    action = {
                        pygame.K_1: "extra_enemies",
                        pygame.K_2: "tougher_enemies",
                        pygame.K_3: "elemental_chance",
                        pygame.K_4: "change_weather",
                    }[event.key]
                    multiplayer_status = _send_multiplayer_attack(
                        action,
                        selected_attack_element,
                        player,
                        multiplayer,
                    )
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_h
                and not farm.planting
            ):
                hud_visible = not hud_visible
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_o:
                turrets.show_ranges = not turrets.show_ranges
            elif turrets.modal_slot is not None:
                turrets.handle_event(event, player, screen)
            elif controlling_house_turret and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_f, pygame.K_ESCAPE):
                    controlling_house_turret = False
            elif shop_open and event.type == pygame.KEYDOWN:
                if (
                    event.key in (pygame.K_ESCAPE, pygame.K_m)
                    and not shop.selecting_quadrant
                ):
                    shop_open = False
                    shop.clear_status()
                else:
                    shop.handle_event(event, player, farm, house, screen)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                roof = house.turret_control_rect()
                if roof.collidepoint(player.pos):
                    controlling_house_turret = True
                elif farm.planting:
                    farm.handle_event(event, player)
                elif turrets.interact(player):
                    pass
                else:
                    farm.handle_event(event, player)
            elif event.type == pygame.KEYDOWN and farm.planting:
                farm.handle_event(event, player)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                confirm_exit = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                shop_open = True
                shop.clear_status()
            elif event.type == pygame.KEYDOWN:
                farm.handle_event(event, player)

        if not running:
            break

        game_paused = (
            (
                multiplayer is None
                and (
                    shop_open
                    or confirm_exit
                    or farm.planting
                    or turrets.modal_slot is not None
                )
            )
            or house.health <= 0
            or game_over_dialog is not None
        )
        if not game_paused and house.health > 0:
            run_elapsed += seconds
        if not game_paused and not controlling_house_turret:
            player.update(seconds)
        farm.update(seconds)
        shop.update(seconds)

        if not game_paused:
            phase_remaining -= seconds
            if planting_phase:
                if phase_remaining <= 0:
                    planting_phase = False
                    wave_number += 1
                    waves.new_wave()
                    if pending_weather is not None:
                        waves.state = pending_weather
                    farm.weather_crop_type = waves.crop_type
                    active_health_multiplier = pending_health_multiplier
                    wave_sequence = build_wave_sequence(
                        wave_number,
                        waves.state,
                        extra_enemies=pending_extra_enemies,
                        elemental_biases=pending_elemental_bias,
                    )
                    if multiplayer is not None:
                        try:
                            multiplayer.send_wave(wave_number)
                        except MultiplayerError as error:
                            multiplayer_status = str(error)
                    pending_extra_enemies = 0
                    pending_health_multiplier = 1.0
                    pending_elemental_bias = {}
                    pending_weather = None
                    play_background_music(
                        "boss" if wave_number % 3 == 0 else "enemies",
                        volume=menus.preferences["music_volume"],
                    )
                    wave_spawned = 0
                    wave_elapsed = 0.0
                    phase_remaining = config.ENEMY_WAVE_DURATION
            else:
                wave_elapsed += seconds
                target_spawn_count = min(
                    len(wave_sequence),
                    int(wave_elapsed / config.ENEMY_WAVE_DURATION * len(wave_sequence))
                    + 1,
                )
                while wave_spawned < target_spawn_count:
                    key = wave_sequence[wave_spawned]
                    spawn_y = min(
                        screen.get_height() - 55,
                        max(
                            80,
                            house.return_rect().centery + (wave_spawned % 5 - 2) * 65,
                        ),
                    )
                    spawn_x = -30 if wave_spawned % 2 == 0 else screen.get_width() + 30
                    enemy = EnemyState.create(key, (spawn_x, spawn_y))
                    if active_health_multiplier > 1:
                        enemy.max_health = math.ceil(
                            enemy.max_health * active_health_multiplier
                        )
                        enemy.health = enemy.max_health
                    enemies.append(enemy)
                    wave_spawned += 1
                if phase_remaining <= 0 and not enemies:
                    planting_phase = True
                    phase_remaining = config.PLANTING_PHASE_DURATION
                    play_background_music(volume=menus.preferences["music_volume"])

            turrets.update(seconds, enemies)
            house_turret = house.turret
            keys = pygame.key.get_pressed()
            if controlling_house_turret:
                rotate_direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
                    keys[pygame.K_LEFT] or keys[pygame.K_a]
                )
            else:
                rotate_direction = 0
            house_turret.update(
                seconds,
                enemies,
                (house.return_rect().centerx, house.return_rect().y + 24),
                rotate_direction,
                controlling_house_turret and keys[pygame.K_SPACE],
                screen.get_rect(),
            )

            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                enemy.update_status_effects(seconds)
                enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - seconds)
                destination = pygame.Vector2(house.return_rect().center)
                boss_slot = (
                    turrets.boss_target(enemy.pos, destination)
                    if enemy.is_boss
                    else None
                )
                if boss_slot is not None:
                    destination = pygame.Vector2(boss_slot.center)
                    if enemy.pos.distance_to(destination) <= 44:
                        if enemy.attack_cooldown <= 0:
                            turrets.damage_slot(boss_slot, enemy.damage * 2)
                            enemy.attack_cooldown = 1.0
                    else:
                        enemy.move_towards(destination, seconds)
                    continue
                if enemy.pos.distance_to(destination) > 55:
                    enemy.move_towards(destination, seconds)
                elif enemy.attack_cooldown <= 0:
                    house.take_damage(enemy.damage)
                    enemy.attack_cooldown = 1.0

            survivors = []
            for enemy in enemies:
                if enemy.health <= 0:
                    player.coins += enemy.reward
                    enemies_defeated += 1
                    seed_amount = math.ceil(config.ENEMY_SEED_DROP_MULTIPLIER)
                    if seed_amount > 0:
                        seed_type, seed_tier = roll_enemy_seed_drop(enemy)
                        player.add_seed(seed_type, seed_tier, seed_amount)
                else:
                    survivors.append(enemy)
            enemies = survivors

        # Render the world and the current phase.
        screen.blit(game_background, (0, 0))
        house.draw(screen)
        waves.draw_weather(screen, font)
        farm.draw(screen, font, tile, player)
        turrets.draw(screen, font, player)
        for enemy in enemies:
            enemy.draw(screen, enemy_images)
        house.turret.draw_projectiles(screen)
        if not controlling_house_turret:
            player.draw(screen)
        farm.draw_menu(screen, font)
        turrets.draw_modal(screen, font, player)
        phase_label = "PLANTING" if planting_phase else f"WAVE {wave_number}"
        phase_icon_position = (20, 12)
        if multiplayer is not None:
            room_code = multiplayer.room_code or "------"
            opponent_text = font.render(
                f"VS {multiplayer.opponent_name}  |  Room {room_code}  |  V: attacks",
                True,
                (0, 0, 0),
            )
            screen.blit(opponent_text, (78, config.TEXT_Y))
            if multiplayer_status:
                status_text = font.render(
                    multiplayer_status[:75], True, (255, 225, 125)
                )
                screen.blit(status_text, (78, 34))
        if not planting_phase:
            screen.blit(enemy_marker_background, (14, 6))
        screen.blit(
            phase_icons["planting" if planting_phase else "enemy"],
            phase_icon_position,
        )
        buffer = 0
        if multiplayer:
            buffer = 40
        hint_font = pygame.font.Font(os.path.join(config.ASSETS_DIR, "font", "pixelfont.ttf"), 24)


        if controlling_house_turret and not planting_phase:
            label_text = "Shoot enemies with SPACE!"
        elif planting_phase:
            crop = farm.get_crop(*tile) if tile else None
            can_farm = (
                tile is not None
                and farm.quadrant_at(*tile) in player.unlocked_quadrants
                and (crop is None or crop.is_ready())
            )
            if turrets.can_interact(player):
                label_text = "Press F to upgrade turrets"
            elif can_farm:
                label_text = "Press F to plant or harvest"
            else:
                label_text = "Plant seeds on unlocked plot!"
        else:
            label_text = "Enter house with F!"
        if house.state == HouseState.BROKEN:
            label_text = "QUICK! Repair house in the market!"

        instruction_label = hint_font.render(label_text, True, (0, 0, 0))
        screen.blit(
            instruction_label,
            instruction_label.get_rect(midtop=(screen.get_width() // 2 + buffer, config.TEXT_Y)),
        )
        timer = font.render(
            f"{phase_label}  {max(0, phase_remaining):.0f}s",
            True,
            (0, 0, 0),
        )
        phase_text_position = (
            (78, config.TEXT_Y) if multiplayer is not None else (78, 5)
        )
        screen.blit(
            timer,
            (screen.get_width() - timer.get_width() - 20, phase_text_position[1]),
        )
        if hud_visible:
            draw_inventory_hud(screen, player, wave_number, enemies_defeated)
        if multiplayer is not None and multiplayer_panel_open:
            panel = _multiplayer_attack_panel_rect(screen)
            pygame.draw.rect(screen, (35, 40, 50), panel, border_radius=10)
            pygame.draw.rect(screen, (215, 220, 230), panel, 2, border_radius=10)
            crop_count = (
                player.crops.get(selected_attack_element, 0)
                if selected_attack_element is not None
                else 0
            )
            selected_crop_name = (
                selected_attack_element.name.title()
                if selected_attack_element is not None
                else "none"
            )
            attack_lines = (
                "VS ATTACKS  (V / ESC to close)",
                f"Coins: {player.coins}    Crop: {selected_crop_name} x{crop_count} (Q/E)",
                "1  Send 4 extra enemies  -  6 coins",
                "2  Toughen next wave     -  8 coins",
                "3  Raise elemental odds  -  1 crop",
                "4  Change enemy weather  -  1 crop",
            )
            for index, line in enumerate(attack_lines):
                text = font.render(
                    line, True, (255, 230, 150) if index == 0 else (245, 245, 245)
                )
                screen.blit(text, (panel.x + 18, panel.y + 25 + index * 42))
        if shop_open:
            shop.draw(screen, font, player, farm, house)
        actions_enabled = (
            not confirm_exit
            and not farm.planting
            and turrets.modal_slot is None
            and not controlling_house_turret
            and game_over_dialog is None
            and house.health > 0
        )
        turret_action_available = actions_enabled and turrets.can_interact(player)
        quick_action_availability = {
            "store": actions_enabled,
            "hud": actions_enabled,
            "turret": turret_action_available,
            "attack": actions_enabled and multiplayer is not None,
        }
        mouse_position = pygame.mouse.get_pos()
        hovered_action = None
        for action, rect in quick_action_buttons.items():
            if action == "attack" and multiplayer is None:
                continue
            hovered = rect.collidepoint(mouse_position)
            if hovered:
                hovered_action = action
            _draw_quick_action_button(
                screen,
                rect,
                quick_action_icons[action],
                enabled=quick_action_availability[action],
                hovered=hovered,
            )
        if hovered_action is not None:
            if not actions_enabled:
                tooltip_text = "Unavailable right now"
            elif hovered_action == "store":
                tooltip_text = "Open or close the store (M)"
            elif hovered_action == "hud":
                tooltip_text = "Toggle inventory HUD (H)"
            elif hovered_action == "turret":
                tooltip_text = (
                    "Interact with nearby turret (F)"
                    if turret_action_available
                    else "Move closer to a turret / turret slot"
                )
            else:
                tooltip_text = "Open or close multiplayer attacks (V)"
            _draw_quick_action_tooltip(
                screen,
                font,
                quick_action_buttons[hovered_action],
                tooltip_text,
            )
        if confirm_exit:
            draw_exit_confirmation(screen, font)
        if game_over_dialog is not None:
            game_over_dialog.draw()
        pygame.display.flip()

    if multiplayer is not None:
        multiplayer.close()
    _game_instance_lock.release()
    pygame.quit()


if __name__ == "__main__":
    main()
