import pygame
import pytest


@pytest.fixture
def pygame_display(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    display_was_initialized = pygame.display.get_init()
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    if not display_was_initialized:
        pygame.display.quit()
