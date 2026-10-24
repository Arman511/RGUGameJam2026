from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from elemental_api.config import get_database_path


@lru_cache(maxsize=8)
def _engine_for_url(database_url: str) -> Engine:
    return create_engine(database_url, connect_args={"check_same_thread": False})


def get_database_url() -> str:
    path = Path(get_database_path()).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def get_engine() -> Engine:
    return _engine_for_url(get_database_url())


@lru_cache(maxsize=8)
def _session_factory_for_url(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine_for_url(database_url), expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session_factory = _session_factory_for_url(get_database_url())
    with session_factory() as session:
        yield session


def initialize_database() -> None:
    config_path = Path(__file__).resolve().parents[3] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", get_database_url())
    command.upgrade(config, "head")
