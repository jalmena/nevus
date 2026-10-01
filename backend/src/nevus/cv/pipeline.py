# SPDX-License-Identifier: AGPL-3.0-only
"""What runs after a photograph is stored: the quality checks, and the observation's warning summary."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import analysis
from nevus.cv import quality
from nevus.db.models import Image, Observation
from nevus.db.types import utcnow
from nevus.jobs import queue
from nevus.jobs.registry import JobContext, JobKind, register

QUALITY_KIND = "analyze.quality"


def enqueue_quality(db: Session, image: Image) -> None:
    queue.enqueue(
        db,
        QUALITY_KIND,
        {"image_id": str(image.id)},
        dedupe_key=f"quality:{image.id}:{quality.VERSION}",
        priority=5,
    )


def refresh_observation_flags(db: Session, observation_id: uuid.UUID) -> None:
    """An observation is 'saved with quality warnings' when any of its photographs carries one."""
    observation = db.get(Observation, observation_id)
    if observation is None:
        return
    images = db.scalars(select(Image).where(Image.observation_id == observation_id, Image.deleted_at.is_(None))).all()
    flags = sorted({flag for image in images for flag in (image.quality_flags or [])})
    if flags != list(observation.quality_flags or []):
        observation.quality_flags = flags


def _load(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any] | None:
    image = ctx.db.get(Image, uuid.UUID(payload["image_id"]))
    if image is None or image.deleted_at is not None:
        return None
    path = ctx.store.path(image.sha256)
    if not path.is_file():
        raise FileNotFoundError("original missing from the blob store")
    return {"data": path.read_bytes(), "width": image.width, "height": image.height}


def _compute(value: dict[str, Any]) -> dict[str, Any]:
    return quality.analyze(value["data"], value["width"], value["height"])


def _store(ctx: JobContext, payload: dict[str, Any], result: dict[str, Any]) -> None:
    image = ctx.db.get(Image, uuid.UUID(payload["image_id"]))
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
    image.quality_flags = list(result["flags"])
    image.quality_checked_at = utcnow()
    ctx.db.flush()
    if image.observation_id is not None:
        refresh_observation_flags(ctx.db, image.observation_id)


register(JobKind(QUALITY_KIND, _load, _compute, _store, timeout=90.0))
