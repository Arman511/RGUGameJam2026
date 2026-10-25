import sqlite3
from pathlib import Path

import pytest
from elemental_game.config import ELEMENTAL_KEEP_API_BASE_URL
from elemental_game.database.local_database import LocalLeaderboardStore


def test_database_initialises_and_persists_runs(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run(
        run_id="run-1",
        survival_time=64.2,
        final_wave=5,
        enemies_defeated=14,
        username="alice",
    )
    rows = db.top_scores(limit=5)
    assert rows[0]["survival_time"] == 64.2
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["username"] == "alice"


def test_duplicate_run_ids_are_handled_safely(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run("run-dup", 5.0, 2, 4, username="alice")
    db.submit_run("run-dup", 7.0, 3, 5, username="bob")
    assert db.top_scores(limit=10)[0]["survival_time"] == 7.0
    assert db.top_scores(limit=10)[0]["username"] == "bob"


def test_scores_are_separated_by_username(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run("alice-run", 5.0, 2, 4, username="alice")
    db.submit_run("bob-run", 7.0, 3, 5, username="bob")

    assert [row["username"] for row in db.top_scores()] == ["bob", "alice"]
    assert [row["run_id"] for row in db.top_scores(username="alice")] == ["alice-run"]
    assert db.personal_best(username="bob")["run_id"] == "bob-run"  # type: ignore


def test_leaderboard_sorts_by_wave_and_can_return_all_rows(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run("long-run", 900.0, 1, 2, username="alice")
    db.submit_run("high-wave", 30.0, 8, 2, username="bob")

    assert [row["run_id"] for row in db.top_scores(limit=None)] == [
        "high-wave",
        "long-run",
    ]


def test_sound_preferences_persist_and_validate(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    assert db.sound_preferences() == {"music_volume": 0.5, "sfx_volume": 0.5}
    db.save_sound_preferences(music_volume=0.4, sfx_volume=0.7)
    assert db.sound_preferences() == {"music_volume": 0.4, "sfx_volume": 0.7}

    try:
        db.save_sound_preferences(music_volume=1.1, sfx_volume=0.7)
    except ValueError as error:
        assert str(error) == "sound volumes must be between 0.0 and 1.0"
    else:
        raise AssertionError("out-of-range sound settings must not be saved")


def test_manual_turret_sensitivity_defaults_persists_and_validates(
    tmp_path: Path,
) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    assert db.manual_turret_sensitivity() == 0.5
    db.save_manual_turret_sensitivity(0.75)
    assert LocalLeaderboardStore(path=db.path).manual_turret_sensitivity() == 0.75

    with pytest.raises(ValueError, match="manual turret sensitivity"):
        db.save_manual_turret_sensitivity(1.1)


def test_api_server_url_defaults_persists_and_validates(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    assert db.api_base_url() == ELEMENTAL_KEEP_API_BASE_URL
    db.save_api_base_url("https://staging.example.com/")
    assert LocalLeaderboardStore(path=db.path).api_base_url() == (
        "https://staging.example.com"
    )

    for invalid_url in (
        "",
        "staging.example.com",
        "ftp://staging.example.com",
        "https://example.com/path",
        "https://user:secret@example.com",
        "https://example.com?debug=1",
    ):
        with pytest.raises(ValueError, match="server URL"):
            db.save_api_base_url(invalid_url)


def test_hints_setting_defaults_on_persists_and_validates(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    assert db.hints_enabled() is True
    db.save_hints_enabled(False)
    assert LocalLeaderboardStore(path=db.path).hints_enabled() is False
    db.save_hints_enabled(True)
    assert LocalLeaderboardStore(path=db.path).hints_enabled() is True

    try:
        db.save_hints_enabled(1)  # type: ignore[arg-type]
    except ValueError as error:
        assert str(error) == "hints_enabled must be a boolean"
    else:
        raise AssertionError("non-boolean hints settings must not be saved")


def test_player_image_number_persists_and_validates(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    assert db.player_image_number() == 1
    db.save_player_image_number(6)
    assert db.player_image_number() == 6

    try:
        db.save_player_image_number(7)
    except ValueError as error:
        assert str(error) == "player image number must be between 1 and 6"
    else:
        raise AssertionError("out-of-range player image numbers must not be saved")


def test_run_requires_a_nonempty_username(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")

    try:
        db.submit_run("run-empty-name", 5.0, 2, 4, username="  ")
    except ValueError as error:
        assert str(error) == "username must not be empty"
    else:
        raise AssertionError("empty usernames must not be saved")


def test_legacy_local_leaderboard_migrates_without_score(tmp_path: Path) -> None:
    path = tmp_path / "leaderboard.db"
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                survival_time REAL NOT NULL,
                final_wave INTEGER NOT NULL,
                score INTEGER NOT NULL,
                enemies_defeated INTEGER NOT NULL
            )
            """)
        connection.execute("""
            INSERT INTO leaderboard
                (run_id, timestamp, survival_time, final_wave, score, enemies_defeated)
            VALUES ('legacy-run', '2026-10-24 10:00:00', 64.2, 5, 1500, 14)
            """)

    store = LocalLeaderboardStore(path=path)

    assert store.top_scores()[0] == {
        "run_id": "legacy-run",
        "timestamp": "2026-10-24 10:00:00",
        "survival_time": 64.2,
        "final_wave": 5,
        "enemies_defeated": 14,
        "username": "Guest",
    }
    with sqlite3.connect(path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(leaderboard)")
        }
    assert revision == "0007_api_base_url"
    assert "score" not in columns


def test_leaderboard_rank_index_is_created(tmp_path: Path) -> None:
    path = tmp_path / "leaderboard.db"
    LocalLeaderboardStore(path=path)

    with sqlite3.connect(path) as connection:
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(leaderboard)")
        }

    assert "ix_leaderboard_rank" in indexes
