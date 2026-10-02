# SPDX-License-Identifier: AGPL-3.0-only
"""The reference card, coins and manual lines, and measurements with their uncertainty.

Gates from docs/design/REFERENCE_CARD_SPEC.md, section 9, on synthetic photographs: detection at
every tilt up to 30 degrees, the 5 mm disc within 0.3 mm inside the tilt limit, and tilt flagged
beyond it.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from nevus import measure
from nevus.cv import card_detect, fit
from nevus.cv.card import STRIP, WINDOW, marker_cells
from nevus.cv.card_sheet import render_sheet
from tests.scene import photograph
from tests.synthetic import jpeg, skin
from tests.test_accounts import claim

SAME_ORIGIN = {"sec-fetch-site": "same-origin"}


def test_marker_cells_have_a_black_border() -> None:
    cells = marker_cells(0)
    assert cells.shape == (6, 6)
    assert cells[0].all() and cells[-1].all() and cells[:, 0].all() and cells[:, -1].all()


@pytest.mark.parametrize("page", ["a4", "letter"])
@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_sheet_is_a_one_page_pdf(page: str, lang: str) -> None:
    pdf = render_sheet(page, lang)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert pdf.count(b"/Type /Page ") == 1
    expected = b"595.276 841.89" if page == "a4" else b"612 792"
    assert expected in pdf


@pytest.mark.parametrize("tilt", [0, 10, 20, 30])
def test_the_card_is_found_and_its_tilt_estimated(tilt: int) -> None:
    photo, _ = photograph(WINDOW, tilt_deg=tilt)
    result = card_detect.detect(photo)
    assert result["found"] and result["card"] == "window" and result["ids"] == [0, 1, 2, 3]
    assert abs(result["tilt_deg"] - tilt) < 2.0
    assert ("tilted" in result["flags"]) == (tilt > 15)


def test_the_strip_is_found() -> None:
    photo, true_px_per_mm = photograph(STRIP, tilt_deg=0)
    result = card_detect.detect(photo)
    assert result["found"] and result["card"] == "strip" and result["ids"] == [4, 5]
    assert result["mm_per_px"] * true_px_per_mm == pytest.approx(1.0, rel=0.02)


def test_scale_error_is_within_two_percent_when_flat() -> None:
    photo, true_px_per_mm = photograph(WINDOW, tilt_deg=0)
    assert card_detect.detect(photo)["mm_per_px"] * true_px_per_mm == pytest.approx(1.0, rel=0.02)


def test_a_card_too_far_away_is_flagged() -> None:
    photo, _ = photograph(WINDOW, distance_mm=1000, focal_px=3000)  # 3 px/mm: 36 px markers
    result = card_detect.detect(photo)
    assert result["found"] and "card_small" in result["flags"]


def test_no_card_means_not_found() -> None:
    assert card_detect.detect(skin(1200, 900))["found"] is False


@pytest.mark.parametrize("tilt", [0, 10, 15])
def test_a_five_millimetre_disc_measures_within_three_tenths(tilt: int) -> None:
    photo, _ = photograph(WINDOW, tilt_deg=tilt, disc_mm=5.0)
    detection = card_detect.detect(photo)
    proposal = fit.propose(photo, *detection["centre_px"], "lesion")
    assert proposal is not None and proposal["outline"]
    result = measure.measure(
        {"type": "outline", "points": proposal["outline"]},
        measure.card_scale(detection, card_line_mm=50.0),
        measure.border_px("assisted", 3000),
    )
    assert abs(result["longest_mm"] - 5.0) <= 0.3
    assert abs(result["perpendicular_mm"] - 5.0) <= 0.3
    assert result["area_mm2"] == pytest.approx(math.pi * 2.5**2, rel=0.15)
    assert 0.05 < result["sigma_longest_mm"] < 0.5


def test_a_coin_is_fitted_from_a_tap() -> None:
    img = np.full((1500, 2000, 3), (150, 175, 215), np.uint8)
    cv2.circle(img, (1000, 750), 180, (120, 140, 160), -1, cv2.LINE_AA)
    cv2.circle(img, (1000, 750), 180, (60, 70, 80), 6, cv2.LINE_AA)
    proposal = fit.propose(img, 1040, 720, "coin")
    assert proposal is not None
    assert proposal["cx"] == pytest.approx(1000, abs=8) and proposal["cy"] == pytest.approx(750, abs=8)
    assert proposal["r"] == pytest.approx(180, rel=0.05)


def test_uncertainty_grows_with_a_coin_and_change_needs_to_exceed_it() -> None:
    coin = measure.coin_scale(r_px=150, diameter_mm=23.25, border_px=2.5)
    card = measure.card_scale(
        {"card": "window", "homography": None, "mm_per_px": 0.05, "sigma_fit": 0.0002, "tilt_deg": 2}, 50.0
    )
    assert coin.sigma_scale > card.sigma_scale, "a coin cannot reveal tilt"
    assert measure.change(4.0, 0.2, 4.3, 0.2)["detectable"] is False
    assert measure.change(4.0, 0.1, 4.6, 0.1)["detectable"] is True


def test_an_unverified_print_is_less_certain_than_a_verified_one() -> None:
    detection = {"card": "window", "homography": None, "mm_per_px": 0.05, "sigma_fit": 0.0002, "tilt_deg": 2}
    assert measure.card_scale(detection, None).sigma_scale > measure.card_scale(detection, 50.0).sigma_scale
    assert measure.card_scale(detection, 49.5).print_factor == pytest.approx(0.99)


def _visit_with_card_photo(client: TestClient, tilt: float = 0.0, disc: float = 5.0) -> tuple[str, str, str]:
    pid = client.post("/api/persons", json={"display_name": "Ana"}, headers=SAME_ORIGIN).json()["id"]
    lesion = client.post(
        f"/api/persons/{pid}/lesions",
        json={"location": {"zone": "1250", "x": 0.4, "y": 0.25}, "status": "active", "interval_days": 90},
        headers=SAME_ORIGIN,
    ).json()
    visit = client.post(f"/api/lesions/{lesion['id']}/observations", json={}, headers=SAME_ORIGIN).json()
    photo, _ = photograph(WINDOW, tilt_deg=tilt, disc_mm=disc)
    image = client.post(
        f"/api/observations/{visit['id']}/images",
        files={"file": ("card.jpg", jpeg(photo, 95), "image/jpeg")},
        data={"role": "with_reference"},
        headers=SAME_ORIGIN,
    ).json()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    return lesion["id"], visit["id"], image["id"]


def _measure_disc(client: TestClient, visit_id: str, image_id: str) -> dict:  # type: ignore[type-arg]
    scale = client.get(f"/api/images/{image_id}/scale").json()
    assert scale["card_checked"] and scale["card"]["found"]
    reference = next(r for r in scale["references"] if r["kind"] == "card")
    cx, cy = scale["card"]["centre_px"]
    proposal = client.post(
        f"/api/images/{image_id}/fit", json={"x": cx, "y": cy, "target": "lesion"}, headers=SAME_ORIGIN
    )
    assert proposal.status_code == 200, proposal.text
    body = {
        "image_id": image_id,
        "scale_reference_id": reference["id"],
        "method": "assisted",
        "shape": {"type": "outline", "points": proposal.json()["outline"]},
    }
    preview = client.post(f"/api/observations/{visit_id}/measurements/preview", json=body, headers=SAME_ORIGIN)
    assert preview.status_code == 200, preview.text
    assert client.get(f"/api/observations/{visit_id}/measurements").json() == [], "a preview stores nothing"
    created = client.post(
        f"/api/observations/{visit_id}/measurements",
        json={
            "image_id": image_id,
            "scale_reference_id": reference["id"],
            "method": "assisted",
            "shape": {"type": "outline", "points": proposal.json()["outline"]},
        },
        headers=SAME_ORIGIN,
    )
    assert created.status_code == 201, created.text
    assert created.json()["longest_mm"] == preview.json()["longest_mm"]
    return dict(created.json())


def test_measuring_through_the_api_with_the_detected_card(client: TestClient) -> None:
    claim(client)
    client.patch("/api/auth/me", json={"card_line_mm": 50.0}, headers=SAME_ORIGIN)
    lesion_id, visit_id, image_id = _visit_with_card_photo(client)
    result = _measure_disc(client, visit_id, image_id)
    assert abs(result["longest_mm"] - 5.0) <= 0.3 and result["scale_kind"] == "card"
    assert result["flags"] == []
    summary = client.get(f"/api/lesions/{lesion_id}").json()
    assert summary["latest_measurement"]["longest_mm"] == result["longest_mm"]
    assert summary["measurement_change"] is None


def test_a_second_visit_reports_change_with_its_uncertainty(client: TestClient) -> None:
    claim(client)
    client.patch("/api/auth/me", json={"card_line_mm": 50.0}, headers=SAME_ORIGIN)
    lesion_id, visit_id, image_id = _visit_with_card_photo(client, disc=5.0)
    _measure_disc(client, visit_id, image_id)
    second = client.post(f"/api/lesions/{lesion_id}/observations", json={}, headers=SAME_ORIGIN).json()
    photo, _ = photograph(WINDOW, tilt_deg=5, disc_mm=5.1)
    image = client.post(
        f"/api/observations/{second['id']}/images",
        files={"file": ("card.jpg", jpeg(photo, 95), "image/jpeg")},
        headers=SAME_ORIGIN,
    ).json()
    client.app.state.jobs.run_until_idle()  # type: ignore[attr-defined]
    _measure_disc(client, second["id"], image["id"])
    series = client.get(f"/api/lesions/{lesion_id}/measurements").json()
    assert len(series) == 2 and series[0]["change"] is None
    change = series[1]["change"]
    assert change["detectable"] is False, "0.1 mm is inside the combined uncertainty"
    assert client.get(f"/api/lesions/{lesion_id}").json()["measurement_change"]["detectable"] is False


def test_a_tilted_card_flags_the_measurement_and_the_photo(client: TestClient) -> None:
    claim(client)
    _, visit_id, image_id = _visit_with_card_photo(client, tilt=25)
    assert "tilted" in client.get(f"/api/images/{image_id}").json()["quality_flags"]
    result = _measure_disc(client, visit_id, image_id)
    assert "tilted" in result["flags"] and "unverified_card" in result["flags"]


def test_a_coin_reference_and_a_manual_line(client: TestClient) -> None:
    claim(client)
    _, visit_id, image_id = _visit_with_card_photo(client)
    coin = client.post(
        f"/api/images/{image_id}/scale-references",
        json={"kind": "coin", "cx": 400, "cy": 400, "r": 120, "denomination": "1e"},
        headers=SAME_ORIGIN,
    )
    assert coin.status_code == 201 and coin.json()["mm_per_px"] == pytest.approx(23.25 / 240)
    line = client.post(
        f"/api/images/{image_id}/scale-references",
        json={"kind": "manual", "x1": 100, "y1": 100, "x2": 600, "y2": 100, "length_mm": 25},
        headers=SAME_ORIGIN,
    )
    assert line.status_code == 201 and line.json()["mm_per_px"] == pytest.approx(0.05)
    measured = client.post(
        f"/api/observations/{visit_id}/measurements",
        json={
            "image_id": image_id,
            "scale_reference_id": line.json()["id"],
            "method": "manual",
            "shape": {"type": "circle", "cx": 1500, "cy": 1125, "r": 50},
        },
        headers=SAME_ORIGIN,
    ).json()
    assert measured["longest_mm"] == pytest.approx(5.0, rel=0.01) and "tilt_unknown" in measured["flags"]
    assert client.delete(f"/api/measurements/{measured['id']}", headers=SAME_ORIGIN).status_code == 204


def test_the_reference_card_downloads(client: TestClient) -> None:
    claim(client)
    response = client.get("/api/reference-card?page=letter&lang=es")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
