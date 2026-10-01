# SPDX-License-Identifier: AGPL-3.0-only
"""Aligning two photographs, abstaining when unsure, and the comparison pictures behind access checks."""

from __future__ import annotations

import csv
import io
import uuid

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from nevus.cv import align, card_detect
from nevus.cv.card import WINDOW
from nevus.db.models import Analysis
from nevus.domain import purge
from tests.scene import photograph
from tests.synthetic import jpeg, skin
from tests.test_accounts import MEMBER, claim
from tests.test_scale import SAME_ORIGIN, _measure_disc


def _apply(matrix: list[list[float]], points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, np.float64).reshape(-1, 1, 2)
    return np.asarray(cv2.perspectiveTransform(pts, np.asarray(matrix, np.float64))).reshape(-1, 2)


def _moved(image: np.ndarray, angle: float, scale: float, shift: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    """Photo B: photo A rotated, zoomed and shifted. Returns B and the true map from A to B."""
    h, w = image.shape[:2]
    m = np.vstack([cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale), [0, 0, 1]])
    m[0, 2] += shift[0]
    m[1, 2] += shift[1]
    return cv2.warpPerspective(image, m, (w, h), borderMode=cv2.BORDER_REFLECT), m


def test_a_moved_photo_is_aligned_back_onto_the_first() -> None:
    a = skin(1600, 1200, seed=4)
    b, a_to_b = _moved(a, angle=8, scale=1.12, shift=(40, -25))
    result = align.from_features(a, b)
    assert result["status"] == "aligned", result
    assert result["inliers"] >= 100 and result["inlier_ratio"] > 0.5
    probes_a = np.array([[600, 500], [900, 700], [800, 600]], np.float64)
    probes_b = _apply(a_to_b.tolist(), probes_a)
    assert np.abs(_apply(result["matrix"], probes_b) - probes_a).max() < 1.5


def test_full_resolution_is_recovered_when_matching_runs_downscaled() -> None:
    a = skin(3200, 2400, seed=5)
    b, a_to_b = _moved(a, angle=-5, scale=0.95, shift=(-60, 30))
    result = align.from_features(a, b)
    assert result["status"] == "aligned"
    probes_a = np.array([[1600, 1200], [2000, 1500]], np.float64)
    assert np.abs(_apply(result["matrix"], _apply(a_to_b.tolist(), probes_a)) - probes_a).max() < 3.0


def test_two_unrelated_photos_are_not_forced_into_an_alignment() -> None:
    result = align.from_features(skin(1600, 1200, seed=6), skin(1600, 1200, seed=7))
    assert result["status"] == "abstained" and result["matrix"] is None
    assert result["reason"] in align.REASONS


def test_a_featureless_photo_abstains() -> None:
    flat = np.full((1200, 1600, 3), (150, 175, 215), np.uint8)
    result = align.from_features(flat, flat.copy())
    assert result["status"] == "abstained" and result["reason"] == "too_little_detail"


@pytest.mark.parametrize(
    ("matrix", "reason"),
    [
        ([[-1, 0, 1600], [0, 1, 0], [0, 0, 1]], "mirrored"),
        ([[4, 0, 0], [0, 4, 0], [0, 0, 1]], "distance"),
        ([[1, 0, 0], [0, 1, 0], [0.01, 0, 1]], "angle"),
    ],
)
def test_implausible_transforms_are_refused(matrix: list[list[float]], reason: str) -> None:
    assert align._plausible(np.asarray(matrix, np.float64), align.PARAMS) == reason


def test_two_photos_with_the_card_align_through_it() -> None:
    a, _ = photograph(WINDOW, tilt_deg=0, distance_mm=150)
    b, _ = photograph(WINDOW, tilt_deg=12, distance_mm=180)
    card_a, card_b = card_detect.detect(a), card_detect.detect(b)
    result = align.from_cards(card_a["homography"], card_b["homography"])
    assert result["status"] == "aligned" and result["method"] == "card"
    mapped = _apply(result["matrix"], np.array([card_b["centre_px"]]))[0]
    assert np.linalg.norm(mapped - np.array(card_a["centre_px"])) < 2.0


def test_the_difference_map_is_quiet_where_nothing_changed() -> None:
    a = skin(1600, 1200, seed=8)
    changed = a.copy()
    cv2.circle(changed, (400, 300), 60, (40, 50, 80), -1)
    identity = np.eye(3).tolist()
    same = align.difference(a, a.copy(), identity)
    assert same["coverage"] == pytest.approx(1.0, abs=0.01) and same["mean_difference"] < 1.0
    moved = align.difference(a, changed, identity)
    heat = cv2.imdecode(np.frombuffer(moved["heatmap"], np.uint8), cv2.IMREAD_UNCHANGED)
    assert heat.shape[2] == 4
    scale = heat.shape[1] / 1600
    spot = heat[int(300 * scale), int(400 * scale), 3]
    elsewhere = heat[int(900 * scale), int(1300 * scale), 3]
    assert spot > 150 and elsewhere < 30
    overlay = cv2.imdecode(np.frombuffer(moved["overlay"], np.uint8), cv2.IMREAD_UNCHANGED)
    assert overlay.shape[:2] == (moved["height"], moved["width"])  # fully covered: WebP drops the alpha


