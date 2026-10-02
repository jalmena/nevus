# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic close-ups for analyzer tests: skin-coloured grain, pores and one dark oval mark."""

from __future__ import annotations

import cv2
import numpy as np


def skin(
    width: int = 3000, height: int = 2250, seed: int = 1, tone: tuple[int, int, int] = (150, 175, 215)
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.full((height, width, 3), tone, np.int16) + rng.normal(0, 9, (height, width, 1)).astype(np.int16)
    darker = tuple(int(c) - 35 for c in tone)
    for _ in range(width * height // 1700):
        cv2.circle(
            img, (int(rng.integers(0, width)), int(rng.integers(0, height))), int(rng.integers(1, 3)), darker, -1
        )
    cv2.ellipse(img, (width // 2, height // 2), (width // 23, width // 27), 15, 0, 360, (50, 60, 90), -1)
    return np.clip(img, 0, 255).astype(np.uint8)


def jpeg(img: np.ndarray, quality: int = 90) -> bytes:
    ok, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert ok
    return buffer.tobytes()


# Six steps of the Monk Skin Tone scale (Google, CC BY 4.0), lightest to darkest.
MONK = {
    "MST1": "#f6ede4",
    "MST3": "#f7ead0",
    "MST5": "#d7bd96",
    "MST6": "#a07e56",
    "MST8": "#604134",
    "MST10": "#292420",
}


def _bgr(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return b, g, r


def toned_skin(
    tone: str,
    seed: int = 0,
    hair: bool = False,
    mark_factor: float = 0.45,
    width: int = 3000,
    height: int = 2250,
    offset: tuple[int, int] | None = None,
    mark_scale: float = 1.0,
) -> tuple[np.ndarray, float, tuple[int, int]]:
    """A close-up on one skin tone: grain, pores, an oval mark darker by `mark_factor`, optional hairs.

    Returns the image, the mark's true equivalent diameter in pixels and its centre.
    """
    rng = np.random.default_rng(seed)
    base = np.array(_bgr(tone), np.int16)
    img = np.full((height, width, 3), base, np.int16) + rng.normal(0, 6, (height, width, 1)).astype(np.int16)
    pores = tuple(int(c * 0.86) for c in base)
    for _ in range(width * height // 2500):
        centre = (int(rng.integers(0, width)), int(rng.integers(0, height)))
        cv2.circle(img, centre, int(rng.integers(1, 3)), pores, -1)
    a, b = int(width / 23 * mark_scale), int(width / 27 * mark_scale)
    angle = float(rng.uniform(0, 180))
    dx, dy = offset if offset is not None else (int(rng.integers(-150, 150)), int(rng.integers(-100, 100)))
    cx, cy = width // 2 + dx, height // 2 + dy
    cv2.ellipse(img, (cx, cy), (a, b), angle, 0, 360, tuple(int(c * mark_factor) for c in base), -1, cv2.LINE_AA)
    if hair:
        for _ in range(6):
            x0 = int(rng.integers(cx - 3 * a, cx + 3 * a))
            x1 = x0 + int(rng.integers(-a, a))
            cv2.line(img, (x0, cy - 4 * b), (x1, cy + 4 * b), tuple(int(c * 0.3) for c in base), 4, cv2.LINE_AA)
    img = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (0, 0), 1.2)
    return img, 2 * float(np.sqrt(a * b)), (cx, cy)
