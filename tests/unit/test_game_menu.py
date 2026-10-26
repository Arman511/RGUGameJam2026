from __future__ import annotations

from unittest.mock import Mock

import pygame
from elemental_game import menus
from elemental_game.api_client.http import APIError
from elemental_game.menus.common import (
    CREDITS_BUTTON,
    HINTS_TOGGLE_BUTTON,
    UPDATE_DOWNLOAD_BUTTON,
)
from elemental_game.version_check import UpdateInfo, check_for_update


def test_register_page_uses_windows_browser_from_wsl(monkeypatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    commands: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> None:
        commands.append((command, kwargs))

    monkeypatch.setattr(menus.subprocess, "run", fake_run)

    assert menus.open_registration_page()
    assert commands[0][0] == [
        "cmd.exe",
        "/c",
        "start",
        "",
        "https://elemental-keep.armandev.co.uk/register",
    ]


def test_version_check_returns_newer_release(monkeypatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        "elemental_game.version_check.httpx.get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "version": "v2.1.0",
                "release_url": "https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0",
            },
        ),
    )

    assert check_for_update("https://api.example.com/", "v2.0.2") == UpdateInfo(
        version="v2.1.0",
        release_url="https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0",
    )


def test_version_check_ignores_current_or_newer_version(monkeypatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        "elemental_game.version_check.httpx.get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "version": "v2.1.0",
                "release_url": "https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0",
            },
        ),
    )

    assert check_for_update("https://api.example.com", "v2.1.0") is None
    assert check_for_update("https://api.example.com", "v2.2.0") is None


def test_update_prompt_opens_release_download(monkeypatch) -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.update_info = UpdateInfo(
        version="v2.1.0",
        release_url="https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0",
    )
    app.update_prompt_open = True
    app.update_open_error = ""
    opened_urls: list[str] = []
    monkeypatch.setattr(
        menus.system,
        "open_external_page",
        lambda url: (opened_urls.append(url), True)[1],
    )

    app._handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {
                "button": 1,
                "pos": app.layout.rect(UPDATE_DOWNLOAD_BUTTON).center,
            },
        )
    )

    assert opened_urls == [
        "https://github.com/Arman511/RGUGameJam2026/releases/tag/v2.1.0"
    ]
    assert not app.update_prompt_open


def test_register_page_uses_the_selected_api_server(monkeypatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    commands = []
    monkeypatch.setattr(
        menus.subprocess,
        "run",
        lambda command, **kwargs: commands.append((command, kwargs)),
    )

    assert menus.open_registration_page("https://staging.example.com/")

    assert commands[0][0][-1] == "https://staging.example.com/register"


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
        menus.login,
        "open_registration_page",
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
    monkeypatch.setattr(menus.login, "open_registration_page", lambda: False)

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


def test_credits_button_opens_modal_and_escape_closes_it() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.state = "menu"

    menu_click(app, CREDITS_BUTTON.center)

    assert app.state == "credits"
    app._handle_credits_event(
        pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
    )
    assert app.state == "menu"


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


def test_leaderboard_filter_is_horizontally_centered() -> None:
    assert menus.LEADERBOARD_FILTER_RECT.centerx == menus.MENU_DESIGN_WIDTH // 2


def test_settings_toggle_gameplay_hints() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.api_base_url_input = menus.InputField(
        menus.API_BASE_URL_INPUT,
        placeholder="https://example.com",
        max_length=255,
    )
    app.hints_enabled = True
    click_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": HINTS_TOGGLE_BUTTON.center},
    )

    app._handle_settings_event(click_event)
    assert app.hints_enabled is False

    app._handle_settings_event(click_event)
    assert app.hints_enabled is True


def test_settings_api_input_accepts_text_without_triggering_gameplay_actions() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.api_base_url_input = menus.InputField(
        menus.API_BASE_URL_INPUT,
        placeholder="https://example.com",
        max_length=255,
    )
    app.dragging_slider = None
    app.hints_enabled = True
    app.api_base_url_input.value = ""

    app._handle_settings_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menus.API_BASE_URL_INPUT.center},
        )
    )
    app._handle_settings_event(
        pygame.event.Event(
            pygame.KEYDOWN,
            {"key": pygame.K_h, "unicode": "h"},
        )
    )

    assert app.api_base_url_input.value == "h"
    assert app.api_base_url_input.focused
    assert app.hints_enabled


