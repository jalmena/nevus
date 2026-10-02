# SPDX-License-Identifier: AGPL-3.0-only
"""PDF reports: made in the background, PDF/A-3 with the data attached, private, and gone with what they show."""

from __future__ import annotations

import dataclasses
import json
import re
import uuid
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from nevus.db.models import Job, Report
from nevus.db.types import utcnow
from nevus.domain import purge
from nevus.jobs.registry import KINDS
from nevus.reports import i18n
from nevus.reports.jobs import REPORT_KIND
from nevus.reports.render import _fetcher, css_string
from nevus.reports.tokens import COLOURS
from tests.test_accounts import MEMBER, claim
from tests.test_comparison import _two_visits
from tests.test_scale import SAME_ORIGIN, _measure_disc

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def _streams(pdf: bytes) -> list[bytes]:
    """Every stream of the file, inflated when compressed."""
    out = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        raw = match.group(1)
        try:
            out.append(zlib.decompress(raw))
        except zlib.error:
            out.append(raw)
    return out


def _attached(pdf: bytes) -> dict[str, Any]:
    for stream in _streams(pdf):
        if stream.lstrip().startswith(b"{") and b'"nevus-report/1"' in stream:
            data: dict[str, Any] = json.loads(stream)
            return data
    raise AssertionError("no attached report data")


def _measured_lesion(client: TestClient) -> tuple[str, str, str]:
    claim(client)
    client.patch("/api/auth/me", json={"card_line_mm": 50.0}, headers=SAME_ORIGIN)
    pid, visit_a, image_a, visit_b, image_b = _two_visits(client)
    _measure_disc(client, visit_a, image_a)
    _measure_disc(client, visit_b, image_b)
    lesion_id = client.get(f"/api/observations/{visit_a}").json()["lesion_id"]
    client.patch(f"/api/observations/{visit_b}", json={"notes": 'Itches a bit "now" & then'}, headers=SAME_ORIGIN)
    return pid, lesion_id, image_b


