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
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 364)})
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
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 364)})
    )

    assert app.error_message == "Could not open the registration page."


def menu_click(app: menus.MenuSystem, pos: tuple[int, int]) -> None:
    app._handle_menu_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
    )


def test_guest_can_return_to_sign_in_from_menu() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.username = None
    app.error_message = "A previous error"
    app.state = "menu"

    menu_click(app, menus.SIGN_IN_BUTTON.center)

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

    menu_click(app, menus.SIGN_IN_BUTTON.center)

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

    menu_click(app, menus.SIGN_IN_BUTTON.center)

    assert app.state == "menu"
    assert app.username == "alice"
    assert app.error_message == "Sign out failed: service unavailable"


def test_menu_layout_scales_and_centers_for_configured_window() -> None:
    layout = menus.MenuLayout(1000, 800)

    assert layout.scale == 1.25
    assert layout.offset == (0, 25)
    assert layout.rect(menus.PLAY_BUTTON).center == layout.point((265, 234))


def test_menu_click_target_uses_scaled_window_layout() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(1000, 800)
    app.state = "menu"
    app.start_game = False
    app.running = True

    menu_click(app, app.layout.rect(menus.PLAY_BUTTON).center)

    assert app.start_game
    assert not app.running


def test_main_menu_help_button_opens_controls_and_escape_returns_to_menu() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.state = "menu"
    app._handle_menu_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": app.layout.rect(menus.HELP_BUTTON).center},
        )
    )

    assert app.state == "help"
    app._handle_help_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert app.state == "menu"


def test_local_leaderboard_censors_rude_username_until_clicked() -> None:
    class Filter:
        value = ""

        def handle_event(self, event) -> None:
            return None

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.leaderboard_filter = Filter()
    app.leaderboard_rows = [
        {
            "run_id": "run-1",
            "username": "fuck player",
            "final_wave": 1,
            "survival_time": 10,
            "enemies_defeated": 2,
        }
    ]
    app.leaderboard_scroll = 0
    app.revealed_usernames = set()
    assert menus.censor_username("fuckface") == "********"
    assert menus.censor_username("garden") == "garden"

    pygame.font.init()
    app.font = pygame.font.Font(None, 22)
    click = app.layout.point((146, 221))
    app._handle_leaderboard_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": click})
    )

    assert "run-1" in app.revealed_usernames


def test_game_over_saves_guest_run_locally_and_requests_username() -> None:
    from elemental_game.screen_rendering.game_over import GameOverDialog

    class Store:
        def __init__(self) -> None:
            self.saved_runs = []

        def submit_run(self, *args, **kwargs) -> None:
            self.saved_runs.append((args, kwargs))

    class Menus:
        username = None
        store = Store()

    pygame.font.init()
    dialog = GameOverDialog(
        pygame.Surface((800, 600)),
        pygame.font.Font(None, 22),
        Menus(),
        run_id="run-guest",
        survival_time=61.5,
        final_wave=2,
        enemies_defeated=9,
    )

    assert dialog.state == "username"
    assert dialog.local_saved
    dialog.draw()
    assert Menus.store.saved_runs[0] == (
        ("run-guest", 61.5, 2, 9),
        {"username": "Guest"},
    )
    dialog.username_input.value = "player-one"
    dialog._save_guest_username()
    assert dialog.state == "publish"
    assert Menus.store.saved_runs[-1][1] == {"username": "player-one"}


def test_successful_publish_completes_game_over_dialog_immediately() -> None:
    from elemental_game.screen_rendering.game_over import GameOverDialog

    class Store:
        def submit_run(self, *args, **kwargs) -> None:
            return None

    class Client:
        def submit_run(self, run) -> None:
            return None

    class Auth:
        client = Client()

    class Menus:
        username = "player-one"
        store = Store()
        auth = Auth()

    pygame.font.init()
    dialog = GameOverDialog(
        pygame.Surface((800, 600)),
        pygame.font.Font(None, 22),
        Menus(),
        run_id="run-published",
        survival_time=61.5,
        final_wave=2,
        enemies_defeated=9,
    )

    dialog._publish()

    assert dialog.done


def test_exit_button_closes_menu_without_starting_game() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(1000, 800)
    app.state = "menu"
    app.start_game = False
    app.running = True
    app.username = None

    menu_click(app, app.layout.rect(menus.EXIT_BUTTON).center)

    assert not app.start_game
    assert not app.running
