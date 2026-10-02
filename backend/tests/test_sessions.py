# SPDX-License-Identifier: AGPL-3.0-only
"""Full-body sessions: the protocol, zone photos, marks linked to the registry, proposals and matching."""

from __future__ import annotations

import math
import uuid

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from nevus.cv import candidates
from nevus.cv.imageio import decode
from nevus.db.models import Analysis, BodySession, Image
from nevus.domain import purge
from nevus.sessions import PROTOCOL
from tests.synthetic import MONK, _bgr, jpeg
from tests.test_accounts import MEMBER, claim
from tests.test_scale import SAME_ORIGIN


def zone_photo(seed: int, spots: list[tuple[int, int, int]], shift: tuple[float, float, float] = (0, 0, 0)) -> bytes:
    """A region of skin with pores and the given dark spots, optionally re-photographed (dx, dy, degrees)."""
    rng = np.random.default_rng(seed)
    w, h = 2400, 1800
    base = np.array(_bgr(MONK["MST5"]), np.int16)
    img = np.full((h, w, 3), base, np.int16) + rng.normal(0, 6, (h, w, 1)).astype(np.int16)
    for _ in range(w * h // 1500):
        centre = (int(rng.integers(0, w)), int(rng.integers(0, h)))
        cv2.circle(img, centre, int(rng.integers(1, 3)), tuple(int(c * 0.86) for c in base), -1)
    for x, y, r in spots:
        cv2.circle(img, (x, y), r, tuple(int(c * 0.5) for c in base), -1, cv2.LINE_AA)
    picture = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (0, 0), 1.0)
    dx, dy, angle = shift
    if any(shift):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        m[0, 2] += dx
        m[1, 2] += dy
        picture = cv2.warpAffine(picture, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    return jpeg(picture, 92)


SPOTS = [(600, 500, 26), (1500, 420, 20), (1100, 1100, 30), (1800, 1300, 22), (700, 1400, 18)]


def _person(client: TestClient, experimental: bool = False) -> str:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    if experimental:
        client.patch(f"/api/persons/{pid}", json={"experimental_analysis": True}, headers=SAME_ORIGIN)
    return str(pid)


def _upload(client: TestClient, session: str, zone: str, data: bytes) -> dict:  # type: ignore[type-arg]
    response = client.post(
        f"/api/sessions/{session}/zones/{zone}/photo",
        files={"file": ("zone.jpg", data, "image/jpeg")},
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_the_protocol_covers_the_body_and_every_zone_can_be_skipped(client: TestClient) -> None:
    claim(client)
    zones = client.get("/api/sessions/protocol").json()
    assert len(zones) == len(PROTOCOL) == 18
    assert {z["id"] for z in zones if z["sensitive"]} == {"abdomen", "lower-back"}
    pid = _person(client)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()
    assert [z["status"] for z in session["zones"]] == ["pending"] * 18
    skipped = client.post(f"/api/sessions/{session['id']}/zones/abdomen/skip", headers=SAME_ORIGIN).json()
    assert next(z for z in skipped["zones"] if z["zone"] == "abdomen")["status"] == "skipped"
    reopened = client.delete(f"/api/sessions/{session['id']}/zones/abdomen/skip", headers=SAME_ORIGIN).json()
    assert next(z for z in reopened["zones"] if z["zone"] == "abdomen")["status"] == "pending"
    finished = client.post(f"/api/sessions/{session['id']}/finish", headers=SAME_ORIGIN).json()
    assert finished["status"] == "finished" and finished["finished_at"]


def test_marks_on_a_zone_photo_link_to_the_registry(client: TestClient) -> None:
    claim(client)
    pid = _person(client)
    known = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "1250", "x": 0.4, "y": 0.25}}, headers=SAME_ORIGIN
    ).json()["id"]
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    early = client.post(f"/api/sessions/{session}/zones/chest/marks", json={"x": 0.5, "y": 0.5}, headers=SAME_ORIGIN)
    assert early.status_code == 409, "the photo comes first"
    _upload(client, session, "chest", zone_photo(1, SPOTS))
    linked = client.post(
        f"/api/sessions/{session}/zones/chest/marks",
        json={"x": 0.25, "y": 0.28, "lesion_id": known},
        headers=SAME_ORIGIN,
    ).json()
    assert linked["lesion_id"] == known and linked["state"] == "confirmed"
    created = client.post(
        f"/api/sessions/{session}/zones/chest/marks",
        json={"x": 0.62, "y": 0.23, "new_mark": {"zone_code": "1251", "label": "Left one"}},
        headers=SAME_ORIGIN,
    ).json()
    assert client.get(f"/api/lesions/{created['lesion_id']}").json()["label"] == "Left one"
    wrong = client.post(
        f"/api/sessions/{session}/zones/chest/marks",
        json={"x": 0.5, "y": 0.5, "new_mark": {"zone_code": "2300"}},
        headers=SAME_ORIGIN,
    )
    assert wrong.status_code == 422, "the chest photo does not show the lower back"
    crop = client.get(linked["crop_url"])
    assert crop.status_code == 200 and crop.headers["content-type"] == "image/jpeg"
    seen = client.get(f"/api/lesions/{known}/sightings").json()
    assert [s["mark_id"] for s in seen] == [linked["id"]] and seen[0]["zone"] == "chest"
    summary = client.get(f"/api/persons/{pid}/sessions").json()[0]
    assert summary["captured"] == 1 and summary["pending"] == 17 and summary["marks"] == 2