def test_settings_player_selector_is_aligned_and_separated_from_clear_button() -> None:
    assert menus.PLAYER_PREVIOUS_BUTTON.centery == menus.PLAYER_SELECT_PANEL.centery
    assert menus.PLAYER_NEXT_BUTTON.centery == menus.PLAYER_SELECT_PANEL.centery
    assert menus.CLEAR_LEADERBOARD_BUTTON.top - menus.PLAYER_SELECT_PANEL.bottom >= 10


def test_settings_slider_updates_manual_turret_sensitivity() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.dragging_slider = "manual_turret_sensitivity"
    app.manual_turret_sensitivity = 0.5

    app._update_slider(menus.TURRET_SENSITIVITY_SLIDER.right)

    assert app.manual_turret_sensitivity == 1.0


def test_settings_save_updates_persisted_api_url_and_turret_sensitivity(tmp_path) -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from elemental_game.database.local_database import LocalLeaderboardStore

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.store = LocalLeaderboardStore(path=tmp_path / "settings.db")
    app.api_base_url_input = menus.InputField(
        menus.API_BASE_URL_INPUT,
        placeholder="https://example.com",
        max_length=255,
    )
    app.api_base_url = "https://elemental-keep.armandev.co.uk"
    app.api_base_url_input.value = "https://staging.example.com"
    app.login_username = menus.InputField(
        menus.LOGIN_USERNAME_RECT,
        placeholder="Username",
        max_length=32,
    )
    app.login_username.value = "alice"
    app.login_password = menus.InputField(
        menus.LOGIN_PASSWORD_RECT,
        placeholder="Password",
        max_length=128,
        secret=True,
    )
    app.login_password.value = "S3cretpass!"
    app.auth = SimpleNamespace(client=SimpleNamespace(base_url="old"))
    app.credentials = Mock()
    app.username = "alice"
    app.error_message = ""
    app._save_sound_preferences = Mock()
    app.manual_turret_sensitivity = 0.8
    app.state = "settings"

    app._close_settings()

    assert app.api_base_url == "https://staging.example.com"
    assert app.auth.client.base_url == "https://staging.example.com"
    assert app.store.api_base_url() == "https://staging.example.com"
    assert app.store.manual_turret_sensitivity() == 0.8
    assert app.state == "menu"
    assert app.credentials.clear_token.called
    assert app.username is None
    assert app.login_username.value == ""
    assert app.login_password.value == ""
    assert "Sign in again" in app.error_message


def test_host_fetches_server_timeout_before_creating_room(monkeypatch) -> None:
    from types import SimpleNamespace

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.auth = SimpleNamespace(
        client=SimpleNamespace(
            get_match_config=Mock(
                return_value=SimpleNamespace(join_timeout_seconds=45.25)
            )
        )
    )
    app.username = "alice"
    app.error_message = ""
    app.state = "online_select"
    app.api_base_url = "https://staging.example.com"
    client = SimpleNamespace(room_code="ABC123")
    used_endpoints = []
    monkeypatch.setattr(
        menus.MultiplayerClient,
        "host",
        lambda _username, *, base_url: (
            used_endpoints.append(base_url),
            client,
        )[1],
    )
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    app._host_multiplayer_game()

    assert app.multiplayer_client is client
    assert app.host_join_timeout_ms == 45250
    assert app.host_join_deadline_ms == 46250
    assert app.state == "hosting"
    assert used_endpoints == ["https://staging.example.com"]


def test_queued_host_starts_countdown_when_room_is_created(monkeypatch) -> None:
    from types import SimpleNamespace

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.multiplayer_client = SimpleNamespace(
        poll=lambda: [{"type": "room_created", "payload": {"room_code": "ABC123"}}]
    )
    app.host_join_timeout_ms = 5000
    app.host_join_deadline_ms = None
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 2000)

    app._poll_hosting_room()

    assert app.host_join_deadline_ms == 7000


