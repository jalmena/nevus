# SPDX-License-Identifier: AGPL-3.0-only
"""Comparing two photographs: alignment that abstains when unsure, an overlay and a difference map."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from nevus import analysis
from nevus.auth.dependencies import CurrentUser, DbSession
from nevus.cv import align, card_detect
from nevus.cv.pipeline import load_upright, upright_size
from nevus.db.models import Analysis, Image, Person, PersonAccess, ScaleReference, User
from nevus.storage.blobs import BlobStore

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])
PAIR_NAMESPACE = uuid.UUID("6f1c2f5e-9d1b-4e1a-9c6a-6e5b7c0d2a11")


class ComparisonIn(BaseModel):
    image_a: uuid.UUID
    image_b: uuid.UUID


class SideOut(BaseModel):
    image_id: uuid.UUID
    upright_width: int
    upright_height: int
    mm_per_px: float | None
    scale_kind: str | None


Reason = Literal[
    "too_little_detail",
    "too_few_matches",
    "no_consistent_alignment",
    "matches_disagree",
    "mirrored",
    "distance",
    "angle",
]


class ComparisonOut(BaseModel):
    id: uuid.UUID
    status: Literal["aligned", "abstained"]
    reason: Reason | None
    method: Literal["card", "features"]
    inliers: int | None
    inlier_ratio: float | None
    matrix: list[list[float]] | None
    a: SideOut
    b: SideOut
    overlay_url: str | None
    heatmap_url: str | None
    coverage: float | None
    mean_difference: float | None


def _image(db: DbSession, image_id: uuid.UUID, user: User) -> Image:
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
    return image


def _card(db: DbSession, image: Image) -> dict[str, Any] | None:
    row = analysis.latest(db, "image", image.id, card_detect.NAME)
    return row.outputs if row is not None and row.outputs.get("found") else None


def _side(db: DbSession, image: Image) -> SideOut:
    width, height = upright_size(image)
    card = _card(db, image)
    if card:
        return SideOut(
            image_id=image.id,
            upright_width=width,
            upright_height=height,
            mm_per_px=float(card["mm_per_px"]),
            scale_kind="card",
        )
    ref = db.scalar(
        select(ScaleReference)
        .where(ScaleReference.image_id == image.id, ScaleReference.deleted_at.is_(None))
        .order_by(ScaleReference.created_at.desc())
    )
    return SideOut(
        image_id=image.id,
        upright_width=width,
        upright_height=height,
        mm_per_px=ref.mm_per_px if ref else None,
        scale_kind=ref.kind if ref else None,
    )


def _out(db: DbSession, row: Analysis, a: Image, b: Image) -> ComparisonOut:
    out = row.outputs
    aligned = out.get("status") == "aligned"
    return ComparisonOut(
        id=row.id,
        status=out.get("status", "abstained"),
        reason=out.get("reason"),
        method=out.get("method", "features"),
        inliers=out.get("inliers"),
        inlier_ratio=out.get("inlier_ratio"),
        matrix=out.get("matrix"),
        a=_side(db, a),
        b=_side(db, b),
        overlay_url=f"/api/comparisons/{row.id}/overlay" if aligned else None,
        heatmap_url=f"/api/comparisons/{row.id}/heatmap" if aligned else None,
        coverage=out.get("coverage"),
        mean_difference=out.get("mean_difference"),
    )


@router.post("", response_model=ComparisonOut)
def compare(body: ComparisonIn, request: Request, user: CurrentUser, db: DbSession) -> ComparisonOut:
    """Align photo B onto photo A (same person). The result is cached as an analysis record."""
    a, b = _image(db, body.image_a, user), _image(db, body.image_b, user)
    if a.person_id != b.person_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Both photos must be of the same person.")
    pair_id = uuid.uuid5(PAIR_NAMESPACE, f"{a.id}:{b.id}")
    input_hash = hashlib.sha256(f"{a.sha256}:{b.sha256}".encode()).hexdigest()
    existing = analysis.find(db, "pair", pair_id, align.NAME, align.VERSION, align.PARAMS, input_hash)
    if existing is not None:
        return _out(db, existing, a, b)
    store: BlobStore = request.app.state.blob_store
    card_a, card_b = _card(db, a), _card(db, b)
    image_a, image_b = load_upright(store, a), load_upright(store, b)
    if card_a and card_b:
        result = align.from_cards(card_a["homography"], card_b["homography"])
    else:
        result = align.from_features(image_a, image_b)
    if result["status"] == "aligned":
        pictures = align.difference(image_a, image_b, result["matrix"])
        result["overlay_sha256"] = store.put(pictures.pop("overlay"), derived=True)
        result["heatmap_sha256"] = store.put(pictures.pop("heatmap"), derived=True)
        result.update(pictures)
    row = analysis.record(
        db,
        target_type="pair",
        target_id=pair_id,
        analyzer=align.NAME,
        version=align.VERSION,
        params=align.PARAMS,
        input_hash=input_hash,
        outputs={**result, "image_a": str(a.id), "image_b": str(b.id)},
    )
    return _out(db, row, a, b)


@router.get("/{comparison_id}/{kind}", response_class=FileResponse)
def picture(comparison_id: uuid.UUID, kind: str, request: Request, user: CurrentUser, db: DbSession) -> Response:
    row = db.get(Analysis, comparison_id)
    if row is None or row.analyzer != align.NAME or kind not in ("overlay", "heatmap"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such comparison.")
    _image(db, uuid.UUID(row.outputs["image_a"]), user)
    _image(db, uuid.UUID(row.outputs["image_b"]), user)
    digest = row.outputs.get(f"{kind}_sha256")
    if not digest:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This comparison has no picture.")
    store: BlobStore = request.app.state.blob_store
    path = store.path(digest, derived=True)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The picture is missing from the store.")
    return FileResponse(
        path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"}
    )
