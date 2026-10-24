from __future__ import annotations

import pygame
from elemental_game.api_client.http import APIError
from elemental_game.main import GameApplication


def menu_click(app: GameApplication, pos: tuple[int, int]) -> None:
    app._handle_menu_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos}
        )
    )


def test_guest_can_return_to_sign_in_from_menu() -> None:
    app = GameApplication.__new__(GameApplication)
    app.username = None
    app.error_message = "A previous error"
    app.state = "menu"

    menu_click(app, (400, 457))

    assert app.state == "login"
    assert app.error_message == ""


def test_signed_in_player_can_sign_out_from_menu() -> None:
    class Auth:
        def logout(self) -> None:
            return None

    app = GameApplication.__new__(GameApplication)
    app.username = "alice"
    app.error_message = ""
    app.state = "menu"
    app.auth = Auth()

    menu_click(app, (400, 457))

    assert app.state == "menu"
    assert app.username is None


def test_sign_out_failure_keeps_signed_in_state() -> None:
    class Auth:
        def logout(self) -> None:
            raise APIError("service unavailable")

    app = GameApplication.__new__(GameApplication)
    app.username = "alice"
    app.error_message = ""
    app.state = "menu"
    app.auth = Auth()

    menu_click(app, (400, 457))

    assert app.state == "menu"
    assert app.username == "alice"
    assert app.error_message == "Sign out failed: service unavailable"