def test_hosting_screen_displays_remaining_join_time(monkeypatch) -> None:
    from types import SimpleNamespace

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.multiplayer_client = SimpleNamespace(room_code="ABC123", queue_position=None)
    app.host_join_deadline_ms = 2500
    app.error_message = ""
    app._draw_panel = Mock()
    app._draw_title = Mock()
    app._draw_text = Mock()
    app._draw_button = Mock()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    app._draw_hosting()

    assert any(
        call.args[:3] == ("Time remaining: 2s", 400, 350)
        for call in app._draw_text.call_args_list
    )


def test_help_instructions_and_expired_room_message_fit_their_panel() -> None:
    from pathlib import Path

    pygame.font.init()
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.font = pygame.font.Font(
        str(Path(menus.ASSETS_DIR) / "font" / "pixelfont.ttf"), 28
    )
    app._draw_panel = Mock()
    app._draw_title = Mock()
    app._draw_text = Mock()
    app._draw_button = Mock()

    app._draw_help()

    app._draw_panel.assert_called_once_with(menus.MENU_FRAME_PANEL)
    assert menus.MENU_FRAME_PANEL == pygame.Rect(5, 60, 775, 475)
    assert menus.MENU_FRAME_PANEL.width > menus.MENU_FRAME_PANEL.height
    assert menus.MENU_FRAME_PANEL.contains(menus.HELP_BACK_BUTTON)
    assert menus.SETTINGS_PANEL.contains(menus.SAVE_SETTINGS_BUTTON)
    assert menus.MENU_FRAME_PANEL.contains(pygame.Rect(115, 70, 570, 45))
    instruction_calls = app._draw_text.call_args_list
    assert instruction_calls
    assert all(
        call.kwargs["text_font"].size(call.args[0])[0] <= 680
        for call in instruction_calls
    )
    assert all(
        call.kwargs["text_font"].get_height() < app.font.get_height()
        for call in instruction_calls
    )
    assert min(call.args[2] for call in instruction_calls) >= 145
    assert all(
        call.args[2] + call.kwargs["text_font"].get_linesize() // 2
        < menus.HELP_BACK_BUTTON.top
        for call in instruction_calls
    )
    assert app.font.size("Room expired. No player joined.")[0] <= 520


def test_menu_click_target_uses_scaled_window_layout() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(1000, 800)
    app.state = "menu"
    app.start_game = False
    app.running = True

    menu_click(app, app.layout.rect(menus.PLAY_BUTTON).center)

    assert app.state == "mode_select"
    app._handle_mode_select_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": app.layout.rect(menus.SINGLE_PLAYER_BUTTON).center},
        )
    )

    assert app.game_mode == "single"
    assert app.start_game
    assert not app.running


def test_mode_selection_can_open_online_join_menu() -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.state = "mode_select"
    app.join_code = menus.InputField(
        menus.JOIN_CODE_RECT, placeholder="Room code", max_length=6
    )

    app._handle_mode_select_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menus.ONLINE_PLAYER_BUTTON.center},
        )
    )
    app._handle_online_select_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menus.JOIN_MATCH_BUTTON.center},
        )
    )

    assert app.state == "join_room"
    assert app.join_code.value == ""


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


def test_local_leaderboard_scroll_uses_visible_row_count() -> None:
    class Filter:
        value = ""

        def handle_event(self, event) -> None:
            return None

    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.leaderboard_filter = Filter()
    app.leaderboard_rows = [
        {
            "run_id": f"run-{index}",
            "username": f"player-{index}",
            "final_wave": index,
            "survival_time": index,
            "enemies_defeated": index,
        }
        for index in range(15)
    ]
    app.leaderboard_scroll = 0
    app._handle_leaderboard_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -99}))

    assert app.leaderboard_scroll == 6


