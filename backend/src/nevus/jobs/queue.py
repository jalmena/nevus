# SPDX-License-Identifier: AGPL-3.0-only
"""The job table as a queue. Portable SQL only: claiming is a conditional UPDATE checked by row count."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from nevus.db.models import JOB_DONE, JOB_FAILED, JOB_QUEUED, JOB_RUNNING, Job
from nevus.db.types import utcnow


def enqueue(
    db: Session,
    kind: str,
    payload: dict[str, Any],
    *,
    dedupe_key: str | None = None,
    priority: int = 0,
    run_after: datetime | None = None,
    max_attempts: int = 3,
) -> Job | None:
    """Queue a job. With a dedupe key, a second identical job is not queued while the first one exists."""
    if dedupe_key is not None:
        existing = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
        if existing is not None:
            return None
    job = Job(
        kind=kind,
        payload=payload,
        dedupe_key=dedupe_key,
        priority=priority,
        run_after=run_after or utcnow(),
        max_attempts=max_attempts,
    )
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
    except IntegrityError:
        return None
    return job


def requeue_expired(db: Session, now: datetime | None = None) -> int:
    """Jobs whose worker vanished (restart, crash) go back to the queue."""
    now = now or utcnow()
    result = db.execute(
        update(Job)
        .where(Job.status == JOB_RUNNING, Job.lease_until.is_not(None), Job.lease_until < now)
        .values(status=JOB_QUEUED, lease_until=None)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def claim(db: Session, lease_seconds: int, now: datetime | None = None) -> Job | None:
    """Take the most urgent due job. Two workers racing for the same row: only one UPDATE matches."""
    now = now or utcnow()
    candidates = db.scalars(
        select(Job.id)
        .where(Job.status == JOB_QUEUED, Job.run_after <= now)
        .order_by(Job.priority.desc(), Job.run_after, Job.created_at)
        .limit(5)
    ).all()
    for job_id in candidates:
        result = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JOB_QUEUED)
            .values(
                status=JOB_RUNNING,
                lease_until=now + timedelta(seconds=lease_seconds),
                attempts=Job.attempts + 1,
                started_at=now,
            )
        )
        if int(getattr(result, "rowcount", 0) or 0) == 1:
            db.flush()
            job = db.get(Job, job_id)
            if job is not None:
                db.refresh(job)
            return job
    return None


def finish(db: Session, job_id: uuid.UUID) -> None:
    db.execute(
        update(Job).where(Job.id == job_id).values(status=JOB_DONE, lease_until=None, finished_at=utcnow(), error=None)
    )


def fail(db: Session, job_id: uuid.UUID, error: str, now: datetime | None = None) -> None:
    """Retry with a growing delay until the attempts run out, then keep the job as failed for inspection."""
    now = now or utcnow()
    job = db.get(Job, job_id)
    if job is None:
        return
    job.error = error[:4000]
    job.lease_until = None
    if job.attempts >= job.max_attempts:
        job.status = JOB_FAILED
        job.finished_at = now
    else:
        job.status = JOB_QUEUED
        job.run_after = now + timedelta(seconds=30 * 2 ** max(job.attempts - 1, 0))
    db.flush()


def counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(Job.status, Job.id)).all()
    out = {JOB_QUEUED: 0, JOB_RUNNING: 0, JOB_DONE: 0, JOB_FAILED: 0}
    for status, _ in rows:
        out[status] = out.get(status, 0) + 1
    return out
