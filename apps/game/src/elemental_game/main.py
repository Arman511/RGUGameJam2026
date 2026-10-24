import os

import pygame

from elemental_game import config
from elemental_game.game_entities.farm import Farm, CropMenu
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.game_entities.player.player import Player, PlayerType
from elemental_game.menus import MenuSystem
from enum import Enum

# initialise pygame attributes
pygame.init()
pygame.display.set_icon(
    pygame.image.load(os.path.join(config.ASSETS_DIR, "assets", "icon.ico"))
)
screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(
    os.path.join(config.ASSETS_DIR, "fonts", "pixelfont.ttf"), 28
)
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
def main():
    menus = MenuSystem(screen)
    running = menus.run()

    dimensions = (6, 6)
    farm = Farm(*dimensions,
                origin=((screen.get_width() - dimensions[1] * Farm.TILE_SIZE) // 2, 250))
    player = Player(player_type=PlayerType(menus.store.player_image_number()))

    while running:
        seconds = clock.tick(60) / 1000  # seconds since last frame
        tile = farm.tile_at_pixel(*player.pos)  # tile the player is standing on

        # handle keyboard and mouse inputs
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # close the pygame window
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = menus.run()  # back to the main menu
                clock.tick()  # discard the time spent in the menus
            else:
                farm.handle_event(event, player)

        if not farm.planting:
            player.update(seconds)  # update player pos
        farm.update(seconds)  # update crop growth

        # render screen:
        screen.blit(game_background, (0, 0))
        farm.draw(screen, font, tile)
        player.draw(screen)
        farm.draw_menu(screen, font)  # after the player so the menu sits on top
        hint = font.render(
            "Arrows = move   F = plant   H = harvest", True, (255, 255, 255)
        )
        screen.blit(hint, (10, 10))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
