# SPDX-License-Identifier: AGPL-3.0-only
"""The reference card as something to print in three dimensions: a white plate with black ink raised on it.

The same `draw_card` that lays the card out for paper and for the detector paints here into a mesh:
black fills become raised ink, strokes thin raised bars, and the window a hole through the plate.
The grey patch comes out solid black: two colours cannot make its grey, and the colour descriptors
know to take their reference from the camera when a patch does not read as the printed grey. The
neVus lockup is raised too, where the paper card carries its lettering (see `lockup`).

Each piece is one STL holding the plate and every ink body, the ink sunk one layer into the plate so
the shells overlap and the slicer unites them into a solid. Everything above the plate's height is
ink, so a printer changes filament at that layer, or the whole piece is printed in white and the
raised parts painted black.
"""

from __future__ import annotations

import io
import math
import struct
import textwrap
import zipfile
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nevus.cv import lockup
from nevus.cv.card import APERTURE_RADIUS, STRIP, WINDOW, CardGeometry, draw_card

PLATE_MM = 1.2
INK_MM = 0.4
OVERLAP_MM = 0.2  # the ink sinks one layer into the plate: overlapping shells unite in the slicer, touching may not
INK_Z0, INK_Z1 = PLATE_MM - OVERLAP_MM, PLATE_MM + INK_MM
MIN_BAR_MM = 0.5
LOCKUP_STEP_MM = 0.1
LOCKUPS = {WINDOW.name: (1.8, 6.0), STRIP.name: (8.8, 4.0)}  # top edge and cap height in mm, centred on the card
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

    def in_printer_frame(self, height: float) -> Mesh:
        """The bodies with y running upward from the bottom edge, every face's vertex order reversed.

        The drawing has y downward, as on paper and in photographs. A printer's bed is right-handed with z up,
        so y must run upward there, or the top of the printed piece comes out mirrored and its markers cannot
        be read. Mirroring turns faces inside out, so their vertex order is reversed to keep pointing outward.
        """

        def flip(v: tuple[float, float, float]) -> tuple[float, float, float]:
            return (v[0], height - v[1], v[2])

        return Mesh(bodies=[[(flip(a), flip(c), flip(b)) for a, b, c in body] for body in self.bodies])

    def stl(self, name: str = "neVus reference card") -> bytes:
        """Binary STL; normals from the vertex order, which the slicer recomputes anyway."""
        out = bytearray(name.encode("ascii", "replace")[:80].ljust(80, b"\0"))
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
    """The Painter protocol over a mesh of ink bodies: what is black is raised, what is white is the plate."""

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
        if self.fill < 0.95:  # black, and the grey patch with it: raised ink
            self.ink.box(x, y, w, h, INK_Z0, INK_Z1)

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
        nx, ny = -dy / length * half, dx / length * half  # the bar's left side; right side first: counter-clockwise
        self.ink.prism(
            [(x1 - nx, y1 - ny), (x2 - nx, y2 - ny), (x2 + nx, y2 + ny), (x1 + nx, y1 + ny)],
            INK_Z0,
            INK_Z1,
        )

    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None:
        if stroke and self.stroke < 0.5:
            half = max(self.width, MIN_BAR_MM) / 2
            self.ink.annulus(cx, cy, r - half, r + half, INK_Z0, INK_Z1)

    def text(self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left") -> None:
        return  # lettering is left to the paper version; the lockup stands in for it

    def lockup(self, centre_x: float, top: float, cap_mm: float) -> None:
        """The neVus mark and wordmark, raised like the rest of the ink, centred on `centre_x`."""
        boxes, width, _ = lockup.boxes(cap_mm, LOCKUP_STEP_MM)
        left = centre_x - width / 2
        for x, y, w, h in boxes:
            self.ink.box(left + x, top + y, w, h, INK_Z0, INK_Z1)


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
    n = SEGMENTS  # the same vertices as the ink ring's inner edge, so the ring's wall and the hole's coincide
    hole = [_polar(cx, cy, APERTURE_RADIUS, 2 * math.pi * i / n) for i in range(n)]
    square = [_square_point(cx, cy, half, 2 * math.pi * i / n) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        for z, flip in ((PLATE_MM, True), (0.0, False)):  # the sector runs clockwise: flip the top cap, not the bottom
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


def mesh(card: CardGeometry = WINDOW) -> Mesh:
    """The piece as one mesh in the printer's frame: the plate first, then every ink body, sunk `OVERLAP_MM` in."""
    painter = MeshPainter(card)
    draw_card(painter, card, 0.0, 0.0, cut_aperture=False)
    top, cap_mm = LOCKUPS[card.name]
    painter.lockup(card.centre[0], top, cap_mm)
    return Mesh(bodies=[*plate(card).bodies, *painter.ink.bodies]).in_printer_frame(card.height)


def _mm(value: float, lang: str) -> str:
    text = f"{value:g}"
    return text.replace(".", ",") if lang in {"es", "pt"} else text


def readme(lang: str = "en") -> str:
    """How to print the pieces, with the height at which the colour changes from plate to ink."""
    plate_mm, ink_mm, overlap_mm = (_mm(v, lang) for v in (PLATE_MM, INK_MM, OVERLAP_MM))
    if lang == "es":
        title = "Tarjeta de referencia neVus v1, para impresión 3D"
        paragraphs = [
            "Un STL por pieza: nevus-card-v1.stl (la tarjeta con ventana, 85,6 x 54 mm) y nevus-strip-v1.stl (la tira, "
            f"60 x 20 mm). Cada archivo lleva la placa y la tinta en relieve juntas; la tinta se hunde {overlap_mm} mm "
            "en la placa y el laminador une las dos cáscaras en un solo sólido (PrusaSlicer, Bambu Studio, Orca y Cura "
            "lo hacen por defecto). Escala 100 %, capas de 0,2 mm, sin soportes, cara lisa sobre la cama.",
            f"Color: la placa mide {plate_mm} mm de grosor y todo lo que está por encima de {plate_mm} mm es tinta, de "
            f"{ink_mm} mm de alto. Con una impresora multimaterial o un cambio de filamento, imprime en blanco hasta "
            f"{plate_mm} mm y en negro desde ahí: en el laminador, pon el cambio de color en la capa que empieza a "
            f"{plate_mm} mm. Con un solo color, imprime toda la pieza en blanco y pinta las partes en relieve con un "
            "rotulador permanente negro.",
            "El parche gris sale negro: una impresión no puede hacer su gris, y la aplicación sabe no usarlo. "
            "Filamento mate y claro: las superficies brillantes reflejan y ocultan los marcadores. Comprueba la pieza "
            "con una regla antes de usarla.",
        ]
    else:
        title = "neVus reference card v1, for 3D printing"
        paragraphs = [
            "One STL per piece: nevus-card-v1.stl (the window card, 85.6 x 54 mm) and nevus-strip-v1.stl (the strip, "
            f"60 x 20 mm). Each file holds the plate and the raised ink together; the ink sinks {overlap_mm} mm into "
            "the plate and the slicer unites the two shells into one solid (PrusaSlicer, Bambu Studio, Orca and Cura "
            "do so by default). 100 % scale, 0.2 mm layers, no supports, flat side down.",
            f"Colour: the plate is {plate_mm} mm thick and everything above {plate_mm} mm is ink, {ink_mm} mm high. "
            f"With a multi-material printer or a filament change, print white up to {plate_mm} mm and black from "
            f"there: in the slicer, set the colour change at the layer that starts at {plate_mm} mm. With one colour, "
            "print the whole piece in white and paint the raised parts with a black permanent marker.",
            "The grey patch comes out black: a print cannot make its grey, and the app knows not to use it. Light "
            "matte filament: glossy surfaces reflect and hide the markers. Check the piece with a ruler before "
            "using it.",
        ]
    return title + "\n\n" + "\n\n".join(textwrap.fill(paragraph, 100) for paragraph in paragraphs) + "\n"


def archive(lang: str = "en") -> bytes:
    """A zip with one STL per piece, the window card and the strip, and a note on how to print them."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for card, name in ((WINDOW, "card"), (STRIP, "strip")):
            zf.writestr(f"nevus-{name}-v1.stl", mesh(card).stl(f"neVus reference card v1: {name}"))
        zf.writestr("README.txt", readme(lang))
    return buffer.getvalue()
