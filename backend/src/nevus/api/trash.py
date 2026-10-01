# SPDX-License-Identifier: AGPL-3.0-only
"""The trash: what was deleted in the last days, put back with one tap, or removed for good."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, SudoSession, client_ip
from nevus.cv.pipeline import refresh_observation_flags
from nevus.db.models import ACCESS_MANAGER, ACCESS_OWNER, Image, Lesion, Observation, Person, PersonAccess, User
from nevus.domain import purge

router = APIRouter(prefix="/api/trash", tags=["trash"])
Kind = Literal["person", "lesion", "observation", "image"]
Trashed = Person | Lesion | Observation | Image


class TrashItem(BaseModel):
    kind: Kind
    id: uuid.UUID
    label: str
    person_id: uuid.UUID
    person_name: str
    deleted_at: datetime
    purge_after: datetime


def _roles(db: Session, user: User) -> dict[uuid.UUID, str]:
    rows = db.execute(select(PersonAccess.person_id, PersonAccess.role).where(PersonAccess.user_id == user.id))
    return {person_id: role for person_id, role in rows}


@router.get("", response_model=list[TrashItem])
def list_trash(user: CurrentUser, db: DbSession, settings: AppSettings) -> list[TrashItem]:
    """Top-level deletions only: a visit deleted together with its mark comes back with the mark."""
    roles = _roles(db, user)
    writable = [pid for pid, role in roles.items() if role in (ACCESS_OWNER, ACCESS_MANAGER)]
    keep = timedelta(days=settings.trash_days)
    persons = {p.id: p for p in db.scalars(select(Person).where(Person.id.in_(writable)))}
    items: list[TrashItem] = []

    def add(kind: Kind, item_id: uuid.UUID, label: str, person_id: uuid.UUID, deleted_at: datetime) -> None:
        items.append(
            TrashItem(
                kind=kind,
                id=item_id,
                label=label,
                person_id=person_id,
                person_name=persons[person_id].display_name,
                deleted_at=deleted_at,
                purge_after=deleted_at + keep,
            )
        )

    for person in persons.values():
        if person.deleted_at is not None and roles.get(person.id) == ACCESS_OWNER:
            add("person", person.id, person.display_name, person.id, person.deleted_at)
    live = [pid for pid, p in persons.items() if p.deleted_at is None]
    for lesion in db.scalars(select(Lesion).where(Lesion.person_id.in_(live), Lesion.deleted_at.is_not(None))):
        if lesion.deleted_at is not None:
            add("lesion", lesion.id, lesion.label or lesion.zone_code, lesion.person_id, lesion.deleted_at)
    visits = db.execute(
        select(Observation, Lesion)
        .join(Lesion, Lesion.id == Observation.lesion_id)
        .where(Lesion.person_id.in_(live), Lesion.deleted_at.is_(None), Observation.deleted_at.is_not(None))
    )
    for observation, lesion in visits:
        if observation.deleted_at is not None:
            label = f"{lesion.label or lesion.zone_code} · {observation.captured_local_date.isoformat()}"
            add("observation", observation.id, label, lesion.person_id, observation.deleted_at)
    for image in db.scalars(select(Image).where(Image.person_id.in_(live), Image.deleted_at.is_not(None))):
        observation = db.get(Observation, image.observation_id) if image.observation_id else None
        if observation is not None and observation.deleted_at is not None:
            continue
        parent = db.get(Lesion, observation.lesion_id) if observation else None
        if (parent is not None and parent.deleted_at is not None) or image.deleted_at is None:
            continue
        label = f"{parent.label or parent.zone_code} · {image.role}" if parent else image.role
        add("image", image.id, label, image.person_id, image.deleted_at)
    return sorted(items, key=lambda item: item.deleted_at, reverse=True)


def _check(db: Session, user: User, person_id: uuid.UUID, owner_only: bool = False) -> None:
    access = db.get(PersonAccess, (person_id, user.id))
    allowed = (ACCESS_OWNER,) if owner_only else (ACCESS_OWNER, ACCESS_MANAGER)
    if access is None or access.role not in allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing like that in the trash.")


def _find(db: Session, kind: Kind, item_id: uuid.UUID) -> Trashed:
    row: Trashed | None
    if kind == "person":
        row = db.get(Person, item_id)
    elif kind == "lesion":
        row = db.get(Lesion, item_id)
    elif kind == "observation":
        row = db.get(Observation, item_id)
    else:
        row = db.get(Image, item_id)
    if row is None or row.deleted_at is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing like that in the trash.")
    return row


def _person_of(db: Session, row: Trashed) -> uuid.UUID:
    if isinstance(row, Person):
        return row.id
    if isinstance(row, Lesion | Image):
        return row.person_id
    lesion = db.get(Lesion, row.lesion_id)
    if lesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing like that in the trash.")
    return lesion.person_id


@router.post("/{kind}/{item_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore(
    kind: Kind, item_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    row = _find(db, kind, item_id)
    _check(db, user, _person_of(db, row), owner_only=kind == "person")
    stamp = row.deleted_at
    if isinstance(row, Observation):
        lesion = db.get(Lesion, row.lesion_id)
        if lesion is not None and lesion.deleted_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Restore the mark first.")
    if isinstance(row, Image) and row.observation_id:
        observation = db.get(Observation, row.observation_id)
        if observation is not None and observation.deleted_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Restore the visit first.")
    row.deleted_at = None
    # What was trashed together comes back together.
    if isinstance(row, Lesion):
        for visit in db.scalars(
            select(Observation).where(Observation.lesion_id == row.id, Observation.deleted_at == stamp)
        ):
            visit.deleted_at = None
            for image in db.scalars(select(Image).where(Image.observation_id == visit.id, Image.deleted_at == stamp)):
                image.deleted_at = None
    if isinstance(row, Observation):
        for image in db.scalars(select(Image).where(Image.observation_id == row.id, Image.deleted_at == stamp)):
            image.deleted_at = None
    db.flush()
    if isinstance(row, Image) and row.observation_id:
        refresh_observation_flags(db, row.observation_id)
    service.audit(db, f"{kind}.restore", user, kind, item_id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{kind}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def purge_now(
    kind: Kind, item_id: uuid.UUID, request: Request, session: SudoSession, db: DbSession, settings: AppSettings
) -> Response:
    """Remove for good, without waiting for the purge. Needs the password again."""
    user = session.user
    row = _find(db, kind, item_id)
    _check(db, user, _person_of(db, row), owner_only=kind == "person")
    actions = {
        "person": purge.purge_person,
        "lesion": purge.purge_lesion,
        "observation": purge.purge_observation,
        "image": purge.purge_image,
    }
    actions[kind](db, item_id)
    service.audit(db, f"{kind}.purge", user, kind, item_id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
