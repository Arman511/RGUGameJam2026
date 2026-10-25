from types import SimpleNamespace

import pygame
from elemental_game.application.multiplayer import MultiplayerController


def make_controller() -> MultiplayerController:
    controller = MultiplayerController.__new__(MultiplayerController)
    controller.client = object()
    controller.panel_open = False
    controller.selected_element = None
    controller.screen = pygame.Surface((1280, 720))
    controller.sent_attacks = []
    controller._send_attack = lambda action, _game: controller.sent_attacks.append(
        action
    )
    return controller


def make_game() -> SimpleNamespace:
    return SimpleNamespace(
        seed_tier_reward=None,
        player=SimpleNamespace(crops={}),
    )


def test_attack_panel_toggles_with_v_and_closes_with_escape() -> None:
    controller = make_controller()
    game = make_game()

    assert controller.handle_key_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_v}), game
    )
    assert controller.panel_open
    assert controller.handle_key_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}), game
    )
    assert not controller.panel_open


def test_attack_panel_stays_open_after_sending_keyboard_attack() -> None:
    controller = make_controller()
    controller.panel_open = True
    game = make_game()

    controller.handle_key_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}), game
    )
    controller.handle_key_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_2}), game
    )

    assert controller.sent_attacks == ["extra_enemies", "tougher_enemies"]
    assert controller.panel_open


def test_attack_button_toggles_panel_and_mouse_attack_can_be_clicked() -> None:
    controller = make_controller()
    game = make_game()
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})

    controller.handle_mouse_result(click, "attack", game)
    assert controller.panel_open

    panel = pygame.Rect(665, 170, 470, 300)
    attack_click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": (panel.centerx, panel.y + 114)},
    )
    assert controller.handle_panel_click(attack_click, game)

    assert controller.sent_attacks == ["extra_enemies"]
    assert controller.panel_open

    controller.handle_mouse_result(click, "attack", game)
    assert not controller.panel_open
