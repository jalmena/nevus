# SPDX-License-Identifier: AGPL-3.0-only
"""The reference card as something to print in three dimensions: a white plate and black ink on top.

The same `draw_card` that lays the card out for paper and for the detector paints here into meshes:
black fills become raised ink, the grey patch a halftone of raised cells, strokes thin raised bars,
and the window a hole through the plate. Two bodies come out, the plate and the ink, so a printer
can change filament at the ink's height, or print both in white and paint the raised parts black.
"""

from __future__ import annotations

import io
import math
import struct
import zipfile
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nevus.cv.card import APERTURE_RADIUS, STRIP, WINDOW, CardGeometry, draw_card

PLATE_MM = 1.2
INK_MM = 0.4
MIN_BAR_MM = 0.5
HALFTONE_CELL_MM = 1.0
SEGMENTS = 96
Tri = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


@dataclass
class Mesh:
    """Closed bodies, each a list of triangles; the slicer unites bodies that touch or overlap."""

    bodies: list[list[Tri]] = field(default_factory=list)

    @property
    def triangles(self) -> list[Tri]:
        return [tri for body in self.bodies for tri in body]

    def begin(self) -> list[Tri]:
        body: list[Tri] = []
        self.bodies.append(body)
        return body

    def quad(self, a: Any, b: Any, c: Any, d: Any, body: list[Tri] | None = None) -> None:
        target = body if body is not None else (self.bodies[-1] if self.bodies else self.begin())
        target.append((tuple(a), tuple(b), tuple(c)))
        target.append((tuple(a), tuple(c), tuple(d)))

    def prism(self, polygon: list[tuple[float, float]], z0: float, z1: float) -> None:
        """A convex polygon (counter-clockwise, seen from above) extruded between two heights."""
        body = self.begin()
        top = [(x, y, z1) for x, y in polygon]
        bottom = [(x, y, z0) for x, y in polygon]
        for i in range(1, len(polygon) - 1):
            body.append((top[0], top[i], top[i + 1]))
            body.append((bottom[0], bottom[i + 1], bottom[i]))
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            self.quad(bottom[i], bottom[j], top[j], top[i], body)

    def box(self, x: float, y: float, w: float, h: float, z0: float, z1: float) -> None:
        self.prism([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], z0, z1)

    def annulus(self, cx: float, cy: float, r_in: float, r_out: float, z0: float, z1: float) -> None:
        self.begin()
        for i in range(SEGMENTS):
            a0 = 2 * math.pi * i / SEGMENTS
            a1 = 2 * math.pi * ((i + 1) % SEGMENTS) / SEGMENTS  # the last segment closes on the first vertex
            o0, o1 = _polar(cx, cy, r_out, a0), _polar(cx, cy, r_out, a1)
            i0, i1 = _polar(cx, cy, r_in, a0), _polar(cx, cy, r_in, a1)
            self.quad((*i0, z1), (*o0, z1), (*o1, z1), (*i1, z1))
            self.quad((*i0, z0), (*i1, z0), (*o1, z0), (*o0, z0))
            self.quad((*o0, z0), (*o1, z0), (*o1, z1), (*o0, z1))
            self.quad((*i0, z0), (*i0, z1), (*i1, z1), (*i1, z0))

    def stl(self) -> bytes:
        """Binary STL; normals from the vertex order, which the slicer recomputes anyway."""
        out = bytearray(b"neVus reference card".ljust(80, b"\0"))
        out += struct.pack("<I", len(self.triangles))
        for a, b, c in self.triangles:
            n = np.cross(np.subtract(b, a), np.subtract(c, a))
            length = float(np.linalg.norm(n))
            n = n / length if length else n
            out += struct.pack("<3f", *n)
            for v in (a, b, c):
                out += struct.pack("<3f", *v)
            out += struct.pack("<H", 0)
        return bytes(out)


def _polar(cx: float, cy: float, r: float, angle: float) -> tuple[float, float]:
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))


