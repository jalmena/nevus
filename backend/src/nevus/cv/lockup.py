# SPDX-License-Identifier: AGPL-3.0-only
"""The neVus lockup, mark and wordmark, as raised boxes for the printed card.

The identity ships the wordmark as outlines (`reports/assets/wordmark.svg`, the file the report header
uses): four glyphs as paths and the mark as a nested drawing of lines and circles. Reading that file here
means the printed card carries the lockup as approved and follows it if it ever changes. The shapes are
rasterised on a fine grid and turned into boxes, one per run of ink, merged down the columns: the slicer
unites them, and steps of a tenth of a millimetre are well below what a nozzle can draw.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files

import cv2
import numpy as np

PAPER = {"#f6f1ea", "#17161a"}  # the identity's paper colours: a shape filled with one is a hole
SHIFT = 8  # fixed-point bits for sub-cell edges when rasterising
CURVE_STEPS = 8
_TOKEN = re.compile(r"[MmLlHhVvQqCcZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ATTR = re.compile(r'([\w:-]+)="([^"]*)"')

Box = tuple[float, float, float, float]  # x, y, width, height in mm from the lockup's top-left corner


@dataclass
class Shapes:
    """The lockup's shapes on the wordmark's grid: y down, baseline at 0, cap height 100 px."""

    polygons: list[list[np.ndarray]] = field(default_factory=list)  # contours per glyph, filled even-odd
    quads: list[np.ndarray] = field(default_factory=list)  # the mark's legs, four corners each
    discs: list[tuple[float, float, float, bool]] = field(default_factory=list)  # cx, cy, r, ink (else a hole)

    def extent(self) -> tuple[float, float, float, float]:
        """The ink's bounding box: left, top, right, bottom."""
        points = [c for glyph in self.polygons for c in glyph] + self.quads
        xs = np.concatenate(
            [c[:, 0] for c in points] + [np.array([cx - r, cx + r]) for cx, _, r, ink in self.discs if ink]
        )
        ys = np.concatenate(
            [c[:, 1] for c in points] + [np.array([cy - r, cy + r]) for _, cy, r, ink in self.discs if ink]
        )
        return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def _attrs(tag: str) -> dict[str, str]:
    return {k.split(":")[-1]: v for k, v in _ATTR.findall(tag)}


def _path(d: str) -> list[np.ndarray]:
    """An SVG path (M, L, H, V, Q, C, Z, absolute or relative) flattened into closed contours."""
    tokens = _TOKEN.findall(d)
    contours: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    x = y = start_x = start_y = 0.0
    command = "M"
    i = 0

    def number() -> float:
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    def close() -> None:
        nonlocal current
        if len(current) >= 3:
            contours.append(current)
        current = []

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command in "Zz":
                close()
                x, y = start_x, start_y
                continue
        relative = command.islower()
        kind = command.upper()
        if kind == "M":
            px, py = number(), number()
            x, y = (x + px, y + py) if relative else (px, py)
            close()
            current = [(x, y)]
            start_x, start_y = x, y
            command = "l" if relative else "L"  # further pairs are line segments
        elif kind == "L":
            px, py = number(), number()
            x, y = (x + px, y + py) if relative else (px, py)
            current.append((x, y))
        elif kind == "H":
            px = number()
            x = x + px if relative else px
            current.append((x, y))
        elif kind == "V":
            py = number()
            y = y + py if relative else py
            current.append((x, y))
        elif kind in {"Q", "C"}:
            count = 2 if kind == "Q" else 3
            handles = [(number(), number()) for _ in range(count)]
            if relative:
                handles = [(x + hx, y + hy) for hx, hy in handles]
            points = np.array([(x, y), *handles], np.float64)
            for t in np.linspace(0.0, 1.0, CURVE_STEPS + 1)[1:]:
                current.append(_bezier(points, float(t)))
            x, y = handles[-1]
        else:
            raise ValueError(f"unsupported path command {command!r}")
    close()
    return [np.array(c, np.float64) for c in contours]


def _bezier(points: np.ndarray, t: float) -> tuple[float, float]:
    while len(points) > 1:
        points = (1 - t) * points[:-1] + t * points[1:]
    return float(points[0][0]), float(points[0][1])


