# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental proposals (FR-ANA-02, FR-ANA-03): shown labelled as such, recorded only once confirmed.

A proposal is an analysis record waiting for a decision. Confirming one turns its outline into a
measurement linked to the analysis that proposed it; rejecting one keeps the record, marked rejected,
so the evaluation of the analyzer can count it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, get_args

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import measure
from nevus.api.measurements import (
    MeasurementIn,
    MeasurementOut,
    _measurement_out,
    _scale_for,
    save_measurement,
)
from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.cv import segment
from nevus.cv.pipeline import upright_size
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    Analysis,
    Image,
    Lesion,
    Observation,
    Person,
    PersonAccess,
    ScaleReference,
    User,
)
from nevus.db.types import utcnow

router = APIRouter(prefix="/api", tags=["proposals"])
Reason = Literal["no_mark_found", "low_contrast", "irregular_region", "too_large", "too_small"]
Framing = Literal["mark_off_centre", "mark_small", "mark_cut", "no_mark_found"]


class ProposedSize(BaseModel):
    scale_reference_id: uuid.UUID
    scale_kind: str
    longest_mm: float
    perpendicular_mm: float
    area_mm2: float
    sigma_longest_mm: float
    sigma_perpendicular_mm: float
    sigma_area_mm2: float


class ProposalOut(BaseModel):
    id: uuid.UUID
    image_id: uuid.UUID
    analyzer: str
    version: str
    found: bool
    reason: Reason | None
    outline: list[list[float]] | None
    confidence: float | None
    framing_flags: list[Framing]
    decision: Literal["pending", "confirmed", "rejected", "automatic"]
    created_at: datetime
    size: ProposedSize | None


class ConfirmIn(BaseModel):
    scale_reference_id: uuid.UUID | None = None


def _image(db: Session, image_id: uuid.UUID, user: User, *roles: str) -> tuple[Image, Person]:
    image = db.get(Image, image_id)
    person = db.get(Person, image.person_id) if image else None
    access = db.get(PersonAccess, (image.person_id, user.id)) if image else None
    if (
        image is None
        or image.deleted_at is not None
        or person is None
        or person.deleted_at is not None
        or access is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such image.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")
    return image, person


def _reference(db: Session, image: Image, wanted: uuid.UUID | None) -> ScaleReference | None:
    if wanted is not None:
        row = db.get(ScaleReference, wanted)
        return row if row is not None and row.image_id == image.id and row.deleted_at is None else None
    rows = db.scalars(
        select(ScaleReference)
        .where(ScaleReference.image_id == image.id, ScaleReference.deleted_at.is_(None))
        .order_by(ScaleReference.created_at.desc())
    ).all()
    return next((r for r in rows if r.kind == "card"), rows[0] if rows else None)


def _size(db: Session, image: Image, row: Analysis, user: User) -> ProposedSize | None:
    outline = row.outputs.get("outline")
    reference = _reference(db, image, None)
    if not row.outputs.get("found") or not outline or reference is None:
        return None
    scale = _scale_for(reference, user)
    try:
        values = measure.measure(
            {"type": "outline", "points": outline}, scale, measure.border_px("automatic", max(upright_size(image)))
        )
    except ValueError:
        return None
    return ProposedSize(
        scale_reference_id=reference.id,
        scale_kind=reference.kind,
        longest_mm=values["longest_mm"],
        perpendicular_mm=values["perpendicular_mm"],
        area_mm2=values["area_mm2"],
        sigma_longest_mm=values["sigma_longest_mm"],
        sigma_perpendicular_mm=values["sigma_perpendicular_mm"],
        sigma_area_mm2=values["sigma_area_mm2"],
    )


def _out(db: Session, image: Image, row: Analysis, user: User) -> ProposalOut:
    out = row.outputs
    return ProposalOut(
        id=row.id,
        image_id=image.id,
        analyzer=row.analyzer,
        version=row.version,
        found=bool(out.get("found")),
        reason=out.get("reason"),
        outline=out.get("outline"),
        confidence=out.get("confidence"),
        framing_flags=[f for f in out.get("framing_flags", []) if f in get_args(Framing)],
        decision=row.decision,
        created_at=row.created_at,
        size=_size(db, image, row, user),
    )


@router.get("/images/{image_id}/proposals", response_model=list[ProposalOut])
def list_proposals(image_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ProposalOut]:
    """Nothing unless the person turned the experimental analysis on (FR-ANA-01)."""
    image, person = _image(db, image_id, user)
    if not person.experimental_analysis:
        return []
    rows = db.scalars(
        select(Analysis)
        .where(Analysis.target_type == "image", Analysis.target_id == image.id, Analysis.analyzer == segment.NAME)
        .order_by(Analysis.created_at.desc())
    ).all()
    return [_out(db, image, row, user) for row in rows]


def _proposal(db: Session, proposal_id: uuid.UUID, user: User) -> tuple[Analysis, Image, Person]:
    row = db.get(Analysis, proposal_id)
    if row is None or row.analyzer != segment.NAME or row.target_type != "image":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such proposal.")
    image, person = _image(db, row.target_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    if not person.experimental_analysis:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such proposal.")
    if row.decision != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This proposal has already been decided.")
    return row, image, person


@router.post("/proposals/{proposal_id}/confirm", response_model=MeasurementOut, status_code=status.HTTP_201_CREATED)
def confirm_proposal(
    proposal_id: uuid.UUID,
    body: ConfirmIn,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> MeasurementOut:
    """The person accepts the proposed outline: it becomes a measurement, linked to the analysis."""
    row, image, _ = _proposal(db, proposal_id, user)
    observation = db.get(Observation, image.observation_id) if image.observation_id else None
    lesion = db.get(Lesion, observation.lesion_id) if observation else None
    if observation is None or lesion is None or observation.deleted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This photo is no longer part of a visit.")
    reference = _reference(db, image, body.scale_reference_id)
    if reference is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Give this photo a scale first: the card, a coin or a length.")
    request_body = MeasurementIn(
        image_id=image.id,
        scale_reference_id=reference.id,
        method="assisted",
        shape={"type": "outline", "points": row.outputs["outline"]},
    )
    measurement = save_measurement(db, observation, lesion, request_body, user, "automatic", analysis_id=row.id)
    row.decision, row.decided_by, row.decided_at = "confirmed", user.id, utcnow()
    service.audit(db, "proposal.confirm", user, "analysis", row.id, client_ip(request, settings))
    return _measurement_out(db, measurement)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> ProposalOut:
    row, image, _ = _proposal(db, proposal_id, user)
    row.decision, row.decided_by, row.decided_at = "rejected", user.id, utcnow()
    service.audit(db, "proposal.reject", user, "analysis", row.id, client_ip(request, settings))
    return _out(db, image, row, user)
