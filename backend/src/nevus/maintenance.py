# SPDX-License-Identifier: AGPL-3.0-only
"""Housekeeping jobs: building exports, the daily purge, and the nightly backup."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete

from nevus import backup, exporting
from nevus.api.exports import EXPORT_KIND, mark_ready
from nevus.db.models import JOB_DONE, Export, Job
from nevus.db.types import utcnow
from nevus.domain import purge
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.logging import get_logger

log = get_logger(__name__)
BACKUP_KIND = "backup.nightly"


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
