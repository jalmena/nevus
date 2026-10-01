# SPDX-License-Identifier: AGPL-3.0-only
"""Encrypted exports of one person, or of the whole instance for administrators."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from nevus import secretbox
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, SudoSession, client_ip
from nevus.db.models import ACCESS_OWNER, Export, PersonAccess
from nevus.db.types import utcnow
from nevus.jobs import queue

router = APIRouter(prefix="/api/exports", tags=["exports"])
EXPORT_KIND = "export.build"


class ExportIn(BaseModel):
    person_id: uuid.UUID | None = Field(default=None, description="None exports every person (administrators only)")
    passphrase: str = Field(min_length=10, max_length=1024)


class ExportOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID | None
    status: str
    file_name: str | None
    bytes: int | None
    error: str | None
    created_at: datetime
    expires_at: datetime | None


def _out(row: Export) -> ExportOut:
    return ExportOut(
        id=row.id,
        person_id=row.person_id,
        status=row.status,
        file_name=row.file_name,
        bytes=row.bytes,
        error=row.error,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


@router.post("", response_model=ExportOut, status_code=status.HTTP_202_ACCEPTED)
def request_export(
    body: ExportIn, request: Request, session: SudoSession, db: DbSession, settings: AppSettings
) -> ExportOut:
    """Exporting everything is sensitive, so it needs the password again (sudo mode)."""
    user = session.user
    if body.person_id is None:
        if not user.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only administrators export the whole instance.")
    else:
        access = db.get(PersonAccess, (body.person_id, user.id))
        if access is None or access.role != ACCESS_OWNER:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    row = Export(
        person_id=body.person_id,
        requested_by=user.id,
        sealed_passphrase=secretbox.seal(settings.secret_key(), body.passphrase, purpose="export"),
    )
    db.add(row)
    db.flush()
    queue.enqueue(
        db, EXPORT_KIND, {"export_id": str(row.id)}, dedupe_key=f"export:{row.id}", priority=1, max_attempts=2
    )
    scope = str(body.person_id) if body.person_id else "all"
    service.audit(db, "export.request", user, "export", row.id, client_ip(request, settings), {"person": scope})
    return _out(row)


@router.get("", response_model=list[ExportOut])
def list_exports(user: CurrentUser, db: DbSession) -> list[ExportOut]:
    rows = db.scalars(select(Export).where(Export.requested_by == user.id).order_by(Export.created_at.desc())).all()
    return [_out(r) for r in rows]


def _mine(db: DbSession, export_id: uuid.UUID, user_id: uuid.UUID) -> Export:
    row = db.get(Export, export_id)
    if row is None or row.requested_by != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such export.")
    return row


@router.get("/{export_id}/download", response_class=FileResponse)
def download(
    export_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    row = _mine(db, export_id, user.id)
    if row.status != "ready" or not row.file_name:
        raise HTTPException(status.HTTP_409_CONFLICT, "The export is not ready.")
    path = settings.exports_dir / row.file_name
    if not path.is_file():
        raise HTTPException(status.HTTP_410_GONE, "The export has expired.")
    service.audit(db, "export.download", user, "export", row.id, client_ip(request, settings))
    return FileResponse(
        path, media_type="application/octet-stream", filename=row.file_name, headers={"Cache-Control": "no-store"}
    )


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_export(export_id: uuid.UUID, user: CurrentUser, db: DbSession, settings: AppSettings) -> Response:
    row = _mine(db, export_id, user.id)
    if row.file_name:
        (settings.exports_dir / row.file_name).unlink(missing_ok=True)
    db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def mark_ready(row: Export, file_name: str, size: int, days: int) -> None:
    """The archive exists: forget the passphrase and start the download window."""
    row.status = "ready"
    row.file_name = file_name
    row.bytes = size
    row.sealed_passphrase = None
    row.finished_at = utcnow()
    row.expires_at = utcnow() + timedelta(days=days)
