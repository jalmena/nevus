# SPDX-License-Identifier: AGPL-3.0-only
"""The body map asset: MoleMapper's 56 front/back zones on the neVus silhouette."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nevus.bodymap import body_map, zone_codes

FRONTEND_COPY = Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "bodymap" / "zones.json"


def test_both_views_carry_twenty_eight_zones_with_unique_codes() -> None:
    bm = body_map()
    assert bm.version == "nevus-body-map/1"
    assert len(bm.zones) == 56
    assert len(zone_codes()) == 56
    for view in ("front", "back"):
        codes = [z.code for z in bm.zones if z.view == view]
        assert len(codes) == 28
        assert bm.views[view].zones == sorted(codes)  # type: ignore[index]
        assert bm.views[view].silhouette.startswith("M")  # type: ignore[index]


def test_names_and_sides_follow_the_patient_not_the_screen() -> None:
    bm = body_map()
    assert bm.zone("1250").name == "Right Pectoral"  # type: ignore[union-attr]
    assert bm.zone("1250").side == "right"  # type: ignore[union-attr]
    assert bm.zone("2250").name == "Left Upper Back"  # type: ignore[union-attr]
    assert bm.zone("2250").side == "left"  # type: ignore[union-attr]
    assert bm.zone("1200").side == "midline"  # type: ignore[union-attr]
    regions = {z.region for z in bm.zones}
    assert regions == {"head", "trunk", "arm", "leg"}


def test_every_zone_has_geometry_inside_the_view_box() -> None:
    bm = body_map()
    _x0, _y0, width, height = bm.viewBox
    for zone in bm.zones:
        assert zone.path.startswith("M") and zone.path.endswith("Z")
        left, top, right, bottom = zone.bbox
        assert 0 <= left < right <= width and 0 <= top < bottom <= height
        assert left <= zone.anchor[0] <= right and top <= zone.anchor[1] <= bottom


def test_the_frontend_copy_is_identical() -> None:
    if not FRONTEND_COPY.exists():
        pytest.skip("frontend checkout not present")
    ours = json.loads(Path(__file__).resolve().parents[1].joinpath("src/nevus/bodymap/zones.json").read_text())
    theirs = json.loads(FRONTEND_COPY.read_text())
    assert ours == theirs


def test_the_body_map_is_served(client: TestClient) -> None:
    response = client.get("/api/bodymap")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "nevus-body-map/1"
    assert len(payload["zones"]) == 56
    assert "MoleMapper" in payload["attribution"]
