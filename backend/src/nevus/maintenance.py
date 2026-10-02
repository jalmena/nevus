# SPDX-License-Identifier: AGPL-3.0-only
"""Housekeeping jobs: building exports, the daily purge, the nightly backup and its weekly verification."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from nevus import backup, exporting, settings_store
from nevus.api.exports import EXPORT_KIND, mark_ready
from nevus.db.models import JOB_DONE, ROLE_ADMIN, Export, Job, User
from nevus.db.types import utcnow
from nevus.domain import purge
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger
from nevus.notify import email

log = get_logger(__name__)
BACKUP_KIND = "backup.nightly"
VERIFY_KIND = "backup.verify"
VERIFICATION_KEY = "backup.verification"


# --- exports ---------------------------------------------------------------------------------------


def _export_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = ctx.db.get(Export, uuid.UUID(payload["export_id"]))
    if row is None or row.status not in ("queued", "building") or not row.sealed_passphrase:
        return None
    row.status = "building"
    return exporting.plan(ctx.db, ctx.store, ctx.settings, row)


def _export_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    row = ctx.db.get(Export, uuid.UUID(payload["export_id"]))
    if row is not None:
        mark_ready(row, result["file_name"], int(result["bytes"]), ctx.settings.export_days)


register(JobKind(EXPORT_KIND, _export_load, exporting.build, _export_store, timeout=3600.0, max_attempts=2))


# --- backup ----------------------------------------------------------------------------------------


def _backup_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not ctx.settings.backup_passphrase:
        return None
    return {"settings": ctx.settings.model_dump(mode="json"), "passphrase": ctx.settings.backup_passphrase}


def _backup_run(value: dict[str, Any]) -> dict[str, Any]:
    from nevus.config import Settings

    settings = Settings(**value["settings"])
    path = backup.create(settings, value["passphrase"])
    removed = backup.prune(settings.backups_dir)
    return {"file": path.name, "bytes": path.stat().st_size, "pruned": len(removed)}


def _backup_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    log.info("backup.done", file=result["file"], bytes=result["bytes"], pruned=result["pruned"])


register(JobKind(BACKUP_KIND, _backup_load, _backup_run, _backup_store, timeout=6 * 3600.0, max_attempts=2))


# --- verification -----------------------------------------------------------------------------------


def _verify_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not ctx.settings.backup_passphrase:
        return None
    return {
        "settings": ctx.settings.model_dump(mode="json"),
        "passphrase": ctx.settings.backup_passphrase,
        "archive": payload.get("archive"),
    }


def _verify_run(value: dict[str, Any]) -> dict[str, Any]:
    from nevus.config import Settings

    settings = Settings(**value["settings"])
    archive = Path(value["archive"]) if value.get("archive") else None
    return backup.rehearse(settings, value["passphrase"], archive)


def _verify_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    settings_store.put(ctx.db, VERIFICATION_KEY, result)
    if result["ok"]:
        log.info("backup.verified", archive=result.get("archive"))
        return
    log.warning("backup.verification_failed", archive=result.get("archive"), problems=result["problems"])
    _warn_administrators(ctx, result)


def _warn_administrators(ctx: JobContext, result: dict[str, Any]) -> None:
    """A backup that would not restore is the one thing worth an email: every administrator with an
    address gets one, once the mail server is set up. The result is on the settings page regardless."""
    config = settings_store.email_config(ctx.db, ctx.settings)
    if not config.ready:
        return
    admins = ctx.db.scalars(
        select(User).where(User.role == ROLE_ADMIN, User.email.is_not(None), User.disabled_at.is_(None))
    ).all()
    body = (
        "The check of the latest backup of this neVus found problems.\n\n"
        + backup.describe(result)
        + "\n\nOpen Settings as an administrator for the details. Make sure a copy of the backups directory "
        "exists on another machine, and take a new backup once the cause is clear."
    )
    for admin in admins:
        try:
            email.send(email.envelope(config, str(admin.email), "neVus: the backup did not verify", body))
        except Exception as error:  # best effort; the warning is also on the settings page
            log.warning("backup.warning_not_sent", to=str(admin.id), error=str(error))


register(JobKind(VERIFY_KIND, _verify_load, _verify_run, _verify_store, timeout=4 * 3600.0, max_attempts=1))


# --- periodic --------------------------------------------------------------------------------------


def daily_housekeeping(ctx: JobContext) -> None:
    """Purge the trash, collect unreferenced files, expire exports, forget finished jobs."""
    counts = purge.purge_expired(ctx.db, ctx.settings.trash_days)
    removed = purge.collect_garbage(ctx.db, ctx.store)
    expired = purge.expire_exports(ctx.db, ctx.settings.exports_dir)
    ctx.db.execute(delete(Job).where(Job.status == JOB_DONE, Job.finished_at < utcnow() - timedelta(days=7)))
    log.info("housekeeping", **counts, blobs_removed=removed, exports_expired=expired)


def schedule_backup(ctx: JobContext, now: datetime | None = None) -> bool:
    """Queue tonight's backup once, after the backup hour in the instance time zone."""
    if not ctx.settings.backup_passphrase:
        return False
    zone = ZoneInfo(ctx.settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < ctx.settings.backup_hour:
        return False
    queued = queue.enqueue(ctx.db, BACKUP_KIND, {"date": local.date().isoformat()}, dedupe_key=f"backup:{local.date()}")
    return queued is not None


def schedule_verification(ctx: JobContext, now: datetime | None = None) -> bool:
    """Queue a read-back of the latest backup when the last one is older than the configured days,
    an hour after the backup hour so that the night's backup is the one checked."""
    settings = ctx.settings
    if not settings.backup_passphrase or settings.backup_verify_days <= 0:
        return False
    zone = ZoneInfo(settings.effective_timezone)
    local = (now or datetime.now(tz=zone)).astimezone(zone)
    if local.hour < min(settings.backup_hour + 1, 23):
        return False
    last = settings_store.get(ctx.db, VERIFICATION_KEY) or {}
    if last.get("checked_at"):
        checked_at = datetime.fromisoformat(last["checked_at"])
        if local - checked_at < timedelta(days=settings.backup_verify_days):
            return False
    queued = queue.enqueue(
        ctx.db, VERIFY_KIND, {"date": local.date().isoformat()}, dedupe_key=f"backup-verify:{local.date()}"
    )
    return queued is not None
