import argparse
import math
import os
import random
from collections.abc import Sequence
from uuid import uuid4

import pygame

from elemental_game import config
from elemental_game.game_entities.enemies.enemies import EnemyState, load_enemy_images
from elemental_game.game_entities.enemies.waves import Waves, build_wave_sequence
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.house import House
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.shop import ShopMenu
from elemental_game.game_entities.turrets.turrets import TurretSystem
from elemental_game.menus import MenuSystem
from elemental_game.screen_rendering.exit_confirmation import draw_exit_confirmation
from elemental_game.screen_rendering.game_over import GameOverDialog
from elemental_game.screen_rendering.hud import draw_inventory_hud
from elemental_game.types.player import PlayerType
from elemental_game.types.seed import SeedType

# initialise pygame attributes
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
    player = Player(player_type=PlayerType(player_type))
    return farm, player


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
    waves = Waves(house)
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

    while running:
        if house.health <= 0 and game_over_dialog is None:
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
        tile = farm.tile_at_pixel(*player.pos)  # tile the player is standing on

        # Handle keyboard and mouse inputs.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif confirm_exit and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    confirm_exit = False
                    running = menus.run()
                    if running:
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
                        shop_open = False
                        hud_visible = False
                    clock.tick()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    confirm_exit = False
            elif game_over_dialog is not None:
                game_over_dialog.handle_event(event)
                if game_over_dialog.done:
                    game_over_dialog = None
                    running = menus.run()
                    if running:
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
                        shop_open = False
                        hud_visible = False
                    clock.tick()
                    if not running:
                        break
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_h
                and not farm.planting
            ):
                hud_visible = not hud_visible
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_o:
                turrets.show_ranges = not turrets.show_ranges
            elif turrets.modal_slot is not None:
                turrets.handle_event(event, player)
            elif controlling_house_turret and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_f, pygame.K_ESCAPE):
                    controlling_house_turret = False
            elif shop_open and event.type == pygame.KEYDOWN:
                if (
                    event.key in (pygame.K_ESCAPE, pygame.K_m)
                    and not shop.selecting_quadrant
                ):
                    shop_open = False
                else:
                    shop.handle_event(event, player, farm, house)
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
            elif event.type == pygame.KEYDOWN:
                farm.handle_event(event, player)

        game_paused = (
            shop_open
            or confirm_exit
            or farm.planting
            or turrets.modal_slot is not None
            or house.health <= 0
            or game_over_dialog is not None
        )
        if not game_paused and house.health > 0:
            run_elapsed += seconds
        if not game_paused and not controlling_house_turret:
            player.update(seconds)
        farm.update(seconds)

        if not game_paused:
            phase_remaining -= seconds
            if planting_phase:
                if phase_remaining <= 0:
                    planting_phase = False
                    wave_number += 1
                    wave_sequence = build_wave_sequence(wave_number)
                    waves.new_wave()
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
                    enemies.append(EnemyState.create(key, (spawn_x, spawn_y)))
                    wave_spawned += 1
                if phase_remaining <= 0:
                    planting_phase = True
                    phase_remaining = config.PLANTING_PHASE_DURATION

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
            )

            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - seconds)
                destination = pygame.Vector2(house.return_rect().center)
                boss_slot = turrets.nearest_turret(enemy.pos) if enemy.is_boss else None
                if boss_slot is not None:
                    destination = pygame.Vector2(boss_slot.center)
                    if enemy.pos.distance_to(destination) <= 44:
                        if enemy.attack_cooldown <= 0:
                            turrets.damage_slot(boss_slot, enemy.damage * 2)
                            enemy.attack_cooldown = 1.0
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
                        player.add_seed(
                            random.choice(tuple(SeedType)), "tier1", seed_amount
                        )
                else:
                    survivors.append(enemy)
            enemies = survivors

        # Render the world and the current phase.
        screen.blit(game_background, (0, 0))
        house.draw(screen)
        waves.draw_weather(screen)
        farm.draw(screen, font, tile, player)
        for enemy in enemies:
            enemy.draw(screen, enemy_images)
        turrets.draw(screen, font, player)
        house.turret.draw_projectiles(screen)
        if not controlling_house_turret:
            player.draw(screen)
        farm.draw_menu(screen, font)
        turrets.draw_modal(screen, font, player)
        phase_label = "PLANTING" if planting_phase else f"WAVE {wave_number}"
        screen.blit(
            phase_icons["planting" if planting_phase else "enemy"],
            (20, 12),
        )
        timer = font.render(
            f"{phase_label}  {max(0, phase_remaining):.0f}s",
            True,
            (255, 255, 255),
        )
        screen.blit(
            timer,
            (screen.get_width() - timer.get_width() - 20, 5),
        )
        if hud_visible:
            draw_inventory_hud(screen, player)
        if shop_open:
            shop.draw(screen, font, player, farm, house)
        if confirm_exit:
            draw_exit_confirmation(screen, font)
        if game_over_dialog is not None:
            game_over_dialog.draw()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
