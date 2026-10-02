# SPDX-License-Identifier: AGPL-3.0-only
"""Photograph quality checks: sharpness, exposure, specular glare and resolution.

Warnings, not verdicts: a photo with warnings is still saved, the person decides whether to retake.
Thresholds are provisional and recorded with every analysis, so a recalibrated version can be run
over old photos without overwriting what was recorded (see the analysis records).
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from nevus.cv.imageio import Img, decode, resize_long_edge

NAME = "quality"
VERSION = "1.0.0"
PARAMS: dict[str, Any] = {
    "long_edge": 1024,
    "tiles": 8,
    "sharpness_min": 15.0,
    "dark_mean": 45.0,
    "bright_mean": 228.0,
    "dark_clip": 0.30,
    "bright_clip": 0.20,
    "glare_min": 0.002,
    "glare_blob_max": 0.02,
    "min_short_edge": 1000,
}
FLAGS = ("blurry", "too_dark", "too_bright", "glare", "low_resolution")


def analyze(data: bytes, width: int, height: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**PARAMS, **(params or {})}
    image = decode(data, max_long_edge=int(p["long_edge"]), original_long_edge=max(width, height))
    small, _ = resize_long_edge(image, int(p["long_edge"]))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    sharpness = _sharpness(_normalise_exposure(gray), int(p["tiles"]))
    brightness = float(gray.mean())
    dark_clip = float((gray <= 10).mean())
    bright_clip = float((gray >= 245).mean())
    glare = _glare(small, float(p["glare_blob_max"]))

    flags: list[str] = []
    if sharpness < float(p["sharpness_min"]):
        flags.append("blurry")
    if brightness < float(p["dark_mean"]) or dark_clip > float(p["dark_clip"]):
        flags.append("too_dark")
    if brightness > float(p["bright_mean"]) or bright_clip > float(p["bright_clip"]):
        flags.append("too_bright")
    elif glare >= float(p["glare_min"]):
        flags.append("glare")
    if min(width, height) < int(p["min_short_edge"]):
        flags.append("low_resolution")
    return {
        "sharpness": round(sharpness, 2),
        "brightness": round(brightness, 2),
        "dark_clip": round(dark_clip, 4),
        "bright_clip": round(bright_clip, 4),
        "glare": round(glare, 4),
        "width": width,
        "height": height,
        "flags": flags,
    }


def _normalise_exposure(gray: Img) -> Img:
    """Bring the mean to mid-grey. Exposure scales pixel values, so this undoes it without inventing detail.

    Without it, an underexposed photo would also be called blurry: its edges are just as sharp, only darker.
    """
    mean = float(gray.mean())
    factor = min(max(128.0 / max(mean, 1.0), 0.5), 4.0)
    out: Img = np.clip(gray.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return out


def _glare(bgr: Img, blob_max: float) -> float:
    """Specular highlights: small, saturated, colourless spots.

    A large bright area (white paper, an overexposed background) is exposure, not glare, and is
    already counted as clipping; only blobs smaller than `blob_max` of the frame count here.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 2] >= 250) & (hsv[:, :, 1] <= 40)).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    total = mask.size
    area = sum(
        int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] / total < blob_max
    )
    return area / total


def _sharpness(gray: Img, tiles: int) -> float:
    """Laplacian variance of the sharpest tiles: a sharp mole on smooth skin is still sharp.

    A whole-image measure would call a crisp close-up "blurry" because most of the frame is
    featureless skin; the 90th percentile of per-tile variances follows the detail that exists.
    """
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    h, w = lap.shape
    ys = np.linspace(0, h, tiles + 1, dtype=int)
    xs = np.linspace(0, w, tiles + 1, dtype=int)
    variances = [float(lap[ys[i] : ys[i + 1], xs[j] : xs[j + 1]].var()) for i in range(tiles) for j in range(tiles)]
    return float(np.percentile(variances, 90))
