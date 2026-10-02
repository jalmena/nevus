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
