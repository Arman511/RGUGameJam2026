from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL


def upgrade_database(database_path: Path) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    database_url = URL.create("sqlite", database=str(database_path)).render_as_string(
        hide_password=False
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
