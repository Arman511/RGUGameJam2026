from __future__ import annotations

import pygame
from elemental_game import menus
from elemental_game.api_client.http import APIError


def test_register_page_uses_windows_browser_from_wsl(monkeypatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    commands: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> None:
        commands.append((command, kwargs))

    monkeypatch.setattr(menus.subprocess, "run", fake_run)

    assert menus._open_registration_page()
    assert commands[0][0] == [
        "cmd.exe",
        "/c",
        "start",
        "",
        "https://elemental-keep.armandev.co.uk/register",
    ]


def test_register_button_opens_registration_page(monkeypatch) -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.login_username = menus.InputField(
        pygame.Rect(250, 205, 300, 44), placeholder="Username", max_length=32
    )
    app.login_password = menus.InputField(
        pygame.Rect(250, 265, 300, 44), placeholder="Password", max_length=128
    )
    app.error_message = ""
    opened_urls: list[str] = []
    monkeypatch.setattr(
        menus,
        "_open_registration_page",
        lambda: (opened_urls.append(menus.REGISTER_URL), True)[1],
    )

    app._handle_login_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 364)}
        )
    )

    assert opened_urls == ["https://elemental-keep.armandev.co.uk/register"]
    assert app.error_message == ""


def test_register_button_reports_browser_failure(monkeypatch) -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.login_username = menus.InputField(
        pygame.Rect(250, 205, 300, 44), placeholder="Username", max_length=32
    )
    app.login_password = menus.InputField(
        pygame.Rect(250, 265, 300, 44), placeholder="Password", max_length=128
    )
    app.error_message = ""
    monkeypatch.setattr(menus, "_open_registration_page", lambda: False)

    app._handle_login_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 364)}
        )
    )

    assert app.error_message == "Could not open the registration page."


def menu_click(app: menus.MenuSystem, pos: tuple[int, int]) -> None:
    app._handle_menu_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos}
        )
    )


def test_guest_can_return_to_sign_in_from_menu() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
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

    app = menus.MenuSystem.__new__(menus.MenuSystem)
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

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.username = "alice"
    app.error_message = ""
    app.state = "menu"
    app.auth = Auth()

    menu_click(app, (400, 457))

    assert app.state == "menu"
    assert app.username == "alice"
    assert app.error_message == "Sign out failed: service unavailable"


def test_menu_layout_scales_and_centers_for_configured_window() -> None:
    layout = menus.MenuLayout(1000, 800)

    assert layout.scale == 1.25
    assert layout.offset == (0, 25)
    assert layout.rect(menus.PLAY_BUTTON).center == layout.point((400, 217))


def test_menu_click_target_uses_scaled_window_layout() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(1000, 800)
    app.state = "menu"
    app.start_game = False
    app.running = True

    menu_click(app, app.layout.rect(menus.PLAY_BUTTON).center)

    assert app.start_game
    assert not app.running
