# SPDX-License-Identifier: AGPL-3.0-only
"""Outlines of the printed plate: a rectangle with rounded corners, and the frame that follows it.

Points go the way `card_mesh.Mesh.box` winds its polygon (along the top edge first), so a prism or a ring
built from them faces outward like every other body of the mesh.
"""

from __future__ import annotations

import math

Point = tuple[float, float]
ARC_POINTS = 8  # per corner, an even number so the corner's midpoint is a shared vertex


def corner_arcs(x: float, y: float, w: float, h: float, r: float, steps: int = ARC_POINTS) -> list[list[Point]]:
    """The four corner arcs of a rounded rectangle, top-left first and clockwise on the page, each `steps + 1`
    points from where the arc leaves one edge to where it meets the next."""
    centres = [(x + r, y + r), (x + w - r, y + r), (x + w - r, y + h - r), (x + r, y + h - r)]
    starts = [math.pi, 1.5 * math.pi, 0.0, 0.5 * math.pi]  # from the left edge, the top edge, the right, the bottom
    arcs: list[list[Point]] = []
    for (cx, cy), start in zip(centres, starts, strict=True):
        arc: list[Point] = []
        for i in range(steps + 1):
            angle = start + 0.5 * math.pi * i / steps
            arc.append((round(cx + r * math.cos(angle), 6), round(cy + r * math.sin(angle), 6)))
        arcs.append(arc)
    return arcs


def rounded_rect(x: float, y: float, w: float, h: float, r: float, steps: int = ARC_POINTS) -> list[Point]:
    """The outline of a rounded rectangle, every corner arc included, starting after the top-left corner."""
    points: list[Point] = []
    for arc in corner_arcs(x, y, w, h, r, steps):
        points.extend(arc)
    return points


def sides(x: float, y: float, w: float, h: float, r: float, steps: int = ARC_POINTS) -> list[list[Point]]:
    """The outline split into its four sides, top first and clockwise on the page, each side from the middle
    of one corner arc to the middle of the next, so the corner midpoints are shared by two sides."""
    tl, tr, br, bl = corner_arcs(x, y, w, h, r, steps)
    half = steps // 2
    return [
        tl[half:] + tr[: half + 1],
        tr[half:] + br[: half + 1],
        br[half:] + bl[: half + 1],
        bl[half:] + tl[: half + 1],
    ]
