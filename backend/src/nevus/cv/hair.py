# SPDX-License-Identifier: AGPL-3.0-only
"""Thin dark lines (hairs) painted over from their surroundings: the DullRazor idea.

A black-hat with a kernel wider than a hair and narrower than a mark keeps only the thin dark
structures. Of those, only long and narrow ones are hairs (specks of skin texture and noise are
left alone); they are dilated a little and inpainted, so a hair crossing a mark does not change its
outline or join it to its neighbours.
"""

from __future__ import annotations

import cv2
import numpy as np

from nevus.cv.imageio import Img


def paint_over_hairs(img: Img, kernel_fraction: float, threshold: int) -> Img:
    """The same image with hairs inpainted, or the image itself when there are none."""
    size = max(9, int(kernel_fraction * min(img.shape[:2])) | 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    response = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    found = (response > threshold).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(found, connectivity=8)
    mask = np.zeros_like(found)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < 3 * size:
            continue  # specks of skin texture and noise, not hairs
        points = np.column_stack(np.nonzero(labels == label)[::-1]).astype(np.float32)
        (_, _), (w, h), _ = cv2.minAreaRect(points)
        long_side, short_side = max(w, h), max(1.0, min(w, h))
        if long_side >= 2.5 * size and long_side / short_side >= 4:
            mask[labels == label] = 255
    if not mask.any():
        return img
    grown = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cleaned: Img = cv2.inpaint(img, grown, 5, cv2.INPAINT_TELEA)
    return cleaned
