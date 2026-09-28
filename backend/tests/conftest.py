from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from nevus.app import create_app
from nevus.config import Settings


def _reset_database(url: str) -> None:
    """SQLite gets a fresh file per test; an external PostgreSQL is shared, so its schema is recreated."""
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    settings = Settings(data_dir=tmp_path / "data", allowed_hosts=["nevus.example.test"], log_level="warning")
    if not settings.is_sqlite:
        _reset_database(settings.effective_database_url)
    return settings


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client
