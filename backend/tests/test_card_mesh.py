# SPDX-License-Identifier: AGPL-3.0-only
"""The card for a 3D printer: closed meshes of the right size, ink raised on the plate, a window through it."""

from __future__ import annotations

import io
import math
import struct
import zipfile
from collections import Counter

import cv2
import numpy as np
from fastapi.testclient import TestClient

from nevus.cv import card_detect, card_mesh, lockup
from nevus.cv.card import APERTURE_RADIUS, STRIP, WINDOW, CardGeometry
from tests.test_accounts import claim


def _open_edges(body: list[card_mesh.Tri]) -> int:
    """Edges of a body not shared by exactly two faces; zero for a closed, watertight body."""
    edges: Counter[tuple[tuple[float, float, float], tuple[float, float, float]]] = Counter()
    for tri in body:
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            edges[(min(a, b), max(a, b))] += 1
    return sum(1 for n in edges.values() if n != 2)


def test_each_piece_is_one_mesh_of_closed_bodies_with_the_ink_sunk_into_the_plate() -> None:
    for card in (WINDOW, STRIP):
        made = card_mesh.mesh(card)
        plate, *ink = made.bodies
        assert ink, f"{card.name}: nothing raised to print"
        assert all(_open_edges(body) == 0 for body in made.bodies), f"{card.name}: a body is not closed"
        points = np.array([v for tri in made.triangles for v in tri])
        width, height = card_mesh.plate_size(card)
        assert points[:, 0].min() >= -1e-6 and points[:, 0].max() <= width + 1e-6
        assert points[:, 1].min() >= -1e-6 and points[:, 1].max() <= height + 1e-6
        plate_points = np.array([v for tri in plate for v in tri])
        ink_points = np.array([v for body in ink for tri in body for v in tri])
        assert plate_points[:, 2].min() == 0.0 and abs(plate_points[:, 2].max() - card_mesh.PLATE_MM) < 1e-9
        # The ink starts below the plate's top, so the shells overlap and the slicer unites them into one solid.
        assert abs(ink_points[:, 2].min() - (card_mesh.PLATE_MM - card_mesh.OVERLAP_MM)) < 1e-9
        assert ink_points[:, 2].min() < card_mesh.PLATE_MM
        assert abs(ink_points[:, 2].max() - card_mesh.PLATE_MM - card_mesh.INK_MM) < 1e-9


def _signed_volume(body: list[card_mesh.Tri]) -> float:
    """Positive when every face points outward; a body with faces turned inward prints inside out."""
    return sum(float(np.dot(a, np.cross(b, c))) for a, b, c in body) / 6.0


def _edges_against_the_grain(body: list[card_mesh.Tri]) -> int:
    """Directed edges a neighbouring face runs the same way: zero when every face is wound consistently."""
    directed: Counter[tuple[tuple[float, float, float], tuple[float, float, float]]] = Counter()
    for tri in body:
        for i in range(3):
            directed[(tri[i], tri[(i + 1) % 3])] += 1
    return sum(1 for n in directed.values() if n != 1)


def test_every_body_is_wound_consistently_with_its_faces_outward() -> None:
    for card in (WINDOW, STRIP):
        for n, body in enumerate(card_mesh.mesh(card).bodies):
            assert _edges_against_the_grain(body) == 0, f"{card.name} body {n}: faces wound against each other"
            assert _signed_volume(body) > 0, f"{card.name} body {n}: faces point inward"


def _seen_from_above_the_bed(card: CardGeometry, px_per_mm: int = 12, pad: int = 40) -> np.ndarray:
    """The printed piece photographed from above: x to the right and y away, as a right-handed bed has them."""
    plate_w, plate_h = card_mesh.plate_size(card)
    width, height = round(plate_w * px_per_mm), round(plate_h * px_per_mm)
    picture = np.full((height + 2 * pad, width + 2 * pad), 150, np.uint8)
    picture[pad : pad + height, pad : pad + width] = 235
    _plate, *ink = card_mesh.mesh(card).bodies
    for body in ink:
        for tri in body:
            if all(abs(v[2] - card_mesh.INK_Z1) < 1e-9 for v in tri):
                points = [(pad + v[0] * px_per_mm, pad + (plate_h - v[1]) * px_per_mm) for v in tri]
                cv2.fillConvexPoly(picture, np.round(points).astype(np.int32), 20, lineType=cv2.LINE_AA)
    return picture


