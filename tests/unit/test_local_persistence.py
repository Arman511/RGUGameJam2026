import sqlite3
from pathlib import Path

from game_core.local_database import LocalLeaderboardStore


def test_database_initialises_and_persists_runs(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run(
        run_id="run-1",
        survival_time=64.2,
        final_wave=5,
        enemies_defeated=14,
    )
    rows = db.top_scores(limit=5)
    assert rows[0]["survival_time"] == 64.2
    assert rows[0]["run_id"] == "run-1"


def test_duplicate_run_ids_are_handled_safely(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run("run-dup", 5.0, 2, 4)
    db.submit_run("run-dup", 7.0, 3, 5)
    assert db.top_scores(limit=10)[0]["survival_time"] == 7.0


def test_legacy_local_leaderboard_migrates_without_score(tmp_path: Path) -> None:
    path = tmp_path / "leaderboard.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                survival_time REAL NOT NULL,
                final_wave INTEGER NOT NULL,
                score INTEGER NOT NULL,
                enemies_defeated INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO leaderboard
                (run_id, timestamp, survival_time, final_wave, score, enemies_defeated)
            VALUES ('legacy-run', '2026-10-24 10:00:00', 64.2, 5, 1500, 14)
            """
        )

    store = LocalLeaderboardStore(path=path)

    assert store.top_scores()[0] == {
        "run_id": "legacy-run",
        "timestamp": "2026-10-24 10:00:00",
        "survival_time": 64.2,
        "final_wave": 5,
        "enemies_defeated": 14,
    }
    with sqlite3.connect(path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(leaderboard)")
        }
    assert revision == "0002_remove_local_score"
    assert "score" not in columns