def test_a_retake_replaces_the_photo_and_its_marks(client: TestClient) -> None:
    claim(client)
    pid = _person(client)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    first = _upload(client, session, "chest", zone_photo(1, SPOTS))
    first_image = next(z for z in first["zones"] if z["zone"] == "chest")["image_id"]
    client.post(f"/api/sessions/{session}/zones/chest/marks", json={"x": 0.3, "y": 0.3}, headers=SAME_ORIGIN)
    second = _upload(client, session, "chest", zone_photo(2, SPOTS))
    zone = next(z for z in second["zones"] if z["zone"] == "chest")
    assert zone["image_id"] != first_image and zone["marks"] == []
    assert client.post(f"/api/sessions/{session}/zones/chest/skip", headers=SAME_ORIGIN).status_code == 409
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        assert db.get(Image, uuid.UUID(first_image)).deleted_at is not None, "the earlier photo is in the trash"


def test_viewers_see_sessions_but_do_not_change_them(client: TestClient) -> None:
    claim(client)
    pid = _person(client)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.put(
        f"/api/persons/{pid}/access", json={"username": MEMBER["username"], "role": "viewer"}, headers=SAME_ORIGIN
    )
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get(f"/api/sessions/{session}").json()["can_edit"] is False
    assert client.post(f"/api/sessions/{session}/zones/chest/skip", headers=SAME_ORIGIN).status_code == 403
    assert client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).status_code == 403


def test_spots_are_proposed_only_with_the_experimental_analysis(client: TestClient) -> None:
    claim(client)
    pid = _person(client, experimental=False)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    _upload(client, session, "chest", zone_photo(1, SPOTS))
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    zone = next(z for z in client.get(f"/api/sessions/{session}").json()["zones"] if z["zone"] == "chest")
    assert zone["marks"] == []


