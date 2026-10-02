# SPDX-License-Identifier: AGPL-3.0-only
"""Draw the card into an image at a known resolution: test fixtures and on-screen previews."""

from __future__ import annotations

import cv2
import numpy as np

from nevus.cv.imageio import Img


class RasterPainter:
    def __init__(self, image: Img, px_per_mm: float, origin: tuple[float, float] = (0.0, 0.0)) -> None:
        self.image = image
        self.k = px_per_mm
        self.ox, self.oy = origin
        self._fill = 255
        self._stroke = 0
        self._width = 1

    def _p(self, x: float, y: float) -> tuple[int, int]:
        return round((x + self.ox) * self.k), round((y + self.oy) * self.k)

    def fill_gray(self, level: float) -> None:
        self._fill = round(level * 255)

    def stroke_gray(self, level: float) -> None:
        self._stroke = round(level * 255)

    def line_width(self, mm: float) -> None:
        self._width = max(1, round(mm * self.k))

    def rect(self, x: float, y: float, w: float, h: float, *, fill: bool = True, stroke: bool = False) -> None:
        p1, p2 = self._p(x, y), self._p(x + w, y + h)
        if fill:
            cv2.rectangle(self.image, p1, (p2[0] - 1, p2[1] - 1), _bgr(self._fill), -1)
        if stroke:
            cv2.rectangle(self.image, p1, p2, _bgr(self._stroke), self._width)

    def rects(self, boxes: list[tuple[float, float, float, float]]) -> None:
        for x, y, w, h in boxes:
            self.rect(x, y, w, h)

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        cv2.line(self.image, self._p(x1, y1), self._p(x2, y2), _bgr(self._stroke), self._width, cv2.LINE_AA)

    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None:
        centre, radius = self._p(cx, cy), round(r * self.k)
        if fill:
            cv2.circle(self.image, centre, radius, _bgr(self._fill), -1, cv2.LINE_AA)
        if stroke:
            cv2.circle(self.image, centre, radius, _bgr(self._stroke), self._width, cv2.LINE_AA)

    def text(self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left") -> None:
        return  # labels are for people; fixtures do not need them


def _bgr(level: int) -> tuple[int, int, int]:
    return (level, level, level)


def blank(width_mm: float, height_mm: float, px_per_mm: float, tone: int = 255) -> Img:
    out: Img = np.full((round(height_mm * px_per_mm), round(width_mm * px_per_mm), 3), tone, np.uint8)
    return out