def test_what_photo_b_does_not_cover_stays_empty() -> None:
    a = skin(1600, 1200, seed=9)
    shifted = [[1.0, 0.0, 400.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]  # B lands 400 px to the right in A
    result = align.difference(a, a.copy(), shifted)
    overlay = cv2.imdecode(np.frombuffer(result["overlay"], np.uint8), cv2.IMREAD_UNCHANGED)
    assert overlay[600, 100, 3] == 0 and overlay[600, 1200, 3] == 255
    assert result["coverage"] == pytest.approx(0.75, abs=0.02)


def _two_visits(client: TestClient) -> tuple[str, str, str, str, str]:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions",
        json={"location": {"zone": "1250", "x": 0.4, "y": 0.25}, "status": "active", "interval_days": 90},
        headers=SAME_ORIGIN,
    ).json()
    ids: list[str] = []
    for tilt, distance in ((0, 150), (10, 170)):
        visit = client.post(f"/api/lesions/{lesion['id']}/observations", json={}, headers=SAME_ORIGIN).json()
        photo, _ = photograph(WINDOW, tilt_deg=tilt, distance_mm=distance)
        image = client.post(
            f"/api/observations/{visit['id']}/images",
            files={"file": ("card.jpg", jpeg(photo, 92), "image/jpeg")},
            data={"role": "with_reference"},
            headers=SAME_ORIGIN,
        ).json()
        ids += [visit["id"], image["id"]]
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    return pid, ids[0], ids[1], ids[2], ids[3]


def test_comparing_two_visits_through_the_api(client: TestClient) -> None:
    claim(client)
    _, _, image_a, _, image_b = _two_visits(client)
    response = client.post("/api/comparisons", json={"image_a": image_a, "image_b": image_b}, headers=SAME_ORIGIN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "aligned" and body["method"] == "card"
    assert body["a"]["scale_kind"] == "card" and body["a"]["mm_per_px"] > 0
    overlay = client.get(body["overlay_url"])
    assert overlay.status_code == 200 and overlay.headers["content-type"] == "image/webp"
    heatmap = client.get(body["heatmap_url"])
    assert heatmap.status_code == 200 and heatmap.headers["content-type"] == "image/webp"
    again = client.post("/api/comparisons", json={"image_a": image_a, "image_b": image_b}, headers=SAME_ORIGIN)
    assert again.json()["id"] == body["id"], "the same pair is not computed twice"


def test_comparison_pictures_need_access_to_both_photos(client: TestClient) -> None:
    claim(client)
    _, _, image_a, _, image_b = _two_visits(client)
    body = client.post("/api/comparisons", json={"image_a": image_a, "image_b": image_b}, headers=SAME_ORIGIN).json()
    assert client.post("/api/users", json=MEMBER, headers=SAME_ORIGIN).status_code == 201
    client.post("/api/auth/logout", headers=SAME_ORIGIN)
    assert client.post("/api/auth/login", json=MEMBER, headers=SAME_ORIGIN).status_code == 200
    assert client.get(body["overlay_url"]).status_code == 404
    refused = client.post("/api/comparisons", json={"image_a": image_a, "image_b": image_b}, headers=SAME_ORIGIN)
    assert refused.status_code == 404


def test_photos_of_two_people_are_not_compared(client: TestClient) -> None:
    claim(client)
    _, _, image_a, _, _ = _two_visits(client)
    _, _, other, _, _ = _two_visits(client)
    response = client.post("/api/comparisons", json={"image_a": image_a, "image_b": other}, headers=SAME_ORIGIN)
    assert response.status_code == 422


def test_purging_a_photo_removes_its_comparisons(client: TestClient) -> None:
    claim(client)
    _, _, image_a, _, image_b = _two_visits(client)
    body = client.post("/api/comparisons", json={"image_a": image_a, "image_b": image_b}, headers=SAME_ORIGIN).json()
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    with factory() as db:
        purge.purge_image(db, uuid.UUID(image_b))
        db.commit()
        assert db.get(Analysis, uuid.UUID(body["id"])) is None


def test_the_measurement_series_downloads_as_csv(client: TestClient) -> None:
    claim(client)
    client.patch("/api/auth/me", json={"card_line_mm": 50.0}, headers=SAME_ORIGIN)
    _, visit_a, image_a, _, _ = _two_visits(client)
    lesion_id = client.get(f"/api/observations/{visit_a}").json()["lesion_id"]
    _measure_disc(client, visit_a, image_a)
    response = client.get(f"/api/lesions/{lesion_id}/measurements.csv")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:3] == ["captured_at", "longest_mm", "sigma_longest_mm"]
    assert len(rows) == 2 and abs(float(rows[1][1]) - 5.0) <= 0.3
