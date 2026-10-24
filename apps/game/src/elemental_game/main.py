import pygame
from elemental_game.game_entities.farm import Farm, CropMenu
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.game_entities.player.player import Player
from elemental_game.menus import MenuSystem
import enum

# initialise pygame attributes
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

# game state attributes
class GameState(enum):
    FARMING = 1
    ENEMIES_TURRET = 2
    ENEMIES_NO_TURRET = 3
    BOSS = 4
    SHOP = 5

PLANTING = True

# login / main menu / leaderboard / settings (menus.py)
# returns True when they press Play, False if they close the window
menus = MenuSystem(screen)
running = menus.run()

farm = Farm(rows=4, cols=6, origin=(300, 300))
player = Player()

while running:
    seconds = clock.tick(60) / 1000 # seconds since last frame
    tile = farm.tile_at_pixel(*player.pos)   # tile the player is standing on

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False # close the pygame window
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = menus.run()   # back to the main menu
            clock.tick()            # discard the time spent in the menus
        else:
            farm.handle_event(event, tile)

    player.update(seconds)
    farm.update(seconds)
    screen.fill((30, 30, 30)) #TODO PLACEHOLDER
    farm.draw(screen, font, tile)
    player.draw(screen)
    farm.draw_menu(screen, font)   # after the player so the menu sits on top
    hint = font.render("Arrows = move   F = plant   H = harvest", True, (255, 255, 255))
    screen.blit(hint, (10, 10))
    pygame.display.flip()

pygame.quit()