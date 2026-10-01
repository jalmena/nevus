# SPDX-License-Identifier: AGPL-3.0-only
"""A person's calendar feed behind a secret link (FR-REM-03): next photo dates and appointments.

The link is the only credential a calendar app can carry, so it is long, shown once, stored as a hash,
and checked against the maker's current access on every read.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from nevus import settings_store
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.db.models import CalendarFeed, Person, PersonAccess, User
from nevus.db.types import utcnow
from nevus.notify.calendar import feed

router = APIRouter(prefix="/api", tags=["calendar"])


class FeedOut(BaseModel):
    exists: bool
    created_at: datetime | None
    last_used_at: datetime | None


class NewFeedOut(BaseModel):
    url: str
    created_at: datetime


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _person(db: DbSession, person_id: uuid.UUID, user: User) -> Person:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    return person


def _mine(db: DbSession, person_id: uuid.UUID, user_id: uuid.UUID) -> CalendarFeed | None:
    return db.scalar(select(CalendarFeed).where(CalendarFeed.person_id == person_id, CalendarFeed.user_id == user_id))


@router.get("/persons/{person_id}/calendar", response_model=FeedOut)
def get_feed(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FeedOut:
    _person(db, person_id, user)
    row = _mine(db, person_id, user.id)
    return FeedOut(
        exists=row is not None,
        created_at=row.created_at if row else None,
        last_used_at=row.last_used_at if row else None,
    )


@router.post("/persons/{person_id}/calendar", response_model=NewFeedOut, status_code=status.HTTP_201_CREATED)
def new_feed(
    person_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> NewFeedOut:
    """A new secret link; the previous one, if any, stops working."""
    _person(db, person_id, user)
    existing = _mine(db, person_id, user.id)
    if existing is not None:
        db.delete(existing)
        db.flush()
    token = secrets.token_urlsafe(32)
    row = CalendarFeed(person_id=person_id, user_id=user.id, token_hash=_hash(token))
    db.add(row)
    db.flush()
    base = settings_store.email_config(db, settings).public_url or str(request.base_url)
    service.audit(db, "calendar.create", user, "person", person_id, client_ip(request, settings))
    return NewFeedOut(url=f"{base.rstrip('/')}/api/calendar/{token}.ics", created_at=row.created_at)


@router.delete("/persons/{person_id}/calendar", status_code=status.HTTP_204_NO_CONTENT)
def stop_feed(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    _person(db, person_id, user)
    row = _mine(db, person_id, user.id)
    if row is not None:
        db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/calendar/{token}.ics", include_in_schema=False)
def calendar(token: str, db: DbSession, settings: AppSettings) -> Response:
    """No session: calendar apps cannot sign in. The secret link and the maker's access decide."""
    row = db.scalar(select(CalendarFeed).where(CalendarFeed.token_hash == _hash(token)))
    user = db.get(User, row.user_id) if row else None
    person = db.get(Person, row.person_id) if row else None
    access = db.get(PersonAccess, (row.person_id, row.user_id)) if row else None
    if (
        row is None
        or user is None
        or user.disabled_at is not None
        or person is None
        or person.deleted_at is not None
        or access is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such calendar.")
    row.last_used_at = utcnow()
    body = feed(db, person, user.language, settings_store.email_config(db, settings).public_url)
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "private, max-age=300", "Content-Disposition": 'inline; filename="nevus.ics"'},
    )
