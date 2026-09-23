"""Run the Alembic migrations programmatically, so a container upgrades its database at start-up."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

# backend/alembic in a checkout, /app/alembic in the image (src/nevus/db/migrate.py -> three levels up)
ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "alembic"


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.set_main_option("prepend_sys_path", str(ALEMBIC_DIR.parent / "src"))
    config.set_main_option("path_separator", "os")
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")
