# SPDX-License-Identifier: AGPL-3.0-only
"""Backups: one encrypted, consistent snapshot of everything neVus owns, and its restore (FR-DAT-03).

SQLite mode: the database copied with SQLite's online backup API (consistent while the app runs),
the server secret, and the blob tree. PostgreSQL mode: the secret and the blob tree with a manifest;
the database itself is the operator's to back up (docs/DEPLOYMENT.md shows a pg_dump example).
Blobs never change after they are written and are only deleted a day after nothing refers to them,
so copying the database first and the blobs second always yields a consistent pair.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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


def newest(backups_dir: Path) -> Path | None:
    """The most recent backup in the directory, by the time in its name."""
    if not backups_dir.is_dir():
        return None
    files = sorted(path for path in backups_dir.glob("nevus-backup-*.tar.age") if path.is_file())
    return files[-1] if files else None


def rehearse(settings: Settings, passphrase: str, archive: Path | None = None) -> dict[str, Any]:
    """Prove that a backup (the latest, by default) would restore, without restoring it.

    The archive is decrypted and read through once. Every photograph in it is hashed and must match
    the name it is stored under: blobs are content-addressed, so the archive carries its own
    checksums. The database copy is written to a temporary directory and checked with SQLite's
    integrity check, and every photograph and rendition it refers to must be in the archive. The
    live store is checked too (`verify`). The report says what was checked and what, if anything,
    is wrong; `problems` is empty when the backup is good.
    """
    report: dict[str, Any] = {
        "ok": False,
        "checked_at": datetime.now(tz=UTC).isoformat(),
        "archive": None,
        "problems": [],
    }
    archive = archive or newest(settings.backups_dir)
    if archive is None:
        report["problems"].append("no_backup")
        return report
    report.update({"archive": archive.name, "archive_bytes": archive.stat().st_size})
    manifest: dict[str, Any] | None = None
    in_archive: set[str] = set()
    damaged = 0
    secret_present = False
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=settings.data_dir) as tmp:
        database: Path | None = None
        try:
            with (
                open(archive, "rb") as raw,
                AgeReader(raw, passphrase) as sealed,
                tarfile.open(fileobj=sealed, mode="r|") as tar,
            ):
                for member in tar:
                    if not _safe_member(member.name) or not (member.isfile() or member.isdir()):
                        raise RestoreError(f"unexpected entry in the backup: {member.name}")
                    stream = tar.extractfile(member) if member.isfile() else None
                    if stream is None:
                        continue
                    if member.name == "manifest.json":
                        manifest = json.loads(stream.read())
                        if not manifest or manifest.get("format") != FORMAT:
                            raise RestoreError("not a neVus backup")
                    elif member.name == "nevus.sqlite3":
                        database = Path(tmp) / "nevus.sqlite3"
                        with open(database, "wb") as out:
                            shutil.copyfileobj(stream, out)
                    elif member.name == "secret.key":
                        secret_present = bool(stream.read())
                    elif member.name.startswith("blobs/"):
                        digest = hashlib.sha256()
                        while chunk := stream.read(1 << 20):
                            digest.update(chunk)
                        name = PurePosixPath(member.name).name
                        if digest.hexdigest() != name:
                            damaged += 1
                        in_archive.add(name)
        except Exception as error:  # whatever stops the read is the finding
            report["problems"].append(f"unreadable: {type(error).__name__}: {error}")
            return report
        if manifest is None:
            report["problems"].append("no_manifest")
            return report
        report.update(
            {
                "created_at": manifest.get("created_at"),
                "nevus_version": manifest.get("nevus_version"),
                "database": manifest.get("database"),
                "blobs_in_archive": len(in_archive),
                "blobs_damaged": damaged,
                "secret_present": secret_present,
            }
        )
        if damaged:
            report["problems"].append("damaged_blobs")
        if not secret_present:
            report["problems"].append("no_secret")
        if manifest.get("database") == "sqlite":
            if database is None:
                report["problems"].append("no_database")
            else:
                report.update(_database_report(database, in_archive))
                if report["integrity"] != "ok":
                    report["problems"].append("database_integrity")
                if report["blobs_missing_from_archive"]:
                    report["problems"].append("missing_blobs")
    live = verify(settings)
    report["live_store"] = live
    if live["missing"] or live["corrupt"]:
        report["problems"].append("live_store")
    report["ok"] = not report["problems"]
    return report


def _database_report(database: Path, in_archive: set[str]) -> dict[str, Any]:
    connection = sqlite3.connect(database)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        referenced = {row[0] for row in connection.execute("SELECT sha256 FROM images")}
        referenced |= {row[0] for row in connection.execute("SELECT sha256 FROM renditions")}
        images = int(connection.execute("SELECT count(*) FROM images").fetchone()[0])
    except sqlite3.DatabaseError as error:
        integrity, referenced, images = f"error: {error}", set(), 0
    finally:
        connection.close()
    return {"integrity": integrity, "images": images, "blobs_missing_from_archive": len(referenced - in_archive)}


def describe(report: dict[str, Any]) -> str:
    """The report in a few lines, for the command line and the warning email."""
    verdict = "would restore" if report["ok"] else "has problems"
    lines = [f"Backup {report.get('archive') or '(none)'}: {verdict}"]
    if report.get("created_at"):
        size = float(report.get("archive_bytes") or 0) / 1e6
        lines.append(f"  made {report['created_at']} by neVus {report.get('nevus_version')}, {size:.1f} MB")
    if "blobs_in_archive" in report:
        lines.append(
            f"  {report['blobs_in_archive']} files in the archive, {report.get('blobs_damaged', 0)} damaged, "
            f"{report.get('blobs_missing_from_archive', 0)} missing"
        )
    if report.get("integrity") is not None:
        lines.append(f"  database copy: {report['integrity']}, {report.get('images', 0)} photographs")
    live = report.get("live_store")
    if live:
        lines.append(
            f"  live store: {live['checked']} files checked, {live['missing']} missing, {live['corrupt']} damaged"
        )
    lines.extend(f"  problem: {problem}" for problem in report["problems"])
    return "\n".join(lines)
