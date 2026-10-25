import argparse
import atexit
import os
import sys
from collections.abc import Sequence

import pygame

from elemental_game import config
from elemental_game.audio import handle_background_music_end_event
from elemental_game.game_entities.enemies.enemies import load_enemy_images
from elemental_game.gameplay import GameSession
from elemental_game.instance_lock import GameInstanceLock
from elemental_game.menus import MenuSystem
from elemental_game.multiplayer import MultiplayerError
from elemental_game.screen_rendering.game import (
    GameScreenRenderer,
    multiplayer_attack_panel_rect,
)
from elemental_game.screen_rendering.game_over import GameOverDialog
from elemental_game.screen_rendering.multiplayer_game_over import (
    MultiplayerGameOverDialog,
)
from elemental_game.types.crop import CropType
from elemental_game.types.weather import WeatherTypes

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
    if (
        action in MULTIPLAYER_COIN_COSTS
        and player.coins < MULTIPLAYER_COIN_COSTS[action]
    ):
        return "Not enough coins for that attack."
    if multiplayer is None:
        return "Multiplayer attacks are unavailable."
    try:
        multiplayer.send_action(action, element.name if element is not None else None)
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
    game = GameSession(screen, menus.store.player_image_number())
    enemy_images = load_enemy_images()
    game_renderer = GameScreenRenderer(screen, font, enemy_images)
    game_over_dialog = None
    multiplayer_panel_open = False
    multiplayer_status = ""
    pending_extra_enemies = 0
    pending_health_multiplier = 1.0
    pending_elemental_bias: dict[CropType, int] = {}
    pending_weather: WeatherTypes | None = None
    selected_attack_element: CropType | None = next(
        (crop for crop, count in game.player.crops.items() if count > 0),
        None,
    )
    multiplayer_result_sent = False

    def reset_run() -> None:
        nonlocal game_over_dialog, multiplayer_panel_open, multiplayer_status
        nonlocal pending_extra_enemies, pending_health_multiplier
        nonlocal pending_elemental_bias, pending_weather
        nonlocal multiplayer_result_sent

        game.reset(menus.store.player_image_number())
        game_over_dialog = None
        multiplayer_panel_open = False
        multiplayer_status = ""
        pending_extra_enemies = 0
        pending_health_multiplier = 1.0
        pending_elemental_bias = {}
        pending_weather = None
        multiplayer_result_sent = False

    def notify_wave_started(started_wave: int) -> None:
        nonlocal multiplayer_status, pending_extra_enemies
        nonlocal pending_health_multiplier, pending_elemental_bias, pending_weather

        if multiplayer is not None:
            try:
                multiplayer.send_wave(started_wave)
            except MultiplayerError as error:
                multiplayer_status = str(error)
        pending_extra_enemies = 0
        pending_health_multiplier = 1.0
        pending_elemental_bias = {}
        pending_weather = None

    clock.tick()
    while running:
        if game.house.health <= 0 and game_over_dialog is None and multiplayer is None:
            game_over_dialog = GameOverDialog(
                screen,
                font,
                menus,
                run_id=game.run_id,
                survival_time=game.run_elapsed,
                final_wave=game.wave_number,
                enemies_defeated=game.enemies_defeated,
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
            and game.house.health <= 0
            and not multiplayer_result_sent
        ):
            try:
                multiplayer.end_match()
            except MultiplayerError as error:
                multiplayer_status = str(error)
                game_over_dialog = MultiplayerGameOverDialog(screen, font, "defeat")
            multiplayer_result_sent = True
        tile = game.farm.tile_at_pixel(*game.player.pos)

        # Handle keyboard and mouse inputs.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif handle_background_music_end_event(
                event, volume=menus.preferences["music_volume"]
            ):
                continue
            elif (
                game_over_dialog is None
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                mouse_result = game.handle_mouse_event(
                    event,
                    game_renderer.quick_action_buttons,
                )
                if mouse_result == "attack" and multiplayer is not None:
                    multiplayer_panel_open = not multiplayer_panel_open
                    available = [
                        crop for crop, count in game.player.crops.items() if count > 0
                    ]
                    if selected_attack_element not in available:
                        selected_attack_element = available[0] if available else None
                elif mouse_result is None and multiplayer_panel_open:
                    panel = multiplayer_attack_panel_rect(screen)
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
                                game.player,
                                multiplayer,
                            )
                            break
                continue
            elif game.confirm_exit and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    game.confirm_exit = False
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
                        reset_run()
                    clock.tick()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    game.confirm_exit = False
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
                        reset_run()
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
                available = [
                    crop for crop, count in game.player.crops.items() if count > 0
                ]
                if selected_attack_element not in available:
                    selected_attack_element = available[0] if available else None
            elif multiplayer_panel_open and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_v):
                    multiplayer_panel_open = False
                elif event.key in (pygame.K_q, pygame.K_e):
                    available = [
                        crop for crop, count in game.player.crops.items() if count > 0
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
                        game.player,
                        multiplayer,
                    )
            else:
                game.handle_event(event)

        if not running:
            break

        game_paused = (
            (
                multiplayer is None
                and (
                    game.shop_open
                    or game.confirm_exit
                    or game.farm.planting
                    or game.turrets.modal_slot is not None
                )
            )
            or game.house.health <= 0
            or game_over_dialog is not None
        )
        game.update(
            seconds,
            paused=game_paused,
            music_volume=menus.preferences["music_volume"],
            pending_extra_enemies=pending_extra_enemies,
            pending_health_multiplier=pending_health_multiplier,
            pending_elemental_bias=pending_elemental_bias,
            pending_weather=pending_weather,
            on_wave_started=notify_wave_started,
        )

        game_renderer.draw(
            farm=game.farm,
            player=game.player,
            house=game.house,
            turrets=game.turrets,
            waves=game.waves,
            enemies=game.enemies,
            enemy_images=enemy_images,
            tile=tile,
            planting_phase=game.planting_phase,
            phase_remaining=game.phase_remaining,
            wave_number=game.wave_number,
            enemies_defeated=game.enemies_defeated,
            controlling_house_turret=game.controlling_house_turret,
            multiplayer=multiplayer,
            multiplayer_status=multiplayer_status,
            hud_visible=game.hud_visible,
            hints_enabled=menus.hints_enabled,
            multiplayer_panel_open=multiplayer_panel_open,
            selected_attack_element=selected_attack_element,
            shop_open=game.shop_open,
            shop=game.shop,
            confirm_exit=game.confirm_exit,
            game_over_dialog=game_over_dialog,
        )
        pygame.display.flip()

    if multiplayer is not None:
        multiplayer.close()
    _game_instance_lock.release()
    pygame.quit()


if __name__ == "__main__":
    main()
