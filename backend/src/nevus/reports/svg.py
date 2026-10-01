# SPDX-License-Identifier: AGPL-3.0-only
"""Figures drawn for reports as SVG: the size chart and the body map with its markers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from html import escape

from nevus.bodymap import View, body_map
from nevus.reports.i18n import Words
from nevus.reports.tokens import COLOURS

STEPS = [0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20]


@dataclass(frozen=True)
class Point:
    at: datetime
    value: float
    sigma: float


def y_domain(points: Sequence[Point], floor: float = 2.0) -> tuple[float, float]:
    """As in the app: never narrower than the floor or 40 % of the typical value, never below zero."""
    lo = min(p.value - p.sigma for p in points)
    hi = max(p.value + p.sigma for p in points)
    mean = sum(p.value for p in points) / len(points)
    span = max(floor, 0.4 * mean)
    if hi - lo < span:
        mid = (lo + hi) / 2
        lo, hi = mid - span / 2, mid + span / 2
    if lo < 0:
        hi, lo = hi - lo, 0.0
    return lo, hi


def ticks(lo: float, hi: float, count: int = 4) -> tuple[list[float], float, float]:
    span = max(hi - lo, 1e-6)
    step = next((s for s in STEPS if span / s <= count), STEPS[-1])
    start = (lo // step) * step
    end = -((-hi) // step) * step
    values = []
    value = start
    while value <= end + step / 2:
        values.append(round(value, 3))
        value += step
    return values, start, end


def _tick(words: Words, value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(round(value))
    return words.number(value, 1 if abs(value * 10 - round(value * 10)) < 1e-9 else 2)


def size_chart(points: Sequence[Point], words: Words, width: float = 480, height: float = 180) -> str:
    """Longest diameter over time: a 2 px line, ringed markers, the uncertainty as a light band."""
    if len(points) < 2:
        return ""
    left, right, top, bottom = 40.0, 12.0, 22.0, 24.0
    plot_w, plot_h = width - left - right, height - top - bottom
    t0 = min(p.at for p in points).timestamp()
    t1 = max(p.at for p in points).timestamp()
    pad = min(16.0, plot_w * 0.05)

    def x(at: datetime) -> float:
        if t1 == t0:
            return left + plot_w / 2
        return left + pad + (at.timestamp() - t0) / (t1 - t0) * (plot_w - 2 * pad)

    lo0, hi0 = y_domain(points)
    values, lo, hi = ticks(lo0, hi0)

    def y(value: float) -> float:
        return top + plot_h - (value - lo) / (hi - lo) * plot_h

    c = COLOURS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img">',
        f'<text x="{left - 6:.1f}" y="{top - 10:.1f}" text-anchor="end" font-size="8" fill="{c["ink-3"]}">mm</text>',
    ]
    for value in values:
        parts.append(
            f'<line x1="{left:.1f}" x2="{width - right:.1f}" y1="{y(value):.1f}" y2="{y(value):.1f}" '
            f'stroke="{c["border"]}" stroke-width="0.75"/>'
        )
        parts.append(
            f'<text x="{left - 6:.1f}" y="{y(value) + 3:.1f}" text-anchor="end" font-size="8" '
            f'fill="{c["ink-3"]}">{escape(_tick(words, value))}</text>'
        )
    upper = " ".join(f"{x(p.at):.1f},{y(p.value + p.sigma):.1f}" for p in points)
    lower = " ".join(f"{x(p.at):.1f},{y(p.value - p.sigma):.1f}" for p in reversed(points))
    parts.append(f'<polygon points="{upper} {lower}" fill="{c["chart-1"]}" fill-opacity="0.12"/>')
    line = " ".join(f"{x(p.at):.1f},{y(p.value):.1f}" for p in points)
    parts.append(
        f'<polyline points="{line}" fill="none" stroke="{c["chart-1"]}" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for p in points:
        parts.append(
            f'<circle cx="{x(p.at):.1f}" cy="{y(p.value):.1f}" r="3.5" fill="{c["chart-1"]}" '
            'stroke="#ffffff" stroke-width="1.5"/>'
        )
    last_x = -1e9
    labelled: list[tuple[int, str]] = []
    for index, p in enumerate(points):
        label = words.short_day(p.at)
        if x(p.at) - last_x >= 70 and (not labelled or labelled[-1][1] != label):
            labelled.append((index, label))
            last_x = x(p.at)
    for index, label in labelled:
        parts.append(
            f'<text x="{x(points[index].at):.1f}" y="{height - 6:.1f}" text-anchor="middle" font-size="8" '
            f'fill="{c["ink-3"]}">{escape(label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


@dataclass(frozen=True)
class Marker:
    x: float
    y: float
    label: str
    view: str
    highlighted: bool = False


def body_view(
    view: str, markers: Sequence[Marker], zone: str | None = None, height: float = 230, radius: float = 5.5
) -> str:
    """One view of the silhouette with numbered markers; the mark's own zone shaded when given."""
    data = body_map()
    side: View = "back" if view == "back" else "front"
    vx, vy, vw, vh = data.viewBox
    width = height * vw / vh
    c = COLOURS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {vw} {vh}" width="{width:.0f}" '
        f'height="{height:.0f}" role="img">',
        f'<path d="{data.views[side].silhouette}" fill="{c["surface-2"]}" stroke="{c["ink-3"]}" stroke-width="0.8"/>',
    ]
    if zone:
        shape = data.zone(zone)
        if shape is not None and shape.view == view:
            parts.append(
                f'<path d="{shape.path}" fill="{c["accent"]}" fill-opacity="0.16" stroke="{c["accent"]}" '
                'stroke-width="0.6"/>'
            )
    for m in markers:
        if m.view != view:
            continue
        cx, cy = vx + m.x * vw, vy + m.y * vh
        fill = c["accent"] if m.highlighted else c["marker"]
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius}" fill="{fill}" stroke="#ffffff" stroke-width="1.2"/>'
        )
        if m.label:
            size = radius * 1.15 if len(m.label) < 3 else radius * 0.85
            parts.append(
                f'<text x="{cx:.1f}" y="{cy + size * 0.36:.1f}" text-anchor="middle" font-size="{size:.1f}" '
                f'font-weight="600" fill="#ffffff">{escape(m.label)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)
