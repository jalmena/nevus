# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental: an outline of the mark without a tap, and a word on the framing (FR-ANA-03).

Runs only for persons who turned the experimental analysis on, and every result waits for the
person to confirm or reject it. The seed is the reference card's window when the card is there;
otherwise the darkest compact spot near the middle of the photo, the card itself left out. From the
seed, the same fit as a tap. The analyzer abstains, with a reason, when the region is faint, ragged,
implausibly large or small, or when nothing stands out.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from nevus.cv import fit
from nevus.cv.card import APERTURE_RADIUS, CARDS, WINDOW
from nevus.cv.hair import paint_over_hairs
from nevus.cv.imageio import Img, resize_long_edge

NAME = "segment.auto"
VERSION = "1.0.0"
PARAMS: dict[str, Any] = {
    "seed_px": 512,
    "hair_kernel_fraction": 0.03,
    "hair_threshold": 12,
    "centre_fraction": 0.6,
    "min_contrast": 8.0,
    "min_compactness": 0.35,
    "max_area_fraction": 0.2,
    "min_diameter_fraction": 0.012,
    "off_centre_fraction": 0.22,
    "small_fraction": 0.03,
}
REASONS = ("no_mark_found", "low_contrast", "irregular_region", "too_large", "too_small")


def _card_mask(shape: tuple[int, int], card: dict[str, Any] | None, scale: float) -> np.ndarray:
    """Where the reference card lies in the (scaled) photo, so its printed markers are not taken for marks."""
    mask = np.zeros(shape, np.uint8)
    if not card or not card.get("found"):
        return mask
    geometry = next((c for c in CARDS if c.name == card.get("card")), WINDOW)
    corners = np.array(
        [[0, 0], [geometry.width, 0], [geometry.width, geometry.height], [0, geometry.height]], np.float64
    ).reshape(-1, 1, 2)
    to_image = np.linalg.inv(np.asarray(card["homography"], np.float64))
    quad = cv2.perspectiveTransform(corners, to_image).reshape(-1, 2) * scale
    cv2.fillPoly(mask, [np.round(quad).astype(np.int32)], 255)
    return mask


def _darkness(lightness: np.ndarray) -> np.ndarray:
    """How much darker each pixel is than its surroundings (a wide median as the local skin)."""
    size = max(3, (min(lightness.shape) // 6) | 1)
    background = cv2.medianBlur(lightness, size)
    dark = background.astype(np.float32) - lightness.astype(np.float32)
    return cv2.GaussianBlur(dark, (0, 0), 3.0)


def seed(
    image: Img, card: dict[str, Any] | None, params: dict[str, Any] | None = None
) -> tuple[float, float, str] | None:
    p = {**PARAMS, **(params or {})}
    if card and card.get("found") and card.get("card") == WINDOW.name:
        x, y = card["centre_px"]
        return float(x), float(y), "card_window"
    small, scale = resize_long_edge(image, int(p["seed_px"]))
    lightness = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0]
    dark = _darkness(lightness)
    h, w = dark.shape
    keep = np.zeros_like(dark, dtype=bool)
    margin_y, margin_x = int(h * (1 - p["centre_fraction"]) / 2), int(w * (1 - p["centre_fraction"]) / 2)
    keep[margin_y : h - margin_y, margin_x : w - margin_x] = True
    keep &= _card_mask((h, w), card, scale) == 0
    dark[~keep] = -1e9
    y, x = np.unravel_index(int(np.argmax(dark)), dark.shape)
    if dark[y, x] < float(p["min_contrast"]):
        return None
    return float(x) / scale, float(y) / scale, "darkest_centre"


def only_the_window(image: Img, card: dict[str, Any]) -> Img:
    """Everything but the card's window painted with the skin seen through it, so the card's own print
    (the ring, the markers) can never become, or join, the mark. The window is the aperture circle
    projected through the card's homography, so a tilted card still gets the right ellipse."""
    to_image = np.linalg.inv(np.asarray(card["homography"], np.float64))
    cx, cy = WINDOW.centre
    angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    radius = APERTURE_RADIUS * 0.96  # inside the printed edge
    circle = np.stack([cx + radius * np.cos(angles), cy + radius * np.sin(angles)], axis=1).reshape(-1, 1, 2)
    window = cv2.perspectiveTransform(circle, to_image).reshape(-1, 2)
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(window).astype(np.int32)], 255)
    if not mask.any():
        return image
    inside = image[mask > 0]
    lightness = cv2.cvtColor(inside.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB)[:, 0, 0]
    skin = np.median(inside[lightness >= np.median(lightness)], axis=0)  # the lighter half: skin, not the mark
    painted: Img = np.empty_like(image)
    painted[:] = np.asarray(skin, dtype=image.dtype)
    painted[mask > 0] = image[mask > 0]
    return painted


