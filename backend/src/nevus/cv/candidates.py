# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental: spots on a full-body zone photo that may be marks (FR-SES-03).

The protocol puts the region of the body in the middle of the frame, so the skin is the largest
region close to the median colour of the frame's centre, which works on every skin tone, unlike fixed
skin-colour thresholds, and whatever the background. Within it, spots darker than their surroundings,
compact and of a plausible size are candidates. The person confirms or rejects each one; none is
recorded otherwise.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from nevus.cv.hair import paint_over_hairs
from nevus.cv.imageio import Img, resize_long_edge

NAME = "candidates"
VERSION = "1.0.0"
PARAMS: dict[str, Any] = {
    "work_px": 1600,
    "hair_kernel_fraction": 0.02,
    "hair_threshold": 12,
    "skin_delta_e": 24.0,
    "centre_fraction": 0.5,
    "max_hole_fraction": 0.012,
    "min_diameter_fraction": 0.006,
    "max_diameter_fraction": 0.06,
    "min_contrast": 12.0,
    "min_compactness": 0.45,
    "max_candidates": 80,
}


def skin_mask(small: Img, p: dict[str, Any]) -> np.ndarray:
    """The largest region near the colour of the frame's centre, with mark-sized holes filled."""
    lab = cv2.cvtColor(cv2.GaussianBlur(small, (0, 0), 3), cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    my, mx = int(h * (1 - float(p["centre_fraction"])) / 2), int(w * (1 - float(p["centre_fraction"])) / 2)
    median = np.median(lab[my : h - my, mx : w - mx].reshape(-1, 3), axis=0)
    close = (np.sqrt(((lab - median) ** 2).sum(axis=2)) < float(p["skin_delta_e"])).astype(np.uint8)
    # Hairs and creases are thin and would cut the skin into strips: close them before choosing the region.
    gap = max(5, int(0.02 * min(close.shape)) | 1)
    joined = cv2.morphologyEx(close, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (gap, gap)))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    if count <= 1:
        return np.zeros(close.shape, bool)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    region = labels == largest
    # The marks themselves are holes in that region: fill those, but not larger ones, which are things
    # lying on the skin (a ruler, a card, clothing) whose dark parts must not become candidates.
    holes, hole_labels, hole_stats, _ = cv2.connectedComponentsWithStats((~region).astype(np.uint8), connectivity=4)
    largest_hole = float(p["max_hole_fraction"]) * h * w
    for label in range(1, holes):
        x, y, bw, bh, area = hole_stats[label]
        touches_border = x == 0 or y == 0 or x + bw == w or y + bh == h
        if not touches_border and area <= largest_hole:
            region |= hole_labels == label
    margin = max(3, int(0.01 * min(h, w)))
    eroded = cv2.erode(region.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (margin, margin)))
    return eroded > 0


def skin(image: Img, params: dict[str, Any] | None = None) -> np.ndarray:
    """The skin mask of a photo, at the working size (the long edge `work_px`)."""
    p = {**PARAMS, **(params or {})}
    small, _ = resize_long_edge(image, int(p["work_px"]))
    return skin_mask(paint_over_hairs(small, float(p["hair_kernel_fraction"]), int(p["hair_threshold"])), p)


def detect(image: Img, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**PARAMS, **(params or {})}
    small, _ = resize_long_edge(image, int(p["work_px"]))
    small = paint_over_hairs(small, float(p["hair_kernel_fraction"]), int(p["hair_threshold"]))
    h, w = small.shape[:2]
    short = min(h, w)
    skin = skin_mask(small, p)
    if skin.mean() < 0.2:
        return {"found": False, "reason": "no_skin", "candidates": []}
    lightness = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0]
    size = max(3, (int(short * float(p["max_diameter_fraction"]) * 3)) | 1)
    background = cv2.medianBlur(lightness, min(size, 255) | 1)
    dark: np.ndarray = cv2.GaussianBlur(background.astype(np.float32) - lightness.astype(np.float32), (0, 0), 1.5)
    dark[~skin] = 0
    binary = (dark > float(p["min_contrast"])).astype(np.uint8)
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
    found: list[dict[str, Any]] = []
    min_d, max_d = float(p["min_diameter_fraction"]) * short, float(p["max_diameter_fraction"]) * short
    for label in range(1, count):
        area = float(stats[label, cv2.CC_STAT_AREA])
        diameter = 2 * math.sqrt(area / math.pi)
        if not min_d <= diameter <= max_d:
            continue
        region = (labels == label).astype(np.uint8)
        contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        perimeter = cv2.arcLength(max(contours, key=cv2.contourArea), True) if contours else 0.0
        compactness = 4 * math.pi * area / perimeter**2 if perimeter else 0.0
        if compactness < float(p["min_compactness"]):
            continue  # hairs, creases, the edge of clothing
        contrast = float(dark[region > 0].mean())
        cx, cy = centroids[label]
        found.append(
            {
                "x": round(float(cx) / w, 4),
                "y": round(float(cy) / h, 4),
                "diameter": round(diameter / short, 4),
                "contrast": round(contrast, 1),
                "confidence": round(
                    min(1.0, contrast / (3 * float(p["min_contrast"]))) * min(1.0, compactness / 0.8), 2
                ),
            }
        )
    found.sort(key=lambda c: -c["contrast"])
    return {
        "found": bool(found),
        "reason": None if found else "nothing_found",
        "candidates": found[: int(p["max_candidates"])],
    }
