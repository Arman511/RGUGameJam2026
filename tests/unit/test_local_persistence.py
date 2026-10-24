import sqlite3
from pathlib import Path

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
    assert revision == "0004_local_leaderboard_username"
    assert "score" not in columns


def test_leaderboard_rank_index_is_created(tmp_path: Path) -> None:
    path = tmp_path / "leaderboard.db"
    LocalLeaderboardStore(path=path)

    with sqlite3.connect(path) as connection:
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(leaderboard)")
        }

    assert "ix_leaderboard_rank" in indexes
