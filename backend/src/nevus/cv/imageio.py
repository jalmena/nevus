# SPDX-License-Identifier: AGPL-3.0-only
"""Decoding helpers shared by the analyzers."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

Img = NDArray[Any]
"""A decoded image (BGR or grey); OpenCV's own types are wider than NumPy's, so keep this loose."""


class DecodeError(ValueError):
    """The bytes are not an image OpenCV can read."""


def decode(data: bytes, *, max_long_edge: int | None = None, original_long_edge: int | None = None) -> Img:
    """Decode to BGR, using JPEG's built-in downscaling when only a smaller image is needed."""
    flag = cv2.IMREAD_COLOR
    if max_long_edge and original_long_edge:
        for factor, reduced in (
            (8, cv2.IMREAD_REDUCED_COLOR_8),
            (4, cv2.IMREAD_REDUCED_COLOR_4),
            (2, cv2.IMREAD_REDUCED_COLOR_2),
        ):
            if original_long_edge / factor >= max_long_edge:
                flag = reduced
                break
    image = cv2.imdecode(np.frombuffer(data, np.uint8), flag | cv2.IMREAD_IGNORE_ORIENTATION)
    if image is None:
        raise DecodeError("not a decodable image")
    return image


def upright(image: Img, orientation: int) -> Img:
    """Apply the EXIF orientation recorded at ingest (the stored original has no EXIF of its own)."""
    match orientation:
        case 2:
            return cv2.flip(image, 1)
        case 3:
            return cv2.rotate(image, cv2.ROTATE_180)
        case 4:
            return cv2.flip(image, 0)
        case 5:
            return cv2.transpose(image)
        case 6:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        case 7:
            return cv2.flip(cv2.transpose(image), -1)
        case 8:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        case _:
            return image


def resize_long_edge(image: Img, long_edge: int) -> tuple[Img, float]:
    """Downscale so the long edge is at most `long_edge`; returns the image and the scale applied."""
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= long_edge:
        return image, 1.0
    scale = long_edge / longest
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA), scale
