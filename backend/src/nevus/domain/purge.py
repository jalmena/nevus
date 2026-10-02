# SPDX-License-Identifier: AGPL-3.0-only
"""Deleting for real: the trash purge, the immediate purge of a profile, and blob garbage collection.

Rows go first, files after: a blob is removed only when no row refers to it any more and it is
older than the grace period, so an upload in flight (file written, row not yet committed) is safe,
and so is a backup taken in the meantime.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from nevus.db.models import (
    Analysis,
    Export,
    Image,
    Lesion,
    Measurement,
    Observation,
    Person,
    PersonAccess,
    Rendition,
    ScaleReference,
)
from nevus.db.types import utcnow
from nevus.storage.blobs import BlobStore

GRACE_SECONDS = 24 * 3600


def _delete_images(db: Session, image_ids: list[uuid.UUID]) -> None:
    if not image_ids:
        return
    measurement_scales = select(ScaleReference.id).where(ScaleReference.image_id.in_(image_ids))
    db.execute(delete(Measurement).where(Measurement.scale_reference_id.in_(measurement_scales)))
    db.execute(delete(Measurement).where(Measurement.image_id.in_(image_ids)))
    db.execute(delete(ScaleReference).where(ScaleReference.image_id.in_(image_ids)))
    db.execute(delete(Analysis).where(Analysis.target_type == "image", Analysis.target_id.in_(image_ids)))
    db.execute(delete(Rendition).where(Rendition.image_id.in_(image_ids)))
    db.execute(delete(Image).where(Image.id.in_(image_ids)))


def _delete_observations(db: Session, observation_ids: list[uuid.UUID]) -> None:
    if not observation_ids:
        return
    images = list(db.scalars(select(Image.id).where(Image.observation_id.in_(observation_ids))))
    _delete_images(db, images)
    db.execute(delete(Measurement).where(Measurement.observation_id.in_(observation_ids)))
    db.execute(delete(Observation).where(Observation.id.in_(observation_ids)))


def _delete_lesions(db: Session, lesion_ids: list[uuid.UUID]) -> None:
    if not lesion_ids:
        return
    observations = list(db.scalars(select(Observation.id).where(Observation.lesion_id.in_(lesion_ids))))
    _delete_observations(db, observations)
    db.execute(delete(Measurement).where(Measurement.lesion_id.in_(lesion_ids)))
    db.execute(delete(Lesion).where(Lesion.id.in_(lesion_ids)))


def purge_person(db: Session, person_id: uuid.UUID) -> None:
    """Everything of one person, at once. The audit log keeps only identifiers."""
    lesions = list(db.scalars(select(Lesion.id).where(Lesion.person_id == person_id)))
    _delete_lesions(db, lesions)
    _delete_images(db, list(db.scalars(select(Image.id).where(Image.person_id == person_id))))
    db.execute(delete(Export).where(Export.person_id == person_id))
    db.execute(delete(PersonAccess).where(PersonAccess.person_id == person_id))
    db.execute(delete(Person).where(Person.id == person_id))
    db.flush()


def purge_lesion(db: Session, lesion_id: uuid.UUID) -> None:
    _delete_lesions(db, [lesion_id])
    db.flush()


def purge_observation(db: Session, observation_id: uuid.UUID) -> None:
    _delete_observations(db, [observation_id])
    db.flush()


def purge_image(db: Session, image_id: uuid.UUID) -> None:
    _delete_images(db, [image_id])
    db.flush()


def purge_expired(db: Session, days: int, now: datetime | None = None) -> dict[str, int]:
    """Hard-delete what has been in the trash longer than `days`."""
    cutoff = (now or utcnow()) - timedelta(days=days)
    persons = list(db.scalars(select(Person.id).where(Person.deleted_at.is_not(None), Person.deleted_at < cutoff)))
    for person_id in persons:
        purge_person(db, person_id)
    lesions = list(db.scalars(select(Lesion.id).where(Lesion.deleted_at.is_not(None), Lesion.deleted_at < cutoff)))
    _delete_lesions(db, lesions)
    observations = list(
        db.scalars(select(Observation.id).where(Observation.deleted_at.is_not(None), Observation.deleted_at < cutoff))
    )
    _delete_observations(db, observations)
    images = list(db.scalars(select(Image.id).where(Image.deleted_at.is_not(None), Image.deleted_at < cutoff)))
    _delete_images(db, images)
    db.execute(delete(Measurement).where(Measurement.deleted_at.is_not(None), Measurement.deleted_at < cutoff))
    db.flush()
    return {"persons": len(persons), "lesions": len(lesions), "observations": len(observations), "images": len(images)}


def collect_garbage(db: Session, store: BlobStore, grace_seconds: int = GRACE_SECONDS) -> int:
    """Remove blob files no row refers to. Returns how many files went."""
    referenced = set(db.scalars(select(Image.sha256))) | set(db.scalars(select(Rendition.sha256)))
    cutoff = time.time() - grace_seconds
    removed = 0
    for kind in ("originals", "derived"):
        root: Path = store.root / kind
        if not root.is_dir():
            continue
        for path in root.glob("*/*/*"):
            if path.is_file() and path.name not in referenced and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
    return removed


def expire_exports(db: Session, exports_dir: Path, now: datetime | None = None) -> int:
    now = now or utcnow()
    rows = db.scalars(select(Export).where(Export.expires_at.is_not(None), Export.expires_at < now)).all()
    for row in rows:
        if row.file_name:
            (exports_dir / row.file_name).unlink(missing_ok=True)
        db.delete(row)
    db.flush()
    return len(rows)
