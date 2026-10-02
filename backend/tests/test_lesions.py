# SPDX-License-Identifier: AGPL-3.0-only
"""Lesions and observations: placing marks on the body map, visiting them, photographing them, trashing them."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from tests.test_accounts import MEMBER, claim
from tests.test_images import jpeg_with_metadata

SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


def person(client: TestClient, name: str = "Ana") -> str:
    response = client.post("/api/persons", json={"display_name": name}, headers=SAME_ORIGIN)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def lesion(client: TestClient, person_id: str, **overrides: object) -> dict:  # type: ignore[type-arg]
    body: dict[str, object] = {"location": {"zone": "1250", "x": 0.4, "y": 0.25}, "label": "Chest mark"}
    body.update(overrides)
    response = client.post(f"/api/persons/{person_id}/lesions", json=body, headers=SAME_ORIGIN)
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_a_lesion_is_a_zone_plus_a_point_and_gets_a_due_date(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid, first_noticed_on="2026-06-01", interval_days=90)
    assert created["type"] == "mole" and created["status"] == "active"
    assert created["location"] == {
        "zone": "1250",
        "x": 0.4,
        "y": 0.25,
        "body_map_version": "nevus-body-map/1",
        "view": "front",
        "side": "right",
    }
    assert created["observation_count"] == 0 and created["last_observed_at"] is None
    assert created["next_due_on"] == "2026-08-30" and created["due"] is True
    listed = client.get(f"/api/persons/{pid}/lesions").json()
    assert [entry["id"] for entry in listed] == [created["id"]]


def test_unknown_zones_and_points_outside_the_map_are_refused(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    bad_zone = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "9999", "x": 0.5, "y": 0.5}}, headers=SAME_ORIGIN
    )
    assert bad_zone.status_code == 422
    outside = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "1250", "x": 1.2, "y": 0.5}}, headers=SAME_ORIGIN
    )
    assert outside.status_code == 422
    head_detail = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "3171", "x": 0.5, "y": 0.5}}, headers=SAME_ORIGIN
    )
    assert head_detail.status_code == 422, "head-detail zones have no silhouette yet"


def test_editing_moves_relabels_and_closes_a_lesion(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid)
    moved = client.patch(
        f"/api/lesions/{created['id']}",
        json={
            "location": {"zone": "2250", "x": 0.6, "y": 0.3},
            "label": "  Upper back  ",
            "tags": ["watch", "watch", " new "],
        },
        headers=SAME_ORIGIN,
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["location"]["zone"] == "2250"
    assert body["location"]["view"] == "back" and body["location"]["side"] == "left"
    assert body["label"] == "Upper back" and body["tags"] == ["watch", "new"]
    removed = client.patch(f"/api/lesions/{created['id']}", json={"status": "removed"}, headers=SAME_ORIGIN).json()
    assert removed["status"] == "removed" and removed["next_due_on"] is None and removed["due"] is False


def test_observations_carry_the_local_date_photos_and_symptoms(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid, first_noticed_on="2026-01-15")
    late_night = datetime(2026, 9, 12, 23, 30, tzinfo=UTC)  # 01:30 on the 13th in Madrid
    response = client.post(
        f"/api/lesions/{created['id']}/observations",
        json={
            "captured_at": late_night.isoformat(),
            "captured_tz": "Europe/Madrid",
            "notes": "Looks the same to me.",
            "symptoms": ["itching"],
        },
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 201, response.text
    observation = response.json()
    assert observation["captured_local_date"] == "2026-09-13"
    assert observation["symptoms"] == ["itching"] and observation["images"] == []

    upload = client.post(
        f"/api/observations/{observation['id']}/images",
        files={"file": ("photo.jpg", jpeg_with_metadata(), "image/jpeg")},
        data={"role": "with_reference"},
        headers=SAME_ORIGIN,
    )
    assert upload.status_code == 201, upload.text
    image = upload.json()
    assert image["observation_id"] == observation["id"] and image["person_id"] == pid
    assert image["captured_at"].startswith("2026-09-12T10:41:07"), "the photo's own capture time wins over the visit's"

    listed = client.get(f"/api/lesions/{created['id']}/observations").json()
    assert len(listed) == 1 and [i["id"] for i in listed[0]["images"]] == [image["id"]]
    summary = client.get(f"/api/lesions/{created['id']}").json()
    assert summary["observation_count"] == 1
    assert summary["last_observed_at"].startswith("2026-09-12T23:30")
    assert summary["next_due_on"] == "2026-12-11" and summary["latest_image_id"] == image["id"]
    assert summary["due"] is (date(2026, 12, 11) <= datetime.now(UTC).date())


def test_trashing_an_observation_or_a_lesion_hides_its_photos_too(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid)
    observation = client.post(f"/api/lesions/{created['id']}/observations", json={}, headers=SAME_ORIGIN).json()
    image = client.post(
        f"/api/observations/{observation['id']}/images",
        files={"file": ("photo.jpg", jpeg_with_metadata(), "image/jpeg")},
        headers=SAME_ORIGIN,
    ).json()
    assert client.get(f"/api/images/{image['id']}").status_code == 200
    assert client.delete(f"/api/observations/{observation['id']}", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/observations/{observation['id']}").status_code == 404
    assert client.get(f"/api/images/{image['id']}").status_code == 404
    assert client.get(f"/api/persons/{pid}/images").json() == []

    second = client.post(f"/api/lesions/{created['id']}/observations", json={}, headers=SAME_ORIGIN).json()
    assert client.delete(f"/api/lesions/{created['id']}", headers=SAME_ORIGIN).status_code == 204
    assert client.get(f"/api/lesions/{created['id']}").status_code == 404
    assert client.get(f"/api/observations/{second['id']}").status_code == 404
    assert client.get(f"/api/persons/{pid}/lesions").json() == []


def test_viewers_read_but_do_not_write(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid)
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    grant = {"username": MEMBER["username"], "role": "viewer"}
    client.put(f"/api/persons/{pid}/access", json=grant, headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    assert client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN).status_code == 200
    assert client.get(f"/api/persons/{pid}/lesions").status_code == 200
    assert client.get(f"/api/lesions/{created['id']}/observations").status_code == 200
    denied = client.post(
        f"/api/persons/{pid}/lesions", json={"location": {"zone": "1250", "x": 0.5, "y": 0.5}}, headers=SAME_ORIGIN
    )
    assert denied.status_code == 403
    assert client.patch(f"/api/lesions/{created['id']}", json={"label": "x"}, headers=SAME_ORIGIN).status_code == 403
    assert client.post(f"/api/lesions/{created['id']}/observations", json={}, headers=SAME_ORIGIN).status_code == 403
    assert client.delete(f"/api/lesions/{created['id']}", headers=SAME_ORIGIN).status_code == 403


def test_a_stranger_sees_nothing(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid)
    client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN)
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN)
    assert client.get(f"/api/persons/{pid}/lesions").status_code == 404
    assert client.get(f"/api/lesions/{created['id']}").status_code == 404


def test_due_dates_follow_the_last_visit(client: TestClient) -> None:
    claim(client)
    pid = person(client)
    created = lesion(client, pid, interval_days=30)
    recent = datetime.now(UTC) - timedelta(days=3)
    client.post(
        f"/api/lesions/{created['id']}/observations", json={"captured_at": recent.isoformat()}, headers=SAME_ORIGIN
    )
    summary = client.get(f"/api/lesions/{created['id']}").json()
    assert summary["next_due_on"] == (recent.date() + timedelta(days=30)).isoformat()
    assert summary["due"] is False


def test_client_minted_identifiers_make_retries_harmless(client: TestClient) -> None:
    """The offline queue may send the same visit and photo twice; nothing is duplicated."""
    import uuid as _uuid

    claim(client)
    pid = person(client)
    created = lesion(client, pid)
    visit_id = str(_uuid.uuid4())
    first = client.post(
        f"/api/lesions/{created['id']}/observations", json={"id": visit_id, "notes": "offline"}, headers=SAME_ORIGIN
    )
    again = client.post(
        f"/api/lesions/{created['id']}/observations", json={"id": visit_id, "notes": "offline"}, headers=SAME_ORIGIN
    )
    assert (
        first.status_code == 201 and again.status_code == 201 and first.json()["id"] == again.json()["id"] == visit_id
    )
    photo_id = str(_uuid.uuid4())
    for _ in range(2):
        response = client.post(
            f"/api/observations/{visit_id}/images",
            files={"file": ("photo.jpg", jpeg_with_metadata(), "image/jpeg")},
            data={"client_id": photo_id},
            headers=SAME_ORIGIN,
        )
        assert response.status_code == 201 and response.json()["id"] == photo_id
    assert len(client.get(f"/api/lesions/{created['id']}/observations").json()[0]["images"]) == 1
    other = lesion(client, pid, label="Other")
    clash = client.post(f"/api/lesions/{other['id']}/observations", json={"id": visit_id}, headers=SAME_ORIGIN)
    assert clash.status_code == 409
