# SPDX-License-Identifier: AGPL-3.0-only
"""Instance settings for administrators: email delivery, the default language for new accounts, the backups."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from nevus import backup, settings_store
from nevus.auth import service
from nevus.auth.dependencies import AdminUser, AppSettings, DbSession, client_ip
from nevus.db.models import JOB_QUEUED, JOB_RUNNING, Job
from nevus.jobs import queue
from nevus.maintenance import BACKUP_KIND, VERIFICATION_KEY, VERIFY_KIND
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


class BackupFileOut(BaseModel):
    file: str
    bytes: int
    created_at: datetime


class VerificationOut(BaseModel):
    """What the last read-back of a backup found; see `backup.rehearse`."""

    ok: bool
    checked_at: datetime
    archive: str | None = None
    archive_bytes: int | None = None
    created_at: str | None = None
    nevus_version: str | None = None
    database: str | None = None
    integrity: str | None = None
    images: int | None = None
    blobs_in_archive: int | None = None
    blobs_damaged: int | None = None
    blobs_missing_from_archive: int | None = None
    secret_present: bool | None = None
    live_store: dict[str, int] | None = None
    problems: list[str]


class BackupStatusOut(BaseModel):
    enabled: bool
    backup_hour: int
    verify_days: int
    count: int
    latest: BackupFileOut | None
    verification: VerificationOut | None
    backup_queued: bool
    verification_queued: bool


class QueuedOut(BaseModel):
    queued: bool


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


# --- backups ----------------------------------------------------------------------------------------


def _backup_files(settings: Any) -> list[BackupFileOut]:
    directory = settings.backups_dir
    if not directory.is_dir():
        return []
    out: list[BackupFileOut] = []
    for path in sorted(directory.glob("nevus-backup-*.tar.age")):
        try:
            made = datetime.strptime(path.name, backup.NAME_FORMAT).replace(tzinfo=UTC)
        except ValueError:
            continue
        out.append(BackupFileOut(file=path.name, bytes=path.stat().st_size, created_at=made))
    return out


def _queued(db: DbSession, kind: str) -> bool:
    return (
        db.scalar(select(Job.id).where(Job.kind == kind, Job.status.in_([JOB_QUEUED, JOB_RUNNING])).limit(1))
        is not None
    )


@router.get("/backups", response_model=BackupStatusOut)
def backup_status(admin: AdminUser, db: DbSession, settings: AppSettings) -> BackupStatusOut:
    files = _backup_files(settings)
    stored = settings_store.get(db, VERIFICATION_KEY)
    return BackupStatusOut(
        enabled=bool(settings.backup_passphrase),
        backup_hour=settings.backup_hour,
        verify_days=settings.backup_verify_days,
        count=len(files),
        latest=files[-1] if files else None,
        verification=VerificationOut.model_validate(stored) if stored else None,
        backup_queued=_queued(db, BACKUP_KIND),
        verification_queued=_queued(db, VERIFY_KIND),
    )


def _on_demand(db: DbSession, settings: Any, kind: str, prefix: str) -> QueuedOut:
    if not settings.backup_passphrase:
        raise HTTPException(status.HTTP_409_CONFLICT, "Set NEVUS_BACKUP_PASSPHRASE first; see docs/DEPLOYMENT.md.")
    minute = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M")
    job = queue.enqueue(db, kind, {"date": minute, "manual": True}, dedupe_key=f"{prefix}:manual:{minute}")
    return QueuedOut(queued=job is not None)


@router.post("/backups/run", response_model=QueuedOut, status_code=status.HTTP_202_ACCEPTED)
def backup_now(request: Request, admin: AdminUser, db: DbSession, settings: AppSettings) -> QueuedOut:
    out = _on_demand(db, settings, BACKUP_KIND, "backup")
    service.audit(db, "backup.run", admin, None, None, client_ip(request, settings))
    return out


@router.post("/backups/verify", response_model=QueuedOut, status_code=status.HTTP_202_ACCEPTED)
def verify_now(request: Request, admin: AdminUser, db: DbSession, settings: AppSettings) -> QueuedOut:
    out = _on_demand(db, settings, VERIFY_KIND, "backup-verify")
    service.audit(db, "backup.verify", admin, None, None, client_ip(request, settings))
    return out
