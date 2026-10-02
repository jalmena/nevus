# SPDX-License-Identifier: AGPL-3.0-only
"""Descriptive numbers about a measured mark: its shape, and its colour next to the skin around it.

These describe; they do not judge. The shape numbers come from the outline the person confirmed.
The colour numbers come from the photograph, so they depend on the light and the camera: when the
reference card is in the photo, its grey patch (printed to read as sRGB #777777) sets the exposure
and the white balance, and the values are comparable from one visit to the next; without it they
are what the camera saw, and say so. Nothing here carries a threshold or a meaning.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import measure
from nevus.cv.card import APERTURE_RADIUS, CARDS, WINDOW
from nevus.cv.imageio import Img, decode, upright
from nevus.cv.pipeline import upright_size
from nevus.db.models import Image, Measurement, ScaleReference
from nevus.measure import shape_points
from nevus.storage.blobs import BlobStore

VERSION = "1.0.0"
GREY_PATCH_SRGB = 0x77 / 255  # how the card's grey patch is printed
MIN_PIXELS = 40


def shape(values: dict[str, Any]) -> dict[str, float]:
    """Perimeter, compactness (1 for a circle, less for anything else) and the ratio of the two diameters."""
    perimeter = float(values["perimeter_mm"])
    area = float(values["area_mm2"])
    compactness = 4 * math.pi * area / perimeter**2 if perimeter > 0 else 0.0
    longest = float(values["longest_mm"])
    return {
        "perimeter_mm": round(perimeter, 3),
        "compactness": round(min(1.0, compactness), 3),
        "aspect": round(float(values["perpendicular_mm"]) / longest, 3) if longest > 0 else 0.0,
    }


def _linear(srgb: np.ndarray) -> np.ndarray:
    c = np.asarray(srgb, dtype=np.float64) / 255.0
    return np.asarray(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4), dtype=np.float64)


def _srgb(linear: np.ndarray) -> np.ndarray:
    c = np.clip(linear, 0.0, 1.0)
    return np.asarray(
        np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055) * 255.0, dtype=np.float64
    )


def _lab(bgr: np.ndarray) -> np.ndarray:
    """OpenCV's Lab for uint8 input, rescaled to L* in 0..100 and a*, b* about zero."""
    lab = cv2.cvtColor(bgr.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
    lab[:, 0] *= 100.0 / 255.0
    lab[:, 1:] -= 128.0
    return lab


def _hex(bgr: np.ndarray) -> str:
    b, g, r = (round(float(v)) for v in bgr)
    return f"#{r:02x}{g:02x}{b:02x}"


def _card_masks(shape_hw: tuple[int, int], geometry: dict[str, Any]) -> tuple[np.ndarray | None, np.ndarray | None]:
    """The card's own pixels, and the aperture of a window card, in the photo."""
    homography = geometry.get("homography")
    card = next((c for c in CARDS if c.name == geometry.get("card", WINDOW.name)), None)
    if homography is None or card is None:
        return None, None
    to_image = np.linalg.inv(np.asarray(homography, np.float64))
    quad = np.array([[0, 0], [card.width, 0], [card.width, card.height], [0, card.height]], np.float64)
    card_px = cv2.perspectiveTransform(quad.reshape(-1, 1, 2), to_image).reshape(-1, 2)
    card_mask = np.zeros(shape_hw, np.uint8)
    cv2.fillPoly(card_mask, [np.round(card_px).astype(np.int32)], 255)
    aperture_mask = None
    if card.name == WINDOW.name:
        angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        cx, cy = card.centre
        radius = APERTURE_RADIUS * 0.96
        circle = np.stack([cx + radius * np.cos(angles), cy + radius * np.sin(angles)], axis=1).reshape(-1, 1, 2)
        aperture_px = cv2.perspectiveTransform(circle, to_image).reshape(-1, 2)
        aperture_mask = np.zeros(shape_hw, np.uint8)
        cv2.fillPoly(aperture_mask, [np.round(aperture_px).astype(np.int32)], 255)
    return card_mask, aperture_mask


def _grey_patch_gains(image: Img, geometry: dict[str, Any]) -> np.ndarray | None:
    """Per-channel gains in linear light that make the card's grey patch read as it was printed."""
    homography = geometry.get("homography")
    card = next((c for c in CARDS if c.name == geometry.get("card", WINDOW.name)), None)
    if homography is None or card is None:
        return None
    gx, gy, gw, gh = card.grey
    inset = 0.15  # stay away from the patch's edges and the print's bleed
    rect = np.array(
        [
            [gx + gw * inset, gy + gh * inset],
            [gx + gw * (1 - inset), gy + gh * inset],
            [gx + gw * (1 - inset), gy + gh * (1 - inset)],
            [gx + gw * inset, gy + gh * (1 - inset)],
        ],
        np.float64,
    )
    to_image = np.linalg.inv(np.asarray(homography, np.float64))
    patch_px = cv2.perspectiveTransform(rect.reshape(-1, 1, 2), to_image).reshape(-1, 2)
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(patch_px).astype(np.int32)], 255)
    pixels = image[mask > 0]
    if len(pixels) < MIN_PIXELS:
        return None
    seen = _linear(np.median(pixels.astype(np.float64), axis=0))
    if np.any(seen <= 0.002):
        return None  # a black patch is not the grey patch: the card was not read where it is
    gains = _linear(np.array([GREY_PATCH_SRGB * 255] * 3)) / seen
    return np.asarray(np.clip(gains, 0.25, 4.0), dtype=np.float64)


