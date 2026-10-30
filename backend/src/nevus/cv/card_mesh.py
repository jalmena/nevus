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

from nevus.cv import lockup, outline
from nevus.cv.card import APERTURE_RADIUS, GREY, STRIP, WINDOW, CardGeometry, draw_card
from nevus.languages import normalise
from nevus.reports.i18n import catalogue

PLATE_MM = 1.2
INK_MM = 0.4
OVERLAP_MM = 0.2  # the ink sinks one layer into the plate: overlapping shells unite in the slicer, touching may not
INK_Z0, INK_Z1 = PLATE_MM - OVERLAP_MM, PLATE_MM + INK_MM
GREY_MM = 0.4  # the grey square stands two 0.2 mm layers higher, for a change to grey filament at INK_Z1
MIN_BAR_MM = 0.5
PLATE_MARGIN_MM = 1.0  # the plate reaches this far beyond the drawing, so a frame line keeps clear of the markers
CORNER_MM = 3.0  # the plate's corners, rounded like a bank card's
FRAME_MM, FRAME_INSET_MM = 0.5, 0.3  # a thin raised line following the plate's edge
LOCKUP_STEP_MM = 0.1
# Top edge and cap height in mm, centred on the card; on the window card, as large as the room above the ring allows.
LOCKUPS = {WINDOW.name: (0.7, 9.0), STRIP.name: (8.3, 5.0)}
# At the strip's size the hole in the mark's hinge (0.66 mm) and the ring round it (0.30 mm) are finer than a
# 0.41 mm line, so its hinge is printed solid; every other stroke of the lockups is 0.54 mm or more.
SOLID_HINGE = {STRIP.name}
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
        angles = [2 * math.pi * i / SEGMENTS for i in range(SEGMENTS)]
        self.ring([_polar(cx, cy, r_out, a) for a in angles], [_polar(cx, cy, r_in, a) for a in angles], z0, z1)

    def ring(self, outer: list[tuple[float, float]], inner: list[tuple[float, float]], z0: float, z1: float) -> None:
        """The band between two closed outlines with corresponding points, both wound like `box`'s polygon."""
        self.begin()
        for i in range(len(outer)):
            j = (i + 1) % len(outer)  # the last segment closes on the first vertex
            o0, o1, i0, i1 = outer[i], outer[j], inner[i], inner[j]
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
            grey = abs(self.fill - GREY) < 0.01
            self.ink.box(x, y, w, h, INK_Z0, INK_Z1 + (GREY_MM if grey else 0.0))

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

    def lockup(self, centre_x: float, top: float, cap_mm: float, hinge_hole: bool = True) -> None:
        """The neVus mark and wordmark, raised like the rest of the ink, centred on `centre_x`."""
        boxes, width, _ = lockup.boxes(cap_mm, LOCKUP_STEP_MM, hinge_hole)
        left = centre_x - width / 2
        for x, y, w, h in boxes:
            self.ink.box(left + x, top + y, w, h, INK_Z0, INK_Z1)

    def frame(self, width: float, height: float) -> None:
        """A thin raised line following the plate's edge and its rounded corners."""
        o, i = FRAME_INSET_MM, FRAME_INSET_MM + FRAME_MM
        outer = outline.rounded_rect(o, o, width - 2 * o, height - 2 * o, CORNER_MM - o)
        inner = outline.rounded_rect(i, i, width - 2 * i, height - 2 * i, CORNER_MM - i)
        self.ink.ring(outer, inner, INK_Z0, INK_Z1)


def plate_size(card: CardGeometry) -> tuple[float, float]:
    """The plate: the drawing plus the margin all round."""
    return card.width + 2 * PLATE_MARGIN_MM, card.height + 2 * PLATE_MARGIN_MM


def plate(card: CardGeometry) -> Mesh:
    """The plate with rounded corners, and the window cut through it for the window card."""
    mesh = Mesh()
    w, h = plate_size(card)
    if card is not WINDOW:
        mesh.prism(outline.rounded_rect(0.0, 0.0, w, h, CORNER_MM), 0.0, PLATE_MM)
        return mesh
    body = mesh.begin()
    cx, cy = card.centre[0] + PLATE_MARGIN_MM, card.centre[1] + PLATE_MARGIN_MM
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
    # Four bands between the square and the plate's edges, each fanned from its first vertex (they are convex),
    # so the points along the square are shared with the sectors and no edge is left hanging. Each band's outer
    # edge runs from the middle of one corner arc to the middle of the next, so the arcs are shared too.
    left, right, top, bottom = cx - half, cx + half, cy - half, cy + half
    along_top = sorted({p for p in square if abs(p[1] - top) < 1e-6})
    along_bottom = sorted({p for p in square if abs(p[1] - bottom) < 1e-6})
    along_left = sorted({p for p in square if abs(p[0] - left) < 1e-6}, key=lambda p: p[1])
    along_right = sorted({p for p in square if abs(p[0] - right) < 1e-6}, key=lambda p: p[1])
    edge_top, edge_right, edge_bottom, edge_left = outline.sides(0.0, 0.0, w, h, CORNER_MM)
    bands: list[list[tuple[float, float]]] = [
        [*edge_top, *reversed(along_top)],  # the outer edge first, then back along the square's side
        [*edge_bottom, *along_bottom],
        [*edge_left, *along_left],
        [*edge_right, *reversed(along_right)],
    ]
    for polygon in bands:
        _fan(body, polygon, PLATE_MM, 0.0)
    rim = outline.rounded_rect(0.0, 0.0, w, h, CORNER_MM)
    for i in range(len(rim)):  # outer walls
        a, b = rim[i], rim[(i + 1) % len(rim)]
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
    m = PLATE_MARGIN_MM
    draw_card(painter, card, m, m, cut_aperture=False)
    top, cap_mm = LOCKUPS[card.name]
    painter.lockup(card.centre[0] + m, top + m, cap_mm, hinge_hole=card.name not in SOLID_HINGE)
    width, height = plate_size(card)
    painter.frame(width, height)
    return Mesh(bodies=[*plate(card).bodies, *painter.ink.bodies]).in_printer_frame(height)


