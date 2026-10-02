# SPDX-License-Identifier: AGPL-3.0-only
"""Tap-seeded circle and outline proposals: the person taps, the app proposes, the person adjusts.

The idea is MoleMapper's (tap, auto-fit, correct), redone for full-resolution photos: work on a
crop around the tap, find the round edge (coins) or the dark region containing the tap (marks), and
map the result back to the photo's pixels. A proposal is never a measurement until it is accepted.
"""

from __future__ import annotations

from typing import Any, Literal

import cv2
import numpy as np

from nevus.cv.imageio import Img

NAME = "fit"
VERSION = "1.0.0"
Target = Literal["coin", "lesion"]
WORK_PX = 640


def propose(image: Img, x: float, y: float, target: Target) -> dict[str, Any] | None:
    height, width = image.shape[:2]
    half = int(max(60, 0.18 * min(width, height)))
    x0, y0 = max(0, int(x) - half), max(0, int(y) - half)
    x1, y1 = min(width, int(x) + half), min(height, int(y) + half)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    scale = min(1.0, WORK_PX / max(crop.shape[:2]))
    small = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else crop
    tap = ((x - x0) * scale, (y - y0) * scale)
    result: tuple[float, float, float, list[list[float]] | None, str] | None = (
        _coin(small, tap) if target == "coin" else None
    )
    if result is None:
        result = _dark_region(small, tap)
    if result is None:
        return None
    cx, cy, r, outline, method = result
    back = np.asarray(outline, np.float64) / scale + [x0, y0] if outline is not None else None
    return {
        "cx": round(cx / scale + x0, 2),
        "cy": round(cy / scale + y0, 2),
        "r": round(r / scale, 2),
        "outline": None if back is None else [[round(float(px), 1), round(float(py), 1)] for px, py in back],
        "method": method,
    }


def _coin(img: Img, tap: tuple[float, float]) -> tuple[float, float, float, None, str] | None:
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5)
    size = min(gray.shape[:2])
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=size / 6,
        param1=120,
        param2=28,
        minRadius=int(size * 0.04),
        maxRadius=int(size * 0.48),
    )
    if circles is None:
        return None
    for cx, cy, r in np.asarray(circles)[0]:
        if (cx - tap[0]) ** 2 + (cy - tap[1]) ** 2 <= r**2:
            return float(cx), float(cy), float(r), None, "hough"
    return None


def _dark_region(img: Img, tap: tuple[float, float]) -> tuple[float, float, float, list[list[float]], str] | None:
    """The darker region under the tap: lightness in Lab, Otsu threshold, small opening against hairs."""
    lightness = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0]
    blurred = cv2.GaussianBlur(lightness, (0, 0), 2.0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    count, labels, _stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return None
    tx, ty = round(tap[0]), round(tap[1])
    label = int(labels[min(max(ty, 0), labels.shape[0] - 1), min(max(tx, 0), labels.shape[1] - 1)])
    if label == 0:
        distances = [np.hypot(*(centroids[i] - tap)) for i in range(1, count)]
        nearest = int(np.argmin(distances)) + 1
        if distances[nearest - 1] > min(img.shape[:2]) / 4:
            return None
        label = nearest
    region = (labels == label).astype(np.uint8)
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    (cx, cy), r = cv2.minEnclosingCircle(contour)
    approx = cv2.approxPolyDP(contour, 1.0, True).reshape(-1, 2)
    if len(approx) > 96:
        approx = approx[np.linspace(0, len(approx) - 1, 96).astype(int)]
    return float(cx), float(cy), float(r), approx.astype(float).tolist(), "threshold"
