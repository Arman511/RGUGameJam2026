from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest
from elemental_game.application.game_loop import GameLoop
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


@pytest.mark.parametrize(
    ("seed_tier_reward", "shop_open"),
    [(object(), False), (None, True)],
)
def test_foreground_modals_receive_clicks_before_attack_panel(
    seed_tier_reward, shop_open
) -> None:
    loop = GameLoop.__new__(GameLoop)
    game = SimpleNamespace(
        seed_tier_reward=seed_tier_reward,
        shop_open=shop_open,
        handle_mouse_event=Mock(return_value="handled"),
    )
    loop.game = game
    loop.multiplayer = SimpleNamespace(
        handle_panel_click=Mock(return_value=True),
        handle_mouse_result=Mock(),
    )
    loop.renderer = SimpleNamespace(quick_action_buttons={})
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})

    loop._handle_mouse_click(click)

    loop.multiplayer.handle_panel_click.assert_not_called()
    game.handle_mouse_event.assert_called_once_with(click, {})
    loop.multiplayer.handle_mouse_result.assert_called_once_with(
        click, "handled", game
    )
