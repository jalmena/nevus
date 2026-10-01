# SPDX-License-Identifier: AGPL-3.0-only
"""Scale and measurement: the printable card, tap proposals, scale references and confirmed measurements."""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import analysis, measure
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.cv import card_detect, fit
from nevus.cv.card_sheet import render_sheet
from nevus.cv.pipeline import load_upright, upright_size
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    Image,
    Lesion,
    Measurement,
    Observation,
    Person,
    PersonAccess,
    ScaleReference,
    User,
)
from nevus.db.types import utcnow
from nevus.storage.blobs import BlobStore

router = APIRouter(prefix="/api", tags=["measurements"])

EURO_COINS_MM: dict[str, float] = {
    "1c": 16.25,
    "2c": 18.75,
    "5c": 21.25,
    "10c": 19.75,
    "20c": 22.25,
    "50c": 24.25,
    "1e": 23.25,
    "2e": 25.75,
}
Denomination = Literal["1c", "2c", "5c", "10c", "20c", "50c", "1e", "2e"]
TILT_LIMIT_DEG = float(card_detect.PARAMS["tilt_limit_deg"])


# --- schemas ---------------------------------------------------------------------------------------


class FitIn(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    target: Literal["coin", "lesion"]


class FitOut(BaseModel):
    cx: float
    cy: float
    r: float
    outline: list[list[float]] | None
    method: str


class CardOut(BaseModel):
    found: bool
    card: str | None = None
    tilt_deg: float | None = None
    mm_per_px: float | None = None
    centre_px: list[float] | None = None
    marker_px: float | None = None
    flags: list[str] = Field(default_factory=list)


class ScaleReferenceOut(BaseModel):
    id: uuid.UUID
    image_id: uuid.UUID
    kind: str
    reference_mm: float | None
    mm_per_px: float
    sigma_scale: float
    tilt_deg: float | None
    geometry: dict[str, Any]
    created_at: datetime


class ImageScaleOut(BaseModel):
    image_id: uuid.UUID
    upright_width: int
    upright_height: int
    card_checked: bool
    card: CardOut | None
    references: list[ScaleReferenceOut]
    tilt_limit_deg: float


class CoinIn(BaseModel):
    kind: Literal["coin"]
    cx: float
    cy: float
    r: float = Field(gt=2)
    denomination: Denomination


class ManualIn(BaseModel):
    kind: Literal["manual"]
    x1: float
    y1: float
    x2: float
    y2: float
    length_mm: float = Field(gt=0.5, le=500)


class CircleShape(BaseModel):
    type: Literal["circle"]
    cx: float
    cy: float
    r: float = Field(gt=0.5)


class OutlineShape(BaseModel):
    type: Literal["outline"]
    points: list[list[float]] = Field(min_length=3, max_length=400)


class MeasurementIn(BaseModel):
    image_id: uuid.UUID
    scale_reference_id: uuid.UUID
    method: Literal["assisted", "manual"]
    shape: Annotated[CircleShape | OutlineShape, Field(discriminator="type")]


class ChangeOut(BaseModel):
    delta_mm: float
    sigma_mm: float
    detectable: bool
    since: datetime


class MeasurementOut(BaseModel):
    id: uuid.UUID
    observation_id: uuid.UUID
    lesion_id: uuid.UUID
    image_id: uuid.UUID
    scale_reference_id: uuid.UUID
    scale_kind: str
    method: str
    shape: dict[str, Any]
    longest_mm: float
    perpendicular_mm: float
    area_mm2: float
    sigma_longest_mm: float
    sigma_perpendicular_mm: float
    sigma_area_mm2: float
    tilt_deg: float | None
    flags: list[str]
    captured_at: datetime
    created_at: datetime
    change: ChangeOut | None = None


# --- access helpers --------------------------------------------------------------------------------


def _person_access(db: Session, person_id: uuid.UUID, user: User, *roles: str) -> None:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")


def _image(db: Session, image_id: uuid.UUID, user: User, *roles: str) -> Image:
    image = db.get(Image, image_id)
    if image is None or image.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such image.")
    _person_access(db, image.person_id, user, *roles)
    return image


def _observation(db: Session, observation_id: uuid.UUID, user: User, *roles: str) -> tuple[Observation, Lesion]:
    observation = db.get(Observation, observation_id)
    if observation is None or observation.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such observation.")
    lesion = db.get(Lesion, observation.lesion_id)
    if lesion is None or lesion.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such lesion.")
    _person_access(db, lesion.person_id, user, *roles)
    return observation, lesion


def _store(request: Request) -> BlobStore:
    store: BlobStore = request.app.state.blob_store
    return store


def _reference_out(row: ScaleReference) -> ScaleReferenceOut:
    return ScaleReferenceOut(
        id=row.id,
        image_id=row.image_id,
        kind=row.kind,
        reference_mm=row.reference_mm,
        mm_per_px=row.mm_per_px,
        sigma_scale=row.sigma_scale,
        tilt_deg=row.tilt_deg,
        geometry={k: v for k, v in row.geometry.items() if k != "homography"},
        created_at=row.created_at,
    )


# --- the printable card ----------------------------------------------------------------------------


@router.get("/reference-card", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def reference_card(
    user: CurrentUser,
    page: Annotated[Literal["a4", "letter"], Query()] = "a4",
    lang: Annotated[Literal["en", "es"], Query()] = "en",
) -> Response:
    """Two window cards, two strips and a 50 mm line to verify the printer did not scale the page."""
    pdf = render_sheet(page, lang)
    name = f"nevus-reference-card-v1-{page}-{lang}.pdf"
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


# --- scale -----------------------------------------------------------------------------------------


@router.post("/images/{image_id}/fit", response_model=FitOut)
def propose_fit(image_id: uuid.UUID, body: FitIn, request: Request, user: CurrentUser, db: DbSession) -> FitOut:
    """A proposal around a tap, in the photo's upright pixels. Nothing is stored."""
    image = _image(db, image_id, user)
    width, height = upright_size(image)
    if body.x > width or body.y > height:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The point is outside the photo.")
    proposal = fit.propose(load_upright(_store(request), image), body.x, body.y, body.target)
    if proposal is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Nothing to fit was found at that point.")
    return FitOut(**proposal)


@router.get("/images/{image_id}/scale", response_model=ImageScaleOut)
def image_scale(image_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ImageScaleOut:
    image = _image(db, image_id, user)
    width, height = upright_size(image)
    card_row = analysis.latest(db, "image", image.id, card_detect.NAME)
    card = None
    if card_row is not None:
        out = card_row.outputs
        card = CardOut(
            found=bool(out.get("found")),
            card=out.get("card"),
            tilt_deg=out.get("tilt_deg"),
            mm_per_px=out.get("mm_per_px"),
            centre_px=out.get("centre_px"),
            marker_px=out.get("marker_px"),
            flags=list(out.get("flags", [])),
        )
    references = db.scalars(
        select(ScaleReference)
        .where(ScaleReference.image_id == image.id, ScaleReference.deleted_at.is_(None))
        .order_by(ScaleReference.created_at.desc())
    ).all()
    return ImageScaleOut(
        image_id=image.id,
        upright_width=width,
        upright_height=height,
        card_checked=card_row is not None,
        card=card,
        references=[_reference_out(r) for r in references],
        tilt_limit_deg=TILT_LIMIT_DEG,
    )


@router.post(
    "/images/{image_id}/scale-references", response_model=ScaleReferenceOut, status_code=status.HTTP_201_CREATED
)
def add_scale_reference(
    image_id: uuid.UUID,
    body: Annotated[CoinIn | ManualIn, Field(discriminator="kind")],
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> ScaleReferenceOut:
    image = _image(db, image_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    long_edge = max(upright_size(image))
    border = measure.border_px("manual", long_edge)
    if isinstance(body, CoinIn):
        diameter = EURO_COINS_MM[body.denomination]
        scale = measure.coin_scale(body.r, diameter, border)
        geometry: dict[str, Any] = {"cx": body.cx, "cy": body.cy, "r": body.r, "denomination": body.denomination}
        reference_mm = diameter
    else:
        length_px = math.hypot(body.x2 - body.x1, body.y2 - body.y1)
        if length_px < 10:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The two points are too close together.")
        scale = measure.manual_scale(length_px, body.length_mm, border)
        geometry = {"x1": body.x1, "y1": body.y1, "x2": body.x2, "y2": body.y2}
        reference_mm = body.length_mm
    row = ScaleReference(
        image_id=image.id,
        kind=scale.kind,
        reference_mm=reference_mm,
        geometry=geometry,
        mm_per_px=scale.mm_per_px,
        sigma_scale=scale.sigma_scale,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    service.audit(db, "scale.create", user, "image", image.id, client_ip(request, settings), {"kind": scale.kind})
    return _reference_out(row)


# --- measurements ----------------------------------------------------------------------------------


def _scale_for(row: ScaleReference, user: User) -> measure.Scale:
    if row.kind == "card":
        detection = {
            "card": row.geometry.get("card", "window"),
            "homography": row.geometry["homography"],
            "mm_per_px": row.mm_per_px,
            "sigma_fit": row.sigma_scale,
            "tilt_deg": row.tilt_deg or 0.0,
        }
        return measure.card_scale(detection, user.card_line_mm)
    return measure.Scale(kind=row.kind, mm_per_px=row.mm_per_px, sigma_scale=row.sigma_scale)


def _measurement_out(db: Session, row: Measurement, change: ChangeOut | None = None) -> MeasurementOut:
    observation = db.get(Observation, row.observation_id)
    reference = db.get(ScaleReference, row.scale_reference_id)
    return MeasurementOut(
        id=row.id,
        observation_id=row.observation_id,
        lesion_id=row.lesion_id,
        image_id=row.image_id,
        scale_reference_id=row.scale_reference_id,
        scale_kind=reference.kind if reference else "unknown",
        method=row.method,
        shape=row.shape,
        longest_mm=row.longest_mm,
        perpendicular_mm=row.perpendicular_mm,
        area_mm2=row.area_mm2,
        sigma_longest_mm=row.sigma_longest_mm,
        sigma_perpendicular_mm=row.sigma_perpendicular_mm,
        sigma_area_mm2=row.sigma_area_mm2,
        tilt_deg=row.tilt_deg,
        flags=list(row.flags or []),
        captured_at=observation.captured_at if observation else row.created_at,
        created_at=row.created_at,
        change=change,
    )


class MeasurementPreview(BaseModel):
    longest_mm: float
    perpendicular_mm: float
    area_mm2: float
    sigma_longest_mm: float
    sigma_perpendicular_mm: float
    sigma_area_mm2: float
    tilt_deg: float | None
    flags: list[str]


def _evaluate(
    db: Session, observation: Observation, body: MeasurementIn, user: User
) -> tuple[Image, ScaleReference, measure.Scale, dict[str, Any], dict[str, Any], list[str]]:
    image = db.get(Image, body.image_id)
    if image is None or image.deleted_at is not None or image.observation_id != observation.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That photo does not belong to this visit.")
    reference = db.get(ScaleReference, body.scale_reference_id)
    if reference is None or reference.deleted_at is not None or reference.image_id != image.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That scale belongs to another photo.")
    scale = _scale_for(reference, user)
    shape = body.shape.model_dump()
    try:
        values = measure.measure(shape, scale, measure.border_px(body.method, max(upright_size(image))))
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    flags: list[str] = []
    if scale.tilt_deg is not None and scale.tilt_deg > TILT_LIMIT_DEG:
        flags.append("tilted")
    if scale.kind == "card" and user.card_line_mm is None:
        flags.append("unverified_card")
    if scale.kind in ("coin", "manual"):
        flags.append("tilt_unknown")
    return image, reference, scale, shape, values, flags


@router.post("/observations/{observation_id}/measurements/preview", response_model=MeasurementPreview)
def preview_measurement(
    observation_id: uuid.UUID, body: MeasurementIn, user: CurrentUser, db: DbSession
) -> MeasurementPreview:
    """The same computation as saving, without saving: the interface shows it while the outline moves."""
    observation, _ = _observation(db, observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    _, _, scale, _, values, flags = _evaluate(db, observation, body, user)
    return MeasurementPreview(
        longest_mm=values["longest_mm"],
        perpendicular_mm=values["perpendicular_mm"],
        area_mm2=values["area_mm2"],
        sigma_longest_mm=values["sigma_longest_mm"],
        sigma_perpendicular_mm=values["sigma_perpendicular_mm"],
        sigma_area_mm2=values["sigma_area_mm2"],
        tilt_deg=scale.tilt_deg,
        flags=flags,
    )


@router.post(
    "/observations/{observation_id}/measurements", response_model=MeasurementOut, status_code=status.HTTP_201_CREATED
)
def create_measurement(
    observation_id: uuid.UUID,
    body: MeasurementIn,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> MeasurementOut:
    """Submitting a measurement is the confirmation: nothing proposed is ever stored without it."""
    observation, lesion = _observation(db, observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    image, reference, scale, shape, values, flags = _evaluate(db, observation, body, user)
    row = Measurement(
        observation_id=observation.id,
        lesion_id=lesion.id,
        image_id=image.id,
        scale_reference_id=reference.id,
        method=body.method,
        shape=shape,
        longest_mm=values["longest_mm"],
        perpendicular_mm=values["perpendicular_mm"],
        area_mm2=values["area_mm2"],
        sigma_longest_mm=values["sigma_longest_mm"],
        sigma_perpendicular_mm=values["sigma_perpendicular_mm"],
        sigma_area_mm2=values["sigma_area_mm2"],
        tilt_deg=scale.tilt_deg,
        flags=flags,
        details={
            "sigma_scale": values["sigma_scale"],
            "border_mm": values["border_mm"],
            "print_factor": scale.print_factor,
        },
        confirmed_by=user.id,
        confirmed_at=utcnow(),
    )
    db.add(row)
    db.flush()
    service.audit(db, "measurement.create", user, "measurement", row.id, client_ip(request, settings))
    return _measurement_out(db, row)


@router.get("/observations/{observation_id}/measurements", response_model=list[MeasurementOut])
def observation_measurements(observation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[MeasurementOut]:
    observation, _ = _observation(db, observation_id, user)
    rows = db.scalars(
        select(Measurement)
        .where(Measurement.observation_id == observation.id, Measurement.deleted_at.is_(None))
        .order_by(Measurement.created_at)
    ).all()
    return [_measurement_out(db, r) for r in rows]


def lesion_series(db: Session, lesion_id: uuid.UUID) -> list[tuple[Measurement, datetime]]:
    """One measurement per visit (the latest confirmed one), oldest visit first."""
    rows = db.execute(
        select(Measurement, Observation.captured_at)
        .join(Observation, Observation.id == Measurement.observation_id)
        .where(
            Measurement.lesion_id == lesion_id,
            Measurement.deleted_at.is_(None),
            Observation.deleted_at.is_(None),
        )
        .order_by(Observation.captured_at, Measurement.created_at)
    ).all()
    latest_per_visit: dict[uuid.UUID, tuple[Measurement, datetime]] = {}
    for row, captured_at in rows:
        latest_per_visit[row.observation_id] = (row, captured_at)
    return sorted(latest_per_visit.values(), key=lambda pair: pair[1])


def change_between(before: tuple[Measurement, datetime], after: tuple[Measurement, datetime]) -> ChangeOut:
    a, b = before[0], after[0]
    result = measure.change(a.longest_mm, a.sigma_longest_mm, b.longest_mm, b.sigma_longest_mm)
    return ChangeOut(
        delta_mm=result["delta"], sigma_mm=result["sigma"], detectable=result["detectable"], since=before[1]
    )


@router.get("/lesions/{lesion_id}/measurements", response_model=list[MeasurementOut])
def lesion_measurements(lesion_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[MeasurementOut]:
    lesion = db.get(Lesion, lesion_id)
    if lesion is None or lesion.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such lesion.")
    _person_access(db, lesion.person_id, user)
    series = lesion_series(db, lesion.id)
    out: list[MeasurementOut] = []
    for index, pair in enumerate(series):
        change = change_between(series[index - 1], pair) if index > 0 else None
        out.append(_measurement_out(db, pair[0], change))
    return out


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    measurement_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    row = db.get(Measurement, measurement_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such measurement.")
    _observation(db, row.observation_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    row.deleted_at = utcnow()
    service.audit(db, "measurement.delete", user, "measurement", row.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
