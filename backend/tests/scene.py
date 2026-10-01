# SPDX-License-Identifier: AGPL-3.0-only
"""A photographed reference card: the card drawn at high resolution, a disc of known size in its window,
then projected by a pinhole camera looking at the card plane with a chosen tilt."""

from __future__ import annotations

import math

import cv2
import numpy as np

from nevus.cv.card import APERTURE_RADIUS, STRIP, WINDOW, CardGeometry, draw_card
from nevus.cv.card_raster import RasterPainter, blank

K = 20.0  # card raster resolution, px per mm


def card_raster(card: CardGeometry = WINDOW, disc_mm: float = 5.0, seed: int = 3) -> np.ndarray:
    img = blank(card.width, card.height, K)
    painter = RasterPainter(img, K)
    draw_card(painter, card, 0.0, 0.0, cut_aperture=False)
    if card is WINDOW:
        rng = np.random.default_rng(seed)
        cx, cy = card.centre
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.circle(mask, (round(cx * K), round(cy * K)), round(APERTURE_RADIUS * K), 1, -1)
        skin = np.full(img.shape, (150, 175, 215), np.int16) + rng.normal(0, 6, (*img.shape[:2], 1)).astype(np.int16)
        img[mask.astype(bool)] = np.clip(skin, 0, 255).astype(np.uint8)[mask.astype(bool)]
        cv2.circle(img, (round(cx * K), round(cy * K)), round(disc_mm / 2 * K), (50, 60, 90), -1, cv2.LINE_AA)
    return img


def photograph(
    card: CardGeometry = WINDOW,
    tilt_deg: float = 0.0,
    distance_mm: float = 150.0,
    focal_px: float = 3000.0,
    size: tuple[int, int] = (3000, 2250),
    disc_mm: float = 5.0,
    background: tuple[int, int, int] = (140, 165, 205),
) -> tuple[np.ndarray, float]:
    """Returns the photo and the true pixels per millimetre at the card centre."""
    raster = card_raster(card, disc_mm)
    width, height = size
    theta = math.radians(tilt_deg)
    cx, cy = card.centre

    def project(x_mm: float, y_mm: float) -> tuple[float, float]:
        x, y = x_mm - cx, y_mm - cy
        z = distance_mm + y * math.sin(theta)
        return width / 2 + focal_px * x / z, height / 2 + focal_px * y * math.cos(theta) / z

    corners_mm = [(0.0, 0.0), (card.width, 0.0), (card.width, card.height), (0.0, card.height)]
    src = np.array([[x * K, y * K] for x, y in corners_mm], np.float32)
    dst = np.array([project(x, y) for x, y in corners_mm], np.float32)
    h = cv2.getPerspectiveTransform(src, dst)
    photo = np.full((height, width, 3), background, np.uint8)
    warped = cv2.warpPerspective(raster, h, (width, height), flags=cv2.INTER_AREA)
    mask = cv2.warpPerspective(np.full(raster.shape[:2], 255, np.uint8), h, (width, height)) > 127
    photo[mask] = warped[mask]
    return photo, focal_px / distance_mm


__all__ = ["STRIP", "WINDOW", "photograph"]