def test_leaderboard_scroll_hint_does_not_overlap_visible_records() -> None:
    from pathlib import Path

    class Filter:
        value = ""

        def draw(self, surface, font) -> None:
            return None

    pygame.font.init()
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.layout = menus.MenuLayout(800, 600)
    app.font = pygame.font.Font(
        str(Path(menus.ASSETS_DIR) / "font" / "pixelfont.ttf"), 28
    )
    app.screen = pygame.Surface((800, 600))
    app.leaderboard_filter = Filter()
    app.leaderboard_rows = [
        {
            "run_id": f"run-{index}",
            "username": f"player-{index}",
            "final_wave": index,
            "survival_time": index,
            "enemies_defeated": index,
        }
        for index in range(10)
    ]
    app.leaderboard_scroll = 0
    app.revealed_usernames = set()
    app._draw_panel = Mock()
    app._draw_text = Mock()
    app._draw_button = Mock()

    app._draw_leaderboard()

    row_calls = [
        call
        for call in app._draw_text.call_args_list
        if call.args[0].startswith("player-")
    ]
    hint_call = next(
        call
        for call in app._draw_text.call_args_list
        if call.args[0] == "Scroll to see more runs"
    )
    hint_top = app.font.render(hint_call.args[0], True, (245, 245, 245)).get_rect(
        center=(400, hint_call.args[2])
    ).top

    assert row_calls
    assert max(call.args[2] + app.font.get_linesize() for call in row_calls) <= hint_top


def test_game_over_saves_guest_or_local_alias_and_finishes(monkeypatch) -> None:
    from elemental_game.screen_rendering.game_over import GameOverDialog

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)

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
    assert Menus.store.saved_runs[0] == (
        ("run-guest", 61.5, 2, 9),
        {"username": "Guest"},
    )
    ticks = 1500
    dialog.handle_event(pygame.event.Event(pygame.TEXTINPUT, {"text": "player-one"}))
    dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert dialog.done
    assert dialog.state == "username"
    assert dialog.username == "player-one"
    assert Menus.store.saved_runs[-1][1] == {"username": "player-one"}


def test_guest_can_finish_game_over_without_entering_a_username(monkeypatch) -> None:
    from elemental_game.screen_rendering.game_over import GameOverDialog

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)

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
        run_id="run-guest-finish",
        survival_time=12.0,
        final_wave=1,
        enemies_defeated=2,
    )

    ticks = 1500
    dialog.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": dialog._button_rect(1).center},
        )
    )

    assert dialog.done
    assert Menus.store.saved_runs[0][1] == {"username": "Guest"}


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


def test_multiplayer_game_over_keeps_mouse_dismissal_immediate(
    monkeypatch,
) -> None:
    from elemental_game.screen_rendering.multiplayer_game_over import (
        MultiplayerGameOverDialog,
    )

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    pygame.font.init()
    dialog = MultiplayerGameOverDialog(
        pygame.Surface((800, 600)),
        pygame.font.Font(None, 22),
        "victory",
    )

    for key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
        dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key}))
        assert not dialog.done

    dialog.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": dialog._menu_button_rect().center},
        )
    )

    assert dialog.done


def test_multiplayer_game_over_keyboard_dismissal_waits_half_second(
    monkeypatch,
) -> None:
    from elemental_game.screen_rendering.multiplayer_game_over import (
        MultiplayerGameOverDialog,
    )

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)
    pygame.font.init()
    dialog = MultiplayerGameOverDialog(
        pygame.Surface((800, 600)),
        pygame.font.Font(None, 22),
        "victory",
    )

    ticks = 1499
    dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert not dialog.done

    ticks = 1500
    dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert dialog.done


def test_multiplayer_defeat_screen_says_you_lost(monkeypatch) -> None:
    from elemental_game.screen_rendering.multiplayer_game_over import (
        MultiplayerGameOverDialog,
    )

    rendered = []

    class Font:
        def render(self, text, *_args):
            rendered.append(text)
            return pygame.Surface((1, 1), pygame.SRCALPHA)

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)
    dialog = MultiplayerGameOverDialog(pygame.Surface((800, 600)), Font(), "defeat")
    ticks = 1500
    dialog.draw()

    assert "You Lost" in rendered


