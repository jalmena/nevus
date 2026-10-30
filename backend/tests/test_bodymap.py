# SPDX-License-Identifier: AGPL-3.0-only
"""The body map asset: MoleMapper's 56 front/back zones on the neVus silhouette."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nevus.bodymap import body_map, zone_codes

FRONTEND_COPY = Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "bodymap" / "zones.json"


def test_body_views_carry_twenty_eight_zones_and_the_detail_views_theirs() -> None:
    bm = body_map()
    assert bm.version == "nevus-body-map/4"
    assert len(bm.zones) == 79
    assert len(zone_codes()) == 79
    for view, count in (("front", 35), ("back", 30), ("head", 6), ("hands", 4), ("feet", 4)):
        codes = [z.code for z in bm.zones if z.view == view]
        assert len(codes) == count
        assert bm.views[view].zones == sorted(codes)  # type: ignore[index]
        assert bm.views[view].silhouette.startswith("M")  # type: ignore[index]


def test_names_and_sides_follow_the_patient_not_the_screen() -> None:
    bm = body_map()
    assert bm.zone("1250").name == "Right Pectoral"  # type: ignore[union-attr]
    assert bm.zone("1250").side == "right"  # type: ignore[union-attr]
    assert bm.zone("2250").name == "Left Dorsal Region"  # type: ignore[union-attr]
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
    assert payload["version"] == "nevus-body-map/4"
    assert len(payload["zones"]) == 79
    assert "MoleMapper" in payload["attribution"]


def test_hands_and_feet_are_seen_as_ones_own() -> None:
    """Backs of the hands and tops of the feet above, palms and soles below, the left one on the left."""
    bm = body_map()

    def box(code: str) -> tuple[float, float, float, float]:
        return bm.zone(code).bbox  # type: ignore[union-attr]

    for upper, lower in (("3221", "3211"), ("3220", "3210"), ("3321", "3311"), ("3320", "3310")):
        assert box(upper)[3] < box(lower)[1]
    for left, right in (("3221", "3220"), ("3211", "3210"), ("3321", "3320"), ("3311", "3310")):
        assert box(left)[2] < box(right)[0]
        assert bm.zone(left).side == "left" and bm.zone(right).side == "right"  # type: ignore[union-attr]


def _migration():  # type: ignore[no-untyped-def]
    path = next(Path(__file__).resolve().parents[1].joinpath("alembic/versions").glob("*_body_map_4.py"))
    spec = importlib.util.spec_from_file_location("body_map_4", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_marks_on_map_three_keep_their_place_on_the_hand() -> None:
    migration = _migration()
    bm = body_map()
    width, height = bm.viewBox[2], bm.viewBox[3]
    for code, (old, new, mirrored) in migration.MOVED.items():
        left, top, right, bottom = bm.zone(code).bbox  # type: ignore[union-attr]
        if code in ("3170", "3172"):
            # Seen from above and from behind, the ears stand out of the head the points are carried onto.
            assert left < new[0] and right > new[2] and (top, bottom) == (new[1], new[3])
        else:
            assert (left, top, right, bottom) == new
        # Near the old box's left edge, halfway down: the thumb of the old right palm, for example.
        x, y = (old[0] + 0.05 * (old[2] - old[0])) / width, (old[1] + 0.5 * (old[3] - old[1])) / height
        nx, ny = migration.carry(x, y, old, new, mirrored)
        u = (nx * width - new[0]) / (new[2] - new[0])
        assert u > 0.9 if mirrored else u < 0.1
        assert abs((ny * height - new[1]) / (new[3] - new[1]) - 0.5) < 0.01
        back = migration.carry(nx, ny, new, old, mirrored)
        assert abs(back[0] - x) < 2e-4 and abs(back[1] - y) < 2e-4


def test_landmarks_are_drawn_where_they_belong() -> None:
    """Nipples and navel on the front, the cleft on the back, the face on the head, nails on backs and tops only."""
    bm = body_map()
    for view in ("front", "back", "head", "hands", "feet"):
        assert bm.views[view].details.startswith("M")  # type: ignore[index]
    # The nails sit on the upper row (backs of the hands, tops of the feet), never on palms or soles.
    for view, upper in (("hands", ("3220", "3221")), ("feet", ("3320", "3321"))):
        bottom = max(bm.zone(code).bbox[3] for code in upper)  # type: ignore[union-attr]
        ys = [float(pair.split(",")[1]) for pair in bm.views[view].details.replace("M", " ").replace("Z", " ").split()]  # type: ignore[index]
        assert max(ys) < bottom


def test_the_front_draws_each_part_of_the_anatomy_on_its_own() -> None:
    front = body_map().views["front"]  # type: ignore[index]
    assert set(front.details_by_part) == {"breasts", "vulva", "penis"}
    assert all(path.startswith("M") for path in front.details_by_part.values())
    for view in ("back", "head", "hands", "feet"):
        assert not body_map().views[view].details_by_part  # type: ignore[index]


def test_behind_the_armpit_gap_climbs_to_just_under_the_shoulder() -> None:
    """The back has no armpit to unroll, so the gap between arm and trunk runs up to where the arm leaves the
    shoulder: past the middle of the front's armpit, which reaches the front's shoulder line, and no higher."""
    migration = _migration()
    bm = body_map()
    back = [migration._rings(zone.path) for zone in bm.zones if zone.view == "back"]

    def covered(x: float, y: float) -> bool:
        # Paths are rounded to 0.1, so a point on the edge between two zones may fall in neither.
        return any(migration.inside(x + dx, y, rings) for rings in back for dx in (-0.1, 0.0, 0.1))

    for pit in ("1660", "1661"):
        left, top, right, bottom = bm.zone(pit).bbox  # type: ignore[union-attr]
        xs = [left + step * (right - left) / 100 for step in range(101)]
        assert not all(covered(x, (top + bottom) / 2) for x in xs)
        assert all(covered(x, top - 1.5) for x in xs)


def test_marks_on_the_arms_move_with_them() -> None:
    """The arms hang further out on map 4: a mark on one stays on it, in the band at its height, and comes back."""
    migration = _migration()
    bm = body_map()
    zones = {zone.code: migration._rings(zone.path) for zone in bm.zones}
    width, height = bm.viewBox[2], bm.viewBox[3]
    middle = width / 2
    # On map 3's axis of the upper arm, halfway to the elbow; on the top of a shoulder; at the wrist, off its axis.
    for code, (distance, y), lands_in in (
        ("1700", (46.75, 119.0), "1700"),
        ("2701", (46.75, 119.0), "2701"),
        ("1650", (36.0, 70.0), "1650"),
        ("1800", (72.0, 180.0), "1800"),
    ):
        side = -1 if code[-1] == "0" else 1
        x = (middle + side * distance) / width
        nx, ny = migration.along_arm(x, y / height, True)
        assert migration.inside(nx * width, ny * height, zones[lands_in])
        assert migration.band(code, nx, ny, zones) == lands_in
        back = migration.along_arm(nx, ny, False)
        assert abs(back[0] - x) < 2e-4 and back[1] == y / height


def test_marks_on_the_limbs_take_the_band_their_point_lies_in() -> None:
    migration = _migration()
    zones = {zone.code: migration._rings(zone.path) for zone in body_map().zones}
    width, height = body_map().viewBox[2], body_map().viewBox[3]

    def at(code: str, fraction_down: float) -> tuple[float, float]:
        left, top, right, bottom = body_map().zone(code).bbox  # type: ignore[union-attr]
        return ((left + right) / 2) / width, (top + fraction_down * (bottom - top)) / height

    # A mark stored on the old "lower thigh and knee" but high on the thigh, and one low on the old "upper thigh".
    x, y = at("1400", 0.5)
    assert migration.band("1450", x, y, zones) == "1400"
    x, y = at("1450", 0.5)
    assert migration.band("1400", x, y, zones) == "1450"
    # A point in the back's new forearm band, stored on the elbow, moves to the forearm.
    x, y = at("2780", 0.5)
    assert migration.band("2750", x, y, zones) == "2780"
    # Between map 3's line and the navel, a mark on the pelvis or the buttock is now on the abdomen or the lower
    # back; one on the middle of the old pelvis, low down, is now on the pubic area.
    assert migration.band("1350", 0.45, 175 / height, zones) == "1300"
    assert migration.band("2351", 0.55, 175 / height, zones) == "2301"
    assert migration.band("1350", 0.5, 212 / height, zones) == "1360"
    # Outside any limb, or on a zone that is not a limb, the code stays.
    assert migration.band("1250", 0.4, 0.25, zones) == "1250"
    assert migration.band("1400", 0.01, 0.01, zones) == "1400"
