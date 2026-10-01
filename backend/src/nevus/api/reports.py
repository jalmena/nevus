# SPDX-License-Identifier: AGPL-3.0-only
"""PDF reports of one mark or of a person's whole map, made in the background and kept until deleted."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.db.models import ACCESS_MANAGER, ACCESS_OWNER, Lesion, Person, PersonAccess, Report, User
from nevus.jobs import queue
from nevus.reports.jobs import REPORT_KIND
from nevus.storage.blobs import BlobStore

router = APIRouter(prefix="/api", tags=["reports"])
Scope = Literal["lesion", "profile", "visit"]
RequestScope = Literal["lesion", "profile"]
Language = Literal["en", "es"]
Paper = Literal["a4", "letter"]


class ReportIn(BaseModel):
    scope: RequestScope
    lesion_id: uuid.UUID | None = None
    language: Language | None = None
    paper: Paper = "a4"


class ReportOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    scope: Scope
    lesion_ids: list[uuid.UUID]
    language: Language
    paper: Paper
    status: Literal["queued", "rendering", "ready", "failed"]
    bytes: int | None
    pages: int | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    download_url: str | None
    can_delete: bool


def _may_delete(row: Report, user: User, access: PersonAccess) -> bool:
    return row.requested_by == user.id or access.role in (ACCESS_OWNER, ACCESS_MANAGER)


def _out(row: Report, user: User, access: PersonAccess) -> ReportOut:
    return ReportOut(
        id=row.id,
        person_id=row.person_id,
        scope=row.scope,
        lesion_ids=[uuid.UUID(i) for i in row.lesion_ids],
        language=row.language,
        paper=row.paper,
        status=row.status,
        bytes=row.bytes,
        pages=row.pages,
        error=row.error,
        created_at=row.created_at,
        finished_at=row.finished_at,
        download_url=f"/api/reports/{row.id}/download" if row.status == "ready" else None,
        can_delete=_may_delete(row, user, access),
    )


def _access(db: DbSession, person_id: uuid.UUID, user: User) -> PersonAccess:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    return access


def _report(db: DbSession, report_id: uuid.UUID, user: User) -> tuple[Report, PersonAccess]:
    row = db.get(Report, report_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such report.")
    try:
        access = _access(db, row.person_id, user)
    except HTTPException:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such report.") from None
    return row, access


def create_report(
    db: Session,
    user: User,
    person_id: uuid.UUID,
    scope: str,
    lesion_ids: list[str],
    language: str | None,
    paper: str,
    ip: str | None,
    options: dict[str, Any] | None = None,
) -> Report:
    """A report row and its job; the PDF is ready a few seconds later."""
    row = Report(
        person_id=person_id,
        requested_by=user.id,
        scope=scope,
        lesion_ids=lesion_ids,
        language=language or (user.language if user.language in ("en", "es") else "en"),
        paper=paper,
        options=options or {},
    )
    db.add(row)
    db.flush()
    queue.enqueue(
        db, REPORT_KIND, {"report_id": str(row.id)}, dedupe_key=f"report:{row.id}", priority=2, max_attempts=2
    )
    service.audit(db, "report.request", user, "report", row.id, ip, {"scope": scope})
    return row


@router.post("/persons/{person_id}/reports", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
def request_report(
    person_id: uuid.UUID, body: ReportIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> ReportOut:
    """Anyone who may see the person may print what they see. The PDF is ready in a few seconds."""
    access = _access(db, person_id, user)
    lesion_ids: list[str] = []
    if body.scope == "lesion":
        lesion = db.get(Lesion, body.lesion_id) if body.lesion_id else None
        if lesion is None or lesion.person_id != person_id or lesion.deleted_at is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a mark of this person.")
        lesion_ids = [str(lesion.id)]
    row = create_report(
        db, user, person_id, body.scope, lesion_ids, body.language, body.paper, client_ip(request, settings)
    )
    return _out(row, user, access)


@router.get("/persons/{person_id}/reports", response_model=list[ReportOut])
def list_reports(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ReportOut]:
    access = _access(db, person_id, user)
    rows = db.scalars(select(Report).where(Report.person_id == person_id).order_by(Report.created_at.desc())).all()
    return [_out(row, user, access) for row in rows]


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ReportOut:
    row, access = _report(db, report_id, user)
    return _out(row, user, access)


@router.get("/reports/{report_id}/download", response_class=FileResponse)
def download_report(
    report_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    row, _ = _report(db, report_id, user)
    if row.status != "ready" or not row.blob_sha256:
        raise HTTPException(status.HTTP_409_CONFLICT, "The report is not ready.")
    store: BlobStore = request.app.state.blob_store
    path = store.path(row.blob_sha256, derived=True)
    if not path.is_file():
        raise HTTPException(status.HTTP_410_GONE, "The report file is missing: make it again.")
    service.audit(db, "report.download", user, "report", row.id, client_ip(request, settings))
    name = f"nevus-{row.scope}-report-{row.created_at:%Y-%m-%d}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=name, headers={"Cache-Control": "no-store"})


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    row, access = _report(db, report_id, user)
    if not _may_delete(row, user, access):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only its author or the person's managers delete a report.")
    db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
