"""Persons whose skin marks are tracked, and who may see or manage them."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.api.schemas import AccessIn, AccessOut, PersonIn, PersonOut, PersonUpdate
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, SudoSession, client_ip
from nevus.db.models import ACCESS_MANAGER, ACCESS_OWNER, ACCESS_VIEWER, Person, PersonAccess, User
from nevus.db.types import utcnow

router = APIRouter(prefix="/api/persons", tags=["persons"])


def _access_for(db: Session, person_id: uuid.UUID, user: User) -> PersonAccess | None:
    return db.get(PersonAccess, (person_id, user.id))


def _person_out(person: Person, role: str) -> PersonOut:
    return PersonOut(
        id=person.id,
        display_name=person.display_name,
        birth_year=person.birth_year,
        skin_tone=person.skin_tone,
        owner_user_id=person.owner_user_id,
        experimental_analysis=person.experimental_analysis,
        created_at=person.created_at,
        updated_at=person.updated_at,
        my_role=role,
    )


def _load(db: Session, person_id: uuid.UUID, user: User, *roles: str) -> tuple[Person, PersonAccess]:
    """Return the person and the caller's access row, or 404 when the person is invisible to the caller."""
    person = db.get(Person, person_id)
    access = _access_for(db, person_id, user) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")
    return person, access


@router.get("", response_model=list[PersonOut])
def list_persons(user: CurrentUser, db: DbSession) -> list[PersonOut]:
    rows = db.execute(
        select(Person, PersonAccess.role)
        .join(PersonAccess, PersonAccess.person_id == Person.id)
        .where(PersonAccess.user_id == user.id, Person.deleted_at.is_(None))
        .order_by(Person.display_name)
    )
    return [_person_out(person, role) for person, role in rows]


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(
    body: PersonIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> PersonOut:
    person = Person(
        display_name=body.display_name, birth_year=body.birth_year, skin_tone=body.skin_tone, owner_user_id=user.id
    )
    db.add(person)
    db.flush()
    db.add(PersonAccess(person_id=person.id, user_id=user.id, role=ACCESS_OWNER))
    db.flush()
    service.audit(db, "person.create", user, "person", person.id, client_ip(request, settings))
    return _person_out(person, ACCESS_OWNER)


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> PersonOut:
    person, access = _load(db, person_id, user)
    return _person_out(person, access.role)


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(
    person_id: uuid.UUID, body: PersonUpdate, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> PersonOut:
    person, access = _load(db, person_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    changes = body.model_dump(exclude_unset=True)
    if "experimental_analysis" in changes and access.role != ACCESS_OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can change the experimental analysis setting.")
    for field, value in changes.items():
        setattr(person, field, value)
    db.flush()
    service.audit(
        db, "person.update", user, "person", person.id, client_ip(request, settings), {"fields": sorted(changes)}
    )
    return _person_out(person, access.role)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: uuid.UUID, request: Request, session: SudoSession, db: DbSession, settings: AppSettings
) -> Response:
    """Soft delete (30-day trash); the purge arrives with the data-management features. Needs sudo mode."""
    user = session.user
    person, _ = _load(db, person_id, user, ACCESS_OWNER)
    person.deleted_at = utcnow()
    service.audit(db, "person.delete", user, "person", person.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{person_id}/access", response_model=list[AccessOut])
def list_access(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[AccessOut]:
    _load(db, person_id, user)
    rows = db.execute(
        select(PersonAccess.user_id, User.username, PersonAccess.role)
        .join(User, User.id == PersonAccess.user_id)
        .where(PersonAccess.person_id == person_id)
        .order_by(User.username)
    )
    return [AccessOut(user_id=uid, username=username, role=role) for uid, username, role in rows]


@router.put("/{person_id}/access", response_model=AccessOut)
def grant_access(
    person_id: uuid.UUID, body: AccessIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> AccessOut:
    _load(db, person_id, user, ACCESS_OWNER)
    grantee = service.get_user_by_username(db, body.username)
    if grantee is None or not grantee.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    if grantee.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You already own this person.")
    existing = _access_for(db, person_id, grantee)
    if existing is None:
        db.add(PersonAccess(person_id=person_id, user_id=grantee.id, role=body.role))
    else:
        existing.role = body.role
    db.flush()
    service.audit(
        db, "person.access_grant", user, "person", person_id, client_ip(request, settings), {"role": body.role}
    )
    return AccessOut(user_id=grantee.id, username=grantee.username, role=body.role)


@router.delete("/{person_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    person_id: uuid.UUID, user_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    person, _ = _load(db, person_id, user, ACCESS_OWNER)
    if user_id == person.owner_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The owner's access cannot be revoked.")
    access = db.get(PersonAccess, (person_id, user_id))
    if access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such access.")
    db.delete(access)
    service.audit(db, "person.access_revoke", user, "person", person_id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["ACCESS_VIEWER", "router"]
