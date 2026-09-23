"""Runtime configuration, read from environment variables prefixed with NEVUS_."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings have safe defaults for a development checkout; the container sets the paths."""

    model_config = SettingsConfigDict(env_prefix="NEVUS_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("data"), description="Holds the database, blobs, backups and secrets")
    database_url: str | None = Field(default=None, description="SQLAlchemy URL; defaults to SQLite inside data_dir")
    static_dir: Path | None = Field(default=None, description="Built frontend; a placeholder is served when missing")
    allowed_hosts: list[str] = Field(default_factory=list, description="Hostnames answered beyond private addresses")
    secret_key_file: Path | None = Field(default=None, description="Server secret file; generated when missing")
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    role: Literal["all", "web", "worker"] = "all"
    workers: int = Field(default=1, ge=1, le=8, description="Analysis worker processes")
    bind: str = "0.0.0.0"  # noqa: S104 - the container binds all interfaces; the compose file publishes one host port
    port: int = Field(default=8080, ge=1, le=65535)

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [h.strip().lower() for h in value.split(",") if h.strip()]
        return value

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'nevus.sqlite3').as_posix()}"

    @property
    def is_sqlite(self) -> bool:
        return self.effective_database_url.startswith("sqlite")

    @property
    def blobs_dir(self) -> Path:
        return self.data_dir / "blobs"

    def secret_key(self) -> bytes:
        """Return the server secret, creating it with restrictive permissions on first use."""
        path = self.secret_key_file or self.data_dir / "secret.key"
        if path.exists():
            return path.read_bytes().strip()
        path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_hex(32).encode()
        path.touch(mode=0o600)
        path.write_bytes(key)
        path.chmod(0o600)
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