def test_proposals_carry_confirmed_marks_over_to_the_next_session(client: TestClient) -> None:
    claim(client)
    pid = _person(client, experimental=True)
    first = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    uploaded = _upload(client, first, "chest", zone_photo(1, SPOTS))
    assert next(z for z in uploaded["zones"] if z["zone"] == "chest")["analysing"] is True
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    chest = next(z for z in client.get(f"/api/sessions/{first}").json()["zones"] if z["zone"] == "chest")
    assert chest["analysing"] is False
    proposed = chest["marks"]
    assert len(proposed) == len(SPOTS) and all(m["state"] == "pending" and m["source"] == "candidate" for m in proposed)
    by_position = sorted(proposed, key=lambda m: (m["x"], m["y"]))
    keep = by_position[:2]
    for index, mark in enumerate(keep):
        response = client.patch(
            f"/api/session-marks/{mark['id']}",
            json={"new_mark": {"zone_code": "1250", "label": f"Mark {index}"}},
            headers=SAME_ORIGIN,
        )
        assert response.json()["state"] == "confirmed"
    client.post(f"/api/sessions/{first}/finish", headers=SAME_ORIGIN)
    lesions = {
        m["lesion_id"]
        for z in client.get(f"/api/sessions/{first}").json()["zones"]
        for m in z["marks"]
        if m["state"] == "confirmed"
    }
    second = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    _upload(client, second, "chest", zone_photo(1, [*SPOTS, (1950, 600, 24)], shift=(60, -40, 3)))
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    marks = next(z for z in client.get(f"/api/sessions/{second}").json()["zones"] if z["zone"] == "chest")["marks"]
    matched = [m for m in marks if m["match"] == "matched"]
    assert {m["lesion_id"] for m in matched} == lesions, "both confirmed marks found again"
    assert sum(m["match"] == "new" for m in marks) == len(SPOTS) - 2 + 1, "the rest, and the new spot"
    pairs = client.get(f"/api/sessions/{second}/compare/{first}").json()
    assert pairs[0]["zone"] == "chest" and pairs[0]["earlier_image_id"] != pairs[0]["later_image_id"]


def test_a_densely_spotted_region_is_lined_up_by_its_pattern(client: TestClient) -> None:
    claim(client)
    pid = _person(client, experimental=True)
    rng = np.random.default_rng(11)
    spots = [(int(rng.integers(250, 2150)), int(rng.integers(200, 1600)), int(rng.integers(14, 28))) for _ in range(30)]
    first = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    _upload(client, first, "upper-back", zone_photo(4, spots))
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    proposed = next(z for z in client.get(f"/api/sessions/{first}").json()["zones"] if z["zone"] == "upper-back")
    for index, mark in enumerate(sorted(proposed["marks"], key=lambda m: (m["x"], m["y"]))[:3]):
        client.patch(
            f"/api/session-marks/{mark['id']}",
            json={"new_mark": {"zone_code": "2250", "label": f"Mark {index}"}},
            headers=SAME_ORIGIN,
        )
    second = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    _upload(client, second, "upper-back", zone_photo(9, spots, shift=(70, -50, 4)))
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    marks = next(z for z in client.get(f"/api/sessions/{second}").json()["zones"] if z["zone"] == "upper-back")["marks"]
    assert sum(m["match"] == "matched" for m in marks) == 3
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        record = db.scalars(
            select(Analysis).where(Analysis.analyzer == candidates.NAME).order_by(Analysis.created_at)
        ).all()[-1]
        assert record.outputs["alignment"]["method"] == "constellation"


def test_spot_detection_gate_across_skin_tones() -> None:
    """The gate MODEL_CARD.md reports: most spots found and no skin texture taken for one."""
    for tone in MONK.values():
        rng = np.random.default_rng(3)
        base = np.array(_bgr(tone), np.int16)
        w, h = 2400, 1800
        img = np.full((h, w, 3), base, np.int16) + rng.normal(0, 6, (h, w, 1)).astype(np.int16)
        for _ in range(w * h // 1500):
            cv2.circle(
                img, (int(rng.integers(0, w)), int(rng.integers(0, h))), 2, tuple(int(c * 0.86) for c in base), -1
            )
        for x, y, r in SPOTS:
            cv2.circle(img, (x, y), r, tuple(int(c * 0.5) for c in base), -1, cv2.LINE_AA)
        for _ in range(8):
            x0 = int(rng.integers(0, w))
            cv2.line(img, (x0, 0), (x0 + int(rng.integers(-300, 300)), h), tuple(int(c * 0.35) for c in base), 3)
        result = candidates.detect(cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (0, 0), 1.0))
        found = [(c["x"] * w, c["y"] * h) for c in result["candidates"]]
        hits = sum(any(math.hypot(fx - x, fy - y) < max(25, r) for fx, fy in found) for x, y, r in SPOTS)
        assert hits >= len(SPOTS) - 1, tone
        assert len(found) <= len(SPOTS) + 1, tone


