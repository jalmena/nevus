# SPDX-License-Identifier: AGPL-3.0-only
"""The report job: gather in the main process, render in a worker, keep the PDF as a derived blob."""

from __future__ import annotations

import uuid
from typing import Any

from nevus.db.models import Person, Report
from nevus.db.types import utcnow
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.reports import render
from nevus.reports.data import gather

REPORT_KIND = "report.render"


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = ctx.db.get(Report, uuid.UUID(payload["report_id"]))
    if row is None or row.status not in ("queued", "rendering"):
        return None
    person = ctx.db.get(Person, row.person_id)
    if person is None or person.deleted_at is not None:
        row.status, row.error, row.finished_at = "failed", "The person is no longer available.", utcnow()
        return None
    row.status = "rendering"
    data = gather(ctx.db, ctx.store, ctx.settings, person, row.scope, list(row.lesion_ids), row.language, row.paper)
    row.analyzer_versions = data["analyzers"]
    return data


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    row = ctx.db.get(Report, uuid.UUID(payload["report_id"]))
    if row is None:
        return
    pdf: bytes = result["pdf"]
    row.blob_sha256 = ctx.store.put(pdf, derived=True)
    row.bytes = len(pdf)
    row.pages = int(result["pages"])
    row.status = "ready"
    row.error = None
    row.finished_at = utcnow()


def _failed(ctx: JobContext, payload: dict[str, Any], message: str) -> None:
    row = ctx.db.get(Report, uuid.UUID(payload["report_id"]))
    if row is not None:
        # The job keeps the technical detail for the operator; the person gets a plain sentence.
        row.status, row.error, row.finished_at = "failed", "The report could not be made.", utcnow()


register(JobKind(REPORT_KIND, _load, render.render, _store, timeout=300.0, max_attempts=2, on_failure=_failed))
