# SPDX-License-Identifier: AGPL-3.0-only
"""Full-body sessions (FR-SES-01 to FR-SES-04): the protocol, the zone photos, the marks seen on them."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.api.images import ingest_upload
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.bodymap import body_map
from nevus.cv.imageio import decode
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    BodySession,
    Image,
    Lesion,
    Person,
    PersonAccess,
    Rendition,
    SessionMark,
    SessionZone,
    User,
)
from nevus.db.types import utcnow
from nevus.sessions import BY_ID, PROTOCOL, PROTOCOL_VERSION
from nevus.sessions.jobs import analysing, enqueue_candidates
from nevus.storage.blobs import BlobStore

router = APIRouter(prefix="/api", tags=["sessions"])
ZoneStatus = Literal["pending", "captured", "skipped"]
MarkState = Literal["pending", "confirmed", "rejected"]
Match = Literal["matched", "new", "uncertain"]


class CaptureZoneOut(BaseModel):
    id: str
    covers: list[str]
    sensitive: bool


class SessionMarkOut(BaseModel):
    id: uuid.UUID
    x: float
    y: float
    lesion_id: uuid.UUID | None
    source: Literal["person", "candidate"]
    state: MarkState
    match: Match | None
    crop_url: str


class SessionZoneOut(BaseModel):
    zone: str
    status: ZoneStatus
    image_id: uuid.UUID | None
    upright_width: int | None
    upright_height: int | None
    marks: list[SessionMarkOut]
    analysing: bool


class BodySessionOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    protocol: str
    status: Literal["open", "finished"]
    notes: str | None
    started_at: datetime
    finished_at: datetime | None
    zones: list[SessionZoneOut]
    can_edit: bool
    experimental: bool


class BodySessionSummary(BaseModel):
    id: uuid.UUID
    status: Literal["open", "finished"]
    started_at: datetime
    finished_at: datetime | None
    captured: int
    skipped: int
    pending: int
    marks: int


class SessionIn(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class NewMark(BaseModel):
    zone_code: str
    label: str | None = Field(default=None, max_length=120)


class MarkIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    lesion_id: uuid.UUID | None = None
    new_mark: NewMark | None = None


class MarkUpdate(BaseModel):
    state: Literal["confirmed", "rejected"] | None = None
    lesion_id: uuid.UUID | None = None
    new_mark: NewMark | None = None


class Sighting(BaseModel):
    mark_id: uuid.UUID
    session_id: uuid.UUID
    zone: str
    started_at: datetime
    crop_url: str


class SessionPairOut(BaseModel):
    zone: str
    earlier_image_id: uuid.UUID
    later_image_id: uuid.UUID


# --- access ---------------------------------------------------------------------------------------


def _person(db: Session, person_id: uuid.UUID, user: User, *roles: str) -> tuple[Person, PersonAccess]:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")
    return person, access


def _session(db: Session, session_id: uuid.UUID, user: User, *roles: str) -> tuple[BodySession, Person, PersonAccess]:
    row = db.get(BodySession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such session.")
    try:
        person, access = _person(db, row.person_id, user, *roles)
    except HTTPException as error:
        if error.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such session.") from None
        raise
    return row, person, access


def _zone(db: Session, session: BodySession, zone: str) -> SessionZone:
    row = db.scalar(select(SessionZone).where(SessionZone.session_id == session.id, SessionZone.zone == zone))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such zone in this session.")
    return row


# --- output ---------------------------------------------------------------------------------------


def _mark_out(mark: SessionMark) -> SessionMarkOut:
    return SessionMarkOut(
        id=mark.id,
        x=mark.x,
        y=mark.y,
        lesion_id=mark.lesion_id,
        source=mark.source,
        state=mark.state,
        match=mark.match,
        crop_url=f"/api/session-marks/{mark.id}/crop",
    )


def _out(db: Session, row: BodySession, person: Person, access: PersonAccess) -> BodySessionOut:
    zones = {z.zone: z for z in db.scalars(select(SessionZone).where(SessionZone.session_id == row.id))}
    out: list[SessionZoneOut] = []
    for capture in PROTOCOL:
        zone = zones.get(capture.id)
        if zone is None:
            continue
        image = db.get(Image, zone.image_id) if zone.image_id else None
        if image is not None and image.deleted_at is not None:
            image = None
        width, height = (
            ((image.height, image.width) if image.orientation in (5, 6, 7, 8) else (image.width, image.height))
            if image
            else (None, None)
        )
        marks = db.scalars(
            select(SessionMark).where(SessionMark.session_zone_id == zone.id).order_by(SessionMark.created_at)
        ).all()
        visible = [m for m in marks if m.source == "person" or person.experimental_analysis]
        out.append(
            SessionZoneOut(
                zone=zone.zone,
                status=zone.status,
                image_id=image.id if image else None,
                upright_width=width,
                upright_height=height,
                marks=[_mark_out(m) for m in visible if m.state != "rejected"],
                analysing=image is not None and person.experimental_analysis and analysing(db, zone),
            )
        )
    return BodySessionOut(
        id=row.id,
        person_id=row.person_id,
        protocol=row.protocol,
        status=row.status,
        notes=row.notes,
        started_at=row.started_at,
        finished_at=row.finished_at,
        zones=out,
        can_edit=access.role in (ACCESS_OWNER, ACCESS_MANAGER),
        experimental=person.experimental_analysis,
    )


# --- sessions -------------------------------------------------------------------------------------


@router.get("/sessions/protocol", response_model=list[CaptureZoneOut])
def protocol() -> list[CaptureZoneOut]:
    return [CaptureZoneOut(id=z.id, covers=list(z.covers), sensitive=z.sensitive) for z in PROTOCOL]


@router.post("/persons/{person_id}/sessions", response_model=BodySessionOut, status_code=status.HTTP_201_CREATED)
def start_session(
    person_id: uuid.UUID, body: SessionIn, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> BodySessionOut:
    person, access = _person(db, person_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    row = BodySession(
        person_id=person.id, protocol=PROTOCOL_VERSION, notes=(body.notes or "").strip() or None, started_by=user.id
    )
    db.add(row)
    db.flush()
    for capture in PROTOCOL:
        db.add(SessionZone(session_id=row.id, zone=capture.id))
    db.flush()
    service.audit(db, "session.start", user, "session", row.id, client_ip(request, settings))
    return _out(db, row, person, access)


@router.get("/persons/{person_id}/sessions", response_model=list[BodySessionSummary])
def list_sessions(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[BodySessionSummary]:
    _person(db, person_id, user)
    out: list[BodySessionSummary] = []
    for row in db.scalars(
        select(BodySession).where(BodySession.person_id == person_id).order_by(BodySession.started_at.desc())
    ):
        zones = db.scalars(select(SessionZone).where(SessionZone.session_id == row.id)).all()
        marks = db.scalars(
            select(SessionMark.id).where(
                SessionMark.session_zone_id.in_([z.id for z in zones]), SessionMark.state == "confirmed"
            )
        ).all()
        out.append(
            BodySessionSummary(
                id=row.id,
                status=row.status,
                started_at=row.started_at,
                finished_at=row.finished_at,
                captured=sum(z.status == "captured" for z in zones),
                skipped=sum(z.status == "skipped" for z in zones),
                pending=sum(z.status == "pending" for z in zones),
                marks=len(marks),
            )
        )
    return out


@router.get("/sessions/{session_id}", response_model=BodySessionOut)
def get_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession) -> BodySessionOut:
    row, person, access = _session(db, session_id, user)
    return _out(db, row, person, access)


@router.post("/sessions/{session_id}/zones/{zone}/photo", response_model=BodySessionOut)
async def zone_photo(
    session_id: uuid.UUID,
    zone: str,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    captured_tz: Annotated[str | None, Form(max_length=64)] = None,
) -> BodySessionOut:
    row, person, access = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    target = _zone(db, row, zone)
    image = await ingest_upload(
        request,
        user,
        db,
        settings,
        person.id,
        file,
        "session",
        "camera",
        None,
        captured_tz,
        fallback_captured_at=utcnow(),
    )
    if target.image_id is not None:
        previous = db.get(Image, target.image_id)
        if previous is not None and previous.deleted_at is None:
            previous.deleted_at = utcnow()  # a retake: the earlier photo goes to the trash
        for mark in db.scalars(select(SessionMark).where(SessionMark.session_zone_id == target.id)):
            db.delete(mark)
    target.image_id, target.status = image.id, "captured"
    db.flush()
    enqueue_candidates(db, target, image)
    return _out(db, row, person, access)


@router.post("/sessions/{session_id}/zones/{zone}/skip", response_model=BodySessionOut)
def skip_zone(session_id: uuid.UUID, zone: str, user: CurrentUser, db: DbSession) -> BodySessionOut:
    row, person, access = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    target = _zone(db, row, zone)
    if target.status == "captured":
        raise HTTPException(status.HTTP_409_CONFLICT, "This zone already has a photo.")
    target.status = "skipped"
    db.flush()
    return _out(db, row, person, access)


@router.delete("/sessions/{session_id}/zones/{zone}/skip", response_model=BodySessionOut)
def unskip_zone(session_id: uuid.UUID, zone: str, user: CurrentUser, db: DbSession) -> BodySessionOut:
    row, person, access = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    target = _zone(db, row, zone)
    if target.status == "skipped":
        target.status = "pending"
        db.flush()
    return _out(db, row, person, access)


@router.post("/sessions/{session_id}/finish", response_model=BodySessionOut)
def finish_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession) -> BodySessionOut:
    row, person, access = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    row.status, row.finished_at = "finished", utcnow()
    db.flush()
    return _out(db, row, person, access)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    """The session goes; its photos go to the trash, from where the purge removes them."""
    row, _, _ = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    now = utcnow()
    for zone in db.scalars(select(SessionZone).where(SessionZone.session_id == row.id)):
        image = db.get(Image, zone.image_id) if zone.image_id else None
        if image is not None and image.deleted_at is None:
            image.deleted_at = now
    db.delete(row)
    service.audit(db, "session.delete", user, "session", session_id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- marks ----------------------------------------------------------------------------------------


def _new_lesion(db: Session, person: Person, zone: SessionZone, new: NewMark, user: User) -> Lesion:
    capture = BY_ID.get(zone.zone)
    if capture is None or new.zone_code not in capture.covers:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a body zone this photo shows.")
    data = body_map()
    shape = data.zone(new.zone_code)
    if shape is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown body zone.")
    vx, vy, vw, vh = data.viewBox
    lesion = Lesion(
        person_id=person.id,
        label=(new.label or "").strip() or None,
        zone_code=new.zone_code,
        x=round((shape.anchor[0] - vx) / vw, 4),
        y=round((shape.anchor[1] - vy) / vh, 4),
        body_map_version=data.version,
        created_by=user.id,
    )
    db.add(lesion)
    db.flush()
    return lesion


def _check_lesion(db: Session, person: Person, lesion_id: uuid.UUID) -> uuid.UUID:
    lesion = db.get(Lesion, lesion_id)
    if lesion is None or lesion.person_id != person.id or lesion.deleted_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a mark of this person.")
    return lesion.id


@router.post(
    "/sessions/{session_id}/zones/{zone}/marks", response_model=SessionMarkOut, status_code=status.HTTP_201_CREATED
)
def add_mark(session_id: uuid.UUID, zone: str, body: MarkIn, user: CurrentUser, db: DbSession) -> SessionMarkOut:
    """A mark the person points at on the zone photo, linked to a known mark or recorded as a new one."""
    row, person, _ = _session(db, session_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    target = _zone(db, row, zone)
    if target.image_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Take the zone's photo first.")
    lesion_id = None
    if body.lesion_id is not None:
        lesion_id = _check_lesion(db, person, body.lesion_id)
    elif body.new_mark is not None:
        lesion_id = _new_lesion(db, person, target, body.new_mark, user).id
    mark = SessionMark(session_zone_id=target.id, x=body.x, y=body.y, lesion_id=lesion_id, created_by=user.id)
    db.add(mark)
    db.flush()
    return _mark_out(mark)


def _mark(db: Session, mark_id: uuid.UUID, user: User, *roles: str) -> tuple[SessionMark, SessionZone, Person]:
    mark = db.get(SessionMark, mark_id)
    zone = db.get(SessionZone, mark.session_zone_id) if mark else None
    session = db.get(BodySession, zone.session_id) if zone else None
    if mark is None or zone is None or session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such mark.")
    person, _ = _person(db, session.person_id, user, *roles)
    if mark.source == "candidate" and not person.experimental_analysis:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such mark.")
    return mark, zone, person


@router.patch("/session-marks/{mark_id}", response_model=SessionMarkOut)
def update_mark(mark_id: uuid.UUID, body: MarkUpdate, user: CurrentUser, db: DbSession) -> SessionMarkOut:
    """Confirm or reject a proposed mark, or link a mark to a known one or to a new one."""
    mark, zone, person = _mark(db, mark_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    if body.lesion_id is not None:
        mark.lesion_id = _check_lesion(db, person, body.lesion_id)
    elif body.new_mark is not None:
        mark.lesion_id = _new_lesion(db, person, zone, body.new_mark, user).id
    if body.state is not None:
        mark.state = body.state
    elif body.lesion_id is not None or body.new_mark is not None:
        mark.state = "confirmed"  # linking a proposal is accepting it
    db.flush()
    return _mark_out(mark)


@router.delete("/session-marks/{mark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mark(mark_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    mark, _, _ = _mark(db, mark_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    db.delete(mark)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session-marks/{mark_id}/crop")
def mark_crop(mark_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession) -> Response:
    """The mark and its surroundings, cut from the zone photo's full rendition."""
    mark, zone, _ = _mark(db, mark_id, user)
    rendition = (
        db.scalar(select(Rendition).where(Rendition.image_id == zone.image_id, Rendition.kind == "full"))
        if zone.image_id
        else None
    )
    if rendition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The zone has no photo.")
    store: BlobStore = request.app.state.blob_store
    picture = decode(store.path(rendition.sha256, derived=True).read_bytes())
    h, w = picture.shape[:2]
    half = int(0.08 * min(w, h))
    cx, cy = int(mark.x * w), int(mark.y * h)
    crop = picture[max(0, cy - half) : min(h, cy + half), max(0, cx - half) : min(w, cx + half)]
    ok, encoded = cv2.imencode(".jpg", np.ascontiguousarray(crop), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "The crop could not be made.")
    return Response(encoded.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/lesions/{lesion_id}/sightings", response_model=list[Sighting])
def sightings(lesion_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[Sighting]:
    """Where a mark was seen in full-body sessions, newest first."""
    lesion = db.get(Lesion, lesion_id)
    if lesion is None or lesion.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such lesion.")
    _person(db, lesion.person_id, user)
    rows = db.execute(
        select(SessionMark, SessionZone, BodySession)
        .join(SessionZone, SessionZone.id == SessionMark.session_zone_id)
        .join(BodySession, BodySession.id == SessionZone.session_id)
        .where(SessionMark.lesion_id == lesion.id, SessionMark.state == "confirmed")
        .order_by(BodySession.started_at.desc())
    ).all()
    return [
        Sighting(
            mark_id=mark.id,
            session_id=session.id,
            zone=zone.zone,
            started_at=session.started_at,
            crop_url=f"/api/session-marks/{mark.id}/crop",
        )
        for mark, zone, session in rows
    ]


@router.get("/sessions/{session_id}/compare/{other_id}", response_model=list[SessionPairOut])
def compare_sessions(
    session_id: uuid.UUID, other_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> list[SessionPairOut]:
    """FR-SES-04: the zones both sessions photographed, earlier and later, for the comparison view."""
    first, person, _ = _session(db, session_id, user)
    second, other_person, _ = _session(db, other_id, user)
    if person.id != other_person.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Both sessions must be of the same person.")
    earlier, later = sorted((first, second), key=lambda s: s.started_at)

    def photos(session: BodySession) -> dict[str, uuid.UUID]:
        out: dict[str, uuid.UUID] = {}
        for zone in db.scalars(select(SessionZone).where(SessionZone.session_id == session.id)):
            image = db.get(Image, zone.image_id) if zone.image_id else None
            if image is not None and image.deleted_at is None:
                out[zone.zone] = image.id
        return out

    a, b = photos(earlier), photos(later)
    return [
        SessionPairOut(zone=c.id, earlier_image_id=a[c.id], later_image_id=b[c.id])
        for c in PROTOCOL
        if c.id in a and c.id in b
    ]
