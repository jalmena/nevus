# SPDX-License-Identifier: AGPL-3.0-only
"""Measurement mathematics: shapes in photo pixels to millimetres, Feret diameters, area, uncertainty.

A measurement is only as good as its scale and its border, so both are carried as standard
deviations: sigma_d = sqrt((d * sigma_scale)^2 + (2 * sigma_border)^2) for a diameter, and
sigma_A = sqrt((2 * A * sigma_scale)^2 + (P * sigma_border)^2) for an area (ARCHITECTURE.md 4.7).
Two measurements differ detectably only when the difference exceeds twice its combined deviation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

# Placement uncertainty in pixels of the photo as displayed for adjusting (the 2048 px rendition).
BORDER_PX = {"assisted": 1.5, "automatic": 1.5, "manual": 2.5}
DISPLAY_LONG_EDGE = 2048
UNVERIFIED_PRINT_SIGMA = 0.010
VERIFIED_PRINT_SIGMA = 0.004
PLANE_SIGMA = {"window": 0.003, "strip": 0.010}
COIN_TILT_SIGMA = 0.012
MANUAL_TILT_SIGMA = 0.012
CHANGE_K = 2.0


@dataclass(frozen=True)
class Scale:
    kind: str
    mm_per_px: float
    sigma_scale: float
    homography: list[list[float]] | None = None
    print_factor: float = 1.0
    tilt_deg: float | None = None


def card_scale(detection: dict[str, Any], card_line_mm: float | None) -> Scale:
    """The printed card's true size: the person measured the 50 mm line, or nobody did (larger sigma)."""
    factor = (card_line_mm / 50.0) if card_line_mm else 1.0
    print_sigma = VERIFIED_PRINT_SIGMA if card_line_mm else UNVERIFIED_PRINT_SIGMA
    sigma = math.sqrt(
        float(detection["sigma_fit"]) ** 2 + print_sigma**2 + PLANE_SIGMA.get(detection["card"], 0.01) ** 2
    )
    return Scale(
        kind="card",
        mm_per_px=float(detection["mm_per_px"]) * factor,
        sigma_scale=sigma,
        homography=detection["homography"],
        print_factor=factor,
        tilt_deg=float(detection["tilt_deg"]),
    )


def coin_scale(r_px: float, diameter_mm: float, border_px: float) -> Scale:
    """A coin gives a circle but not the tilt, hence the extra term the interface mentions."""
    sigma = math.sqrt((border_px / max(r_px, 1.0)) ** 2 + COIN_TILT_SIGMA**2)
    return Scale(kind="coin", mm_per_px=diameter_mm / (2 * r_px), sigma_scale=sigma)


def manual_scale(length_px: float, length_mm: float, border_px: float) -> Scale:
    sigma = math.sqrt((2 * border_px / max(length_px, 1.0)) ** 2 + MANUAL_TILT_SIGMA**2)
    return Scale(kind="manual", mm_per_px=length_mm / length_px, sigma_scale=sigma)


def border_px(method: str, image_long_edge: int) -> float:
    return BORDER_PX.get(method, BORDER_PX["manual"]) * max(1.0, image_long_edge / DISPLAY_LONG_EDGE)


def shape_points(shape: dict[str, Any]) -> np.ndarray:
    if shape["type"] == "circle":
        angles = np.linspace(0, 2 * math.pi, 72, endpoint=False)
        return np.column_stack([shape["cx"] + shape["r"] * np.cos(angles), shape["cy"] + shape["r"] * np.sin(angles)])
    points = np.asarray(shape["points"], np.float64)
    if points.ndim != 2 or points.shape[0] < 3:
        raise ValueError("an outline needs at least three points")
    return points


def to_mm(points_px: np.ndarray, scale: Scale) -> np.ndarray:
    if scale.homography is not None:
        h = np.asarray(scale.homography, np.float64)
        mapped = np.asarray(cv2.perspectiveTransform(points_px.reshape(-1, 1, 2), h)).reshape(-1, 2)
        return mapped * scale.print_factor
    return points_px * scale.mm_per_px


def feret(points: np.ndarray) -> tuple[float, float]:
    """Longest diameter and the width perpendicular to it."""
    hull = cv2.convexHull(points.astype(np.float32)).reshape(-1, 2).astype(np.float64)
    if len(hull) < 2:
        return 0.0, 0.0
    diffs = hull[:, None, :] - hull[None, :, :]
    distances = np.sqrt((diffs**2).sum(axis=2))
    i, j = np.unravel_index(int(np.argmax(distances)), distances.shape)
    longest = float(distances[i, j])
    direction = (hull[j] - hull[i]) / max(longest, 1e-9)
    normal = np.array([-direction[1], direction[0]])
    projections = hull @ normal
    return longest, float(projections.max() - projections.min())


def measure(shape: dict[str, Any], scale: Scale, border_px_value: float) -> dict[str, Any]:
    points_mm = to_mm(shape_points(shape), scale)
    longest, perpendicular = feret(points_mm)
    area = float(abs(cv2.contourArea(points_mm.astype(np.float32))))
    perimeter = float(cv2.arcLength(points_mm.astype(np.float32), True))
    border_mm = border_px_value * scale.mm_per_px
    s = scale.sigma_scale
    return {
        "longest_mm": round(longest, 3),
        "perpendicular_mm": round(perpendicular, 3),
        "area_mm2": round(area, 3),
        "sigma_longest_mm": round(math.hypot(longest * s, 2 * border_mm), 3),
        "sigma_perpendicular_mm": round(math.hypot(perpendicular * s, 2 * border_mm), 3),
        "sigma_area_mm2": round(math.hypot(2 * area * s, perimeter * border_mm), 3),
        "sigma_scale": round(s, 5),
        "border_mm": round(border_mm, 4),
    }


def change(before: float, sigma_before: float, after: float, sigma_after: float) -> dict[str, Any]:
    delta = after - before
    sigma = math.hypot(sigma_before, sigma_after)
    return {"delta": round(delta, 3), "sigma": round(sigma, 3), "detectable": abs(delta) > CHANGE_K * sigma}