def without_hair(image: Img, x: float, y: float, p: dict[str, Any]) -> Img:
    """Hairs around the seed painted over (see `cv.hair`); only the region the fit will look at is touched."""
    height, width = image.shape[:2]
    half = int(max(60, 0.18 * min(width, height)))
    x0, y0 = max(0, int(x) - half), max(0, int(y) - half)
    x1, y1 = min(width, int(x) + half), min(height, int(y) + half)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return image
    cleaned_crop = paint_over_hairs(crop, float(p["hair_kernel_fraction"]), int(p["hair_threshold"]))
    if cleaned_crop is crop:
        return image
    cleaned = image.copy()
    cleaned[y0:y1, x0:x1] = cleaned_crop
    return cleaned


def _contrast(image: Img, outline: np.ndarray) -> float:
    """Mean lightness of a ring around the region minus the region's own, at a working size."""
    small, scale = resize_long_edge(image, 1024)
    lightness = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    inside = np.zeros(lightness.shape, np.uint8)
    cv2.fillPoly(inside, [np.round(outline * scale).astype(np.int32)], 255)
    radius = max(3, int(math.sqrt(float(inside.sum() / 255) / math.pi) * 0.5))
    ring = cv2.dilate(inside, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1)))
    ring = cv2.subtract(ring, inside)
    if not inside.any() or not ring.any():
        return 0.0
    return float(lightness[ring > 0].mean() - lightness[inside > 0].mean())


def _framing(outline: np.ndarray, size: tuple[int, int], seed_method: str, p: dict[str, Any]) -> list[str]:
    """Hints for the next photo. With the card's window the card frames the mark, so none are needed."""
    if seed_method == "card_window":
        return []
    width, height = size
    short = min(width, height)
    flags: list[str] = []
    cx, cy = outline.mean(axis=0)
    if math.hypot(cx - width / 2, cy - height / 2) > float(p["off_centre_fraction"]) * short:
        flags.append("mark_off_centre")
    area = abs(float(cv2.contourArea(outline.astype(np.float32))))
    if 2 * math.sqrt(area / math.pi) < float(p["small_fraction"]) * short:
        flags.append("mark_small")
    margin = 0.01 * short
    xs, ys = outline[:, 0], outline[:, 1]
    if xs.min() < margin or ys.min() < margin or xs.max() > width - margin or ys.max() > height - margin:
        flags.append("mark_cut")
    return flags


def propose(image: Img, card: dict[str, Any] | None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**PARAMS, **(params or {})}
    height, width = image.shape[:2]
    start = seed(image, card, p)
    if start is None:
        return {"found": False, "reason": "no_mark_found", "framing_flags": ["no_mark_found"]}
    x, y, method = start
    if method == "card_window" and card is not None:
        image = only_the_window(image, card)
    image = without_hair(image, x, y, p)
    fitted = fit.propose(image, x, y, "lesion")
    if fitted is None or not fitted.get("outline"):
        return {
            "found": False,
            "reason": "no_mark_found",
            "seed": [round(x, 1), round(y, 1)],
            "framing_flags": ["no_mark_found"],
        }
    outline = np.asarray(fitted["outline"], np.float64)
    area = abs(float(cv2.contourArea(outline.astype(np.float32))))
    perimeter = float(cv2.arcLength(outline.astype(np.float32), True))
    compactness = 4 * math.pi * area / perimeter**2 if perimeter > 0 else 0.0
    contrast = _contrast(image, outline)
    result: dict[str, Any] = {
        "seed": [round(x, 1), round(y, 1)],
        "seed_method": method,
        "outline": [[round(float(px), 1), round(float(py), 1)] for px, py in outline],
        "contrast": round(contrast, 1),
        "compactness": round(compactness, 3),
    }
    reason = None
    if contrast < float(p["min_contrast"]):
        reason = "low_contrast"
    elif compactness < float(p["min_compactness"]):
        reason = "irregular_region"
    elif area > float(p["max_area_fraction"]) * width * height:
        reason = "too_large"
    elif 2 * math.sqrt(area / math.pi) < float(p["min_diameter_fraction"]) * min(width, height):
        reason = "too_small"
    if reason:
        return {**result, "found": False, "reason": reason, "framing_flags": []}
    confidence = min(1.0, (contrast - float(p["min_contrast"])) / (3 * float(p["min_contrast"])) + 0.25) * min(
        1.0, compactness / 0.8
    )
    return {
        **result,
        "found": True,
        "reason": None,
        "confidence": round(max(0.0, confidence), 2),
        "framing_flags": _framing(outline, (width, height), method, p),
    }