def test_single_player_game_over_waits_half_second_before_showing_or_accepting_input(
    monkeypatch,
) -> None:
    from elemental_game.screen_rendering.game_over import GameOverDialog

    class Store:
        def submit_run(self, *args, **kwargs) -> None:
            return None

    class Menus:
        username = "player-one"
        store = Store()

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)
    pygame.font.init()
    surface = pygame.Surface((800, 600))
    surface.fill((100, 100, 100))
    dialog = GameOverDialog(
        surface,
        pygame.font.Font(None, 22),
        Menus(),
        run_id="run-delay",
        survival_time=20.0,
        final_wave=1,
        enemies_defeated=3,
    )

    ticks = 1499
    dialog.draw()
    dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert surface.get_at((0, 0)) == (100, 100, 100, 255)
    assert not dialog.done

    ticks = 1500
    dialog.draw()
    assert surface.get_at((0, 0)) != (100, 100, 100, 255)
    dialog.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
    assert dialog.done


def test_multiplayer_defeat_waits_half_second_before_showing_or_accepting_input(
    monkeypatch,
) -> None:
    from elemental_game.screen_rendering.multiplayer_game_over import (
        MultiplayerGameOverDialog,
    )

    ticks = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: ticks)
    pygame.font.init()
    surface = pygame.Surface((800, 600))
    surface.fill((100, 100, 100))
    dialog = MultiplayerGameOverDialog(
        surface,
        pygame.font.Font(None, 22),
        "defeat",
    )

    ticks = 1499
    dialog.draw()
    dialog.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": dialog._menu_button_rect().center},
        )
    )
    assert surface.get_at((0, 0)) == (100, 100, 100, 255)
    assert not dialog.done

    ticks = 1500
    dialog.draw()
    assert surface.get_at((0, 0)) != (100, 100, 100, 255)
    dialog.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": dialog._menu_button_rect().center},
        )
    )
    assert dialog.done


def test_game_over_plays_explosion_for_single_player_and_loser_only(
    monkeypatch,
) -> None:
    from elemental_game.screen_rendering import game_over, multiplayer_game_over

    played: list[str] = []
    monkeypatch.setattr(game_over, "play_sfx", played.append)
    monkeypatch.setattr(multiplayer_game_over, "play_sfx", played.append)

    class Store:
        def submit_run(self, *args, **kwargs) -> None:
            return None

    class Menus:
        username = "player-one"
        store = Store()

    pygame.font.init()
    font = pygame.font.Font(None, 22)
    surface = pygame.Surface((800, 600))
    game_over.GameOverDialog(
        surface,
        font,
        Menus(),
        run_id="run-single",
        survival_time=20.0,
        final_wave=1,
        enemies_defeated=3,
    )
    multiplayer_game_over.MultiplayerGameOverDialog(surface, font, "victory")
    multiplayer_game_over.MultiplayerGameOverDialog(surface, font, "defeat")

    assert played == ["explosion", "explosion"]


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


def test_menu_quit_does_not_draw_a_final_frame(monkeypatch) -> None:
    app = menus.MenuSystem.__new__(menus.MenuSystem)
    app.clock = Mock()
    app.preferences = {"music_volume": 0.5}
    app.state = "menu"
    app.layout = menus.MenuLayout(800, 600)
    app.start_game = False
    app._draw = Mock()
    flip = Mock()

    monkeypatch.setattr(menus.system, "play_background_music", Mock())
    monkeypatch.setattr(pygame.display, "flip", flip)

    events = (
        pygame.event.Event(pygame.QUIT),
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {
                "button": 1,
                "pos": app.layout.rect(menus.EXIT_BUTTON).center,
            },
        ),
    )
    for event in events:
        app._handle_event = Mock(wraps=app._handle_event)
        monkeypatch.setattr(pygame.event, "get", lambda event=event: [event])

        assert not app.run()
        app._draw.assert_not_called()

    flip.assert_not_called()
