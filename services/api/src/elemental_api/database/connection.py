from __future__ import annotations

import sqlite3
from pathlib import Path

from elemental_api.config import get_database_path


def initialize_database() -> None:
    path = Path(get_database_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        connection.executescript(schema)


def get_db_connection() -> sqlite3.Connection:
    initialize_database()
    path = Path(get_database_path())
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection
