# SPDX-License-Identifier: AGPL-3.0-only
"""Backups: one encrypted, consistent snapshot of everything neVus owns, and its restore (FR-DAT-03).

SQLite mode: the database copied with SQLite's online backup API (consistent while the app runs),
the server secret, and the blob tree. PostgreSQL mode: the secret and the blob tree with a manifest;
the database itself is the operator's to back up (docs/DEPLOYMENT.md shows a pg_dump example).
Blobs never change after they are written and are only deleted a day after nothing refers to them,
so copying the database first and the blobs second always yields a consistent pair.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from nevus import __version__
from nevus.agecrypt import DEFAULT_WORK_FACTOR, AgeReader, AgeWriter
from nevus.config import Settings
from nevus.db.models import Image, Rendition
from nevus.storage.blobs import sha256_hex

FORMAT = "nevus-backup/1"
NAME_FORMAT = "nevus-backup-%Y%m%dT%H%M%SZ.tar.age"


class RestoreError(RuntimeError):
    pass


def _sqlite_path(settings: Settings) -> Path:
    url = settings.effective_database_url
    return Path(url.split("sqlite:///", 1)[1])


def create(
    settings: Settings,
    passphrase: str,
    *,
    out_dir: Path | None = None,
    now: datetime | None = None,
    work_factor: int = DEFAULT_WORK_FACTOR,
) -> Path:
    out_dir = out_dir or settings.backups_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now(tz=UTC)
    target = out_dir / moment.strftime(NAME_FORMAT)
    partial = target.with_suffix(target.suffix + ".partial")
    manifest: dict[str, Any] = {
        "format": FORMAT,
        "created_at": moment.isoformat(),
        "nevus_version": __version__,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }
    with tempfile.TemporaryDirectory(dir=settings.data_dir) as tmp:
        snapshot: Path | None = None
        if settings.is_sqlite:
            snapshot = Path(tmp) / "nevus.sqlite3"
            source = sqlite3.connect(_sqlite_path(settings))
            destination = sqlite3.connect(snapshot)
            with destination:
                source.backup(destination)
            source.close()
            destination.close()
        else:
            manifest["note"] = "The PostgreSQL database is not included: back it up with pg_dump."
        settings.secret_key()  # make sure the secret exists before it is archived
        with (
            open(partial, "wb") as raw,
            AgeWriter(raw, passphrase, work_factor) as sealed,
            tarfile.open(fileobj=sealed, mode="w|") as tar,
        ):
            data = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(data)
            info.mtime = int(moment.timestamp())
            import io

            tar.addfile(info, io.BytesIO(data))
            if snapshot is not None:
                tar.add(snapshot, "nevus.sqlite3")
            tar.add(settings.secret_key_file or settings.data_dir / "secret.key", "secret.key")
            if settings.blobs_dir.is_dir():
                for kind in ("originals", "derived"):
                    root = settings.blobs_dir / kind
                    if root.is_dir():
                        tar.add(root, f"blobs/{kind}")
    os.replace(partial, target)
    os.chmod(target, 0o640)
    return target


def prune(directory: Path, keep_daily: int = 30, keep_monthly: int = 12, now: datetime | None = None) -> list[Path]:
    """Keep the newest backup of each of the last 30 days and of each of the last 12 months."""
    now = now or datetime.now(tz=UTC)
    backups = []
    for path in directory.glob("nevus-backup-*.tar.age"):
        try:
            when = datetime.strptime(path.name, NAME_FORMAT).replace(tzinfo=UTC)
        except ValueError:
            continue
        backups.append((when, path))
    backups.sort(reverse=True)
    keep: set[Path] = set()
    seen_days: set[str] = set()
    seen_months: set[str] = set()
    for when, path in backups:
        day, month = when.strftime("%Y-%m-%d"), when.strftime("%Y-%m")
        if day not in seen_days and now - when <= timedelta(days=keep_daily):
            seen_days.add(day)
            keep.add(path)
        if month not in seen_months and len(seen_months) < keep_monthly:
            seen_months.add(month)
            keep.add(path)
    removed = [path for _, path in backups if path not in keep]
    for path in removed:
        path.unlink(missing_ok=True)
    return removed


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    return name in ("manifest.json", "nevus.sqlite3", "secret.key") or path.parts[0] == "blobs"


def restore(archive: Path, passphrase: str, data_dir: Path, *, force: bool = False) -> dict[str, Any]:
    """Unpack a backup into an empty data directory (or over one, with force)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    occupied = [p for p in data_dir.iterdir() if p.name not in ("backups", "tmp")]
    if occupied and not force:
        raise RestoreError(f"{data_dir} is not empty; restore into an empty directory or pass --force")
    manifest: dict[str, Any] | None = None
    with (
        open(archive, "rb") as raw,
        AgeReader(raw, passphrase) as sealed,
        tarfile.open(fileobj=sealed, mode="r|") as tar,
    ):
        for member in tar:
            if not _safe_member(member.name) or not (member.isfile() or member.isdir()):
                raise RestoreError(f"unexpected entry in the backup: {member.name}")
            if member.name == "manifest.json":
                extracted = tar.extractfile(member)
                manifest = json.loads(extracted.read()) if extracted else None
                if not manifest or manifest.get("format") != FORMAT:
                    raise RestoreError("not a neVus backup")
                continue
            tar.extract(member, data_dir, filter="data")
    if manifest is None:
        raise RestoreError("the backup has no manifest")
    secret = data_dir / "secret.key"
    if secret.exists():
        secret.chmod(0o600)
    return manifest


def verify(settings: Settings) -> dict[str, int]:
    """Check that every stored photo and rendition exists and still has the hash it is named after."""
    engine = create_engine(settings.effective_database_url)
    counts = {"checked": 0, "missing": 0, "corrupt": 0}
    with Session(engine) as db:
        targets = [(sha, False) for sha in db.scalars(select(Image.sha256))]
        targets += [(sha, True) for sha in db.scalars(select(Rendition.sha256))]
    engine.dispose()
    for sha, derived in targets:
        path = settings.blobs_dir / ("derived" if derived else "originals") / sha[:2] / sha[2:4] / sha
        counts["checked"] += 1
        if not path.is_file():
            counts["missing"] += 1
        elif sha256_hex(path.read_bytes()) != sha:
            counts["corrupt"] += 1
    return counts
