# SPDX-License-Identifier: AGPL-3.0-only
"""Instance settings for administrators: email delivery and the default language for new accounts."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from nevus import settings_store
from nevus.auth import service
from nevus.auth.dependencies import AdminUser, AppSettings, DbSession, client_ip
from nevus.notify import email

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Lenient on purpose: home networks use names such as .home or .lan that strict validators reject.
ADDRESS = r"^[^@\s]+@[^@\s]+$"


class EmailSettingsOut(BaseModel):
    host: str | None
    port: int
    security: Literal["starttls", "ssl", "none"]
    username: str | None
    has_password: bool
    sender: str | None
    public_url: str | None
    ready: bool


class EmailSettingsIn(BaseModel):
    host: str | None = Field(default=None, max_length=253)
    port: int = Field(default=587, ge=1, le=65535)
    security: Literal["starttls", "ssl", "none"] = "starttls"
    username: str | None = Field(default=None, max_length=254)
    password: str | None = Field(default=None, max_length=1024, description="Omit to keep, empty to remove")
    sender: str | None = Field(default=None, max_length=254, pattern=ADDRESS)
    public_url: str | None = Field(default=None, max_length=300, pattern=r"^https?://")


class TestEmailIn(BaseModel):
    to: str = Field(max_length=254, pattern=ADDRESS)


class InstanceOut(BaseModel):
    default_language: Literal["en", "es"]


def _email_out(config: settings_store.EmailConfig) -> EmailSettingsOut:
    return EmailSettingsOut(
        host=config.host,
        port=config.port,
        security=config.security,
        username=config.username,
        has_password=bool(config.password),
        sender=config.sender,
        public_url=config.public_url,
        ready=config.ready,
    )


@router.get("/email", response_model=EmailSettingsOut)
def get_email(admin: AdminUser, db: DbSession, settings: AppSettings) -> EmailSettingsOut:
    return _email_out(settings_store.email_config(db, settings))


@router.put("/email", response_model=EmailSettingsOut)
def put_email(
    body: EmailSettingsIn, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> EmailSettingsOut:
    values = body.model_dump(exclude={"password"})
    settings_store.save_email_config(db, settings, values, body.password)
    service.audit(db, "settings.email", admin, "setting", None, client_ip(request, settings))
    return _email_out(settings_store.email_config(db, settings))


@router.post("/email/test", status_code=status.HTTP_204_NO_CONTENT)
def test_email(body: TestEmailIn, admin: AdminUser, db: DbSession, settings: AppSettings) -> None:
    """Send one message now and say plainly what went wrong if it did not go."""
    config = settings_store.email_config(db, settings)
    if not config.ready:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is not configured: a server and a sender are needed.")
    text = email.TEXT.get(admin.language, email.TEXT["en"])
    try:
        email.send(email.envelope(config, str(body.to), text["test_subject"], text["test_body"]))
    except (OSError, ValueError) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"The mail server refused: {error}") from error


@router.get("/instance", response_model=InstanceOut)
def get_instance(admin: AdminUser, db: DbSession) -> InstanceOut:
    return InstanceOut(default_language=settings_store.default_language(db))


@router.put("/instance", response_model=InstanceOut)
def put_instance(
    body: InstanceOut, request: Request, admin: AdminUser, db: DbSession, settings: AppSettings
) -> InstanceOut:
    settings_store.put(db, settings_store.INSTANCE_KEY, body.model_dump())
    service.audit(db, "settings.instance", admin, "setting", None, client_ip(request, settings))
    return body