class MeshPainter:
    """The Painter protocol over two meshes: what is black is ink, what is white is the plate."""

    def __init__(self, card: CardGeometry) -> None:
        self.card = card
        self.ink = Mesh()
        self.fill = 1.0
        self.stroke = 0.0
        self.width = 0.3

    def fill_gray(self, level: float) -> None:
        self.fill = level

    def stroke_gray(self, level: float) -> None:
        self.stroke = level

    def line_width(self, mm: float) -> None:
        self.width = mm

    def rect(self, x: float, y: float, w: float, h: float, *, fill: bool = True, stroke: bool = False) -> None:
        if not fill:
            return
        if self.fill < 0.5:
            self.ink.box(x, y, w, h, PLATE_MM, PLATE_MM + INK_MM)
        elif self.fill < 0.95:  # the grey patch: a halftone of raised cells reads as grey from a step back
            cell = HALFTONE_CELL_MM
            rows, cols = int(h // cell), int(w // cell)
            for row in range(rows):
                for col in range(cols):
                    if (row + col) % 2 == 0:
                        self.ink.box(x + col * cell, y + row * cell, cell, cell, PLATE_MM, PLATE_MM + INK_MM)

    def rects(self, boxes: list[tuple[float, float, float, float]]) -> None:
        for x, y, w, h in boxes:
            self.rect(x, y, w, h)

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        if self.stroke >= 0.5:
            return
        half = max(self.width, MIN_BAR_MM) / 2
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length * half, dx / length * half
        self.ink.prism(
            [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)],
            PLATE_MM,
            PLATE_MM + INK_MM,
        )

    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None:
        if stroke and self.stroke < 0.5:
            half = max(self.width, MIN_BAR_MM) / 2
            self.ink.annulus(cx, cy, r - half, r + half, PLATE_MM, PLATE_MM + INK_MM)

    def text(self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left") -> None:
        return  # lettering is left to the paper version


def plate(card: CardGeometry) -> Mesh:
    """The plate, with the window cut through it for the window card."""
    mesh = Mesh()
    w, h = card.width, card.height
    if card is not WINDOW:
        mesh.box(0.0, 0.0, w, h, 0.0, PLATE_MM)
        return mesh
    body = mesh.begin()
    cx, cy = card.centre
    half = APERTURE_RADIUS + 2.0  # a square around the hole, tessellated in sectors to meet the circle
    n = 8 * 9
    hole = [_polar(cx, cy, APERTURE_RADIUS, 2 * math.pi * i / n) for i in range(n)]
    square = [_square_point(cx, cy, half, 2 * math.pi * i / n) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        for z, flip in ((PLATE_MM, False), (0.0, True)):
            quad = [(*hole[i], z), (*hole[j], z), (*square[j], z), (*square[i], z)]
            if flip:
                quad.reverse()
            mesh.quad(quad[0], quad[1], quad[2], quad[3], body)
        mesh.quad((*hole[i], 0.0), (*hole[i], PLATE_MM), (*hole[j], PLATE_MM), (*hole[j], 0.0), body)
    # Four bands between the square and the plate's edges, each a trapezoid fanned from a corner, so the
    # points along the square are shared with the sectors and no edge is left hanging.
    left, right, top, bottom = cx - half, cx + half, cy - half, cy + half
    along_top = sorted({p for p in square if abs(p[1] - top) < 1e-6})
    along_bottom = sorted({p for p in square if abs(p[1] - bottom) < 1e-6})
    along_left = sorted({p for p in square if abs(p[0] - left) < 1e-6}, key=lambda p: p[1])
    along_right = sorted({p for p in square if abs(p[0] - right) < 1e-6}, key=lambda p: p[1])
    bands: list[list[tuple[float, float]]] = [
        [(0.0, 0.0), (w, 0.0), *reversed(along_top)],  # clockwise seen from above: outer edge, then the square's
        [(w, h), (0.0, h), *along_bottom],
        [(0.0, h), (0.0, 0.0), *along_left],
        [(w, 0.0), (w, h), *reversed(along_right)],
    ]
    for polygon in bands:
        _fan(body, polygon, PLATE_MM, 0.0)
    corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    for i in range(4):  # outer walls
        a, b = corners[i], corners[(i + 1) % 4]
        mesh.quad((*a, 0.0), (*b, 0.0), (*b, PLATE_MM), (*a, PLATE_MM), body)
    return mesh


def _square_point(cx: float, cy: float, half: float, angle: float) -> tuple[float, float]:
    """Where a ray from the centre at `angle` meets the square of half-side `half`."""
    c, s = math.cos(angle), math.sin(angle)
    t = half / max(abs(c), abs(s))
    return (round(cx + t * c, 6), round(cy + t * s, 6))


def _fan(body: list[Tri], polygon: list[tuple[float, float]], z_top: float, z_bottom: float) -> None:
    for i in range(1, len(polygon) - 1):
        a, b, c = polygon[0], polygon[i], polygon[i + 1]
        body.append(((*a, z_top), (*b, z_top), (*c, z_top)))
        body.append(((*a, z_bottom), (*c, z_bottom), (*b, z_bottom)))


def meshes(card: CardGeometry = WINDOW) -> dict[str, Mesh]:
    painter = MeshPainter(card)
    draw_card(painter, card, 0.0, 0.0, cut_aperture=False)
    return {"plate": plate(card), "ink": painter.ink}


README = {
    "en": (
        "neVus reference card v1, for 3D printing\n\n"
        "Two bodies: the plate (print in white) and the ink (print in black), or print both in white and paint the\n"
        "raised parts black with a permanent marker. 100 % scale, 0.2 mm layers, no supports; the ink starts at\n"
        f"{PLATE_MM} mm and is {INK_MM} mm high, so a single-extruder printer changes filament at that layer.\n"
        "Light matte filament for the plate; glossy surfaces reflect and hide the markers.\n"
        "Check the plate with a ruler: the window card is 85.6 x 54 mm, the strip 60 x 20 mm.\n"
    ),
    "es": (
        "Tarjeta de referencia neVus v1, para impresión 3D\n\n"
        "Dos cuerpos: la placa (imprímela en blanco) y la tinta (en negro), o imprime los dos en blanco y pinta las\n"
        "partes en relieve con un rotulador permanente negro. Escala 100 %, capas de 0,2 mm, sin soportes; la tinta\n"
        f"empieza a {PLATE_MM} mm y tiene {INK_MM} mm de alto: una impresora de un extrusor cambia de filamento ahí.\n"
        "Filamento mate y claro para la placa; las superficies brillantes reflejan y ocultan los marcadores.\n"
        "Comprueba la placa con una regla: la tarjeta con ventana mide 85,6 x 54 mm y la tira 60 x 20 mm.\n"
    ),
}


def archive(lang: str = "en") -> bytes:
    """A zip with the four STL files (window card and strip, plate and ink) and how to print them."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for card, name in ((WINDOW, "card"), (STRIP, "strip")):
            for part, mesh in meshes(card).items():
                zf.writestr(f"nevus-{name}-v1-{part}.stl", mesh.stl())
        zf.writestr("README.txt", README.get(lang, README["en"]))
    return buffer.getvalue()