def test_deleting_and_purging_sessions(client: TestClient) -> None:
    claim(client)
    pid = _person(client)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    zones = _upload(client, session, "chest", zone_photo(1, SPOTS))["zones"]
    image = next(z for z in zones if z["zone"] == "chest")["image_id"]
    assert client.delete(f"/api/sessions/{session}", headers=SAME_ORIGIN).status_code == 204
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        assert db.get(BodySession, uuid.UUID(session)) is None
        assert db.get(Image, uuid.UUID(image)).deleted_at is not None
    other = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        purge.purge_person(db, uuid.UUID(pid))
        db.commit()
        assert db.get(BodySession, uuid.UUID(other)) is None


@pytest.mark.parametrize("zone", [c.id for c in PROTOCOL])
def test_every_capture_zone_covers_known_body_zones(zone: str) -> None:
    from nevus.bodymap import zone_codes
    from nevus.sessions import BY_ID

    assert set(BY_ID[zone].covers) <= zone_codes()


def test_blurring_part_of_a_zone_photo_replaces_it_for_good(client: TestClient) -> None:
    """FR-SES-05: the blurred area is unrecognisable, the rest is untouched, the marks stay, the original is gone."""
    claim(client)
    pid = _person(client)
    session = client.post(f"/api/persons/{pid}/sessions", json={}, headers=SAME_ORIGIN).json()["id"]
    zones = _upload(client, session, "chest", zone_photo(1, SPOTS))["zones"]
    old = next(z for z in zones if z["zone"] == "chest")["image_id"]
    body = {"x": 0.25, "y": 0.28, "new_mark": {"zone_code": "1250", "label": "Kept"}}
    assert client.post(f"/api/sessions/{session}/zones/chest/marks", json=body, headers=SAME_ORIGIN).status_code == 201
    before = decode(client.get(f"/api/images/{old}/full").content)
    store = client.app.state.blob_store  # type: ignore[attr-defined]
    with client.app.state.session_factory() as db:  # type: ignore[attr-defined]
        row = db.get(Image, uuid.UUID(old))
        assert row is not None
        files = [store.path(row.sha256)] + [store.path(r.sha256, derived=True) for r in row.renditions]
    assert all(path.is_file() for path in files)

    bad = client.post(f"/api/sessions/{session}/zones/chest/blur", json={"regions": []}, headers=SAME_ORIGIN)
    assert bad.status_code == 422
    region = {"x": 0.6, "y": 0.6, "width": 0.3, "height": 0.3}  # holds the spot at (0.75, 0.72)
    nothing = client.post(f"/api/sessions/{session}/zones/face/blur", json={"regions": [region]}, headers=SAME_ORIGIN)
    assert nothing.status_code == 409
    response = client.post(f"/api/sessions/{session}/zones/chest/blur", json={"regions": [region]}, headers=SAME_ORIGIN)
    assert response.status_code == 200, response.text
    chest = next(z for z in response.json()["zones"] if z["zone"] == "chest")
    new = chest["image_id"]
    assert new != old and chest["status"] == "captured"
    assert [m["x"] for m in chest["marks"]] == [0.25], "the mark stays with the zone"
    assert client.get(f"/api/images/{old}/full").status_code == 404, "the unblurred photo is gone, not in the trash"
    assert not any(path.exists() for path in files), "and so are its files"

    after = decode(client.get(f"/api/images/{new}/full").content)
    assert after.shape == before.shape
    h, w = after.shape[:2]
    y, x = int(0.722 * h), int(0.75 * w)
    spot_before = before[y - 3 : y + 4, x - 3 : x + 4].mean()
    spot_after = after[y - 3 : y + 4, x - 3 : x + 4].mean()
    assert spot_after - spot_before > 20, "the dark spot inside the area is smeared into the skin"
    outside = (slice(int(0.1 * h), int(0.4 * h)), slice(int(0.1 * w), int(0.4 * w)))
    assert np.abs(before[outside].astype(int) - after[outside].astype(int)).mean() < 4, "the rest is as it was"
