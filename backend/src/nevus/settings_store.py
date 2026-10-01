# SPDX-License-Identifier: AGPL-3.0-only
"""Instance settings an administrator changes from the interface; environment variables are defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from nevus import secretbox
from nevus.config import Settings
from nevus.db.models import Setting

EMAIL_KEY = "notify.email"
INSTANCE_KEY = "instance"


def get(db: Session, key: str) -> Any:
    row = db.get(Setting, key)
    return None if row is None else row.value


def put(db: Session, key: str, value: Any, *, encrypted: bool = False) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value, encrypted=encrypted))
    else:
        row.value = value
        row.encrypted = encrypted
    db.flush()


@dataclass(frozen=True)
class EmailConfig:
    host: str | None
    port: int
    security: str
    username: str | None
    password: str | None
    sender: str | None
    public_url: str | None

    @property
    def ready(self) -> bool:
        return bool(self.host and self.sender)


def email_config(db: Session, settings: Settings) -> EmailConfig:
    stored = get(db, EMAIL_KEY) or {}
    password = settings.smtp_password
    if stored.get("password"):
        try:
            password = secretbox.open_(settings.secret_key(), stored["password"])
        except ValueError:
            password = None
    return EmailConfig(
        host=stored.get("host") or settings.smtp_host,
        port=int(stored.get("port") or settings.smtp_port),
        security=stored.get("security") or settings.smtp_security,
        username=stored.get("username") or settings.smtp_username,
        password=password,
        sender=stored.get("sender") or settings.smtp_from,
        public_url=stored.get("public_url") or settings.public_url,
    )


def save_email_config(db: Session, settings: Settings, values: dict[str, Any], password: str | None) -> None:
    """`password=None` keeps the stored one; an empty string removes it."""
    stored = dict(get(db, EMAIL_KEY) or {})
    stored.update({k: v for k, v in values.items() if k != "password"})
    if password is not None:
        stored["password"] = secretbox.seal(settings.secret_key(), password) if password else None
    put(db, EMAIL_KEY, stored, encrypted=True)


def default_language(db: Session) -> str:
    instance = get(db, INSTANCE_KEY) or {}
    value = instance.get("default_language")
    return value if value in ("en", "es") else "en"
