# SPDX-License-Identifier: AGPL-3.0-only
"""The normalised view of a photo taken with the reference card: flat, upright, cropped to the card.

The card detector gives a homography from image pixels to millimetres on the card's plane. Composed
with a fixed scale and a small margin, it turns every card photo into the same picture: the card
seen from straight above, its markers in their printed places, the mark in the window at a known
number of pixels per millimetre. Nothing is measured here; the original stays the record and the
normalised picture is a rendition that can be made again from it.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from nevus.cv.card import APERTURE_RADIUS, CARDS, CardGeometry
from nevus.cv.imageio import Img

NAME = "normalise.card"
VERSION = "1.1.0"
PARAMS: dict[str, Any] = {
    "margin_mm": 3.0,
    "max_px_per_mm": 24.0,
    "max_long_edge": 2048,
    "window_half_mm": 14.0,
    "glare_mark_min": 0.01,
}


def card_named(name: str) -> CardGeometry | None:
    return next((card for card in CARDS if card.name == name), None)


def plan(card: CardGeometry, mm_per_px: float, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """The output frame: the card plus a margin, at the photo's own resolution unless that is excessive."""
    p = {**PARAMS, **(params or {})}
    margin = float(p["margin_mm"])
    frame_w = card.width + 2 * margin
    frame_h = card.height + 2 * margin
    native = 1.0 / mm_per_px if mm_per_px > 0 else float(p["max_px_per_mm"])
    px_per_mm = min(native, float(p["max_px_per_mm"]), float(p["max_long_edge"]) / max(frame_w, frame_h))
    return {
        "margin_mm": margin,
        "px_per_mm": round(px_per_mm, 4),
        "width": round(frame_w * px_per_mm),
        "height": round(frame_h * px_per_mm),
    }


def matrix(homography: list[list[float]], frame: dict[str, Any]) -> np.ndarray:
    """Image pixels -> normalised pixels: the card plane in millimetres, shifted by the margin, scaled."""
    s = float(frame["px_per_mm"])
    m = float(frame["margin_mm"])
    to_output = np.array([[s, 0.0, s * m], [0.0, s, s * m], [0.0, 0.0, 1.0]])
    return to_output @ np.asarray(homography, np.float64)


def normalise(
    image: Img, card_result: dict[str, Any], params: dict[str, Any] | None = None
) -> tuple[Img, dict[str, Any]] | None:
    """The normalised picture and how it was made, or None when the photo holds no card."""
    if not card_result.get("found"):
        return None
    card = card_named(str(card_result.get("card")))
    if card is None:
        return None
    frame = plan(card, float(card_result["mm_per_px"]), params)
    m = matrix(card_result["homography"], frame)
    out = cv2.warpPerspective(
        image, m, (frame["width"], frame["height"]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )
    how: dict[str, Any] = {**frame, "card": card.name, "matrix": m.tolist(), "flags": []}
    if card.centre is not None and card.name == "window":
        p = {**PARAMS, **(params or {})}
        glare = glare_in_window(out, card, frame)
        how["glare_on_mark"] = round(glare, 4)
        if glare >= float(p["glare_mark_min"]):
            how["flags"].append("glare_on_mark")
    return out, how


def window_rect(
    card: CardGeometry, frame: dict[str, Any], params: dict[str, Any] | None = None
) -> tuple[int, int, int, int]:
    """The square around the card's window in normalised pixels: left, top, side, and the window's radius."""
    p = {**PARAMS, **(params or {})}
    s = float(frame["px_per_mm"])
    cx = (card.centre[0] + float(frame["margin_mm"])) * s
    cy = (card.centre[1] + float(frame["margin_mm"])) * s
    half = float(p["window_half_mm"]) * s
    return round(cx - half), round(cy - half), round(2 * half), round(APERTURE_RADIUS * s)


def window(picture: Img, card: CardGeometry, frame: dict[str, Any], params: dict[str, Any] | None = None) -> Img | None:
    """The mark with the ring around it: the window of the card, cut from the normalised picture."""
    if card.name != "window":
        return None
    left, top, side, _ = window_rect(card, frame, params)
    h, w = picture.shape[:2]
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(w, left + side), min(h, top + side)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return picture[y0:y1, x0:x1].copy()


def glare_in_window(picture: Img, card: CardGeometry, frame: dict[str, Any]) -> float:
    """Specular highlights inside the window (saturated, colourless pixels) as a share of its area."""
    left, top, side, radius = window_rect(card, frame)
    h, w = picture.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.circle(mask, (left + side // 2, top + side // 2), max(1, radius - 2), 1, -1)
    inside = mask.astype(bool)
    if not inside.any() or picture.ndim != 3:
        return 0.0
    hsv = cv2.cvtColor(picture, cv2.COLOR_BGR2HSV)
    specular = (hsv[:, :, 2] >= 250) & (hsv[:, :, 1] <= 40)
    return float((specular & inside).sum() / inside.sum())


def to_normalised(m: list[list[float]], points: np.ndarray) -> np.ndarray:
    """Image pixels to normalised pixels, for drawing what was measured on the normalised picture."""
    pts = np.asarray(points, np.float64).reshape(-1, 1, 2)
    return np.asarray(cv2.perspectiveTransform(pts, np.asarray(m, np.float64))).reshape(-1, 2)
