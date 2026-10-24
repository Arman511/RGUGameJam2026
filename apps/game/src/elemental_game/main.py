import pygame
from elemental_game.game_entities.farm import Farm, CropMenu
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.game_entities.player.player import Player, PlayerType
from elemental_game.menus import MenuSystem

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

# login / main menu / leaderboard / settings (menus.py)
# returns True when they press Play, False if they close the window
menus = MenuSystem(screen)
running = menus.run()

farm = Farm(rows=4, cols=6, origin=(300, 300))

# Holly is currently editing below:

menu = None
player = Player(player_type=PlayerType(menus.store.player_image_number()))
while running:
    dt = clock.tick(60) / 1000
    tile = farm.tile_at_pixel(*player.pos)   # tile the player is standing on


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and farm.menu is None:
            running = menus.run()   # back to the main menu
            clock.tick()            # discard the time spent in the menus
        else:
            farm.handle_event(event, tile)

    player.update(dt)
    farm.update(dt)

    screen.fill((30, 30, 30))
    farm.draw(screen, font, tile)
    player.draw(screen)
    farm.draw_menu(screen, font)   # after the player so the menu sits on top
    hint = font.render("Arrows = move   F = plant   H = harvest", True, (255, 255, 255))
    screen.blit(hint, (10, 10))
    pygame.display.flip()

pygame.quit()