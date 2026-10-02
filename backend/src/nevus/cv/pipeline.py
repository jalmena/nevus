# SPDX-License-Identifier: AGPL-3.0-only
"""What runs after a photograph is stored: quality checks, the reference-card search, and the warnings.

Both run for every photo, whatever the profile's experimental setting: they describe the photo and
find the scale, they do not analyse the skin (ADR-0003). Each writes its own analysis record; the
photo's warning list is recomputed from the latest record of each, so their order does not matter.

The experimental outline proposal runs only for persons who turned the experimental analysis on, after
the card search (lower priority), and waits for the person's decision.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import analysis
from nevus.cv import card_detect, quality, segment
from nevus.cv.imageio import Img, decode, upright
from nevus.db.models import Image, Observation, Person, ScaleReference
from nevus.db.types import utcnow
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register
from nevus.storage.blobs import BlobStore

QUALITY_KIND = "analyze.quality"
CARD_KIND = "analyze.card"
SEGMENT_KIND = "analyze.segment"
CARD_FLAGS = ("tilted", "card_small")


def enqueue_analyses(db: Session, image: Image) -> None:
    queue.enqueue(
        db, QUALITY_KIND, {"image_id": str(image.id)}, dedupe_key=f"quality:{image.id}:{quality.VERSION}", priority=5
    )
    if image.observation_id is not None:
        queue.enqueue(
            db, CARD_KIND, {"image_id": str(image.id)}, dedupe_key=f"card:{image.id}:{card_detect.VERSION}", priority=4
        )
        enqueue_proposal(db, image)


def enqueue_proposal(db: Session, image: Image) -> bool:
    """The experimental outline proposal, only when the person has the experimental analysis on."""
    person = db.get(Person, image.person_id)
    if person is None or not person.experimental_analysis or image.observation_id is None:
        return False
    job = queue.enqueue(
        db,
        SEGMENT_KIND,
        {"image_id": str(image.id)},
        dedupe_key=f"segment:{image.id}:{segment.VERSION}",
        priority=3,
    )
    return job is not None


def upright_size(image: Image) -> tuple[int, int]:
    return (image.height, image.width) if image.orientation in (5, 6, 7, 8) else (image.width, image.height)


@lru_cache(maxsize=2)
def _decoded(path: str, sha256: str, orientation: int) -> Img:
    with open(path, "rb") as handle:
        return upright(decode(handle.read()), orientation)


def load_upright(store: BlobStore, image: Image) -> Img:
    """The original as the person sees it, at full resolution; the last two are kept in memory for taps."""
    return _decoded(str(store.path(image.sha256)), image.sha256, image.orientation)


def refresh_image_flags(db: Session, image: Image) -> None:
    flags: list[str] = []
    q = analysis.latest(db, "image", image.id, quality.NAME)
    if q is not None:
        flags.extend(q.outputs.get("flags", []))
    c = analysis.latest(db, "image", image.id, card_detect.NAME)
    if c is not None:
        flags.extend(f for f in c.outputs.get("flags", []) if f in CARD_FLAGS)
    image.quality_flags = sorted(set(flags))
    if q is not None and image.quality_checked_at is None:
        image.quality_checked_at = utcnow()
    db.flush()
    if image.observation_id is not None:
        refresh_observation_flags(db, image.observation_id)


def refresh_observation_flags(db: Session, observation_id: uuid.UUID) -> None:
    """An observation is 'saved with quality warnings' when any of its photographs carries one."""
    observation = db.get(Observation, observation_id)
    if observation is None:
        return
    images = db.scalars(select(Image).where(Image.observation_id == observation_id, Image.deleted_at.is_(None))).all()
    flags = sorted({flag for image in images for flag in (image.quality_flags or [])})
    if flags != list(observation.quality_flags or []):
        observation.quality_flags = flags


def _image(ctx: JobContext, payload: dict[str, Any]) -> Image | None:
    image = ctx.db.get(Image, uuid.UUID(payload["image_id"]))
    return None if image is None or image.deleted_at is not None else image


def _read(ctx: JobContext, image: Image) -> bytes:
    path = ctx.store.path(image.sha256)
    if not path.is_file():
        raise FileNotFoundError("original missing from the blob store")
    return path.read_bytes()


# --- quality ---------------------------------------------------------------------------------------


def _quality_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    image = _image(ctx, payload)
    if image is None:
        return None
    return {"data": _read(ctx, image), "width": image.width, "height": image.height}


def _quality_compute(value: dict[str, Any]) -> dict[str, Any]:
    return quality.analyze(value["data"], value["width"], value["height"])


def _quality_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    image = _image(ctx, payload)
    if image is None:
        return
    analysis.record(
        ctx.db,
        target_type="image",
        target_id=image.id,
        analyzer=quality.NAME,
        version=quality.VERSION,
        params=quality.PARAMS,
        input_hash=image.sha256,
        outputs=result,
    )
    image.quality_checked_at = utcnow()
    refresh_image_flags(ctx.db, image)


# --- reference card --------------------------------------------------------------------------------


def _card_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    image = _image(ctx, payload)
    if image is None:
        return None
    return {"data": _read(ctx, image), "orientation": image.orientation}


def _card_compute(value: dict[str, Any]) -> dict[str, Any]:
    return card_detect.detect(upright(decode(value["data"]), int(value["orientation"])))


def _card_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    image = _image(ctx, payload)
    if image is None:
        return
    row = analysis.record(
        ctx.db,
        target_type="image",
        target_id=image.id,
        analyzer=card_detect.NAME,
        version=card_detect.VERSION,
        params=card_detect.PARAMS,
        input_hash=image.sha256,
        outputs=result,
    )
    if result.get("found"):
        existing = ctx.db.scalar(
            select(ScaleReference).where(ScaleReference.image_id == image.id, ScaleReference.analysis_id == row.id)
        )
        if existing is None:
            ctx.db.add(
                ScaleReference(
                    image_id=image.id,
                    kind="card",
                    geometry={"card": result["card"], "ids": result["ids"], "homography": result["homography"]},
                    mm_per_px=float(result["mm_per_px"]),
                    sigma_scale=float(result["sigma_fit"]),
                    tilt_deg=float(result["tilt_deg"]),
                    analysis_id=row.id,
                )
            )
    refresh_image_flags(ctx.db, image)


# --- experimental outline proposal ------------------------------------------------------------------


def _segment_load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    image = _image(ctx, payload)
    if image is None:
        return None
    person = ctx.db.get(Person, image.person_id)
    if person is None or not person.experimental_analysis:
        return None  # switched off since it was queued
    card = analysis.latest(ctx.db, "image", image.id, card_detect.NAME)
    return {"data": _read(ctx, image), "orientation": image.orientation, "card": card.outputs if card else None}


def _segment_compute(value: dict[str, Any]) -> dict[str, Any]:
    return segment.propose(upright(decode(value["data"]), int(value["orientation"])), value["card"])


def _segment_store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    image = _image(ctx, payload)
    if image is None:
        return
    analysis.record(
        ctx.db,
        target_type="image",
        target_id=image.id,
        analyzer=segment.NAME,
        version=segment.VERSION,
        params=segment.PARAMS,
        input_hash=image.sha256,
        outputs=result,
        decision="pending" if result.get("found") else "automatic",
    )


register(JobKind(QUALITY_KIND, _quality_load, _quality_compute, _quality_store, timeout=90.0))
register(JobKind(SEGMENT_KIND, _segment_load, _segment_compute, _segment_store, timeout=120.0))
register(JobKind(CARD_KIND, _card_load, _card_compute, _card_store, timeout=120.0))