@lru_cache(maxsize=1)
def shapes() -> Shapes:
    """The lockup read from the identity's wordmark outlines."""
    text = files("nevus.reports").joinpath("assets/wordmark.svg").read_text(encoding="utf-8")
    nested = re.search(r'<svg x="[^>]*>(.*?)</svg>', text, re.S)
    if nested is None:
        raise ValueError("the wordmark has no mark in it")
    result = Shapes()
    for tag in re.findall(r"<path [^>]*/>", text[: nested.start()] + text[nested.end() :]):
        result.polygons.append(_path(_attrs(tag)["d"]))
    frame = _attrs(nested.group(0)[: nested.group(0).index(">")])
    view_x, view_y, view_w, _view_h = (float(v) for v in frame["viewBox"].split())
    scale = float(frame["width"]) / view_w
    offset = np.array([float(frame["x"]), float(frame["y"])]) - np.array([view_x, view_y]) * scale

    def place(u: float, v: float) -> np.ndarray:
        return np.array([u, v]) * scale + offset

    stroke = float(_attrs(re.search(r"<[\w:]*g [^>]*>", nested.group(1)).group(0))["stroke-width"]) * scale  # type: ignore[union-attr]
    for tag in re.findall(r"<[\w:]*line [^>]*/>", nested.group(1)):
        a = _attrs(tag)
        p, q = place(float(a["x1"]), float(a["y1"])), place(float(a["x2"]), float(a["y2"]))
        direction = (q - p) / np.linalg.norm(q - p)
        normal = np.array([-direction[1], direction[0]]) * stroke / 2
        result.quads.append(np.array([p - normal, q - normal, q + normal, p + normal]))
    for tag in re.findall(r"<[\w:]*circle [^>]*/>", nested.group(1)):
        a = _attrs(tag)
        cx, cy = place(float(a["cx"]), float(a["cy"]))
        result.discs.append((float(cx), float(cy), float(a["r"]) * scale, a.get("fill", "").lower() not in PAPER))
    return result


def boxes(cap_mm: float, step_mm: float = 0.1) -> tuple[list[Box], float, float]:
    """Raised boxes for the lockup at `cap_mm` of cap height, with the lockup's width and height in mm."""
    drawing = shapes()
    left, top, right, bottom = drawing.extent()
    cells_per_px = cap_mm / 100.0 / step_mm
    margin = 1
    width = int(np.ceil((right - left) * cells_per_px)) + 2 * margin
    height = int(np.ceil((bottom - top) * cells_per_px)) + 2 * margin
    mask = np.zeros((height, width), np.uint8)
    unit = 1 << SHIFT

    def grid(points: np.ndarray) -> np.ndarray:
        return np.round(((points - [left, top]) * cells_per_px + margin) * unit).astype(np.int32)

    for glyph in drawing.polygons:
        cv2.fillPoly(mask, [grid(c) for c in glyph], 255, cv2.LINE_AA, SHIFT)
    for quad in drawing.quads:
        cv2.fillConvexPoly(mask, grid(quad), 255, cv2.LINE_AA, SHIFT)
    for cx, cy, r, ink in drawing.discs:
        centre = grid(np.array([[cx, cy]]))[0]
        cv2.circle(
            mask,
            (int(centre[0]), int(centre[1])),
            round(r * cells_per_px * unit),
            255 if ink else 0,
            -1,
            cv2.LINE_AA,
            SHIFT,
        )
    return _merged(mask >= 128, step_mm, margin), (right - left) * cap_mm / 100.0, (bottom - top) * cap_mm / 100.0


def _merged(ink: np.ndarray, step_mm: float, margin: int) -> list[Box]:
    """One box per run of ink in a row, runs with the same extent in consecutive rows merged into one."""
    result: list[Box] = []
    open_runs: dict[tuple[int, int], int] = {}
    for row in range(ink.shape[0] + 1):
        runs: set[tuple[int, int]] = set()
        if row < ink.shape[0]:
            edges = np.diff(np.concatenate([[0], ink[row].astype(np.int8), [0]]))
            runs = set(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist(), strict=True))
        for key in [k for k in open_runs if k not in runs]:
            start = open_runs.pop(key)
            x, y = (key[0] - margin) * step_mm, (start - margin) * step_mm
            result.append((x, y, (key[1] - key[0]) * step_mm, (row - start) * step_mm))
        for key in runs:
            open_runs.setdefault(key, row)
    return result
