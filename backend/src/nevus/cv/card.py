# SPDX-License-Identifier: AGPL-3.0-only
"""The neVus reference card, version 1: one geometry for the printable sheet and for the detector.

Coordinates are millimetres from the top-left corner of each card. The card and its detector cannot
disagree, because both read these constants (docs/design/REFERENCE_CARD_SPEC.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

DICTIONARY = cv2.aruco.DICT_4X4_50
MARKER_MM = 12.0
CARD_VERSION = 1


@dataclass(frozen=True)
class CardGeometry:
    name: str
    width: float
    height: float
    markers: dict[int, tuple[float, float]]
    """Marker id -> centre in millimetres."""
    centre: tuple[float, float]
    """Where the measured mark sits: the aperture centre, or the middle of the strip."""
    grey: tuple[float, float, float, float]
    white: tuple[float, float, float, float]
    baseline: float
    """Longest distance between marker centres; the lever arm for the scale uncertainty."""


WINDOW = CardGeometry(
    name="window",
    width=85.6,
    height=54.0,
    markers={0: (12.8, 7.0), 1: (72.8, 7.0), 2: (12.8, 47.0), 3: (72.8, 47.0)},
    centre=(42.8, 27.0),
    grey=(74.0, 22.0, 8.0, 8.0),
    white=(74.0, 32.0, 8.0, 8.0),
    baseline=math.hypot(60.0, 40.0),
)
STRIP = CardGeometry(
    name="strip",
    width=60.0,
    height=20.0,
    markers={4: (8.0, 10.0), 5: (52.0, 10.0)},
    centre=(30.0, 10.0),
    grey=(18.0, 1.5, 6.0, 6.0),
    white=(36.0, 1.5, 6.0, 6.0),
    baseline=44.0,
)
CARDS = (WINDOW, STRIP)
APERTURE_RADIUS = 12.0


def card_for_ids(ids: set[int]) -> CardGeometry | None:
    """The card version is told by its marker ids; a mix of cards in one photo is ambiguous."""
    for card in CARDS:
        if len(ids & set(card.markers)) >= 2:
            return card
    return None


def marker_corners_mm(card: CardGeometry, marker_id: int) -> list[tuple[float, float]]:
    """Corners in ArUco order: top-left, top-right, bottom-right, bottom-left."""
    cx, cy = card.markers[marker_id]
    h = MARKER_MM / 2
    return [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]


def marker_cells(marker_id: int) -> np.ndarray:
    """6 x 6 cells (border included), 1 = black."""
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARY)
    image = cv2.aruco.generateImageMarker(dictionary, marker_id, 6, borderBits=1)
    return (image < 128).astype(np.uint8)


class Painter(Protocol):
    def fill_gray(self, level: float) -> None: ...
    def stroke_gray(self, level: float) -> None: ...
    def line_width(self, mm: float) -> None: ...
    def rect(self, x: float, y: float, w: float, h: float, *, fill: bool = True, stroke: bool = False) -> None: ...
    def rects(self, boxes: list[tuple[float, float, float, float]]) -> None: ...
    def line(self, x1: float, y1: float, x2: float, y2: float) -> None: ...
    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None: ...
    def text(
        self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left"
    ) -> None: ...


def draw_card(p: Painter, card: CardGeometry, ox: float, oy: float, *, cut_aperture: bool = True) -> None:
    """Draw one card with its top-left corner at (ox, oy) in the painter's millimetres."""
    p.stroke_gray(0.0)
    p.line_width(0.3)
    p.fill_gray(1.0)
    p.rect(ox, oy, card.width, card.height, fill=True, stroke=True)
    for marker_id, (cx, cy) in card.markers.items():
        cells = marker_cells(marker_id)
        cell = MARKER_MM / 6
        p.fill_gray(0.0)
        left, top = ox + cx - MARKER_MM / 2, oy + cy - MARKER_MM / 2
        boxes: list[tuple[float, float, float, float]] = []
        for row in range(6):
            col = 0
            while col < 6:  # one box per horizontal run of black cells
                if not cells[row, col]:
                    col += 1
                    continue
                start = col
                while col < 6 and cells[row, col]:
                    col += 1
                boxes.append((left + start * cell, top + row * cell, (col - start) * cell, cell))
        p.rects(boxes)
    gx, gy, gw, gh = card.grey
    p.fill_gray(0x77 / 255)
    p.rect(ox + gx, oy + gy, gw, gh)
    wx, wy, ww, wh = card.white
    p.fill_gray(1.0)
    p.line_width(0.1)
    p.rect(ox + wx, oy + wy, ww, wh, fill=True, stroke=True)
    p.fill_gray(0.0)
    if card is WINDOW:
        cx, cy = card.centre
        # Ink ring around the aperture, then millimetre ticks along its outer edge.
        p.line_width(1.5)
        p.circle(ox + cx, oy + cy, APERTURE_RADIUS + 0.75)
        p.line_width(0.2)
        outer = APERTURE_RADIUS + 1.5
        circumference = 2 * math.pi * APERTURE_RADIUS
        ticks = round(circumference)
        for i in range(ticks):
            angle = 2 * math.pi * i / ticks
            length = 3.0 if i % 5 == 0 else 2.0
            p.line(
                ox + cx + outer * math.cos(angle),
                oy + cy + outer * math.sin(angle),
                ox + cx + (outer + length) * math.cos(angle),
                oy + cy + (outer + length) * math.sin(angle),
            )
        if cut_aperture:
            p.line_width(0.3)
            p.circle(ox + cx, oy + cy, APERTURE_RADIUS)
        p.text(ox + cx, oy + 4.6, "neVus  ·  card v1  ·  24 mm", 2.2, bold=True, align="center")
    else:
        # 30 mm scale between the markers, ticks every millimetre.
        p.line_width(0.2)
        y = oy + 15.0
        p.line(ox + 15.0, y, ox + 45.0, y)
        for i in range(31):
            length = 2.5 if i % 5 == 0 else 1.5
            p.line(ox + 15.0 + i, y, ox + 15.0 + i, y + length)
        p.text(ox + 30.0, oy + 11.5, "neVus strip v1", 1.8, bold=True, align="center")
