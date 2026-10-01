# SPDX-License-Identifier: AGPL-3.0-only
"""Lesions (tracked marks) and their observations (dated visits with photographs and the person's notes)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nevus.api.images import ImageOut, ImageRole, Modality, ingest_upload
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.bodymap import body_map, zone_codes
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    DEFAULT_INTERVAL_DAYS,
    Image,
    Lesion,
    Observation,
    Person,
    PersonAccess,
    User,
)
from nevus.db.types import utcnow
from nevus.domain import due

router = APIRouter(prefix="/api", tags=["lesions"])

LesionType = Literal["mole", "other"]
LesionStatus = Literal["active", "removed", "resolved"]
Symptom = Literal["itching", "bleeding", "pain", "looks_different"]


class LocationIn(BaseModel):
    zone: str = Field(max_length=8)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)

    @field_validator("zone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        if value not in zone_codes():
            raise ValueError("unknown body-map zone")
        return value


class LocationOut(BaseModel):
    zone: str
    x: float
    y: float
    body_map_version: str
    view: str
    side: str


def _strip_label(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class LesionIn(BaseModel):
    type: LesionType = "mole"
    label: str | None = Field(default=None, max_length=120)
    location: LocationIn
    first_noticed_on: date | None = None
    status: LesionStatus = "active"
    tags: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=4000)
    interval_days: int = Field(default=DEFAULT_INTERVAL_DAYS, ge=7, le=3650)

    _label = field_validator("label")(_strip_label)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        cleaned = [tag.strip()[:32] for tag in value if tag.strip()]
        return list(dict.fromkeys(cleaned))


class LesionUpdate(BaseModel):
    type: LesionType | None = None
    label: str | None = Field(default=None, max_length=120)
    location: LocationIn | None = None
    first_noticed_on: date | None = None
    status: LesionStatus | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=4000)
    interval_days: int | None = Field(default=None, ge=7, le=3650)

    _label = field_validator("label")(_strip_label)


class MeasurementBrief(BaseModel):
    longest_mm: float
    sigma_longest_mm: float
    perpendicular_mm: float
    measured_at: datetime
    flags: list[str]


class ChangeBrief(BaseModel):
    delta_mm: float
    sigma_mm: float
    detectable: bool
    since: datetime


class LesionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    type: str
    label: str | None
    location: LocationOut
    first_noticed_on: date | None
    status: str
    tags: list[str]
    notes: str | None
    interval_days: int
    created_at: datetime
    updated_at: datetime
    observation_count: int
    last_observed_at: datetime | None
    next_due_on: date | None
    due: bool
    snoozed_until: date | None = None
    latest_image_id: uuid.UUID | None
    latest_measurement: MeasurementBrief | None = None
    measurement_change: ChangeBrief | None = None


class ObservationIn(BaseModel):
    captured_at: datetime | None = None
    captured_tz: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    symptoms: list[Symptom] = Field(default_factory=list)


class ObservationUpdate(BaseModel):
    captured_at: datetime | None = None
    captured_tz: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    symptoms: list[Symptom] | None = None


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lesion_id: uuid.UUID
    captured_at: datetime
    captured_tz: str | None
    captured_local_date: date
    notes: str | None
    symptoms: list[str]
    quality_flags: list[str]
    created_at: datetime
    updated_at: datetime
    images: list[ImageOut]


# --- access helpers -------------------------------------------------------------------------------


def _person_for(db: Session, person_id: uuid.UUID, user: User, *roles: str) -> Person:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")
    return person


def _lesion_for(db: Session, lesion_id: uuid.UUID, user: User, *roles: str) -> Lesion:
    lesion = db.get(Lesion, lesion_id)
    if lesion is None or lesion.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such lesion.")
    _person_for(db, lesion.person_id, user, *roles)
    return lesion


def _observation_for(db: Session, observation_id: uuid.UUID, user: User, *roles: str) -> tuple[Observation, Lesion]:
    observation = db.get(Observation, observation_id)
    if observation is None or observation.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such observation.")
    lesion = _lesion_for(db, observation.lesion_id, user, *roles)
    return observation, lesion


# --- output assembly ------------------------------------------------------------------------------


def _summaries(
    db: Session, lesion_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, datetime | None, uuid.UUID | None]]:
    """Per lesion: number of observations, last capture time and the newest photograph for a thumbnail."""
    if not lesion_ids:
        return {}
    counts = db.execute(
        select(Observation.lesion_id, func.count(Observation.id), func.max(Observation.captured_at))
        .where(Observation.lesion_id.in_(lesion_ids), Observation.deleted_at.is_(None))
        .group_by(Observation.lesion_id)
    ).all()
    latest_images: dict[uuid.UUID, uuid.UUID] = {}
    rows = db.execute(
        select(Observation.lesion_id, Image.id)
        .join(Image, Image.observation_id == Observation.id)
        .where(Observation.lesion_id.in_(lesion_ids), Observation.deleted_at.is_(None), Image.deleted_at.is_(None))
        .order_by(Observation.captured_at.desc(), Image.created_at.desc())
    ).all()
    for lesion_id, image_id in rows:
        latest_images.setdefault(lesion_id, image_id)
    result: dict[uuid.UUID, tuple[int, datetime | None, uuid.UUID | None]] = {
        lesion_id: (0, None, latest_images.get(lesion_id)) for lesion_id in lesion_ids
    }
    for lesion_id, count, last in counts:
        last_at = last.replace(tzinfo=UTC) if last is not None and last.tzinfo is None else last
        result[lesion_id] = (count, last_at, latest_images.get(lesion_id))
    return result


def _lesion_out(lesion: Lesion, summary: tuple[int, datetime | None, uuid.UUID | None]) -> LesionOut:
    count, last_observed_at, latest_image_id = summary
    zone = body_map().zone(lesion.zone_code)
    next_due = due.next_due(lesion, last_observed_at)
    return LesionOut(
        id=lesion.id,
        person_id=lesion.person_id,
        type=lesion.type,
        label=lesion.label,
        location=LocationOut(
            zone=lesion.zone_code,
            x=lesion.x,
            y=lesion.y,
            body_map_version=lesion.body_map_version,
            view=zone.view if zone else "front",
            side=zone.side if zone else "midline",
        ),
        first_noticed_on=lesion.first_noticed_on,
        status=lesion.status,
        tags=list(lesion.tags or []),
        notes=lesion.notes,
        interval_days=lesion.interval_days,
        created_at=lesion.created_at,
        updated_at=lesion.updated_at,
        observation_count=count,
        last_observed_at=last_observed_at,
        next_due_on=next_due,
        due=due.is_due(lesion, next_due, utcnow().date()),
        snoozed_until=lesion.snoozed_until,
        latest_image_id=latest_image_id,
    )


def _with_measurements(db: Session, lesion: Lesion, out: LesionOut) -> LesionOut:
    from nevus.api.measurements import change_between, lesion_series

    series = lesion_series(db, lesion.id)
    if not series:
        return out
    latest, measured_at = series[-1]
    out.latest_measurement = MeasurementBrief(
        longest_mm=latest.longest_mm,
        sigma_longest_mm=latest.sigma_longest_mm,
        perpendicular_mm=latest.perpendicular_mm,
        measured_at=measured_at,
        flags=list(latest.flags or []),
    )
    if len(series) > 1:
        change = change_between(series[-2], series[-1])
        out.measurement_change = ChangeBrief(**change.model_dump())
    return out


def _one(db: Session, lesion: Lesion) -> LesionOut:
    return _with_measurements(db, lesion, _lesion_out(lesion, _summaries(db, [lesion.id])[lesion.id]))


def _local_date(captured_at: datetime, captured_tz: str | None) -> date:
    """The calendar day where the photo was taken: a late-night capture belongs to that evening, not to UTC."""
    if captured_tz:
        try:
            return captured_at.astimezone(ZoneInfo(captured_tz)).date()
        except ZoneInfoNotFoundError:
            pass
    return captured_at.astimezone(UTC).date()


def _observation_out(db: Session, observation: Observation) -> ObservationOut:
    images = db.scalars(
        select(Image)
        .where(Image.observation_id == observation.id, Image.deleted_at.is_(None))
        .order_by(Image.created_at.asc())
    ).all()
    return ObservationOut(
        id=observation.id,
        lesion_id=observation.lesion_id,
        captured_at=observation.captured_at,
        captured_tz=observation.captured_tz,
        captured_local_date=observation.captured_local_date,
        notes=observation.notes,
        symptoms=list(observation.symptoms or []),
        quality_flags=list(observation.quality_flags or []),
        created_at=observation.created_at,
        updated_at=observation.updated_at,
        images=[ImageOut.model_validate(i) for i in images],
    )


# --- lesions --------------------------------------------------------------------------------------


@router.get("/persons/{person_id}/lesions", response_model=list[LesionOut])
def list_lesions(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[LesionOut]:
    _person_for(db, person_id, user)
    lesions = db.scalars(
        select(Lesion).where(Lesion.person_id == person_id, Lesion.deleted_at.is_(None)).order_by(Lesion.created_at)
    ).all()
    summaries = _summaries(db, [lesion.id for lesion in lesions])
    return [_with_measurements(db, lesion, _lesion_out(lesion, summaries[lesion.id])) for lesion in lesions]


@router.post("/persons/{person_id}/lesions", response_model=LesionOut, status_code=status.HTTP_201_CREATED)
def create_lesion(
    person_id: uuid.UUID, body: LesionIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> LesionOut:
    _person_for(db, person_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    lesion = Lesion(
        person_id=person_id,
        type=body.type,
        label=body.label,
        zone_code=body.location.zone,
        x=body.location.x,
        y=body.location.y,
        body_map_version=body_map().version,
        first_noticed_on=body.first_noticed_on,
        status=body.status,
        tags=body.tags,
        notes=body.notes,
        interval_days=body.interval_days,
        created_by=user.id,
    )
    db.add(lesion)
    db.flush()
    db.refresh(lesion)
    service.audit(
        db, "lesion.create", user, "lesion", lesion.id, client_ip(request, settings), {"person": str(person_id)}
    )
    return _one(db, lesion)


@router.get("/lesions/{lesion_id}", response_model=LesionOut)
def get_lesion(lesion_id: uuid.UUID, user: CurrentUser, db: DbSession) -> LesionOut:
    return _one(db, _lesion_for(db, lesion_id, user))


@router.patch("/lesions/{lesion_id}", response_model=LesionOut)
def update_lesion(
    lesion_id: uuid.UUID, body: LesionUpdate, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> LesionOut:
    lesion = _lesion_for(db, lesion_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    changes = body.model_dump(exclude_unset=True)
    location = changes.pop("location", None)
    if location:
        lesion.zone_code = location["zone"]
        lesion.x = location["x"]
        lesion.y = location["y"]
        lesion.body_map_version = body_map().version
    if "tags" in changes and changes["tags"] is not None:
        changes["tags"] = LesionIn._clean_tags(changes["tags"])
    for field, value in changes.items():
        setattr(lesion, field, value)
    db.flush()
    db.refresh(lesion)
    service.audit(
        db, "lesion.update", user, "lesion", lesion.id, client_ip(request, settings), {"fields": sorted(changes)}
    )
    return _one(db, lesion)


@router.delete("/lesions/{lesion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesion(
    lesion_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    """Moves the lesion, its observations and their photographs to the trash together."""
    lesion = _lesion_for(db, lesion_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    now = utcnow()
    lesion.deleted_at = now
    for observation in lesion.observations:
        if observation.deleted_at is None:
            observation.deleted_at = now
            _trash_images(db, observation.id, now)
    service.audit(db, "lesion.delete", user, "lesion", lesion.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _trash_images(db: Session, observation_id: uuid.UUID, now: datetime) -> None:
    for image in db.scalars(select(Image).where(Image.observation_id == observation_id, Image.deleted_at.is_(None))):
        image.deleted_at = now


# --- observations ---------------------------------------------------------------------------------


@router.get("/lesions/{lesion_id}/observations", response_model=list[ObservationOut])
def list_observations(lesion_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ObservationOut]:
    _lesion_for(db, lesion_id, user)
    rows = db.scalars(
        select(Observation)
        .where(Observation.lesion_id == lesion_id, Observation.deleted_at.is_(None))
        .order_by(Observation.captured_at.desc())
    ).all()
    return [_observation_out(db, o) for o in rows]


@router.post("/lesions/{lesion_id}/observations", response_model=ObservationOut, status_code=status.HTTP_201_CREATED)
def create_observation(
    lesion_id: uuid.UUID,
    body: ObservationIn,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> ObservationOut:
    lesion = _lesion_for(db, lesion_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    captured_at = body.captured_at or utcnow()
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    observation = Observation(
        lesion_id=lesion_id,
        captured_at=captured_at,
        captured_tz=body.captured_tz,
        captured_local_date=_local_date(captured_at, body.captured_tz),
        notes=body.notes,
        symptoms=list(body.symptoms),
        created_by=user.id,
    )
    db.add(observation)
    lesion.snoozed_until = None  # a new visit is what ends a snooze
    db.flush()
    db.refresh(observation)
    service.audit(
        db,
        "observation.create",
        user,
        "observation",
        observation.id,
        client_ip(request, settings),
        {"lesion": str(lesion_id)},
    )
    return _observation_out(db, observation)


@router.get("/observations/{observation_id}", response_model=ObservationOut)
def get_observation(observation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ObservationOut:
    observation, _lesion = _observation_for(db, observation_id, user)
    return _observation_out(db, observation)


@router.patch("/observations/{observation_id}", response_model=ObservationOut)
def update_observation(
    observation_id: uuid.UUID,
    body: ObservationUpdate,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> ObservationOut:
    observation, _lesion = _observation_for(db, observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    changes = body.model_dump(exclude_unset=True)
    if "captured_at" in changes and changes["captured_at"] is not None:
        captured_at = changes["captured_at"]
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=UTC)
        observation.captured_at = captured_at
    if "captured_tz" in changes:
        observation.captured_tz = changes["captured_tz"]
    observation.captured_local_date = _local_date(observation.captured_at, observation.captured_tz)
    if "notes" in changes:
        observation.notes = changes["notes"]
    if "symptoms" in changes and changes["symptoms"] is not None:
        observation.symptoms = list(changes["symptoms"])
    db.flush()
    db.refresh(observation)
    service.audit(
        db,
        "observation.update",
        user,
        "observation",
        observation.id,
        client_ip(request, settings),
        {"fields": sorted(changes)},
    )
    return _observation_out(db, observation)


@router.delete("/observations/{observation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_observation(
    observation_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    """Moves the observation and its photographs to the trash together."""
    observation, _lesion = _observation_for(db, observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    now = utcnow()
    observation.deleted_at = now
    _trash_images(db, observation.id, now)
    service.audit(db, "observation.delete", user, "observation", observation.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/observations/{observation_id}/images", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_observation_image(
    observation_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    role: Annotated[ImageRole, Form()] = "close_up",
    modality: Annotated[Modality, Form()] = "camera",
    captured_at: Annotated[datetime | None, Form()] = None,
    captured_tz: Annotated[str | None, Form(max_length=64)] = None,
) -> ImageOut:
    observation, lesion = _observation_for(db, observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    image = await ingest_upload(
        request,
        user,
        db,
        settings,
        lesion.person_id,
        file,
        role,
        modality,
        captured_at,
        captured_tz or observation.captured_tz,
        observation_id=observation.id,
        fallback_captured_at=observation.captured_at,
    )
    return ImageOut.model_validate(image)


@router.get("/observations/{observation_id}/images", response_model=list[ImageOut])
def list_observation_images(observation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ImageOut]:
    observation, _lesion = _observation_for(db, observation_id, user)
    rows = db.scalars(
        select(Image)
        .where(Image.observation_id == observation.id, Image.deleted_at.is_(None))
        .order_by(Image.created_at)
    )
    return [ImageOut.model_validate(i) for i in rows]


class SnoozeIn(BaseModel):
    days: Literal[7, 30]


@router.post("/lesions/{lesion_id}/snooze", response_model=LesionOut)
def snooze(
    lesion_id: uuid.UUID, body: SnoozeIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> LesionOut:
    """Not now: the mark leaves the due list for a week or a month. A new visit ends the snooze."""
    lesion = _lesion_for(db, lesion_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    lesion.snoozed_until = date.fromordinal(utcnow().date().toordinal() + body.days)
    db.flush()
    service.audit(db, "lesion.snooze", user, "lesion", lesion.id, client_ip(request, settings), {"days": body.days})
    return _one(db, lesion)


@router.delete("/lesions/{lesion_id}/snooze", response_model=LesionOut)
def unsnooze(lesion_id: uuid.UUID, user: CurrentUser, db: DbSession) -> LesionOut:
    lesion = _lesion_for(db, lesion_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    lesion.snoozed_until = None
    db.flush()
    return _one(db, lesion)
