# SPDX-License-Identifier: AGPL-3.0-only
"""Preparing a visit to a clinician: what to photograph before the date, and the report to bring.

The checklist holds the person's active marks that will be due by the appointment, that were never
photographed, or that were photographed since the preparation started (ticked). The visit report is
the summary of every mark followed by the record of each mark on the checklist.
"""

from __future__ import annotations

import datetime as dt
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nevus.api.reports import Paper, ReportOut, _out, create_report
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.db.models import ACCESS_MANAGER, ACCESS_OWNER, Appointment, Lesion, Observation, Person, PersonAccess, User
from nevus.db.types import utcnow
from nevus.domain import due
from nevus.languages import Language

router = APIRouter(prefix="/api", tags=["appointments"])
State = Literal["to_photograph", "never_photographed", "photographed"]


class AppointmentIn(BaseModel):
    date: dt.date
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentUpdate(BaseModel):
    date: dt.date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ChecklistItem(BaseModel):
    lesion_id: uuid.UUID
    label: str | None
    zone: str
    state: State
    last_observed_at: datetime | None
    next_due_on: dt.date | None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    person_name: str
    date: dt.date
    notes: str | None
    report_id: uuid.UUID | None
    created_at: datetime
    checklist: list[ChecklistItem]
    can_edit: bool


class VisitReportIn(BaseModel):
    language: Language | None = None
    paper: Paper = "a4"


def _aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


def checklist(db: Session, appointment: Appointment) -> list[ChecklistItem]:
    lesions = db.scalars(
        select(Lesion).where(
            Lesion.person_id == appointment.person_id, Lesion.deleted_at.is_(None), Lesion.status == "active"
        )
    ).all()
    started = _aware(appointment.created_at)
    items: list[ChecklistItem] = []
    for lesion in lesions:
        last = _aware(
            db.scalar(
                select(func.max(Observation.captured_at)).where(
                    Observation.lesion_id == lesion.id, Observation.deleted_at.is_(None)
                )
            )
        )
        next_due = due.next_due(lesion, last)
        state: State | None = None
        if last is not None and started is not None and last >= started:
            state = "photographed"
        elif last is None:
            state = "never_photographed"
        elif next_due is not None and next_due <= appointment.date:
            state = "to_photograph"
        if state is not None:
            items.append(
                ChecklistItem(
                    lesion_id=lesion.id,
                    label=lesion.label,
                    zone=lesion.zone_code,
                    state=state,
                    last_observed_at=last,
                    next_due_on=next_due,
                )
            )
    order = {"to_photograph": 0, "never_photographed": 1, "photographed": 2}
    return sorted(items, key=lambda item: (order[item.state], item.zone, str(item.lesion_id)))


def _access(db: Session, person_id: uuid.UUID, user: User) -> tuple[Person, PersonAccess]:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    return person, access


def _appointment(db: Session, appointment_id: uuid.UUID, user: User) -> tuple[Appointment, Person, PersonAccess]:
    row = db.get(Appointment, appointment_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such appointment.")
    try:
        person, access = _access(db, row.person_id, user)
    except HTTPException:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such appointment.") from None
    return row, person, access


def _editor(access: PersonAccess) -> None:
    if access.role not in (ACCESS_OWNER, ACCESS_MANAGER):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")


def _out_appointment(db: Session, row: Appointment, person: Person, access: PersonAccess) -> AppointmentOut:
    return AppointmentOut(
        id=row.id,
        person_id=row.person_id,
        person_name=person.display_name,
        date=row.date,
        notes=row.notes,
        report_id=row.report_id,
        created_at=row.created_at,
        checklist=checklist(db, row),
        can_edit=access.role in (ACCESS_OWNER, ACCESS_MANAGER),
    )


@router.post("/persons/{person_id}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    person_id: uuid.UUID, body: AppointmentIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> AppointmentOut:
    person, access = _access(db, person_id, user)
    _editor(access)
    row = Appointment(person_id=person_id, date=body.date, notes=(body.notes or "").strip() or None, created_by=user.id)
    db.add(row)
    db.flush()
    service.audit(db, "appointment.create", user, "appointment", row.id, client_ip(request, settings))
    return _out_appointment(db, row, person, access)


@router.get("/persons/{person_id}/appointments", response_model=list[AppointmentOut])
def list_appointments(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[AppointmentOut]:
    """Upcoming visits first (soonest first), then past ones (latest first)."""
    person, access = _access(db, person_id, user)
    rows = db.scalars(select(Appointment).where(Appointment.person_id == person_id)).all()
    today = utcnow().date()
    upcoming = sorted((r for r in rows if r.date >= today), key=lambda r: r.date)
    past = sorted((r for r in rows if r.date < today), key=lambda r: r.date, reverse=True)
    return [_out_appointment(db, r, person, access) for r in [*upcoming, *past]]


@router.get("/appointments/upcoming", response_model=list[AppointmentOut])
def upcoming_appointments(user: CurrentUser, db: DbSession) -> list[AppointmentOut]:
    """Every visit from today on, for the persons this user may see: the home page's reminder of them."""
    rows = db.execute(
        select(Appointment, Person, PersonAccess)
        .join(Person, Person.id == Appointment.person_id)
        .join(PersonAccess, (PersonAccess.person_id == Person.id) & (PersonAccess.user_id == user.id))
        .where(Person.deleted_at.is_(None), Appointment.date >= utcnow().date())
        .order_by(Appointment.date)
    ).all()
    return [_out_appointment(db, row, person, access) for row, person, access in rows]


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> AppointmentOut:
    row, person, access = _appointment(db, appointment_id, user)
    return _out_appointment(db, row, person, access)


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID, body: AppointmentUpdate, user: CurrentUser, db: DbSession
) -> AppointmentOut:
    row, person, access = _appointment(db, appointment_id, user)
    _editor(access)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("date") is not None:
        row.date = changes["date"]
    if "notes" in changes:
        row.notes = (changes["notes"] or "").strip() or None
    db.flush()
    return _out_appointment(db, row, person, access)


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    row, _, access = _appointment(db, appointment_id, user)
    _editor(access)
    db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/appointments/{appointment_id}/report", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
def visit_report(
    appointment_id: uuid.UUID,
    body: VisitReportIn,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> ReportOut:
    """The summary of every mark, then the record of each mark on the checklist."""
    row, _, access = _appointment(db, appointment_id, user)
    marks = [str(item.lesion_id) for item in checklist(db, row)]
    report = create_report(
        db,
        user,
        row.person_id,
        "visit",
        marks,
        body.language,
        body.paper,
        client_ip(request, settings),
        options={"appointment_id": str(row.id)},
    )
    row.report_id = report.id
    return _out(report, user, access)
