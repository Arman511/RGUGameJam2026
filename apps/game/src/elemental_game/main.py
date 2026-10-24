import pygame
from elemental_game.game_entities.farm import Farm, CropMenu
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.game_entities.player.player import Player

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

running = False # gameplay will not run yet

# def
# 
#
# login function here
#
# exiting function will immediately start game (for now)


farm = Farm(rows=4, cols=6, origin=(300, 300))

# Holly is currently editing below:

menu = None
player = Player()
running = True
while running:
    dt = clock.tick(60) / 1000
    tile = farm.tile_at_pixel(*player.pos)   # tile the player is standing on

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
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