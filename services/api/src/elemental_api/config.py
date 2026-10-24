from __future__ import annotations

import os
from pathlib import Path


def get_database_path() -> str:
    return os.environ.get(
        "ELEMENTAL_API_DB_PATH", str(Path(".local") / "elemental_api.db")
    )
