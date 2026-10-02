# SPDX-License-Identifier: AGPL-3.0-only
"""Trash, purge, exports and backups: what was deleted comes back or goes for good, and nothing is lost."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pyrage
from fastapi.testclient import TestClient
from sqlalchemy import select

from nevus import backup
from nevus.config import Settings
from nevus.db.models import Image, Lesion
from nevus.jobs.registry import JobContext
from nevus.maintenance import daily_housekeeping, schedule_backup, schedule_verification
from tests.synthetic import jpeg, skin
from tests.test_accounts import ADMIN, claim

SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


def _setup(client: TestClient) -> dict[str, str]:
    claim(client)
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions",
        json={
            "label": "Chest",
            "location": {"zone": "1250", "x": 0.4, "y": 0.25},
            "status": "active",
            "interval_days": 90,
        },
        headers=SAME_ORIGIN,
    ).json()
    visit = client.post(
        f"/api/lesions/{lesion['id']}/observations", json={"notes": "first"}, headers=SAME_ORIGIN
    ).json()
    image = client.post(
        f"/api/observations/{visit['id']}/images",
        files={"file": ("p.jpg", jpeg(skin(1600, 1200)), "image/jpeg")},
        headers=SAME_ORIGIN,
    ).json()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    return {"person": pid, "lesion": lesion["id"], "visit": visit["id"], "image": image["id"]}


def _sudo(client: TestClient) -> None:
    assert client.post("/api/auth/sudo", json={"password": ADMIN["password"]}, headers=SAME_ORIGIN).status_code == 200


def _ctx(client: TestClient, settings: Any) -> Any:
    return client.app.state.session_factory, client.app.state.blob_store  # type: ignore[attr-defined]


def test_a_deleted_mark_comes_back_with_its_visits_and_photos(client: TestClient) -> None:
    ids = _setup(client)
    assert client.delete(f"/api/lesions/{ids['lesion']}", headers=SAME_ORIGIN).status_code == 204
    trash = client.get("/api/trash").json()
    assert [(t["kind"], t["label"]) for t in trash] == [("lesion", "Chest")], "children travel with their parent"
    assert client.post(f"/api/trash/lesion/{ids['lesion']}/restore", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/lesions/{ids['lesion']}").json()["observation_count"] == 1
    assert client.get(f"/api/images/{ids['image']}").status_code == 200
    assert client.get("/api/trash").json() == []


def test_a_visit_cannot_come_back_before_its_mark(client: TestClient) -> None:
    ids = _setup(client)
    client.delete(f"/api/observations/{ids['visit']}", headers=SAME_ORIGIN)
    client.delete(f"/api/lesions/{ids['lesion']}", headers=SAME_ORIGIN)
    assert client.post(f"/api/trash/observation/{ids['visit']}/restore", headers=SAME_ORIGIN).status_code == 409


def test_purging_now_needs_the_password_and_removes_the_files(client: TestClient, settings: Any) -> None:
    ids = _setup(client)
    client.delete(f"/api/lesions/{ids['lesion']}", headers=SAME_ORIGIN)
    refused = client.delete(f"/api/trash/lesion/{ids['lesion']}", headers=SAME_ORIGIN)
    assert refused.status_code == 403 and refused.headers.get("x-sudo-required") == "1"
    _sudo(client)
    assert client.delete(f"/api/trash/lesion/{ids['lesion']}", headers=SAME_ORIGIN).status_code == 204
    factory, store = _ctx(client, settings)
    with factory() as db:
        assert db.get(Lesion, __import__("uuid").UUID(ids["lesion"])) is None
        assert db.scalars(select(Image)).all() == []
    originals = list((settings.blobs_dir / "originals").glob("*/*/*"))
    assert originals, "the file outlives its row for the grace period"
    with factory() as db:
        from nevus.domain.purge import collect_garbage

        assert collect_garbage(db, store, grace_seconds=0) >= 1
    assert list((settings.blobs_dir / "originals").glob("*/*/*")) == []


def test_the_daily_purge_takes_what_is_older_than_the_trash_period(client: TestClient, settings: Any) -> None:
    ids = _setup(client)
    client.delete(f"/api/observations/{ids['visit']}", headers=SAME_ORIGIN)
    factory, store = _ctx(client, settings)
    with factory() as db:
        from nevus.db.models import Observation

        visit = db.get(Observation, __import__("uuid").UUID(ids["visit"]))
        visit.deleted_at = datetime.now(UTC) - timedelta(days=31)
        db.commit()
    with factory() as db:
        daily_housekeeping(JobContext(db, store, settings))
        db.commit()
    assert client.get("/api/trash").json() == []
    assert client.get(f"/api/lesions/{ids['lesion']}").json()["observation_count"] == 0


def test_a_profile_purge_leaves_nothing(client: TestClient, settings: Any) -> None:
    ids = _setup(client)
    _sudo(client)
    assert client.delete(f"/api/persons/{ids['person']}/purge", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/persons/{ids['person']}").status_code == 404
    factory, _ = _ctx(client, settings)
    with factory() as db:
        assert db.scalars(select(Lesion)).all() == [] and db.scalars(select(Image)).all() == []


def test_an_export_is_an_encrypted_zip_with_everything(client: TestClient) -> None:
    ids = _setup(client)
    body = {"person_id": ids["person"], "passphrase": "export passphrase 1"}
    assert client.post("/api/exports", json=body, headers=SAME_ORIGIN).status_code == 403, "needs sudo"
    _sudo(client)
    created = client.post("/api/exports", json=body, headers=SAME_ORIGIN)
    assert created.status_code == 202, created.text
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    export = client.get("/api/exports").json()[0]
    assert export["status"] == "ready" and export["bytes"] > 0
    data = client.get(f"/api/exports/{export['id']}/download").content
    archive = zipfile.ZipFile(io.BytesIO(pyrage.passphrase.decrypt(data, "export passphrase 1")))
    names = set(archive.namelist())
    pid = ids["person"]
    assert {"README.txt", "manifest.json", f"persons/{pid}/person.json", f"persons/{pid}/measurements.csv"} <= names
    assert f"persons/{pid}/images/{ids['image']}.jpg" in names
    person = json.loads(archive.read(f"persons/{pid}/person.json"))
    assert person["lesions"][0]["label"] == "Chest" and person["lesions"][0]["visits"][0]["notes"] == "first"
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        from nevus.db.models import Export

        assert db.scalars(select(Export)).one().sealed_passphrase is None, "the passphrase is forgotten"


def test_backup_wipe_restore_round_trip(client: TestClient, settings: Any, tmp_path: Path) -> None:
    ids = _setup(client)
    archive = backup.create(settings, "backup passphrase 1", out_dir=tmp_path / "out", work_factor=10)
    assert pyrage.passphrase.decrypt(archive.read_bytes(), "backup passphrase 1")[:100], "standard age"
    target = tmp_path / "restored"
    manifest = backup.restore(archive, "backup passphrase 1", target)
    assert manifest["format"] == "nevus-backup/1"
    assert manifest["database"] == ("sqlite" if settings.is_sqlite else "postgresql")
    assert (target / "secret.key").read_bytes() == settings.secret_key()
    # A PostgreSQL database is not in the archive (pg_dump backs it up), so the restored files use it as it is.
    database = None if settings.is_sqlite else settings.database_url
    restored = settings.model_copy(update={"data_dir": target, "database_url": database})
    assert backup.verify(restored) == {"checked": 4, "missing": 0, "corrupt": 0}
    from nevus.app import create_app

    with TestClient(create_app(restored), base_url="http://localhost") as again:
        assert again.post("/api/auth/login", json=ADMIN, headers=SAME_ORIGIN).status_code == 200
        assert again.get(f"/api/lesions/{ids['lesion']}").json()["label"] == "Chest"
        assert again.get(f"/api/images/{ids['image']}/original").status_code == 200


def test_restore_refuses_a_non_empty_directory_and_a_wrong_passphrase(settings: Any, tmp_path: Path) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    archive = backup.create(settings, "right passphrase 1", out_dir=tmp_path / "out", work_factor=10)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "something").write_text("x")
    import pytest

    with pytest.raises(backup.RestoreError):
        backup.restore(archive, "right passphrase 1", busy)
    with pytest.raises(ValueError):
        backup.restore(archive, "wrong passphrase", tmp_path / "empty")


def test_retention_keeps_thirty_days_and_twelve_months(tmp_path: Path) -> None:
    now = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
    for days in range(0, 400, 1):
        moment = now - timedelta(days=days)
        (tmp_path / moment.strftime(backup.NAME_FORMAT)).write_bytes(b"")
    backup.prune(tmp_path, now=now)
    kept = sorted(tmp_path.iterdir())
    assert 30 <= len(kept) <= 30 + 12


def test_the_nightly_backup_is_queued_once_after_the_hour(client: TestClient, settings: Any) -> None:
    _setup(client)
    live = settings.model_copy(update={"backup_passphrase": "nightly passphrase"})
    factory, store = _ctx(client, settings)
    with factory() as db:
        ctx = JobContext(db, store, live)
        assert schedule_backup(ctx, now=datetime(2026, 10, 1, 2, 0, tzinfo=UTC)) is False
        assert schedule_backup(ctx, now=datetime(2026, 10, 1, 3, 30, tzinfo=UTC)) is True
        assert schedule_backup(ctx, now=datetime(2026, 10, 1, 4, 0, tzinfo=UTC)) is False
        db.commit()


def test_usage_reports_the_soft_quota(client: TestClient, settings: Any) -> None:
    ids = _setup(client)
    usage = client.get(f"/api/persons/{ids['person']}/usage").json()
    assert usage["images"] == 1 and usage["bytes"] > 0 and usage["quota_bytes"] is None and usage["over_quota"] is False


def test_the_latest_backup_is_read_back_and_damage_is_found(client: TestClient, settings: Any, tmp_path: Path) -> None:
    _setup(client)
    archive = backup.create(settings, "backup passphrase 1", work_factor=10)
    report = backup.rehearse(settings, "backup passphrase 1")
    assert report["ok"] is True and report["problems"] == [], report
    assert report["archive"] == archive.name and report["blobs_in_archive"] == 4 and report["blobs_damaged"] == 0
    assert report["secret_present"] is True
    if settings.is_sqlite:
        # The archive holds a copy of the database: it is opened, checked, and read for what it refers to.
        assert report["database"] == "sqlite" and report["integrity"] == "ok"
        assert report["images"] == 1 and report["blobs_missing_from_archive"] == 0
    else:
        # PostgreSQL is backed up by its own tools; the archive carries the photographs and the secret.
        assert report["database"] == "postgresql" and report["integrity"] is None
    assert report["live_store"] == {"checked": 4, "missing": 0, "corrupt": 0}
    assert "would restore" in backup.describe(report)

    # A photograph damaged on disk goes into the next backup damaged, and both are reported.
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        sha = db.scalar(select(Image.sha256))
    assert sha is not None
    (settings.blobs_dir / "originals" / sha[:2] / sha[2:4] / sha).write_bytes(b"not the photograph any more")
    later = backup.create(
        settings, "backup passphrase 1", work_factor=10, now=datetime.now(tz=UTC) + timedelta(seconds=1)
    )
    report = backup.rehearse(settings, "backup passphrase 1")
    assert report["archive"] == later.name and report["ok"] is False
    assert report["blobs_damaged"] == 1 and "damaged_blobs" in report["problems"] and "live_store" in report["problems"]
    assert "problem: damaged_blobs" in backup.describe(report)

    wrong = backup.rehearse(settings, "wrong passphrase")
    assert wrong["ok"] is False and wrong["problems"][0].startswith("unreadable:")
    none = backup.rehearse(Settings(data_dir=tmp_path / "elsewhere", log_level="warning"), "any")
    assert none["problems"] == ["no_backup"]


def test_the_backup_is_verified_weekly_and_on_demand(client: TestClient, settings: Any) -> None:
    _setup(client)
    settings.backup_passphrase = "backup passphrase 1"  # the app and its runner hold this same object
    backup.create(settings, "backup passphrase 1", work_factor=10)
    factory, store = _ctx(client, settings)
    zone = ZoneInfo(settings.effective_timezone)
    early = datetime(2026, 10, 4, settings.backup_hour, 30, tzinfo=zone)
    later = early.replace(hour=settings.backup_hour + 2)
    with factory() as db:
        ctx = JobContext(db, store, settings)
        assert schedule_verification(ctx, early) is False, "the night's backup may still be running"
        assert schedule_verification(ctx, later) is True
        assert schedule_verification(ctx, later) is False, "once a day"
        db.commit()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]

    status = client.get("/api/admin/backups").json()
    assert status["enabled"] is True and status["count"] == 1 and status["latest"]["file"].startswith("nevus-backup-")
    assert status["verification"]["ok"] is True and status["verification"]["problems"] == []
    assert status["backup_queued"] is False and status["verification_queued"] is False
    with factory() as db:
        ctx = JobContext(db, store, settings)
        assert schedule_verification(ctx, later + timedelta(days=1)) is False, "checked less than a week ago"
        assert schedule_verification(ctx, later + timedelta(days=8)) is True
        db.rollback()

    assert client.post("/api/admin/backups/verify", headers=SAME_ORIGIN).status_code == 202
    assert client.post("/api/admin/backups/run", headers=SAME_ORIGIN).status_code == 202
    status = client.get("/api/admin/backups").json()
    assert status["backup_queued"] is True and status["verification_queued"] is True

    settings.backup_passphrase = None
    assert client.post("/api/admin/backups/verify", headers=SAME_ORIGIN).status_code == 409
    assert client.get("/api/admin/backups").json()["enabled"] is False
