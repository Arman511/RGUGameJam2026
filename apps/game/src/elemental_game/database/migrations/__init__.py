from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _table_columns(
    connection: sqlite3.Connection, table_name: str
) -> list[tuple[int, str, str, int, Any, int]]:
    return connection.execute(f"PRAGMA table_info({table_name})").fetchall()


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    )


def _rename_table(connection: sqlite3.Connection, old_name: str, new_name: str) -> None:
    connection.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')


def upgrade_database(database_path: Path) -> None:
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        leaderboard_columns = {
            column[1] for column in _table_columns(connection, "leaderboard")
        }
        if not _table_exists(connection, "leaderboard"):
            connection.execute("""
                CREATE TABLE leaderboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    survival_time REAL NOT NULL,
                    final_wave INTEGER NOT NULL,
                    enemies_defeated INTEGER NOT NULL,
                    username TEXT NOT NULL DEFAULT 'Guest'
                )
                """)
        else:
            if "score" in leaderboard_columns:
                if "username" not in leaderboard_columns:
                    connection.execute(
                        "ALTER TABLE leaderboard ADD COLUMN username TEXT NOT NULL DEFAULT 'Guest'"
                    )
                    leaderboard_columns = {
                        column[1] for column in _table_columns(connection, "leaderboard")
                    }
                connection.execute("""
                    CREATE TABLE leaderboard_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL UNIQUE,
                        timestamp TEXT NOT NULL,
                        survival_time REAL NOT NULL,
                        final_wave INTEGER NOT NULL,
                        enemies_defeated INTEGER NOT NULL,
                        username TEXT NOT NULL DEFAULT 'Guest'
                    )
                    """)
                connection.execute("""
                    INSERT INTO leaderboard_new (
                        id, run_id, timestamp, survival_time, final_wave,
                        enemies_defeated, username
                    )
                    SELECT id, run_id, timestamp, survival_time, final_wave,
                           enemies_defeated, COALESCE(username, 'Guest')
                    FROM leaderboard
                    """)
                _rename_table(connection, "leaderboard", "leaderboard_old")
                _rename_table(connection, "leaderboard_new", "leaderboard")
                connection.execute("DROP TABLE leaderboard_old")
            if "username" not in leaderboard_columns:
                connection.execute(
                    "ALTER TABLE leaderboard ADD COLUMN username TEXT NOT NULL DEFAULT 'Guest'"
                )

        if not _table_exists(connection, "game_settings"):
            connection.execute("""
                CREATE TABLE game_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value REAL NOT NULL DEFAULT 1.0
                    CHECK (setting_value >= 0.0 AND setting_value <= 1.0)
                )
                """)

        if not _table_exists(connection, "player_settings"):
            connection.execute("""
                CREATE TABLE player_settings (
                    setting_key TEXT PRIMARY KEY,
                    player_number INTEGER NOT NULL
                    CHECK (player_number BETWEEN 1 AND 6)
                )
                """)
            connection.execute(
                "INSERT INTO player_settings(setting_key, player_number) VALUES ('player_number', 1)"
            )
        elif not connection.execute(
            "SELECT 1 FROM player_settings WHERE setting_key = 'player_number'"
        ).fetchone():
            connection.execute(
                "INSERT INTO player_settings(setting_key, player_number) VALUES ('player_number', 1)"
            )

        if not _table_exists(connection, "game_text_settings"):
            connection.execute("""
                CREATE TABLE game_text_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                )
                """)

        if not _table_exists(connection, "alembic_version"):
            connection.execute(
                "CREATE TABLE alembic_version (version_num TEXT NOT NULL)"
            )
        connection.execute("DELETE FROM alembic_version")
        connection.execute(
            "INSERT INTO alembic_version(version_num) VALUES ('0007_api_base_url')"
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_leaderboard_rank ON leaderboard (survival_time, enemies_defeated, final_wave)"
        )
        connection.commit()
