# SPDX-License-Identifier: AGPL-3.0-only
"""Lining up two photos of a body region by the pattern of its spots (MODEL_CARD.md, `constellation`)."""

from __future__ import annotations

import math

import cv2
import numpy as np

from nevus.cv import constellation

SIZE = (3000, 2000)


def pattern(seed: int, count: int = 40) -> np.ndarray:
    """Spots scattered over a region of skin: x, y in pixels, diameter (of the short side) and contrast."""
    rng = np.random.default_rng(seed)
    w, h = SIZE
    xy = np.column_stack([rng.uniform(0.1 * w, 0.9 * w, count), rng.uniform(0.1 * h, 0.9 * h, count)])
    return np.column_stack([xy, rng.uniform(0.006, 0.03, count), rng.uniform(14, 60, count)])


def as_spots(rows: np.ndarray, size: tuple[int, int] = SIZE) -> list[dict[str, float]]:
    w, h = size
    return [{"x": x / w, "y": y / h, "diameter": d, "contrast": c} for x, y, d, c in rows]


def rephotograph(
    rows: np.ndarray, seed: int, drop: float = 0.2, new: int = 8
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """The same skin months later: turned, closer, a little tilted, some spots missed and some new."""
    rng = np.random.default_rng(seed)
    w, h = SIZE
    angle, zoom = math.radians(8), 1.1
    matrix = np.array(
        [
            [zoom * math.cos(angle), -zoom * math.sin(angle), 120],
            [zoom * math.sin(angle), zoom * math.cos(angle), -90],
            [2e-6, -1e-6, 1],
        ]
    )
    moved = cv2.perspectiveTransform(rows[:, None, :2].astype(np.float64), matrix).reshape(-1, 2)
    moved += rng.normal(0, 0.002 * min(SIZE), moved.shape)  # centroids and skin move a little
    kept = [i for i in range(len(rows)) if rng.uniform() > drop and 0 <= moved[i, 0] < w and 0 <= moved[i, 1] < h]
    later = np.column_stack([moved[kept], rows[kept, 2] * zoom, rows[kept, 3] * rng.uniform(0.85, 1.15, len(kept))])
    extra = pattern(seed + 1000, new)
    return np.vstack([later, extra]), matrix, kept


def test_a_rephotographed_pattern_is_lined_up_and_its_spots_paired() -> None:
    earlier = pattern(1)
    later, truth, kept = rephotograph(earlier, 2)
    result = constellation.match(as_spots(earlier), SIZE, as_spots(later), SIZE)
    assert result["status"] == "aligned", result["reason"]
    pairs = result["pairs"]
    correct = sum(kept[j] == i for i, j in pairs if j < len(kept))
    assert len(pairs) >= 0.8 * len(kept) and correct >= 0.95 * len(pairs)
    probe = np.array([[[500.0, 400.0]], [[2500.0, 1600.0]]])
    found = cv2.perspectiveTransform(probe, np.asarray(result["matrix"]))
    expected = cv2.perspectiveTransform(probe, truth)
    assert np.abs(found - expected).max() < 0.01 * min(SIZE)


def test_unrelated_patterns_are_never_lined_up() -> None:
    """Different skin, or a different region: 30 pairs, none aligned."""
    aligned = [
        seed
        for seed in range(30)
        if constellation.match(as_spots(pattern(seed)), SIZE, as_spots(pattern(seed + 500)), SIZE)["status"]
        == "aligned"
    ]
    assert aligned == []


def test_too_few_spots_for_a_pattern() -> None:
    few = pattern(3, count=5)
    result = constellation.match(as_spots(few), SIZE, as_spots(few), SIZE)
    assert result["status"] == "abstained" and result["reason"] == "too_few_spots"


def test_photos_of_different_resolutions_compare() -> None:
    earlier = pattern(4)
    later, _, kept = rephotograph(earlier, 5)
    small = (1500, 1000)
    halved = later.copy()
    halved[:, :2] /= 2
    result = constellation.match(as_spots(earlier), SIZE, as_spots(halved, small), small)
    assert result["status"] == "aligned"
    assert len(result["pairs"]) >= 0.8 * len(kept)
