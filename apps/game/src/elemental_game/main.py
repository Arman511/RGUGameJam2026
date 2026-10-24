import pygame
from game_entities.farm import Farm
from game_entities.crops.crops import CropType

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
class CropMenu:
    """Popup listing the plant types. Opens at the mouse when F is pressed."""
    ITEM_W, ITEM_H = 120, 30

    def __init__(self, tile, pos):
        self.tile = tile
        self.options = [
            (crop_type, pygame.Rect(pos[0], pos[1] + i * self.ITEM_H, self.ITEM_W, self.ITEM_H))
            for i, crop_type in enumerate(CropType)
        ]

    def click(self, pos):
        """Returns the CropType that was clicked, or None."""
        for crop_type, rect in self.options:
            if rect.collidepoint(pos):
                return crop_type
        return None

    def draw(self, surface, font):
        mouse = pygame.mouse.get_pos()
        for crop_type, rect in self.options:
            pygame.draw.rect(surface, (90, 90, 90) if rect.collidepoint(mouse) else (60, 60, 60), rect)
            pygame.draw.rect(surface, (200, 200, 200), rect, 1)
            text = font.render(crop_type.name.title(), True, (255, 255, 255))
            surface.blit(text, text.get_rect(midleft=(rect.x + 8, rect.centery)))


menu = None
running = True
while running:
    dt = clock.tick(60) / 1000
    hovered = farm.tile_at_pixel(*pygame.mouse.get_pos())

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                menu = None
            elif menu is None and hovered:
                row, col = hovered
                if event.key == pygame.K_f and farm.is_empty(row, col):
                    menu = CropMenu(hovered, pygame.mouse.get_pos())
                elif event.key == pygame.K_h:
                    farm.harvest(row, col)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and menu:
            crop_type = menu.click(event.pos)
            if crop_type:
                farm.plant(*menu.tile, crop_type)
            menu = None   # any click closes the menu

    farm.update(dt)

    screen.fill((30, 30, 30))
    farm.draw(screen, font, hovered)
    if menu:
        menu.draw(screen, font)
    hint = font.render("Hover a tile:  F = plant   H = harvest", True, (255, 255, 255))
    screen.blit(hint, (10, 10))
    pygame.display.flip()

pygame.quit()