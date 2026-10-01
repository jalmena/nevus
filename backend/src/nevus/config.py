"""Runtime configuration, read from environment variables prefixed with NEVUS_."""

from __future__ import annotations

import ipaddress
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """All settings have safe defaults for a development checkout; the container sets the paths."""

    model_config = SettingsConfigDict(env_prefix="NEVUS_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("data"), description="Holds the database, blobs, backups and secrets")
    database_url: str | None = Field(default=None, description="SQLAlchemy URL; defaults to SQLite inside data_dir")
    static_dir: Path | None = Field(default=None, description="Built frontend; a placeholder is served when missing")
    # NoDecode keeps pydantic-settings from parsing the variable as JSON, so a plain "a.example, b.example" works.
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=list, description="Hostnames answered beyond private addresses; comma-separated"
    )
    secret_key_file: Path | None = Field(default=None, description="Server secret file; generated when missing")
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    role: Literal["all", "web", "worker"] = "all"
    workers: int = Field(default=1, ge=1, le=8, description="Analysis worker processes")
    jobs_enabled: bool = Field(default=True, description="Run the background job supervisor in this process")
    job_poll_seconds: float = Field(default=1.0, gt=0, le=60)
    job_lease_seconds: int = Field(default=300, ge=10, le=3600)
    bind: str = "0.0.0.0"  # noqa: S104 - the container binds all interfaces; the compose file publishes one host port
    port: int = Field(default=8080, ge=1, le=65535)
    auto_migrate: bool = Field(default=True, description="Apply pending database migrations at start-up")
    admin_user: str | None = Field(default=None, description="First administrator, created or reset at start-up")
    admin_password: str | None = Field(default=None, description="Password for admin_user; read at start-up only")
    session_idle_days: int = Field(default=14, ge=1, le=365)
    session_max_days: int = Field(default=90, ge=1, le=3650)
    sudo_minutes: int = Field(default=5, ge=1, le=60)
    login_attempts: int = Field(default=10, ge=3, le=100, description="Failed logins allowed per window")
    login_window_minutes: int = Field(default=15, ge=1, le=1440)
    trust_proxy_headers: bool = Field(default=False, description="Trust X-Forwarded-Proto/For from a reverse proxy")
    auth_mode: Literal["local", "proxy"] = Field(
        default="local", description="proxy: a reverse proxy signs people in and passes the username in a header"
    )
    proxy_user_header: str = Field(default="Remote-User", description="Header carrying the signed-in username")
    proxy_email_header: str | None = Field(default="Remote-Email", description="Header carrying the email, if any")
    proxy_trusted: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Addresses or networks of the reverse proxy, comma-separated; required in proxy mode",
    )
    proxy_auto_create: bool = Field(default=True, description="Create a member account for a new proxy username")
    proxy_logout_url: str | None = Field(default=None, description="Where signing out goes in proxy mode")
    max_upload_bytes: int = Field(default=30 * 1024 * 1024, ge=1024 * 1024)
    max_upload_pixels: int = Field(default=24_000_000, ge=1_000_000)
    min_free_bytes: int = Field(default=2 * 1024**3, ge=0, description="Refuse uploads below this free space")
    timezone: str | None = Field(default=None, description="Instance time zone for daily tasks; falls back to TZ")
    public_url: str | None = Field(default=None, description="Address people use to reach neVus, for links in emails")
    reminder_hour: int = Field(default=8, ge=0, le=23, description="Local hour after which daily reminders go out")
    trash_days: int = Field(default=30, ge=1, le=365, description="Days in the trash before the purge")
    person_quota_bytes: int | None = Field(default=None, ge=0, description="Soft storage quota per person")
    backup_passphrase: str | None = Field(default=None, description="Enables the nightly encrypted backup")
    backup_hour: int = Field(default=3, ge=0, le=23, description="Local hour after which the nightly backup runs")
    export_days: int = Field(default=7, ge=1, le=60, description="Days an export stays downloadable")
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [h.strip().lower() for h in value.split(",") if h.strip()]
        return value

    @field_validator("proxy_trusted", mode="before")
    @classmethod
    def _split_networks(cls, value: object) -> object:
        if isinstance(value, str):
            value = [n.strip() for n in value.split(",") if n.strip()]
        if isinstance(value, list):
            for network in value:
                ipaddress.ip_network(str(network), strict=False)  # a typo fails at start-up, not at sign-in
        return value

    @model_validator(mode="after")
    def _proxy_needs_its_address(self) -> Settings:
        if self.auth_mode == "proxy" and not self.proxy_trusted:
            raise ValueError(
                "NEVUS_AUTH_MODE=proxy needs NEVUS_PROXY_TRUSTED, the address or network of the reverse proxy: "
                "without it anyone who reaches neVus could claim to be anyone."
            )
        return self

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

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def effective_timezone(self) -> str:
        """NEVUS_TIMEZONE, else the container's TZ (CasaOS sets it), else UTC."""
        import os
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        for candidate in (self.timezone, os.environ.get("TZ"), "UTC"):
            if candidate:
                try:
                    ZoneInfo(candidate)
                    return candidate
                except (ZoneInfoNotFoundError, ValueError):
                    continue
        return "UTC"

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
