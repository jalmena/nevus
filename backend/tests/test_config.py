from __future__ import annotations

from pathlib import Path

from nevus.config import Settings


def test_sqlite_is_the_default_database_inside_the_data_dir(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    assert settings.is_sqlite
    assert settings.effective_database_url == f"sqlite:///{(tmp_path / 'nevus.sqlite3').as_posix()}"


def test_an_external_postgresql_url_is_used_verbatim(tmp_path: Path) -> None:
    url = "postgresql+psycopg://nevus:secret@db.example.test:5432/nevus"
    settings = Settings(data_dir=tmp_path, database_url=url)
    assert not settings.is_sqlite
    assert settings.effective_database_url == url


def test_allowed_hosts_accept_a_comma_separated_string(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, allowed_hosts="A.example.test, b.example.test")  # type: ignore[arg-type]
    assert settings.allowed_hosts == ["a.example.test", "b.example.test"]


def test_secret_key_is_generated_once_with_restrictive_permissions(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    first = settings.secret_key()
    second = settings.secret_key()
    assert first == second
    assert len(first) == 64
    assert oct((tmp_path / "secret.key").stat().st_mode & 0o777) == "0o600"