def test_a_mark_report_in_spanish_is_a_pdf_a3_with_its_data(client: TestClient) -> None:
    pid, lesion_id, _ = _measured_lesion(client)
    response = client.post(
        f"/api/persons/{pid}/reports",
        json={"scope": "lesion", "lesion_id": lesion_id, "language": "es", "paper": "letter"},
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued" and response.json()["download_url"] is None
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    report = client.get(f"/api/reports/{response.json()['id']}").json()
    assert report["status"] == "ready" and report["pages"] >= 2, report
    pdf = client.get(report["download_url"])
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["cache-control"] == "no-store"
    body = pdf.content
    assert body.startswith(b"%PDF-")
    assert any(b"612 792" in s for s in _streams(body)), "US Letter"
    assert any(b'pdfaid:part="3"' in s or b"<pdfaid:part>3</pdfaid:part>" in s for s in _streams(body))
    data = _attached(body)
    assert data["language"] == "es" and data["person"]["name"] == "Ana"
    mark = data["lesions"][0]
    assert len(mark["measurements"]) == 2 and mark["measurements"][1]["change"] is not None
    assert mark["visits"][1]["notes"] == 'Itches a bit "now" & then'
    assert all("path" not in photo for visit in mark["visits"] for photo in visit["photos"]), "no server paths"
    assert "scale.card" in data["analyzers"]
    assert client.get(f"/api/persons/{pid}/reports").json()[0]["id"] == report["id"]


def test_a_profile_summary_lists_every_mark(client: TestClient) -> None:
    pid, _, _ = _measured_lesion(client)
    created = client.post(f"/api/persons/{pid}/reports", json={"scope": "profile"}, headers=SAME_ORIGIN).json()
    assert created["language"] == "en", "the requester's language by default"
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    report = client.get(f"/api/reports/{created['id']}").json()
    assert report["status"] == "ready"
    data = _attached(client.get(report["download_url"]).content)
    assert data["scope"] == "profile" and len(data["lesions"]) == 1 and data["lesions"][0]["visits"] == []


def test_a_mark_report_needs_a_mark_of_that_person(client: TestClient) -> None:
    pid, _, _ = _measured_lesion(client)
    assert client.post(f"/api/persons/{pid}/reports", json={"scope": "lesion"}, headers=SAME_ORIGIN).status_code == 422
    other, *_ = _two_visits(client)
    stranger = client.get(f"/api/persons/{other}/lesions").json()[0]["id"]
    refused = client.post(
        f"/api/persons/{pid}/reports", json={"scope": "lesion", "lesion_id": stranger}, headers=SAME_ORIGIN
    )
    assert refused.status_code == 422


def test_reports_are_private_to_those_who_see_the_person(client: TestClient) -> None:
    pid, lesion_id, _ = _measured_lesion(client)
    made = client.post(
        f"/api/persons/{pid}/reports", json={"scope": "lesion", "lesion_id": lesion_id}, headers=SAME_ORIGIN
    ).json()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    assert client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN).status_code == 201
    client.put(
        f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"}, headers=SAME_ORIGIN
    )
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    assert client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN).status_code == 200
    assert client.get(f"/api/reports/{made['id']}/download").status_code == 200, "a viewer may read it"
    assert client.delete(f"/api/reports/{made['id']}", headers=SAME_ORIGIN).status_code == 403
    mine = client.post(f"/api/persons/{pid}/reports", json={"scope": "profile"}, headers=SAME_ORIGIN).json()
    assert client.delete(f"/api/reports/{mine['id']}", headers=SAME_ORIGIN).status_code == 204
    client.put(f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"})
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json={"username": "jose", "password": "correct horse battery"}, headers=SAME_ORIGIN)
    access = client.get(f"/api/persons/{pid}/access").json()
    member_id = next(a["user_id"] for a in access if a["username"] == MEMBER["username"])
    client.delete(f"/api/persons/{pid}/access/{member_id}", headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get(f"/api/reports/{made['id']}").status_code == 404
    assert client.get(f"/api/reports/{made['id']}/download").status_code == 404
    assert client.get(f"/api/persons/{pid}/reports").status_code == 404


def test_purging_what_a_report_shows_removes_the_report(client: TestClient) -> None:
    pid, lesion_id, image_b = _measured_lesion(client)
    for body in ({"scope": "lesion", "lesion_id": lesion_id}, {"scope": "profile"}):
        client.post(f"/api/persons/{pid}/reports", json=body, headers=SAME_ORIGIN)
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    store = client.app.state.blob_store  # type: ignore[attr-defined]
    with factory() as db:
        shas = [row.blob_sha256 for row in db.scalars(select(Report))]
        assert len(shas) == 2 and all(shas)
        assert purge.collect_garbage(db, store, grace_seconds=0) >= 0
        assert all(store.exists(sha, derived=True) for sha in shas), "live reports keep their files"
        purge.purge_image(db, uuid.UUID(image_b))
        db.commit()
        assert db.scalars(select(Report)).all() == [], "a purged photo takes its reports along"
    other = client.post(f"/api/persons/{pid}/reports", json={"scope": "profile"}, headers=SAME_ORIGIN).json()
    with factory() as db:
        purge.purge_person(db, uuid.UUID(pid))
        db.commit()
        assert db.get(Report, uuid.UUID(other["id"])) is None


def test_a_report_that_cannot_be_made_says_so(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    pid, _, _ = _measured_lesion(client)

    def boom(_: Any) -> Any:
        raise RuntimeError("renderer exploded at /secret/path")

    monkeypatch.setitem(KINDS, REPORT_KIND, dataclasses.replace(KINDS[REPORT_KIND], compute=boom))
    made = client.post(f"/api/persons/{pid}/reports", json={"scope": "profile"}, headers=SAME_ORIGIN).json()
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    for _ in range(2):
        client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
        with factory() as db:  # skip the retry delay
            for job in db.scalars(select(Job).where(Job.kind == REPORT_KIND)):
                job.run_after = utcnow() - timedelta(seconds=1)
            db.commit()
    report = client.get(f"/api/reports/{made['id']}").json()
    assert report["status"] == "failed" and report["error"] == "The report could not be made."


def test_spanish_numbers_dates_and_signs() -> None:
    es, en = i18n.Words("es"), i18n.Words("en")
    assert es.mm(5.12, 0.21) == "5,1\u00a0±\u00a00,2\u00a0mm"
    assert es.mm(-0.3, 0.25, sign=True).startswith("\u22120,3")
    assert en.area(19.6, 1.46) == "19.6\u00a0±\u00a01.5\u00a0mm²"
    assert es.day(date(2026, 3, 2)) == "2 de marzo de 2026" and en.day(date(2026, 3, 2)) == "2 March 2026"
    assert es.zone("1250") == "Pectoral derecho"


def test_user_text_cannot_break_out_of_the_page_footer() -> None:
    assert css_string('Ana "A" \\ <style>') == '"Ana \\"A\\" \\\\ \\3C style>"'


def test_reports_load_only_their_own_files(tmp_path: Path) -> None:
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"x")
    fetcher = _fetcher({photo.resolve()})
    for url in (
        "http://example.com/x.png",
        "https://example.com/",
        (tmp_path / "other.jpg").as_uri(),
        "file:///etc/passwd",
    ):
        with pytest.raises(ValueError):
            fetcher.fetch(url)
    assert fetcher.fetch(photo.as_uri()) is not None


@pytest.mark.skipif(not FRONTEND.is_dir(), reason="needs the frontend sources next to the backend")
def test_report_colours_and_zone_names_match_the_app() -> None:
    css = (FRONTEND / "src/design-system/tokens/tokens.css").read_text()
    light = css[: css.index("@media")]
    for name, value in COLOURS.items():
        assert re.search(rf"--color-{re.escape(name)}:\s*{re.escape(value)};", light), name
    for language in i18n.LANGUAGES:
        app = json.loads((FRONTEND / f"src/lib/i18n/locales/{language}.json").read_text())
        assert i18n.zone_names()[language] == app["zones"], language
