from types import SimpleNamespace
from unittest.mock import Mock

import pygame

from elemental_game.application.game_loop import GameLoop
from elemental_game.application.session import GameSession


def test_completed_waves_only_counts_fully_finished_waves() -> None:
    game = GameSession.__new__(GameSession)
    game.waves = SimpleNamespace(wave_number=0, planting_phase=True)
    assert game.completed_waves == 0

    game.waves.wave_number = 1
    assert game.completed_waves == 1

    game.waves.planting_phase = False
    assert game.completed_waves == 0

    game.waves.wave_number = 2
    assert game.completed_waves == 1


def test_forfeiting_after_a_completed_wave_opens_run_over_dialog(monkeypatch) -> None:
    dialog = object()
    create_dialog = Mock(return_value=dialog)
    monkeypatch.setattr(
        "elemental_game.application.game_loop.GameOverDialog", create_dialog
    )

    loop = GameLoop.__new__(GameLoop)
    loop.game = SimpleNamespace(
        confirm_exit=True,
        completed_waves=1,
        run_id="run-forfeit",
        run_elapsed=61.5,
        wave_number=2,
        enemies_defeated=9,
    )
    loop.screen = pygame.Surface((800, 600))
    loop.font = pygame.font.Font(None, 22)
    loop.menus = object()
    loop.multiplayer = Mock()
    loop._return_to_menu = Mock()

    loop._handle_exit_confirmation(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_y})
    )

    assert loop.game.confirm_exit is False
    assert loop.game_over is dialog
    loop.multiplayer.close_connection.assert_called_once_with()
    loop._return_to_menu.assert_not_called()
    assert create_dialog.call_args.kwargs == {
        "run_id": "run-forfeit",
        "survival_time": 61.5,
        "final_wave": 2,
        "enemies_defeated": 9,
    }


def test_forfeiting_before_finishing_a_wave_returns_to_menu(monkeypatch) -> None:
    loop = GameLoop.__new__(GameLoop)
    loop.game = SimpleNamespace(confirm_exit=True, completed_waves=0)
    loop._return_to_menu = Mock()
    loop.game_over = None

    loop._handle_exit_confirmation(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
    )

    assert loop.game.confirm_exit is False
    loop._return_to_menu.assert_called_once_with()
