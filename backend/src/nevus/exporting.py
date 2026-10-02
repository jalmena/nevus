# SPDX-License-Identifier: AGPL-3.0-only
"""Complete, encrypted exports of one person or of the whole instance (FR-DAT-02).

The archive is a zip inside an age file: photographs as stored (metadata already removed), every
record as JSON, measurements as CSV, and a README that explains it in English and Spanish. It is
built in a worker process straight into the encrypted file, so nothing unencrypted touches the disk.
"""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import __version__, secretbox
from nevus.agecrypt import AgeWriter
from nevus.config import Settings
from nevus.db.models import Export, Image, Lesion, Measurement, Observation, Person, ScaleReference
from nevus.storage.blobs import BlobStore

README = """neVus export
============

This archive contains everything neVus held for the persons listed in manifest.json at the time
of the export: marks, visits, measurements with their uncertainty, your notes, and the photographs
as stored (with camera metadata such as location already removed).

- persons/<id>/person.json      the person, marks, visits, measurements and scale references
- persons/<id>/measurements.csv one row per measurement, in millimetres
- persons/<id>/images/          the photographs, named by their id

neVus is a personal documentation and measurement aid. It does not diagnose, screen for or assess
the risk of any disease.

Exportación de neVus
====================

Este archivo contiene todo lo que neVus guardaba de las personas que figuran en manifest.json en
el momento de exportar: marcas, visitas, medidas con su incertidumbre, tus notas y las fotos tal y
como se guardaron (sin metadatos de la cámara, como la ubicación).

neVus es una ayuda personal de documentación y medición. No diagnostica, no criba ni evalúa el
riesgo de ninguna enfermedad.
"""

CSV_FIELDS = [
    "measurement_id",
    "lesion_id",
    "lesion_label",
    "zone",
    "visit_id",
    "captured_at",
    "longest_mm",
    "sigma_longest_mm",
    "perpendicular_mm",
    "sigma_perpendicular_mm",
    "area_mm2",
    "sigma_area_mm2",
    "scale",
    "method",
    "tilt_deg",
    "flags",
]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _columns(row: Any, *skip: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for column in row.__table__.columns:
        if column.key in skip:
            continue
        value = getattr(row, column.key)
        out[column.key] = (
            str(value) if isinstance(value, uuid.UUID) else value.isoformat() if hasattr(value, "isoformat") else value
        )
    return out


def plan(db: Session, store: BlobStore, settings: Settings, export: Export) -> dict[str, Any]:
    """Everything the worker needs, read in the main process: records as JSON-ready data, file paths."""
    if export.person_id is not None:
        persons = [p for p in [db.get(Person, export.person_id)] if p is not None and p.deleted_at is None]
    else:
        persons = list(db.scalars(select(Person).where(Person.deleted_at.is_(None)).order_by(Person.created_at)))
    out_persons = []
    files: list[tuple[str, str]] = []
    for person in persons:
        lesions = db.scalars(
            select(Lesion).where(Lesion.person_id == person.id, Lesion.deleted_at.is_(None)).order_by(Lesion.created_at)
        ).all()
        lesion_records = []
        rows_csv = []
        for lesion in lesions:
            visits = db.scalars(
                select(Observation)
                .where(Observation.lesion_id == lesion.id, Observation.deleted_at.is_(None))
                .order_by(Observation.captured_at)
            ).all()
            visit_records = []
            for visit in visits:
                images = db.scalars(
                    select(Image).where(Image.observation_id == visit.id, Image.deleted_at.is_(None))
                ).all()
                measurements = db.scalars(
                    select(Measurement).where(Measurement.observation_id == visit.id, Measurement.deleted_at.is_(None))
                ).all()
                scales = db.scalars(
                    select(ScaleReference).where(
                        ScaleReference.image_id.in_([i.id for i in images]), ScaleReference.deleted_at.is_(None)
                    )
                ).all()
                for image in images:
                    extension = "png" if image.mime == "image/png" else "jpg"
                    files.append((f"persons/{person.id}/images/{image.id}.{extension}", str(store.path(image.sha256))))
                scale_kinds = {s.id: s.kind for s in scales}
                for m in measurements:
                    rows_csv.append(
                        {
                            "measurement_id": str(m.id),
                            "lesion_id": str(lesion.id),
                            "lesion_label": lesion.label or "",
                            "zone": lesion.zone_code,
                            "visit_id": str(visit.id),
                            "captured_at": _iso(visit.captured_at),
                            "longest_mm": m.longest_mm,
                            "sigma_longest_mm": m.sigma_longest_mm,
                            "perpendicular_mm": m.perpendicular_mm,
                            "sigma_perpendicular_mm": m.sigma_perpendicular_mm,
                            "area_mm2": m.area_mm2,
                            "sigma_area_mm2": m.sigma_area_mm2,
                            "scale": scale_kinds.get(m.scale_reference_id, ""),
                            "method": m.method,
                            "tilt_deg": m.tilt_deg if m.tilt_deg is not None else "",
                            "flags": " ".join(m.flags or []),
                        }
                    )
                visit_records.append(
                    {
                        **_columns(visit),
                        "images": [_columns(i) for i in images],
                        "measurements": [_columns(m) for m in measurements],
                        "scale_references": [_columns(s) for s in scales],
                    }
                )
            lesion_records.append({**_columns(lesion), "visits": visit_records})
        out_persons.append({"person": _columns(person), "lesions": lesion_records, "csv": rows_csv})
    passphrase = secretbox.open_(settings.secret_key(), export.sealed_passphrase or "", purpose="export")
    return {
        "export_id": str(export.id),
        "persons": out_persons,
        "files": files,
        "passphrase": passphrase,
        "target_dir": str(settings.exports_dir),
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


def build(value: dict[str, Any]) -> dict[str, Any]:
    """Worker process: write the encrypted zip; nothing unencrypted is ever written to disk."""
    target_dir = Path(value["target_dir"])
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"nevus-export-{value['created_at'][:10]}-{value['export_id'][:8]}.zip.age"
    partial = target_dir / (name + ".partial")
    with (
        open(partial, "wb") as raw,
        AgeWriter(raw, value["passphrase"]) as sealed,
        zipfile.ZipFile(sealed, "w", compression=zipfile.ZIP_DEFLATED) as archive,
    ):
        archive.writestr("README.txt", README)
        manifest = {
            "format": "nevus-export/1",
            "created_at": value["created_at"],
            "nevus_version": __version__,
            "persons": [
                {"id": p["person"]["id"], "display_name": p["person"]["display_name"]} for p in value["persons"]
            ],
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        for entry in value["persons"]:
            pid = entry["person"]["id"]
            person = {"person": entry["person"], "lesions": entry["lesions"]}
            archive.writestr(f"persons/{pid}/person.json", json.dumps(person, indent=2, ensure_ascii=False))
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(entry["csv"])
            archive.writestr(f"persons/{pid}/measurements.csv", buffer.getvalue())
        for archive_path, blob_path in value["files"]:
            archive.write(blob_path, archive_path, compress_type=zipfile.ZIP_STORED)
    final = target_dir / name
    os.replace(partial, final)
    os.chmod(final, 0o640)
    return {"file_name": name, "bytes": final.stat().st_size}