def _pixel(picture: np.ndarray, height: float, x: float, y: float, px_per_mm: int = 12, pad: int = 40) -> int:
    """The raster's value at a point of the printed piece, given in the printer's frame in millimetres."""
    return int(picture[round(pad + (height - y) * px_per_mm), round(pad + x * px_per_mm)])


def test_the_plate_is_a_rounded_rectangle_with_the_window_cut_out_and_a_frame_along_its_edge() -> None:
    for card in (WINDOW, STRIP):
        plate, *ink = card_mesh.mesh(card).bodies
        width, height = card_mesh.plate_size(card)
        top_faces = [tri for tri in plate if all(abs(v[2] - card_mesh.PLATE_MM) < 1e-9 for v in tri)]
        area = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2 for a, b, c in top_faces)
        expected = width * height - (4 - math.pi) * card_mesh.CORNER_MM**2
        if card is WINDOW:
            expected -= math.pi * APERTURE_RADIUS**2
        assert abs(area - expected) < 0.005 * expected, (card.name, area, expected)
        # The frame: a dark line along every edge, plate colour just inside it, nothing raised beyond it.
        picture = _seen_from_above_the_bed(card)
        line = card_mesh.FRAME_INSET_MM + card_mesh.FRAME_MM / 2
        inside = card_mesh.FRAME_INSET_MM + card_mesh.FRAME_MM + 0.4

        def pixel(x: float, y: float, picture: np.ndarray = picture, height: float = height) -> int:
            return _pixel(picture, height, x, y)

        for x in np.linspace(card_mesh.CORNER_MM, width - card_mesh.CORNER_MM, 7):
            assert pixel(x, line) < 100 and pixel(x, height - line) < 100, (card.name, "edge", x)
            assert pixel(x, inside) > 200 and pixel(x, height - inside) > 200, (card.name, "inside", x)
        for y in np.linspace(card_mesh.CORNER_MM, height - card_mesh.CORNER_MM, 5):
            assert pixel(line, y) < 100 and pixel(width - line, y) < 100, (card.name, "side", y)
        tops = np.array([np.mean(tri, axis=0) for body in ink for tri in body])
        assert (
            tops[:, 0].min() >= card_mesh.FRAME_INSET_MM - 1e-6
            and tops[:, 0].max() <= width - card_mesh.FRAME_INSET_MM + 1e-6
        )


def test_the_printed_piece_reads_like_the_paper_card_and_not_its_mirror_image() -> None:
    for card in (WINDOW, STRIP):
        found = card_detect.detect(_seen_from_above_the_bed(card))
        assert found["found"], f"{card.name}: the markers on the printed piece cannot be read"
        assert found["ids"] == sorted(card.markers), f"{card.name}: wrong markers"


def test_the_window_is_a_hole_and_the_markers_are_ink() -> None:
    plate, *ink = card_mesh.mesh(WINDOW).bodies
    m = card_mesh.PLATE_MARGIN_MM
    _plate_w, plate_h = card_mesh.plate_size(WINDOW)
    cx, cy = WINDOW.centre[0] + m, plate_h - (WINDOW.centre[1] + m)  # the printer's frame has y running upward
    plate_top = [tri for tri in plate if all(abs(v[2] - card_mesh.PLATE_MM) < 1e-9 for v in tri)]
    centres = np.array([np.mean(tri, axis=0)[:2] for tri in plate_top])
    assert np.all(np.hypot(centres[:, 0] - cx, centres[:, 1] - cy) > APERTURE_RADIUS - 0.5)
    ink_top = np.array([np.mean(tri, axis=0)[:2] for body in ink for tri in body])
    for marker_id, (mx, my) in WINDOW.markers.items():
        near = np.hypot(ink_top[:, 0] - (mx + m), ink_top[:, 1] - (plate_h - (my + m))) < 6.0
        assert near.sum() > 20, f"marker {marker_id} has no ink"
    # Nothing raised hangs over the hole: the ring's inner edge is the hole's edge (centroids of the faces along
    # a 96-gon sit a hundredth of a millimetre inside the circle).
    assert np.all(np.hypot(ink_top[:, 0] - cx, ink_top[:, 1] - cy) > APERTURE_RADIUS - 0.02)


