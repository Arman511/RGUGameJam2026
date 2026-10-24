import pygame


def draw_exit_confirmation(surface, confirm_font):
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 175))
    surface.blit(overlay, (0, 0))
    panel = pygame.Rect(0, 0, 500, 150)
    panel.center = surface.get_rect().center
    pygame.draw.rect(surface, (44, 48, 57), panel)
    pygame.draw.rect(surface, (225, 225, 225), panel, 2)
    prompt = confirm_font.render(
        "Are you sure you want to leave?", True, (255, 255, 255)
    )
    controls = confirm_font.render(
        "Y: Yes, return to menu    N / ESC: No", True, (255, 230, 120)
    )
    surface.blit(prompt, prompt.get_rect(center=(panel.centerx, panel.y + 52)))
    surface.blit(controls, controls.get_rect(center=(panel.centerx, panel.y + 104)))
