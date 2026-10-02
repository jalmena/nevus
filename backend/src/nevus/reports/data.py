# SPDX-License-Identifier: AGPL-3.0-only
"""Everything a report shows, read from the database in the main process.

The result is plain data (plus the paths of the photo renditions to print), so the rendering can run in
a worker process, and the same data, without the paths, is attached to the PDF.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import nevus
from nevus import analysis
from nevus.api.measurements import change_between, lesion_series
from nevus.bodymap import body_map
from nevus.config import Settings
from nevus.cv import card_detect
from nevus.cv.pipeline import upright_size
from nevus.db.models import Analysis, Image, Lesion, Observation, Person, Rendition, ScaleReference
from nevus.db.types import utcnow
from nevus.domain import due
from nevus.storage.blobs import BlobStore

ROLE_ORDER = ("with_reference", "close_up", "overview", "other")
PHOTOS_PER_VISIT = 3


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def _scale_of(db: Session, image: Image) -> float | None:
    card = analysis.latest(db, "image", image.id, card_detect.NAME)
    if card is not None and card.outputs.get("found"):
        return float(card.outputs["mm_per_px"])
    ref = db.scalar(
        select(ScaleReference)
        .where(ScaleReference.image_id == image.id, ScaleReference.deleted_at.is_(None))
        .order_by(ScaleReference.created_at.desc())
    )
    return ref.mm_per_px if ref else None


def _measurements(db: Session, lesion: Lesion) -> list[dict[str, Any]]:
    series = lesion_series(db, lesion.id)
    out: list[dict[str, Any]] = []
    for index, (row, captured_at) in enumerate(series):
        reference = db.get(ScaleReference, row.scale_reference_id)
        change = change_between(series[index - 1], series[index]) if index > 0 else None
        out.append(
            {
                "id": str(row.id),
                "observation_id": str(row.observation_id),
                "image_id": str(row.image_id),
                "captured_at": _iso(captured_at),
                "longest_mm": row.longest_mm,
                "sigma_longest_mm": row.sigma_longest_mm,
                "perpendicular_mm": row.perpendicular_mm,
                "sigma_perpendicular_mm": row.sigma_perpendicular_mm,
                "area_mm2": row.area_mm2,
                "sigma_area_mm2": row.sigma_area_mm2,
                "scale_kind": reference.kind if reference else None,
                "scale_mm_per_px": reference.mm_per_px if reference else None,
                "sigma_scale": reference.sigma_scale if reference else None,
                "method": row.method,
                "tilt_deg": row.tilt_deg,
                "flags": list(row.flags or []),
                "shape": row.shape,
                "descriptors": row.details.get("descriptors"),
                "change": None
                if change is None
                else {"delta_mm": change.delta_mm, "sigma_mm": change.sigma_mm, "detectable": change.detectable},
            }
        )
    return out


def _photos(
    db: Session, store: BlobStore, observation: Observation, measured: dict[str, Any] | None
) -> list[dict[str, Any]]:
    images = db.scalars(select(Image).where(Image.observation_id == observation.id, Image.deleted_at.is_(None))).all()
    ranked = sorted(
        images,
        key=lambda i: (
            0 if measured and str(i.id) == measured["image_id"] else 1,
            ROLE_ORDER.index(i.role) if i.role in ROLE_ORDER else len(ROLE_ORDER),
            i.created_at,
        ),
    )
    out: list[dict[str, Any]] = []
    for image in ranked[:PHOTOS_PER_VISIT]:
        preview = db.scalar(select(Rendition).where(Rendition.image_id == image.id, Rendition.kind == "preview"))
        if preview is None:
            continue
        width, height = upright_size(image)
        on_this = measured if measured is not None and str(image.id) == measured["image_id"] else None
        out.append(
            {
                "image_id": str(image.id),
                "role": image.role,
                "path": str(store.path(preview.sha256, derived=True)),
                "upright_width": width,
                "upright_height": height,
                "mm_per_px": on_this["scale_mm_per_px"] if on_this else _scale_of(db, image),
                "flags": list(image.quality_flags or []),
                "shape": on_this["shape"] if on_this else None,
            }
        )
    return out


def _lesion(db: Session, store: BlobStore, lesion: Lesion, number: int, with_visits: bool) -> dict[str, Any]:
    zone = body_map().zone(lesion.zone_code)
    visits = db.scalars(
        select(Observation)
        .where(Observation.lesion_id == lesion.id, Observation.deleted_at.is_(None))
        .order_by(Observation.captured_at.asc())
    ).all()
    last_observed_at = visits[-1].captured_at if visits else None
    if last_observed_at is not None and last_observed_at.tzinfo is None:
        last_observed_at = last_observed_at.replace(tzinfo=UTC)
    next_due = due.next_due(lesion, last_observed_at)
    measurements = _measurements(db, lesion)
    by_visit = {m["observation_id"]: m for m in measurements}
    data: dict[str, Any] = {
        "id": str(lesion.id),
        "number": number,
        "label": lesion.label,
        "zone": lesion.zone_code,
        "view": zone.view if zone else "front",
        "x": lesion.x,
        "y": lesion.y,
        "type": lesion.type,
        "status": lesion.status,
        "first_noticed_on": lesion.first_noticed_on.isoformat() if lesion.first_noticed_on else None,
        "interval_days": lesion.interval_days,
        "notes": lesion.notes,
        "last_observed_at": _iso(last_observed_at),
        "next_due_on": next_due.isoformat() if next_due else None,
        "due": due.is_due(lesion, next_due, utcnow().date()),
        "snoozed_until": lesion.snoozed_until.isoformat() if lesion.snoozed_until else None,
        "measurements": measurements,
        "visits": [],
    }
    if with_visits:
        data["visits"] = [
            {
                "id": str(visit.id),
                "captured_at": _iso(visit.captured_at),
                "local_date": visit.captured_local_date.isoformat(),
                "notes": visit.notes,
                "symptoms": list(visit.symptoms or []),
                "quality_flags": list(visit.quality_flags or []),
                "photos": _photos(db, store, visit, by_visit.get(str(visit.id))),
            }
            for visit in visits
        ]
    return data


def _analyzers(db: Session, image_ids: list[str]) -> dict[str, list[str]]:
    if not image_ids:
        return {}
    rows = db.execute(
        select(Analysis.analyzer, Analysis.version)
        .where(Analysis.target_type == "image", Analysis.target_id.in_([uuid.UUID(i) for i in image_ids]))
        .distinct()
    ).all()
    found: dict[str, set[str]] = {}
    for name, version in rows:
        found.setdefault(name, set()).add(version)
    return {name: sorted(versions) for name, versions in sorted(found.items())}


def _order(lesion: Lesion) -> tuple[int, float, float]:
    zone = body_map().zone(lesion.zone_code)
    return (0 if zone is None or zone.view == "front" else 1, lesion.y, lesion.x)


def gather(
    db: Session,
    store: BlobStore,
    settings: Settings,
    person: Person,
    scope: str,
    lesion_ids: list[str],
    language: str,
    paper: str,
    appointment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A mark's record (`lesion`), the summary of every mark (`profile`), or the summary followed by the records
    of some marks: those of an appointment's checklist (`visit`) or those the person chose (`selection`)."""
    if scope == "lesion":
        lesions = [db.get(Lesion, uuid.UUID(i)) for i in lesion_ids]
        chosen = [lesion for lesion in lesions if lesion is not None and lesion.deleted_at is None]
    else:
        chosen = sorted(
            db.scalars(select(Lesion).where(Lesion.person_id == person.id, Lesion.deleted_at.is_(None))).all(),
            key=_order,
        )
    with_records = set(lesion_ids) if scope in ("visit", "selection") else set()
    lesions_data = [
        _lesion(db, store, lesion, n, with_visits=scope == "lesion" or str(lesion.id) in with_records)
        for n, lesion in enumerate(chosen, 1)
    ]
    images = [
        photo["image_id"] for lesion in lesions_data for visit in lesion["visits"] for photo in visit["photos"]
    ] + [m["image_id"] for lesion in lesions_data for m in lesion["measurements"]]
    return {
        "format": "nevus-report/1",
        "scope": scope,
        "language": language,
        "paper": paper,
        "generated_at": utcnow().isoformat(),
        "timezone": settings.effective_timezone,
        "version": nevus.__version__,
        "person": {"id": str(person.id), "name": person.display_name, "birth_year": person.birth_year},
        "lesions": lesions_data,
        "records": [lesion["id"] for lesion in lesions_data if lesion["id"] in with_records],
        "appointment": appointment,
        "analyzers": _analyzers(db, sorted(set(images))),
    }