def test_the_archive_holds_one_stl_per_piece_and_a_note_with_the_colour_change_height(client: TestClient) -> None:
    claim(client)
    response = client.get("/api/reference-card/3d?lang=es")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert sorted(zf.namelist()) == ["README.txt", "nevus-card-v1.stl", "nevus-strip-v1.stl"]
        stl = zf.read("nevus-card-v1.stl")
        (count,) = struct.unpack("<I", stl[80:84])
        assert len(stl) == 84 + 50 * count
        assert count == len(card_mesh.mesh(WINDOW).triangles)  # plate and ink in the same file
        note = zf.read("README.txt").decode()
        assert "rotulador" in note and "1,2 mm" in note
    assert "1.2 mm" in card_mesh.readme("en") and "1.2 mm" in card_mesh.readme("xx")


def test_the_lockup_is_read_from_the_identity_with_its_proportions() -> None:
    drawing = lockup.shapes()
    assert len(drawing.polygons) == 4  # n, e, u, s
    assert len(drawing.quads) == 2  # the legs
    assert len(drawing.discs) == 5 and sum(1 for *_, ink in drawing.discs if not ink) == 1  # tips, hinge, hole, dot
    left, top, right, bottom = drawing.extent()
    assert 3.7 < (right - left) / (bottom - top) < 3.9  # 382 px of ink across a cap height of 100


def _enclosed_gaps(boxes: list[lockup.Box], width: float, height: float, step: float = 0.05) -> int:
    """Background regions the ink surrounds completely: the counter of the e and the hole in the hinge."""
    picture = np.zeros((round(height / step) + 2, round(width / step) + 2), np.uint8)
    for x, y, w, h in boxes:
        picture[1 + round(y / step) : 1 + round((y + h) / step), 1 + round(x / step) : 1 + round((x + w) / step)] = 1
    count, labels = cv2.connectedComponents((1 - picture).astype(np.uint8))
    border = set(labels[0]) | set(labels[-1]) | set(labels[:, 0]) | set(labels[:, -1])
    return len({label for label in range(1, count) if label not in border})


def test_the_lockup_is_raised_on_both_pieces_with_its_openings_kept() -> None:
    for card in (WINDOW, STRIP):
        top, cap_mm = card_mesh.LOCKUPS[card.name]
        boxes, width, height = lockup.boxes(cap_mm, card_mesh.LOCKUP_STEP_MM)
        assert abs(height - cap_mm) < 0.1 * cap_mm and 3.7 * cap_mm < width < 3.9 * cap_mm
        slack = 2 * card_mesh.LOCKUP_STEP_MM + 1e-6  # the grid and the anti-aliased edges can stick out a cell or two
        assert all(
            x >= -slack and y >= -slack and x + w <= width + slack and y + h <= height + slack for x, y, w, h in boxes
        )
        assert _enclosed_gaps(boxes, width, height) >= 2
        m = card_mesh.PLATE_MARGIN_MM
        _plate_w, plate_h = card_mesh.plate_size(card)
        left = card.centre[0] + m - width / 2
        _plate, *ink = card_mesh.mesh(card).bodies
        tops = np.array(
            [np.mean(tri, axis=0) for body in ink for tri in body if abs(tri[0][2] - card_mesh.INK_Z1) < 1e-9]
        )
        inside = (tops[:, 0] > left) & (tops[:, 0] < left + width) & (tops[:, 1] > plate_h - top - m - height)
        inside &= tops[:, 1] < plate_h - top - m
        assert inside.sum() > 100, f"{card.name}: the lockup is not raised where it belongs"