README_TEXT: dict[str, tuple[str, list[str]]] = {
    # Title and paragraphs; the numbers are filled in with the language's decimal mark.
    "en": (
        "neVus reference card v1, for 3D printing",
        [
            "One STL per piece: nevus-card-v1.stl (the window card, {card_w} x {card_h} mm) and nevus-strip-v1.stl "
            "(the strip, {strip_w} x {strip_h} mm). Each file holds the plate and the raised ink together; the ink "
            "sinks {overlap_mm} mm into the plate and the slicer unites the two shells into one solid (PrusaSlicer, "
            "Bambu Studio, Orca and Cura do so by default). 100 % scale, 0.2 mm layers, no supports, flat side down.",
            "Colour: the plate is {plate_mm} mm thick and everything above {plate_mm} mm is ink, {ink_mm} mm high. "
            "With a multi-material printer or a filament change, print white up to {plate_mm} mm and black from "
            "there: in the slicer, set the colour change at the layer that starts at {plate_mm} mm. With one colour, "
            "print the whole piece in white and paint the raised parts with a black permanent marker.",
            "The grey square stands {grey_mm} mm above the rest of the ink: change to grey filament at the layer "
            "that starts at {grey_from} mm and only the square goes on, two layers of grey over the black. Left "
            "black, the app takes its colour reference from the camera; for colours that compare across visits, "
            "cut a grey square from the paper sheet (Settings > Reference card; the sheet carries spare squares "
            "at the bottom) and glue it on.",
            "Light matte filament: glossy surfaces reflect and hide the markers. Check the piece with a ruler before "
            "using it.",
        ],
    ),
    "es": (
        "Tarjeta de referencia neVus v1, para impresión 3D",
        [
            "Un STL por pieza: nevus-card-v1.stl (la tarjeta con ventana, {card_w} x {card_h} mm) y "
            "nevus-strip-v1.stl (la tira, {strip_w} x {strip_h} mm). Cada archivo lleva la placa y la tinta en "
            "relieve juntas; la tinta se hunde {overlap_mm} mm en la placa y el laminador une las dos cáscaras en un "
            "solo sólido (PrusaSlicer, Bambu Studio, Orca y Cura lo hacen por defecto). Escala 100 %, capas de "
            "0,2 mm, sin soportes, cara lisa sobre la cama.",
            "Color: la placa mide {plate_mm} mm de grosor y todo lo que está por encima de {plate_mm} mm es tinta, "
            "de {ink_mm} mm de alto. Con una impresora multimaterial o un cambio de filamento, imprime en blanco "
            "hasta {plate_mm} mm y en negro desde ahí: en el laminador, pon el cambio de color en la capa que "
            "empieza a {plate_mm} mm. Con un solo color, imprime toda la pieza en blanco y pinta las partes en "
            "relieve con un rotulador permanente negro.",
            "El cuadrado gris sobresale {grey_mm} mm por encima del resto de la tinta: cambia a filamento gris "
            "en la capa que empieza en {grey_from} mm y solo seguirá el cuadrado, con dos capas de gris sobre el "
            "negro. Si queda negro, la aplicación toma la referencia de color de la cámara; para colores "
            "comparables entre vistazos, recorta un cuadrado gris de la hoja de papel (Ajustes > Tarjeta de "
            "referencia; la hoja lleva cuadrados de repuesto abajo) y pégalo encima.",
            "Filamento mate y claro: las superficies brillantes reflejan y ocultan los marcadores. Comprueba la "
            "pieza con una regla antes de usarla.",
        ],
    ),
    "pt": (
        "Cartão de referência neVus v1, para impressão 3D",
        [
            "Um STL por peça: nevus-card-v1.stl (o cartão com janela, {card_w} x {card_h} mm) e nevus-strip-v1.stl (a "
            "tira, {strip_w} x {strip_h} mm). Cada ficheiro leva a placa e a tinta em relevo juntas; a tinta afunda "
            "{overlap_mm} mm na placa e o fatiador une as duas cascas num só sólido (PrusaSlicer, Bambu Studio, Orca "
            "e Cura fazem-no por defeito). Escala 100 %, camadas de 0,2 mm, sem suportes, face lisa virada para baixo.",
            "Cor: a placa tem {plate_mm} mm de espessura e tudo o que está acima de {plate_mm} mm é tinta, com "
            "{ink_mm} mm de altura. Com uma impressora multimaterial ou uma troca de filamento, imprima a branco até "
            "{plate_mm} mm e a preto a partir daí: no fatiador, ponha a mudança de cor na camada que começa a "
            "{plate_mm} mm. Com uma só cor, imprima a peça toda a branco e pinte as partes em relevo com um marcador "
            "permanente preto.",
            "O quadrado cinzento sobressai {grey_mm} mm acima do resto da tinta: mude para filamento cinzento na "
            "camada que começa em {grey_from} mm e só o quadrado continua, com duas camadas de cinzento sobre o "
            "preto. Se ficar preto, a aplicação tira a referência de cor da câmara; para cores comparáveis entre "
            "visitas, recorte um quadrado cinzento da folha de papel (Definições > Cartão de referência; a folha "
            "leva quadrados sobresselentes em baixo) e cole-o por cima.",
            "Filamento mate e claro: as superfícies brilhantes refletem e escondem os marcadores. Verifique a peça "
            "com uma régua antes de a usar.",
        ],
    ),
    "ca": (
        "Targeta de referència neVus v1, per a impressió 3D",
        [
            "Un STL per peça: nevus-card-v1.stl (la targeta amb finestra, {card_w} x {card_h} mm) i "
            "nevus-strip-v1.stl (la tira, {strip_w} x {strip_h} mm). Cada fitxer porta la placa i la tinta en relleu "
            "juntes; la tinta s'enfonsa {overlap_mm} mm a la placa i el laminador uneix les dues closques en un sol "
            "sòlid (PrusaSlicer, Bambu Studio, Orca i Cura ho fan per defecte). Escala 100 %, capes de 0,2 mm, sense "
            "suports, cara llisa sobre el llit.",
            "Color: la placa fa {plate_mm} mm de gruix i tot el que hi ha per sobre de {plate_mm} mm és tinta, de "
            "{ink_mm} mm d'alçada. Amb una impressora multimaterial o un canvi de filament, imprimeix en blanc fins a "
            "{plate_mm} mm i en negre des d'aquí: al laminador, posa el canvi de color a la capa que comença a "
            "{plate_mm} mm. Amb un sol color, imprimeix tota la peça en blanc i pinta les parts en relleu amb un "
            "retolador permanent negre.",
            "El quadrat gris sobresurt {grey_mm} mm per sobre de la resta de la tinta: canvia a filament gris a "
            "la capa que comença a {grey_from} mm i només continuarà el quadrat, amb dues capes de gris sobre el "
            "negre. Si queda negre, l'aplicació agafa la referència de color de la càmera; per a colors "
            "comparables entre visites, retalla un quadrat gris del full de paper (Ajustos > Targeta de "
            "referència; el full porta quadrats de recanvi a baix) i enganxa'l a sobre.",
            "Filament mat i clar: les superfícies brillants reflecteixen i amaguen els marcadors. Comprova la peça "
            "amb una regla abans d'utilitzar-la.",
        ],
    ),
    "gl": (
        "Tarxeta de referencia neVus v1, para impresión 3D",
        [
            "Un STL por peza: nevus-card-v1.stl (a tarxeta con fiestra, {card_w} x {card_h} mm) e nevus-strip-v1.stl "
            "(a tira, {strip_w} x {strip_h} mm). Cada ficheiro leva a placa e a tinta en relevo xuntas; a tinta "
            "afúndese {overlap_mm} mm na placa e o laminador une as dúas cascas nun só sólido (PrusaSlicer, Bambu "
            "Studio, Orca e Cura fano por defecto). Escala 100 %, capas de 0,2 mm, sen soportes, cara lisa sobre a "
            "cama.",
            "Cor: a placa mide {plate_mm} mm de groso e todo o que está por riba de {plate_mm} mm é tinta, de "
            "{ink_mm} mm de alto. Cunha impresora multimaterial ou un cambio de filamento, imprime en branco ata "
            "{plate_mm} mm e en negro desde aí: no laminador, pon o cambio de cor na capa que comeza a {plate_mm} mm. "
            "Cunha soa cor, imprime toda a peza en branco e pinta as partes en relevo cun rotulador permanente negro.",
            "O cadrado gris sobresae {grey_mm} mm por riba do resto da tinta: cambia a filamento gris na capa "
            "que comeza en {grey_from} mm e só seguirá o cadrado, con dúas capas de gris sobre o negro. Se queda "
            "negro, a aplicación toma a referencia de cor da cámara; para cores comparables entre visitas, "
            "recorta un cadrado gris da folla de papel (Axustes > Tarxeta de referencia; a folla leva cadrados "
            "de reposto abaixo) e pégao enriba.",
            "Filamento mate e claro: as superficies brillantes reflicten e agochan os marcadores. Comproba a peza "
            "cunha regra antes de usala.",
        ],
    ),
    "eu": (
        "neVus erreferentzia-txartela v1, 3D inprimaketarako",
        [
            "STL bat pieza bakoitzeko: nevus-card-v1.stl (leihodun txartela, {card_w} x {card_h} mm) eta "
            "nevus-strip-v1.stl (tira, {strip_w} x {strip_h} mm). Fitxategi bakoitzak plaka eta erliebeko tinta "
            "batera dauzka; tinta {overlap_mm} mm sartzen da plakan, eta laminatzaileak bi oskolak solido bakarrean "
            "elkartzen ditu (PrusaSlicer, Bambu Studio, Orca eta Cura-k hala egiten dute lehenespenez). % 100eko "
            "eskala, 0,2 mm-ko geruzak, euskarririk gabe, alde laua behera.",
            "Kolorea: plakak {plate_mm} mm-ko lodiera du, eta {plate_mm} mm-tik gorako guztia tinta da, {ink_mm} "
            "mm-ko altuerakoa. Material anitzeko inprimagailu batekin edo harizpi-aldaketa batekin, inprimatu zuriz "
            "{plate_mm} mm arte eta beltzez handik aurrera: laminatzailean, jarri kolore-aldaketa {plate_mm} mm-tan "
            "hasten den geruzan. Kolore bakarrarekin, inprimatu pieza osoa zuriz eta margotu erliebeko zatiak "
            "errotulagailu iraunkor beltz batekin.",
            "Koadro grisa tintaren gainerakoa baino {grey_mm} mm altuago dago: aldatu harizpi grisera "
            "{grey_from} mm-tan hasten den geruzan, eta koadroak bakarrik jarraituko du, bi geruza gris "
            "beltzaren gainean. Beltz geratzen bada, aplikazioak kamerako kolore-erreferentzia hartzen du; "
            "bisiten artean alderagarriak diren koloreetarako, moztu koadro gris bat paperezko orritik "
            "(Ezarpenak > Erreferentzia-txartela; orriak ordezko koadroak ditu behean) eta itsatsi gainean.",
            "Harizpi mate eta argia: gainazal distiratsuek islatu egiten dute eta markatzaileak ezkutatzen dituzte. "
            "Egiaztatu pieza erregela batekin erabili aurretik.",
        ],
    ),
    "fr": (
        "Carte de référence neVus v1, pour impression 3D",
        [
            "Un STL par pièce : nevus-card-v1.stl (la carte à fenêtre, {card_w} x {card_h} mm) et nevus-strip-v1.stl "
            "(la bande, {strip_w} x {strip_h} mm). Chaque fichier contient la plaque et l'encre en relief ensemble ; "
            "l'encre s'enfonce de {overlap_mm} mm dans la plaque et le trancheur réunit les deux coques en un seul "
            "solide (PrusaSlicer, Bambu Studio, Orca et Cura le font par défaut). Échelle 100 %, couches de 0,2 mm, "
            "sans supports, face plate sur le plateau.",
            "Couleur : la plaque fait {plate_mm} mm d'épaisseur et tout ce qui dépasse {plate_mm} mm est de l'encre, "
            "haute de {ink_mm} mm. Avec une imprimante multimatériau ou un changement de filament, imprimez en blanc "
            "jusqu'à {plate_mm} mm puis en noir à partir de là : dans le trancheur, placez le changement de couleur à "
            "la couche qui commence à {plate_mm} mm. Avec une seule couleur, imprimez toute la pièce en blanc et "
            "peignez les parties en relief avec un marqueur permanent noir.",
            "Le carré gris dépasse de {grey_mm} mm le reste de l'encre : passez au filament gris à la couche qui "
            "commence à {grey_from} mm et seul le carré continue, avec deux couches de gris sur le noir. S'il "
            "reste noir, l'application prend sa référence de couleur à partir de la caméra ; pour des couleurs "
            "comparables d'une visite à l'autre, découpez un carré gris dans la feuille de papier (Réglages > "
            "Carte de référence ; la feuille comporte des carrés de rechange en bas) et collez-le dessus.",
            "Filament mat et clair : les surfaces brillantes reflètent la lumière et masquent les repères. Vérifiez "
            "la pièce avec une règle avant de l'utiliser.",
        ],
    ),
    "it": (
        "Tessera di riferimento neVus v1, per la stampa 3D",
        [
            "Un STL per pezzo: nevus-card-v1.stl (la tessera con finestra, {card_w} x {card_h} mm) e "
            "nevus-strip-v1.stl (la striscia, {strip_w} x {strip_h} mm). Ogni file contiene insieme la base e "
            "l'inchiostro in rilievo; l'inchiostro affonda di {overlap_mm} mm nella base e lo slicer unisce i due "
            "gusci in un unico solido (PrusaSlicer, Bambu Studio, Orca e Cura lo fanno per impostazione predefinita). "
            "Scala 100 %, strati da 0,2 mm, senza supporti, lato piano verso il basso.",
            "Colore: la base è spessa {plate_mm} mm e tutto ciò che sta sopra {plate_mm} mm è inchiostro, alto "
            "{ink_mm} mm. Con una stampante multimateriale o un cambio di filamento, stampa in bianco fino a "
            "{plate_mm} mm e in nero da lì in poi: nello slicer, imposta il cambio colore sullo strato che inizia a "
            "{plate_mm} mm. Con un solo colore, stampa tutto il pezzo in bianco e dipingi le parti in rilievo con un "
            "pennarello indelebile nero.",
            "Il riquadro grigio sporge di {grey_mm} mm sopra il resto dell'inchiostro: passa al filamento grigio "
            "allo strato che inizia a {grey_from} mm e prosegue solo il riquadro, con due strati di grigio sopra "
            "il nero. Se resta nero, l'app prende il riferimento colore dalla fotocamera; per colori "
            "confrontabili tra una visita e l'altra, ritaglia un quadrato grigio dal foglio di carta "
            "(Impostazioni > Tessera di riferimento; il foglio ha quadrati di scorta in basso) e incollalo "
            "sopra.",
            "Filamento opaco e chiaro: le superfici lucide riflettono e nascondono i marcatori. Controlla il pezzo "
            "con un righello prima di usarlo.",
        ],
    ),
    "de": (
        "neVus-Referenzkarte v1 zum 3D-Drucken",
        [
            "Eine STL-Datei pro Teil: nevus-card-v1.stl (die Karte mit Fenster, {card_w} x {card_h} mm) und "
            "nevus-strip-v1.stl (der Streifen, {strip_w} x {strip_h} mm). Jede Datei enthält die Platte und die "
            "erhabene Farbe zusammen; die Farbe reicht {overlap_mm} mm in die Platte hinein, und der Slicer vereint "
            "die beiden Hüllen zu einem Körper (PrusaSlicer, Bambu Studio, Orca und Cura tun das standardmäßig). "
            "Maßstab 100 %, 0,2-mm-Schichten, keine Stützen, glatte Seite nach unten.",
            "Farbe: Die Platte ist {plate_mm} mm dick, und alles oberhalb von {plate_mm} mm ist Farbe, {ink_mm} mm "
            "hoch. Mit einem Multimaterial-Drucker oder einem Filamentwechsel druckst du bis {plate_mm} mm in Weiß "
            "und ab da in Schwarz: Setze im Slicer den Farbwechsel auf die Schicht, die bei {plate_mm} mm beginnt. "
            "Mit nur einer Farbe druckst du das ganze Teil in Weiß und bemalst die erhabenen Teile mit einem "
            "schwarzen Permanentmarker.",
            "Das graue Feld steht {grey_mm} mm über der übrigen Farbe: Wechsle bei der Schicht, die bei "
            "{grey_from} mm beginnt, auf graues Filament; dann geht nur das Feld weiter, mit zwei Schichten Grau "
            "über dem Schwarz. Bleibt es schwarz, nimmt die App ihre Farbreferenz von der Kamera; für Farben, "
            "die sich über mehrere Besuche vergleichen lassen, schneide ein graues Quadrat aus dem Papierbogen "
            "aus (Einstellungen > Referenzkarte; der Bogen enthält unten Ersatzquadrate) und klebe es darauf.",
            "Helles, mattes Filament: Glänzende Oberflächen spiegeln und verdecken die Markierungen. Prüfe das Teil "
            "vor dem Gebrauch mit einem Lineal.",
        ],
    ),
    "nl": (
        "neVus-referentiekaart v1, om te 3D-printen",
        [
            "Eén STL per onderdeel: nevus-card-v1.stl (de kaart met venster, {card_w} x {card_h} mm) en "
            "nevus-strip-v1.stl (de strip, {strip_w} x {strip_h} mm). Elk bestand bevat de plaat en de verhoogde inkt "
            "samen; de inkt zakt {overlap_mm} mm in de plaat en de slicer voegt de twee schalen samen tot één massief "
            "geheel (PrusaSlicer, Bambu Studio, Orca en Cura doen dat standaard). Schaal 100 %, lagen van 0,2 mm, "
            "geen supports, vlakke kant naar beneden.",
            "Kleur: de plaat is {plate_mm} mm dik en alles boven {plate_mm} mm is inkt, {ink_mm} mm hoog. Met een "
            "multimaterial-printer of een filamentwissel print je wit tot {plate_mm} mm en zwart vanaf daar: stel in "
            "de slicer de kleurwissel in op de laag die begint bij {plate_mm} mm. Met één kleur print je het hele "
            "onderdeel wit en schilder je de verhoogde delen met een zwarte permanente marker.",
            "Het grijze vlak steekt {grey_mm} mm boven de rest van de inkt uit: wissel naar grijs filament bij "
            "de laag die op {grey_from} mm begint, en alleen het vlak gaat door, met twee lagen grijs over het "
            "zwart. Blijft het zwart, dan haalt de app de kleurreferentie uit de camera; voor kleuren die je "
            "tussen bezoeken kunt vergelijken, knip je een grijs vierkantje uit het papieren vel (Instellingen > "
            "Referentiekaart; het vel heeft onderaan reservevierkantjes) en plak je het erop.",
            "Licht, mat filament: glanzende oppervlakken reflecteren en verbergen de markeringen. Controleer het "
            "onderdeel met een liniaal voordat je het gebruikt.",
        ],
    ),
    "pl": (
        "Karta referencyjna neVus v1 do druku 3D",
        [
            "Jeden plik STL na element: nevus-card-v1.stl (karta z oknem, {card_w} x {card_h} mm) i "
            "nevus-strip-v1.stl (pasek, {strip_w} x {strip_h} mm). Każdy plik zawiera razem płytkę i wypukły tusz; "
            "tusz zanurza się {overlap_mm} mm w płytce, a slicer łączy obie powłoki w jedną bryłę (PrusaSlicer, Bambu "
            "Studio, Orca i Cura robią to domyślnie). Skala 100 %, warstwy 0,2 mm, bez podpór, płaską stroną do dołu.",
            "Kolor: płytka ma {plate_mm} mm grubości, a wszystko powyżej {plate_mm} mm to tusz o wysokości {ink_mm} "
            "mm. Na drukarce wielomateriałowej lub ze zmianą filamentu drukuj na biało do {plate_mm} mm, a od tej "
            "wysokości na czarno: w slicerze ustaw zmianę koloru na warstwie zaczynającej się na {plate_mm} mm. Przy "
            "jednym kolorze wydrukuj całość na biało, a wypukłe części pomaluj czarnym markerem permanentnym.",
            "Szare pole wystaje {grey_mm} mm ponad resztę tuszu: zmień filament na szary na warstwie "
            "zaczynającej się na {grey_from} mm, a dalej drukuje się tylko pole, dwie warstwy szarości na "
            "czerni. Jeśli zostanie czarne, aplikacja bierze odniesienie kolorystyczne z aparatu; aby kolory "
            "dały się porównywać między wizytami, wytnij szary kwadrat z papierowego arkusza (Ustawienia > Karta "
            "referencyjna; na dole arkusza są zapasowe kwadraty) i przyklej go na wierzch.",
            "Jasny, matowy filament: błyszczące powierzchnie odbijają światło i zasłaniają znaczniki. Przed użyciem "
            "sprawdź element linijką.",
        ],
    ),
    "ru": (
        "Эталонная карточка neVus v1 для 3D-печати",
        [
            "По одному STL на деталь: nevus-card-v1.stl (карточка с окном, {card_w} x {card_h} мм) и "
            "nevus-strip-v1.stl (полоска, {strip_w} x {strip_h} мм). В каждом файле пластина и рельефная краска "
            "вместе; краска уходит в пластину на {overlap_mm} мм, а слайсер объединяет две оболочки в одно тело "
            "(PrusaSlicer, Bambu Studio, Orca и Cura делают это по умолчанию). Масштаб 100 %, слои 0,2 мм, без "
            "поддержек, плоской стороной вниз.",
            "Цвет: пластина толщиной {plate_mm} мм, всё выше {plate_mm} мм — краска высотой {ink_mm} мм. На "
            "многоматериальном принтере или со сменой филамента печатайте белым до {plate_mm} мм и чёрным выше: в "
            "слайсере поставьте смену цвета на слой, который начинается на {plate_mm} мм. Если цвет один, напечатайте "
            "всю деталь белым, а рельефные части закрасьте чёрным перманентным маркером.",
            "Серое поле выступает на {grey_mm} мм над остальной краской: смените филамент на серый на слое, "
            "который начинается на {grey_from} мм, и дальше печатается только поле, два слоя серого поверх "
            "чёрного. Если оно останется чёрным, приложение берёт цветовой эталон с камеры; чтобы цвета можно "
            "было сравнивать между визитами, вырежьте серый квадрат из бумажного листа (Настройки > Эталонная "
            "карточка; внизу листа есть запасные квадраты) и наклейте его сверху.",
            "Светлый матовый филамент: глянцевые поверхности отражают свет и скрывают маркеры. Перед использованием "
            "проверьте деталь линейкой.",
        ],
    ),
    "tr": (
        "neVus referans kartı v1, 3D baskı için",
        [
            "Parça başına bir STL: nevus-card-v1.stl (pencereli kart, {card_w} x {card_h} mm) ve nevus-strip-v1.stl "
            "(şerit, {strip_w} x {strip_h} mm). Her dosya plakayı ve kabartma mürekkebi birlikte içerir; mürekkep "
            "plakaya {overlap_mm} mm gömülür ve dilimleyici iki kabuğu tek bir katı hâlinde birleştirir (PrusaSlicer, "
            "Bambu Studio, Orca ve Cura bunu varsayılan olarak yapar). % 100 ölçek, 0,2 mm katmanlar, destek yok, düz "
            "yüz aşağıda.",
            "Renk: plaka {plate_mm} mm kalınlığındadır ve {plate_mm} mm üzerindeki her şey {ink_mm} mm yüksekliğinde "
            "mürekkeptir. Çok malzemeli bir yazıcıyla veya filament değişimiyle {plate_mm} mm'ye kadar beyaz, oradan "
            "sonra siyah basın: dilimleyicide renk değişimini {plate_mm} mm'de başlayan katmana ayarlayın. Tek renkle "
            "parçanın tamamını beyaz basın ve kabartmalı kısımları siyah kalıcı bir kalemle boyayın.",
            "Gri alan mürekkebin geri kalanından {grey_mm} mm yüksektir: {grey_from} mm'de başlayan katmanda gri "
            "filamente geçin; yalnızca alan devam eder, siyahın üzerine iki kat gri. Siyah kalırsa uygulama renk "
            "referansını kameradan alır; ziyaretler arasında karşılaştırılabilir renkler için kâğıt sayfadan gri "
            "bir kare kesin (Ayarlar > Referans kartı; sayfanın altında yedek kareler vardır) ve üstüne "
            "yapıştırın.",
            "Açık renkli mat filament: parlak yüzeyler yansır ve işaretleyicileri gizler. Parçayı kullanmadan önce "
            "cetvelle kontrol edin.",
        ],
    ),
    "id": (
        "Kartu referensi neVus v1, untuk cetak 3D",
        [
            "Satu STL per bagian: nevus-card-v1.stl (kartu berjendela, {card_w} x {card_h} mm) dan nevus-strip-v1.stl "
            "(strip, {strip_w} x {strip_h} mm). Setiap berkas memuat pelat dan tinta timbul sekaligus; tinta terbenam "
            "{overlap_mm} mm ke dalam pelat dan slicer menyatukan kedua cangkang menjadi satu benda padat "
            "(PrusaSlicer, Bambu Studio, Orca, dan Cura melakukannya secara bawaan). Skala 100 %, lapisan 0,2 mm, "
            "tanpa penyangga, sisi rata menghadap bawah.",
            "Warna: pelat setebal {plate_mm} mm dan semua yang berada di atas {plate_mm} mm adalah tinta setinggi "
            "{ink_mm} mm. Dengan printer multi-material atau pergantian filamen, cetak putih sampai {plate_mm} mm dan "
            "hitam dari situ: di slicer, atur pergantian warna pada lapisan yang dimulai di {plate_mm} mm. Dengan "
            "satu warna, cetak seluruh bagian dengan warna putih dan cat bagian timbulnya dengan spidol permanen "
            "hitam.",
            "Bidang abu-abu menonjol {grey_mm} mm di atas tinta lainnya: ganti ke filamen abu-abu pada lapisan "
            "yang dimulai di {grey_from} mm, dan hanya bidang itu yang berlanjut, dua lapis abu-abu di atas "
            "hitam. Jika tetap hitam, aplikasi mengambil acuan warna dari kamera; agar warna dapat dibandingkan "
            "antarkunjungan, gunting satu kotak abu-abu dari lembar kertas (Pengaturan > Kartu referensi; lembar "
            "itu memuat kotak cadangan di bagian bawah) dan tempelkan di atasnya.",
            "Filamen matte berwarna terang: permukaan mengilap memantulkan cahaya dan menyembunyikan penanda. Periksa "
            "bagian itu dengan penggaris sebelum dipakai.",
        ],
    ),
    "zh": (
        "neVus 参考卡 v1（3D 打印）",
        [
            "每个部件一个 STL 文件：nevus-card-v1.stl（带窗口的卡片，{card_w} x {card_h} 毫米）和 "
            "nevus-strip-v1.stl（长条，{strip_w} x {strip_h} 毫米）。每个文件都包含底板和凸起的墨层；墨层嵌入底板 "
            "{overlap_mm} 毫米，切片软件会把两个壳体合并为一个实体（PrusaSlicer、Bambu Studio、Orca 和 Cura "
            "默认都会这样做）。缩放 100 %，层高 0.2 毫米，不加支撑，平面朝下。",
            "颜色：底板厚 {plate_mm} 毫米，高于 {plate_mm} 毫米的部分都是墨层，高 {ink_mm} "
            "毫米。使用多材料打印机或中途换料时，到 {plate_mm} "
            "毫米为止打印白色，之后打印黑色：在切片软件中，把换色设在从 {plate_mm} "
            "毫米开始的那一层。只有一种颜色时，整件用白色打印，再用黑色油性记号笔涂满凸起部分。",
            "灰色块比其余墨层高出 {grey_mm} 毫米：在从 {grey_from} 毫"
            "米开始的那一层换成灰色耗材，之后只有灰色块继续打印，黑色上面盖两层灰色。若保持黑"
            "色，应用会改用相机获取颜色参考；若想让不同次拍摄的颜色可以比较，请从纸质页（设置"
            " > 参考卡；纸页底部带有备用方块）上剪下一个灰色方块，贴在上面。",
            "浅色哑光耗材：光面表面会反光，遮住定位标记。使用前请用尺子检查部件。",
        ],
    ),
    "ja": (
        "neVus リファレンスカード v1（3Dプリント用）",
        [
            "パーツごとに1つのSTLファイル：nevus-card-v1.stl（窓付きカード、{card_w} x {card_h} mm）と "
            "nevus-strip-v1.stl（ストリップ、{strip_w} x {strip_h} mm）。各ファイルにはプレートと盛り上がっ"
            "たインクが一緒に入っています。インクはプレートに {overlap_mm} mm 食い込み、スライサーが2つのシェルを1つの"
            "ソリッドにまとめます（PrusaSlicer、Bambu Studio、Orca、Cura は標準でそうします）。倍率100 %、積層0.2 "
            "mm、サポートなし、平らな面を下にします。",
            "色：プレートの厚さは {plate_mm} mm で、{plate_mm} mm より上はすべて高さ {ink_mm} mm "
            "のインクです。マルチマテリアルプリンターやフィラメント交換が使える場合は、{plate_mm} mm "
            "まで白、そこから上を黒で造形します。スライサーで、{plate_mm} mm から始まる層に色替えを設定してください。"
            "1色の場合は全体を白で造形し、盛り上がった部分を黒の油性マーカーで塗ります。",
            "グレーの四角はほかのインクより {grey_mm} mm 高くなっています。{g"
            "rey_from} mm から始まる層でグレーのフィラメントに替えると、四角だけ"
            "が続き、黒の上にグレーが2層重なります。黒のままの場合、アプリはカメラから色の基"
            "準を取ります。訪問をまたいで色を比べたいときは、紙のシート（設定 > リファレン"
            "スカード。シートの下部に予備の四角があります）からグレーの四角を切り取り、上に貼"
            "ってください。",
            "明るい色のマットなフィラメントを使ってください。光沢のある表面は反射してマーカー"
            "を隠します。使う前に、定規で寸法を確認してください。",
        ],
    ),
    "ko": (
        "neVus 참조 카드 v1, 3D 프린트용",
        [
            "부품마다 STL 하나: nevus-card-v1.stl(창이 있는 카드, {card_w} x {card_h} mm)과 nevus-strip-v1.stl(띠, "
            "{strip_w} x {strip_h} mm). 각 파일에는 판과 돌출된 잉크가 함께 들어 있습니다. 잉크는 판 속으로 "
            "{overlap_mm} mm 파고들고, 슬라이서가 두 껍데기를 하나의 솔리드로 합칩니다(PrusaSlicer, Bambu Studio, "
            "Orca, Cura는 기본적으로 그렇게 합니다). 배율 100 %, 레이어 0.2 mm, 서포트 없음, 평평한 면이 아래로 가게 "
            "놓으세요.",
            "색: 판 두께는 {plate_mm} mm이고 {plate_mm} mm보다 위는 모두 높이 {ink_mm} mm의 잉크입니다. 멀티 머티리얼 "
            "프린터나 필라멘트 교체를 쓸 수 있다면 {plate_mm} mm까지는 흰색, 그 위는 검은색으로 출력하세요. "
            "슬라이서에서 {plate_mm} mm에서 시작하는 레이어에 색 변경을 지정하면 됩니다. 한 가지 색만 쓴다면 전체를 "
            "흰색으로 출력하고, 돌출된 부분은 검은색 유성 마커로 칠하세요.",
            "회색 사각형은 나머지 잉크보다 {grey_mm} mm 높습니다. {gre"
            "y_from} mm에서 시작하는 레이어에서 회색 필라멘트로 바꾸면 사각형"
            "만 계속 출력되어 검은색 위에 회색이 두 겹 쌓입니다. 검은색으로 두면 "
            "앱이 카메라에서 색 기준을 가져옵니다. 방문 간에 색을 비교하려면 종이 "
            "시트(설정 > 참조 카드, 시트 아래쪽에 여분의 사각형이 있습니다)에서 "
            "회색 사각형을 오려 위에 붙이세요.",
            "밝은 무광 필라멘트를 쓰세요. 광택 있는 표면은 빛을 반사해 마커를 가립니다. 사용하기 전에 자로 크기를 "
            "확인하세요.",
        ],
    ),
    "hi": (
        "neVus संदर्भ कार्ड v1, 3D प्रिंटिंग के लिए",
        [
            "हर हिस्से के लिए एक STL: nevus-card-v1.stl (खिड़की वाला कार्ड, {card_w} x {card_h} mm) और "
            "nevus-strip-v1.stl (पट्टी, {strip_w} x {strip_h} mm)। हर फ़ाइल में प्लेट और उभरी हुई स्याही साथ-साथ होती "
            "हैं; स्याही प्लेट में {overlap_mm} mm धँसी होती है और स्लाइसर दोनों खोलों को एक ठोस आकृति में जोड़ देता "
            "है (PrusaSlicer, Bambu Studio, Orca और Cura डिफ़ॉल्ट रूप से ऐसा करते हैं)। स्केल 100 %, 0.2 mm की परतें, "
            "बिना सपोर्ट के, सपाट तरफ़ नीचे।",
            "रंग: प्लेट {plate_mm} mm मोटी है और {plate_mm} mm से ऊपर का सब कुछ स्याही है, जिसकी ऊँचाई {ink_mm} mm "
            "है। मल्टी-मटेरियल प्रिंटर या फ़िलामेंट बदलने की सुविधा हो तो {plate_mm} mm तक सफ़ेद और वहाँ से काला "
            "प्रिंट करें: स्लाइसर में रंग बदलने की जगह उस परत पर रखें जो {plate_mm} mm से शुरू होती है। एक ही रंग हो "
            "तो पूरा हिस्सा सफ़ेद प्रिंट करें और उभरे हिस्सों को काले परमानेंट मार्कर से रँग दें।",
            "स्लेटी वर्ग बाकी स्याही से {grey_mm} mm ऊँचा है: {grey_from} mm से शुरू होने वाली परत पर स्लेटी "
            "फ़िलामेंट लगाएँ, तब सिर्फ़ वर्ग आगे छपेगा, काले के ऊपर स्लेटी की दो परतें। काला रहने पर ऐप रंग का "
            "संदर्भ कैमरे से लेता है; अलग-अलग बार के रंगों की तुलना हो सके, इसके लिए काग़ज़ की शीट (सेटिंग > "
            "संदर्भ कार्ड; शीट के नीचे अतिरिक्त वर्ग होते हैं) से एक स्लेटी वर्ग काटें और उसे ऊपर चिपका दें।",
            "हल्का मैट फ़िलामेंट: चमकदार सतहें चमक लौटाती हैं और मार्कर छिपा देती हैं। इस्तेमाल से पहले हिस्से को स्केल से जाँच लें।",
        ],
    ),
    "ar": (
        "بطاقة neVus المرجعية الإصدار 1، للطباعة ثلاثية الأبعاد",
        [
            "ملف STL لكل قطعة: nevus-card-v1.stl (البطاقة ذات النافذة، {card_w} x {card_h} mm) وnevus-strip-v1.stl "
            "(الشريط، {strip_w} x {strip_h} mm). يضم كل ملف اللوحة والحبر البارز معًا؛ يغوص الحبر {overlap_mm} mm "
            "داخل اللوحة ويدمج برنامج التقطيع القشرتين في جسم صلب واحد (يفعل ذلك PrusaSlicer وBambu Studio وOrca "
            "وCura افتراضيًا). المقياس 100 %، طبقات 0.2 mm، بلا دعامات، والوجه المسطح إلى الأسفل.",
            "اللون: سماكة اللوحة {plate_mm} mm، وكل ما يعلو {plate_mm} mm هو حبر بارتفاع {ink_mm} mm. مع طابعة متعددة "
            "المواد أو تغيير الخيط، اطبع باللون الأبيض حتى {plate_mm} mm وبالأسود من هناك: في برنامج التقطيع، اضبط "
            "تغيير اللون عند الطبقة التي تبدأ عند {plate_mm} mm. مع لون واحد، اطبع القطعة كلها بالأبيض وارسم الأجزاء "
            "البارزة بقلم تحديد دائم أسود.",
            "يرتفع المربع الرمادي {grey_mm} mm فوق بقية الحبر: بدّل إلى خيط رمادي عند الطبقة التي تبدأ عند "
            "{grey_from} mm، فلا يكمل إلا المربع، بطبقتين من الرمادي فوق الأسود. وإن بقي أسود، يأخذ التطبيق مرجع "
            "اللون من الكاميرا؛ وللحصول على ألوان قابلة للمقارنة بين الزيارات، قصّ مربعًا رماديًا من الورقة "
            "المطبوعة (الإعدادات > البطاقة المرجعية؛ تحمل الورقة مربعات احتياطية في أسفلها) والصقه فوقه.",
            "خيط طباعة فاتح ومطفي: الأسطح اللامعة تعكس الضوء وتخفي المؤشرات. افحص القطعة بمسطرة قبل استخدامها.",
        ],
    ),
}


