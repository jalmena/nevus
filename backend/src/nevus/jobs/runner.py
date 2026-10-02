# SPDX-License-Identifier: AGPL-3.0-only
"""Running jobs: inline (tests, CLI) or under the asyncio supervisor with a process pool."""

from __future__ import annotations

import asyncio
import contextlib
import multiprocessing
import os
import traceback
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from nevus.config import Settings
from nevus.db.models import Job
from nevus.jobs import queue
from nevus.jobs.registry import KINDS, JobContext, JobKind
from nevus.logging import get_logger
from nevus.storage.blobs import BlobStore

log = get_logger(__name__)


def _load_kinds() -> None:
    """Import every module that registers job kinds."""
    import nevus.jobs.kinds  # noqa: F401


def default_periodic() -> list[Periodic]:
    """Recurring work: email digests and the nightly backup (checked every quarter of an hour, queued once
    a day), and the daily housekeeping (trash purge, file collection, expired exports)."""
    from nevus.maintenance import daily_housekeeping, schedule_backup
    from nevus.notify.email import schedule_digests

    def digests(ctx: JobContext) -> None:
        schedule_digests(ctx)

    def backups(ctx: JobContext) -> None:
        schedule_backup(ctx)

    return [
        Periodic("email-digests", 900.0, digests),
        Periodic("nightly-backup", 900.0, backups),
        Periodic("housekeeping", 24 * 3600.0, daily_housekeeping),
    ]


def _init_worker() -> None:
    """Workers run at lower priority with one thread each, so the web stays responsive on four cores."""
    with contextlib.suppress(OSError):
        os.nice(10)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    try:
        import cv2

        cv2.setNumThreads(1)
    except ImportError:
        pass


@dataclass
class Periodic:
    name: str
    every_seconds: float
    action: Callable[[JobContext], None]
    last_run: float = field(default=0.0)


class JobRunner:
    def __init__(self, session_factory: sessionmaker[Session], store: BlobStore, settings: Settings) -> None:
        _load_kinds()
        self.session_factory = session_factory
        self.store = store
        self.settings = settings
        self.periodic: list[Periodic] = default_periodic()
        self._pool: Any = None
        self._inflight: set[Future[Any]] = set()
        self._tasks: list[asyncio.Task[None]] = []
        self._stopping = asyncio.Event()

    # --- inline ---------------------------------------------------------------------------------

    def run_one(self) -> bool:
        """Claim and run one due job in this process. Returns False when the queue is idle."""
        with self.session_factory() as db:
            queue.requeue_expired(db)
            job = queue.claim(db, self.settings.job_lease_seconds)
            db.commit()
            if job is None:
                return False
            job_id, kind_name, payload = job.id, job.kind, dict(job.payload)
        self._execute(job_id, kind_name, payload, lambda kind, value: kind.compute(value))
        return True

    def run_until_idle(self, limit: int = 1000) -> int:
        done = 0
        while done < limit and self.run_one():
            done += 1
        return done

    def run_periodic_now(self) -> None:
        for task in self.periodic:
            self._run_periodic(task)

    # --- shared ---------------------------------------------------------------------------------

    def _execute(
        self, job_id: Any, kind_name: str, payload: dict[str, Any], compute: Callable[[JobKind, Any], Any]
    ) -> None:
        kind = KINDS.get(kind_name)
        try:
            if kind is None:
                raise LookupError(f"unknown job kind {kind_name!r}")
            with self.session_factory() as db:
                value = kind.load(JobContext(db, self.store, self.settings), payload)
                db.commit()
            if value is not None:
                result = compute(kind, value)
                with self.session_factory() as db:
                    kind.store(JobContext(db, self.store, self.settings), payload, result)
                    db.commit()
            with self.session_factory() as db:
                queue.finish(db, job_id)
                db.commit()
        except Exception as error:
            log.warning("job.failed", kind=kind_name, job=str(job_id), error=type(error).__name__)
            with self.session_factory() as db:
                queue.fail(db, job_id, "".join(traceback.format_exception_only(error)).strip())
                db.commit()

    def _run_periodic(self, task: Periodic) -> None:
        try:
            with self.session_factory() as db:
                task.action(JobContext(db, self.store, self.settings))
                db.commit()
        except Exception as error:
            log.warning("periodic.failed", task=task.name, error=type(error).__name__)

    # --- supervisor -----------------------------------------------------------------------------

    async def start(self) -> None:
        from pebble import ProcessPool

        self._pool = ProcessPool(
            max_workers=self.settings.workers,
            initializer=_init_worker,
            context=multiprocessing.get_context("spawn"),  # type: ignore[arg-type]
        )
        self._stopping.clear()
        for slot in range(self.settings.workers):
            self._tasks.append(asyncio.create_task(self._worker_loop(slot)))
        self._tasks.append(asyncio.create_task(self._periodic_loop()))
        log.info("jobs.started", workers=self.settings.workers)

    async def stop(self) -> None:
        """Stop taking work, cancel what is running in the pool, and wait for the worker threads.

        A running job is cancelled rather than awaited: its lease brings it back after a restart.
        Without the cancellation a thread would wait forever on a result the stopped pool never
        delivers, and the process could not exit.
        """
        self._stopping.set()
        for future in list(self._inflight):
            future.cancel()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._tasks.clear()
        if self._pool is not None:
            self._pool.stop()
            await asyncio.to_thread(self._pool.join, 10)
            self._pool = None

    async def _worker_loop(self, slot: int) -> None:
        poll = self.settings.job_poll_seconds
        while not self._stopping.is_set():
            claimed = await asyncio.to_thread(self._claim)
            if claimed is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), timeout=poll)
                continue
            job_id, kind_name, payload = claimed
            await asyncio.to_thread(self._execute, job_id, kind_name, payload, self._compute_in_pool)

    def _claim(self) -> tuple[Any, str, dict[str, Any]] | None:
        with self.session_factory() as db:
            queue.requeue_expired(db)
            job: Job | None = queue.claim(db, self.settings.job_lease_seconds)
            db.commit()
            return None if job is None else (job.id, job.kind, dict(job.payload))

    def _compute_in_pool(self, kind: JobKind, value: Any) -> Any:
        if self._stopping.is_set() or self._pool is None:
            raise RuntimeError("the job supervisor is stopping")
        future: Future[Any] = self._pool.schedule(kind.compute, args=(value,), timeout=kind.timeout)
        self._inflight.add(future)
        try:
            # Pebble enforces kind.timeout in the worker; the margin only guards against a lost pool.
            return future.result(timeout=kind.timeout + 60)
        finally:
            self._inflight.discard(future)

    async def _periodic_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stopping.is_set():
            now = loop.time()
            for task in self.periodic:
                if now - task.last_run >= task.every_seconds:
                    task.last_run = now
                    await asyncio.to_thread(self._run_periodic, task)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=5)
