# SPDX-License-Identifier: AGPL-3.0-only
"""The labelling tool's API (FR-ANA-05): the operator labels their own photos to evaluate the analyzers.

Administrators only, and only on photos of persons they own or manage. Labels never leave the server.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import analysis, evaluation
from nevus.auth.dependencies import AdminUser, DbSession
from nevus.cv import segment
from nevus.cv.pipeline import upright_size
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    EvaluationLabel,
    Image,
    Lesion,
    Observation,
    Person,
    PersonAccess,
    User,
)
from nevus.db.types import utcnow

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


class LabelIn(BaseModel):
    outline: list[list[float]] | None = Field(default=None, min_length=3, max_length=2000)
    quality: Literal["good", "bad"] | None = None


class LabelOut(BaseModel):
    outline: list[list[float]] | None
    quality: Literal["good", "bad"] | None
    labelled_at: datetime


class EvaluationPhoto(BaseModel):
    image_id: uuid.UUID
    person_name: str
    skin_tone: str | None
    mark: str
    zone: str
    captured_on: date | None
    role: str
    upright_width: int
    upright_height: int
    quality_flags: list[str]
    proposal: list[list[float]] | None
    label: LabelOut | None


def _photos(db: Session, admin: User) -> list[tuple[Image, Person, Lesion, Observation]]:
    rows = db.execute(
        select(Image, Person, Lesion, Observation)
        .join(Observation, Observation.id == Image.observation_id)
        .join(Lesion, Lesion.id == Observation.lesion_id)
        .join(Person, Person.id == Image.person_id)
        .join(PersonAccess, (PersonAccess.person_id == Person.id) & (PersonAccess.user_id == admin.id))
        .where(
            Image.deleted_at.is_(None),
            Observation.deleted_at.is_(None),
            Lesion.deleted_at.is_(None),
            Person.deleted_at.is_(None),
            PersonAccess.role.in_((ACCESS_OWNER, ACCESS_MANAGER)),
        )
        .order_by(Observation.captured_at.desc(), Image.created_at)
    ).all()
    return [(image, person, lesion, observation) for image, person, lesion, observation in rows]


def _label_out(label: EvaluationLabel | None) -> LabelOut | None:
    if label is None:
        return None
    return LabelOut(outline=label.outline, quality=label.quality, labelled_at=label.labelled_at)


@router.get("/photos", response_model=list[EvaluationPhoto])
def list_photos(
    admin: AdminUser, db: DbSession, only: Literal["all", "unlabelled", "labelled"] = Query(default="all")
) -> list[EvaluationPhoto]:
    labels = {row.image_id: row for row in db.scalars(select(EvaluationLabel))}
    out: list[EvaluationPhoto] = []
    for image, person, lesion, observation in _photos(db, admin):
        label = labels.get(image.id)
        if (only == "unlabelled" and label is not None) or (only == "labelled" and label is None):
            continue
        width, height = upright_size(image)
        proposal = analysis.latest(db, "image", image.id, segment.NAME)
        out.append(
            EvaluationPhoto(
                image_id=image.id,
                person_name=person.display_name,
                skin_tone=person.skin_tone,
                mark=lesion.label or lesion.zone_code,
                zone=lesion.zone_code,
                captured_on=observation.captured_local_date,
                role=image.role,
                upright_width=width,
                upright_height=height,
                quality_flags=list(image.quality_flags or []),
                proposal=proposal.outputs.get("outline") if proposal and proposal.outputs.get("found") else None,
                label=_label_out(label),
            )
        )
    return out


def _mine(db: Session, admin: User, image_id: uuid.UUID) -> Image:
    for image, *_ in _photos(db, admin):
        if image.id == image_id:
            return image
    raise HTTPException(status.HTTP_404_NOT_FOUND, "No such photo in your evaluation set.")


@router.put("/photos/{image_id}/label", response_model=LabelOut)
def put_label(image_id: uuid.UUID, body: LabelIn, admin: AdminUser, db: DbSession) -> LabelOut:
    image = _mine(db, admin, image_id)
    if body.outline is None and body.quality is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Give an outline, a quality judgement, or both.")
    label = db.scalar(select(EvaluationLabel).where(EvaluationLabel.image_id == image.id))
    if label is None:
        label = EvaluationLabel(image_id=image.id)
        db.add(label)
    label.outline = body.outline
    label.quality = body.quality
    label.labelled_by = admin.id
    label.labelled_at = utcnow()
    db.flush()
    out = _label_out(label)
    assert out is not None
    return out


@router.delete("/photos/{image_id}/label", status_code=status.HTTP_204_NO_CONTENT)
def delete_label(image_id: uuid.UUID, admin: AdminUser, db: DbSession) -> Response:
    image = _mine(db, admin, image_id)
    label = db.scalar(select(EvaluationLabel).where(EvaluationLabel.image_id == image.id))
    if label is not None:
        db.delete(label)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary")
def summary(admin: AdminUser, db: DbSession) -> dict[str, Any]:
    """Metrics from the proposals already recorded; `nevus evaluate` runs the current analyzer afresh."""
    return evaluation.evaluate(db, evaluation.stored_runner(db))