def _mm(value: float, lang: str) -> str:
    text = f"{value:g}"
    return text.replace(".", ",") if catalogue(normalise(lang))["decimal_comma"] else text


def readme(lang: str = "en") -> str:
    """How to print the pieces, with the height at which the colour changes from plate to ink."""
    title, paragraphs = README_TEXT.get(lang, README_TEXT["en"])
    values = {
        "plate_mm": PLATE_MM,
        "ink_mm": INK_MM,
        "overlap_mm": OVERLAP_MM,
        "grey_mm": GREY_MM,
        "grey_from": INK_Z1,
        "card_w": WINDOW.width + 2 * PLATE_MARGIN_MM,
        "card_h": WINDOW.height + 2 * PLATE_MARGIN_MM,
        "strip_w": STRIP.width + 2 * PLATE_MARGIN_MM,
        "strip_h": STRIP.height + 2 * PLATE_MARGIN_MM,
    }
    numbers = {key: _mm(value, lang) for key, value in values.items()}
    # Scripts without spaces stay on one line rather than being cut mid-word, file names among them.
    body = "\n\n".join(
        textwrap.fill(paragraph.format(**numbers), 100, break_long_words=False, break_on_hyphens=False)
        for paragraph in paragraphs
    )
    return f"{title}\n\n{body}\n"


def archive(lang: str = "en") -> bytes:
    """A zip with one STL per piece, the window card and the strip, and a note on how to print them."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for card, name in ((WINDOW, "card"), (STRIP, "strip")):
            zf.writestr(f"nevus-{name}-v1.stl", mesh(card).stl(f"neVus reference card v1: {name}"))
        zf.writestr("README.txt", readme(lang))
    return buffer.getvalue()
