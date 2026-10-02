# SPDX-License-Identifier: AGPL-3.0-only
"""The job queue: claiming, leases that expire, retries with back-off, failures kept for inspection."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from nevus.config import Settings
from nevus.db.engine import make_engine, make_session_factory
from nevus.db.migrate import upgrade_to_head
from nevus.db.models import JOB_DONE, JOB_FAILED, JOB_QUEUED, JOB_RUNNING, Job
from nevus.db.types import utcnow
from nevus.jobs import queue
from nevus.jobs.registry import KINDS, JobContext, JobKind, identity, register
from nevus.jobs.runner import JobRunner
from nevus.storage.blobs import BlobStore

CALLS: list[str] = []


def _ok_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any]:
    CALLS.append(f"load:{payload['n']}")
    return payload


def _ok_store(ctx: JobContext, payload: dict[str, Any], result: Any) -> None:
    CALLS.append(f"store:{result['n']}")


def _sleepy(value: Any) -> Any:
    import time

    time.sleep(60)
    return value


def _boom(ctx: JobContext, payload: dict[str, Any]) -> None:
    raise RuntimeError("deliberate")


register(JobKind("test.ok", _ok_load, identity, _ok_store))
register(JobKind("test.boom", _boom, identity, _ok_store, max_attempts=2))


def _factory(settings: Settings) -> sessionmaker[Session]:
    upgrade_to_head(settings.effective_database_url)
    return make_session_factory(make_engine(settings.effective_database_url))


def test_jobs_run_in_priority_order_and_deduplicate(settings: Settings) -> None:
    factory = _factory(settings)
    CALLS.clear()
    with factory() as db:
        assert queue.enqueue(db, "test.ok", {"n": 1}) is not None
        assert queue.enqueue(db, "test.ok", {"n": 2}, priority=9, dedupe_key="two") is not None
        assert queue.enqueue(db, "test.ok", {"n": 2}, dedupe_key="two") is None
        db.commit()
    runner = JobRunner(factory, BlobStore(settings.blobs_dir), settings)
    assert runner.run_until_idle() == 2
    assert CALLS == ["load:2", "store:2", "load:1", "store:1"]
    with factory() as db:
        assert queue.counts(db)[JOB_DONE] == 2


def test_a_claimed_job_is_not_claimed_twice_and_an_expired_lease_comes_back(settings: Settings) -> None:
    factory = _factory(settings)
    with factory() as db:
        queue.enqueue(db, "test.ok", {"n": 3})
        db.commit()
    with factory() as db:
        job = queue.claim(db, lease_seconds=60)
        assert job is not None and job.status == JOB_RUNNING and job.attempts == 1
        assert queue.claim(db, lease_seconds=60) is None
        db.commit()
    with factory() as db:
        assert queue.requeue_expired(db, now=utcnow() + timedelta(seconds=61)) == 1
        db.commit()
        again = queue.claim(db, lease_seconds=60, now=utcnow() + timedelta(seconds=62))
        assert again is not None and again.attempts == 2


def test_failures_are_retried_with_back_off_then_kept(settings: Settings) -> None:
    factory = _factory(settings)
    with factory() as db:
        queue.enqueue(db, "test.boom", {}, max_attempts=2)
        db.commit()
    runner = JobRunner(factory, BlobStore(settings.blobs_dir), settings)
    assert runner.run_until_idle() == 1
    with factory() as db:
        job = db.query(Job).one()
        assert job.status == JOB_QUEUED and job.attempts == 1 and "deliberate" in (job.error or "")
        assert job.run_after > utcnow(), "the retry waits"
        job.run_after = utcnow() - timedelta(seconds=1)
        db.commit()
    assert runner.run_until_idle() == 1
    with factory() as db:
        job = db.query(Job).one()
        assert job.status == JOB_FAILED and job.attempts == 2


def test_unknown_kinds_fail_instead_of_looping(settings: Settings) -> None:
    factory = _factory(settings)
    with factory() as db:
        queue.enqueue(db, "test.nothing", {}, max_attempts=1)
        db.commit()
    JobRunner(factory, BlobStore(settings.blobs_dir), settings).run_until_idle()
    with factory() as db:
        assert db.query(Job).one().status == JOB_FAILED
    assert "test.nothing" not in KINDS


def test_stopping_the_supervisor_cancels_a_running_job_and_returns_promptly(settings: Settings) -> None:
    """A job still in the pool at shutdown must not keep a thread waiting forever."""
    import asyncio
    import time

    register(JobKind("test.slow", _ok_load, _sleepy, _ok_store, timeout=120))
    factory = _factory(settings)
    with factory() as db:
        queue.enqueue(db, "test.slow", {"n": 9})
        db.commit()
    live = settings.model_copy(update={"jobs_enabled": True, "job_poll_seconds": 0.1})
    runner = JobRunner(factory, BlobStore(settings.blobs_dir), live)
    runner.periodic = []

    async def scenario() -> float:
        await runner.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with factory() as db:
                if db.query(Job).one().status == JOB_RUNNING:
                    break
            await asyncio.sleep(0.1)
        await asyncio.sleep(1.0)  # the job is now inside the worker process
        started = time.monotonic()
        await runner.stop()
        return time.monotonic() - started

    assert asyncio.run(scenario()) < 20
    with factory() as db:
        job = db.query(Job).one()
        assert job.status in (JOB_QUEUED, JOB_RUNNING), "cancelled work comes back, it is not lost"