def _apply_gains(pixels: np.ndarray, gains: np.ndarray | None) -> np.ndarray:
    if gains is None:
        return pixels
    return _srgb(_linear(pixels.astype(np.float64)) * gains)


def colour(image: Img, outline: dict[str, Any], border_px: float, geometry: dict[str, Any]) -> dict[str, Any] | None:
    """Colour of the mark and of the skin around it, in CIELAB, with their contrast and the mark's spread.

    `image` is the upright photograph; `outline` the confirmed shape in its pixels; `border_px` how
    far the outline may be off, kept clear of both regions; `geometry` the scale reference's, which
    for a card holds its homography and name.
    """
    h, w = image.shape[:2]
    points = np.round(shape_points(outline)).astype(np.int32)
    region = np.zeros((h, w), np.uint8)
    cv2.fillPoly(region, [points], 255)
    if not region.any():
        return None
    gap = max(2, round(2 * border_px))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * gap + 1, 2 * gap + 1))
    inside = cv2.erode(region, kernel)
    if int((inside > 0).sum()) < MIN_PIXELS:
        inside = region
    radius = math.sqrt(float((region > 0).sum()) / math.pi)
    width = max(6, round(0.5 * radius))
    outer = cv2.dilate(region, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * (gap + width) + 1,) * 2))
    ring = cv2.subtract(outer, cv2.dilate(region, kernel))
    card_mask, aperture_mask = _card_masks((h, w), geometry)
    if aperture_mask is not None:
        ring = cv2.bitwise_and(ring, aperture_mask)
    elif card_mask is not None:
        ring = cv2.bitwise_and(ring, cv2.bitwise_not(card_mask))
    if int((ring > 0).sum()) < MIN_PIXELS:
        return None
    gains = _grey_patch_gains(image, geometry)
    mark_pixels = _apply_gains(image[inside > 0], gains)
    skin_pixels = _apply_gains(image[ring > 0], gains)
    mark_lab, skin_lab = _lab(mark_pixels), _lab(skin_pixels)
    mark_mean, skin_mean = mark_lab.mean(axis=0), skin_lab.mean(axis=0)
    return {
        "reference": "card_grey" if gains is not None else "camera",
        "mark": _colour_out(mark_mean, mark_pixels),
        "skin": _colour_out(skin_mean, skin_pixels),
        "contrast": round(float(np.linalg.norm(mark_mean - skin_mean)), 1),
        "lightness_spread": round(float(mark_lab[:, 0].std()), 1),
        "pixels": int((inside > 0).sum()),
    }


def _colour_out(lab_mean: np.ndarray, pixels: np.ndarray) -> dict[str, Any]:
    return {
        "L": round(float(lab_mean[0]), 1),
        "a": round(float(lab_mean[1]), 1),
        "b": round(float(lab_mean[2]), 1),
        "hex": _hex(np.median(pixels, axis=0)),
    }


def describe(
    image: Image,
    reference: ScaleReference,
    outline: dict[str, Any],
    values: dict[str, Any],
    method: str,
    store: BlobStore | None,
) -> dict[str, Any]:
    """Everything descriptive about one measurement; the colour needs the photograph, hence the store."""
    described: dict[str, Any] = {"version": VERSION, "shape": shape(values)}
    path = store.path(image.sha256) if store is not None else None
    if path is not None and path.is_file():
        picture = upright(decode(path.read_bytes()), image.orientation)
        border = measure.border_px(method, max(upright_size(image)))
        described["colour"] = colour(picture, outline, border, reference.geometry)
    return described


def backfill(db: Session, store: BlobStore) -> int:
    """Descriptors for the measurements saved before they existed, the same way; returns how many."""
    count = 0
    for row in db.scalars(select(Measurement).where(Measurement.deleted_at.is_(None))):
        if row.details.get("descriptors"):
            continue
        image = db.get(Image, row.image_id)
        reference = db.get(ScaleReference, row.scale_reference_id)
        if image is None or reference is None:
            continue
        scale = measure.Scale(
            kind=reference.kind,
            mm_per_px=reference.mm_per_px,
            sigma_scale=reference.sigma_scale,
            homography=reference.geometry.get("homography") if reference.kind == "card" else None,
            print_factor=float(row.details.get("print_factor", 1.0)),
            tilt_deg=reference.tilt_deg,
        )
        values = measure.measure(row.shape, scale, measure.border_px(row.method, max(upright_size(image))))
        row.details = {**row.details, "descriptors": describe(image, reference, row.shape, values, row.method, store)}
        count += 1
    db.flush()
    return count
