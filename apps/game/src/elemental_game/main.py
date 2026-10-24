import argparse
import os
from collections.abc import Sequence
from enum import Enum

import pygame

from elemental_game import config
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.player.player import Player
from elemental_game.game_entities.shop import ShopMenu
from elemental_game.menus import MenuSystem
from elemental_game.screen_rendering.edit_confirmation import draw_exit_confirmation
from elemental_game.screen_rendering.hud import draw_inventory_hud
from elemental_game.types.player import PlayerType

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


# game state attributes
class GameState(Enum):
    FARMING = 1
    ENEMIES_TURRET = 2
    ENEMIES_NO_TURRET = 3
    BOSS = 4
    SHOP = 5


PLANTING = True


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
    shop_open = False
    hud_visible = False
    confirm_exit = False

    while running:
        seconds = clock.tick(60) / 1000  # seconds since last frame
        tile = farm.tile_at_pixel(*player.pos)  # tile the player is standing on

        # handle keyboard and mouse inputs
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # close the pygame window
            elif confirm_exit and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    confirm_exit = False
                    running = menus.run()
                    if running:
                        farm, player = _create_game(
                            screen, menus.store.player_image_number()
                        )
                        shop = ShopMenu()
                        shop_open = False
                        hud_visible = False
                    clock.tick()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    confirm_exit = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                hud_visible = not hud_visible
            elif shop_open and event.type == pygame.KEYDOWN:
                if (
                    event.key in (pygame.K_ESCAPE, pygame.K_m)
                    and not shop.selecting_quadrant
                ):
                    shop_open = False
                else:
                    shop.handle_event(event, player, farm)
            elif event.type == pygame.KEYDOWN and farm.planting:
                farm.handle_event(event, player)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                confirm_exit = True
            elif event.type == pygame.KEYDOWN and not farm.planting:
                if event.key == pygame.K_m:
                    shop_open = True
                else:
                    farm.handle_event(event, player)
            else:
                farm.handle_event(event, player)

        if not farm.planting and not shop_open and not confirm_exit:
            player.update(seconds)  # update player pos
        farm.update(seconds)  # update crop growth

        # render screen:
        screen.blit(game_background, (0, 0))
        farm.draw(screen, font, tile, player)
        player.draw(screen)
        farm.draw_menu(screen, font)  # after the player so the menu sits on top
        hint = font.render(
            "Arrows = move  F = interact  M = market  H = Inventory",
            True,
            (0, 0, 0),
        )
        screen.blit(hint, (10, 10))
        if hud_visible:
            draw_inventory_hud(screen, player)
        if shop_open:
            shop.draw(screen, font, player, farm)
        if confirm_exit:
            draw_exit_confirmation(screen, font)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
