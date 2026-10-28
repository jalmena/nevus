# SPDX-License-Identifier: AGPL-3.0-only
"""The card for a 3D printer: closed meshes of the right size, ink raised on the plate, a window through it."""

from __future__ import annotations

import io
import struct
import zipfile
from collections import Counter

import numpy as np
from fastapi.testclient import TestClient

from nevus.cv import card_mesh
from nevus.cv.card import APERTURE_RADIUS, STRIP, WINDOW
from tests.test_accounts import claim


def _open_edges(body: list[card_mesh.Tri]) -> int:
    """Edges of a body not shared by exactly two faces; zero for a closed, watertight body."""
    edges: Counter[tuple[tuple[float, float, float], tuple[float, float, float]]] = Counter()
    for tri in body:
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            edges[(min(a, b), max(a, b))] += 1
    return sum(1 for n in edges.values() if n != 2)


def test_the_plate_and_the_ink_are_closed_meshes_of_the_card_size() -> None:
    for card in (WINDOW, STRIP):
        made = card_mesh.meshes(card)
        for name, mesh in made.items():
            assert mesh.bodies, f"{card.name} {name}: nothing to print"
            assert all(_open_edges(body) == 0 for body in mesh.bodies), f"{card.name} {name}: a body is not closed"
            points = np.array([v for tri in mesh.triangles for v in tri])
            assert points[:, 0].min() >= -1e-6 and points[:, 0].max() <= card.width + 1e-6
            assert points[:, 1].min() >= -1e-6 and points[:, 1].max() <= card.height + 1e-6
        plate = np.array([v for tri in made["plate"].triangles for v in tri])
        ink = np.array([v for tri in made["ink"].triangles for v in tri])
        assert plate[:, 2].min() == 0.0 and abs(plate[:, 2].max() - card_mesh.PLATE_MM) < 1e-9
        assert abs(ink[:, 2].min() - card_mesh.PLATE_MM) < 1e-9
        assert abs(ink[:, 2].max() - card_mesh.PLATE_MM - card_mesh.INK_MM) < 1e-9


def test_the_window_is_a_hole_and_the_markers_are_ink() -> None:
    made = card_mesh.meshes(WINDOW)
    cx, cy = WINDOW.centre
    plate_top = [tri for tri in made["plate"].triangles if all(abs(v[2] - card_mesh.PLATE_MM) < 1e-9 for v in tri)]
    centres = np.array([np.mean(tri, axis=0)[:2] for tri in plate_top])
    assert np.all(np.hypot(centres[:, 0] - cx, centres[:, 1] - cy) > APERTURE_RADIUS - 0.5)
    ink_top = np.array([np.mean(tri, axis=0)[:2] for tri in made["ink"].triangles])
    for marker_id, (mx, my) in WINDOW.markers.items():
        near = np.hypot(ink_top[:, 0] - mx, ink_top[:, 1] - my) < 6.0
        assert near.sum() > 20, f"marker {marker_id} has no ink"


def test_the_archive_holds_four_stl_files_and_a_note(client: TestClient) -> None:
    claim(client)
    response = client.get("/api/reference-card/3d?lang=es")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = sorted(zf.namelist())
        assert names == [
            "README.txt",
            "nevus-card-v1-ink.stl",
            "nevus-card-v1-plate.stl",
            "nevus-strip-v1-ink.stl",
            "nevus-strip-v1-plate.stl",
        ]
        stl = zf.read("nevus-card-v1-plate.stl")
        (count,) = struct.unpack("<I", stl[80:84])
        assert len(stl) == 84 + 50 * count
        assert "rotulador" in zf.read("README.txt").decode()
