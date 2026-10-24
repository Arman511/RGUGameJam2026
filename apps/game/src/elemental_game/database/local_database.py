from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from .migrations import upgrade_database


def get_default_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "ElementalKeep"
    if sys_platform := os.environ.get("XDG_DATA_HOME"):
        return Path(sys_platform) / "elemental_keep"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ElementalKeep"
    if os.name == "posix":
        return Path.home() / ".local" / "share" / "elemental_keep"
    return Path.home() / ".elemental_keep"


class LocalLeaderboardStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else get_default_data_dir() / "leaderboard.db"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        upgrade_database(self.path)

    def submit_run(
        self,
        run_id: str,
        survival_time: float,
        final_wave: int,
        enemies_defeated: int,
        *,
        username: str,
    ) -> None:
        username = username.strip()
        if not username:
            raise ValueError("username must not be empty")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO leaderboard(
                    run_id, timestamp, survival_time, final_wave, enemies_defeated, username
                )
                VALUES (?, datetime('now'), ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    survival_time = excluded.survival_time,
                    final_wave = excluded.final_wave,
                    enemies_defeated = excluded.enemies_defeated,
                    username = excluded.username
                """,
                (run_id, survival_time, final_wave, enemies_defeated, username),
            )
            connection.commit()

    def top_scores(
        self, limit: int | None = 10, *, username: str | None = None
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if username is None:
                query = """
                    SELECT run_id, timestamp, survival_time, final_wave,
                        enemies_defeated, username
                    FROM leaderboard
                    ORDER BY final_wave DESC, survival_time DESC, enemies_defeated DESC
                """
                parameters: tuple[Any, ...] = ()
            else:
                query = """
                    SELECT run_id, timestamp, survival_time, final_wave,
                        enemies_defeated, username
                    FROM leaderboard
                    WHERE username = ?
                    ORDER BY final_wave DESC, survival_time DESC, enemies_defeated DESC
                """
                parameters = (username,)
            if limit is not None:
                if limit < 0:
                    raise ValueError("limit must not be negative")
                query += " LIMIT ?"
                parameters += (limit,)
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def personal_best(self, *, username: str | None = None) -> dict[str, Any] | None:
        rows = self.top_scores(limit=1, username=username)
        return rows[0] if rows else None

    def clear_leaderboard(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM leaderboard")
            connection.commit()

    def sound_preferences(self) -> dict[str, float]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT setting_key, setting_value
                FROM game_settings
                WHERE setting_key IN ('music_volume', 'sfx_volume')
                """
            ).fetchall()
        preferences = {"music_volume": 0.5, "sfx_volume": 0.5}
        preferences.update({row["setting_key"]: row["setting_value"] for row in rows})
        return preferences

    def save_sound_preferences(
        self, *, music_volume: float, sfx_volume: float
    ) -> None:
        if not 0.0 <= music_volume <= 1.0 or not 0.0 <= sfx_volume <= 1.0:
            raise ValueError("sound volumes must be between 0.0 and 1.0")
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO game_settings(setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value
                """,
                (
                    ("music_volume", music_volume),
                    ("sfx_volume", sfx_volume),
                ),
            )
            connection.commit()

    def player_image_number(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT player_number
                FROM player_settings
                WHERE setting_key = 'player_number'
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("player image setting is missing from the database")
        return int(row["player_number"])

    def save_player_image_number(self, player_number: int) -> None:
        if type(player_number) is not int or not 1 <= player_number <= 6:
            raise ValueError("player image number must be between 1 and 6")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO player_settings(setting_key, player_number)
                VALUES ('player_number', ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    player_number = excluded.player_number
                """,
                (player_number,),
            )
            connection.commit()
