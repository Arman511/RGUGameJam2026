from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from .migrations import upgrade_database


def get_default_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "ElementalKeep"
    if sys_platform := os.environ.get("XDG_DATA_HOME"):
        return Path(sys_platform) / "elemental_keep"
    if os.environ.get("DARWIN") or os.name == "posix":
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
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO leaderboard(run_id, timestamp, survival_time, final_wave, enemies_defeated)
                VALUES (?, datetime('now'), ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    survival_time = excluded.survival_time,
                    final_wave = excluded.final_wave,
                    enemies_defeated = excluded.enemies_defeated
                """,
                (run_id, survival_time, final_wave, enemies_defeated),
            )
            connection.commit()

    def top_scores(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, timestamp, survival_time, final_wave, enemies_defeated
                FROM leaderboard
                ORDER BY survival_time DESC, enemies_defeated DESC, final_wave DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def personal_best(self) -> dict[str, Any] | None:
        rows = self.top_scores(limit=1)
        return rows[0] if rows else None
