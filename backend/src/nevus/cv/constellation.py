# SPDX-License-Identifier: AGPL-3.0-only
"""Lining up two photos of a region of the body by the pattern of the spots on it (FR-SES-03).

Spots move with the skin, unlike the background, and stay where they are for years, unlike the light,
so the pattern they form is what lines up two sessions taken months apart. The method is the classic
one for matching star fields (Groth 1986; Valdes et al. 1995; Beroiz et al. 2020): each spot and its
nearest neighbours form triangles whose shape (two ratios of side lengths) does not change with the
photo's position, rotation or zoom; triangles of the same shape in both photos suggest a similarity
transform, which is scored by how many spots it brings onto a spot of the other photo of a similar
size. The best transforms are refitted on the spots they pair and judged three ways: a-contrario
(Moisan and Stival 2004), that many spots falling into place by chance must be very unlikely given
how densely the skin is spotted; a real re-photograph pairs a good share of the spots both photos
show; and paired spots keep their order of darkness. Otherwise the analyzer abstains, and says why.

It pairs spots and concludes nothing about them: the person confirms every pairing.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import cv2
import numpy as np

from nevus.cv.align import plausible

NAME = "constellation"
VERSION = "1.0.0"
# Lengths are fractions of each photo's short side, so photos of different resolutions compare.
PARAMS: dict[str, Any] = {
    "neighbours": 4,
    "invariant_radius": 0.03,
    "min_side": 0.015,
    "distinct_sides": 0.04,
    "max_scale": 2.5,
    "max_rotation_deg": 40.0,
    "max_perspective": 0.25,
    "search_tolerance": 0.02,
    "final_tolerance": 0.012,
    "max_hypotheses": 20000,
    "refined": 12,
    "refinements": 3,
    "max_size_ratio": 2.0,
    "min_pairs": 8,
    "max_nfa": 0.01,
    "min_share": 0.4,
    "min_darkness_agreement": 0.3,
    "ambiguity_distance": 0.05,
}
# Why an alignment was refused, as codes the interface translates.
REASONS = ("too_few_spots", "no_consistent_pattern", "too_few_paired", "darkness_disagrees", "ambiguous_pattern")


def _triangles(points: np.ndarray, p: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Shape invariants and corners of the triangles each spot forms with its nearest neighbours.

    Corners are ordered by the side opposite them, shortest first, so the same triangle in another
    photo lists them in the same order. Triangles with a short side, or with two sides of nearly the
    same length (whose order is then a coin toss), are left out.
    """
    n = len(points)
    if n < 3:
        return np.zeros((0, 2)), np.zeros((0, 3), int)
    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    nearest = np.argsort(distances, axis=1)[:, : min(int(p["neighbours"]), n - 1) + 1]
    combos = sorted({c for row in nearest for c in itertools.combinations(sorted(int(i) for i in row), 3)})
    triangles = np.array(combos, int)
    corners = points[triangles]
    sides = np.stack(
        [
            np.linalg.norm(corners[:, 1] - corners[:, 2], axis=1),  # opposite corner 0
            np.linalg.norm(corners[:, 0] - corners[:, 2], axis=1),  # opposite corner 1
            np.linalg.norm(corners[:, 0] - corners[:, 1], axis=1),  # opposite corner 2
        ],
        axis=1,
    )
    order = np.argsort(sides, axis=1)
    a, b, c = np.take_along_axis(sides, order, axis=1).T
    distinct = float(p["distinct_sides"])
    keep = (a >= float(p["min_side"])) & ((b - a) > distinct * c) & ((c - b) > distinct * c)
    corners_in_order = np.take_along_axis(triangles, order, axis=1)
    return np.stack([b / c, a / c], axis=1)[keep], corners_in_order[keep]


def _similarities(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Least-squares similarity (never a mirror) for each set of corresponding corners, in complex
    numbers: z_dst = factor * (z_src - centre_src) + centre_dst."""
    zs = src[..., 0] + 1j * src[..., 1]
    zd = dst[..., 0] + 1j * dst[..., 1]
    cs, cd = zs.mean(axis=-1), zd.mean(axis=-1)
    us, ud = zs - cs[..., None], zd - cd[..., None]
    factor = (np.conj(us) * ud).sum(axis=-1) / np.maximum((np.abs(us) ** 2).sum(axis=-1), 1e-12)
    return factor, cs, cd


def _apply(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return points
    return cv2.perspectiveTransform(points.reshape(-1, 1, 2).astype(np.float64), matrix).reshape(-1, 2)


def _pairs(
    mapped: np.ndarray, b: np.ndarray, tolerance: float, sizes: tuple[np.ndarray, np.ndarray, float], p: dict[str, Any]
) -> list[tuple[int, int]]:
    """One-to-one pairs of mapped spots and spots of the other photo, the closest first, of similar size."""
    if len(mapped) == 0 or len(b) == 0:
        return []
    size_a, size_b, zoom = sizes
    distances = np.linalg.norm(mapped[:, None, :] - b[None, :, :], axis=2)
    ratio = (size_a[:, None] * zoom) / np.maximum(size_b[None, :], 1e-9)
    limit = float(p["max_size_ratio"])
    distances[(ratio > limit) | (ratio < 1 / limit)] = np.inf
    pairs: list[tuple[int, int]] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for flat in np.argsort(distances, axis=None):
        i, j = divmod(int(flat), len(b))
        if distances[i, j] > tolerance:
            break
        if i not in used_a and j not in used_b:
            pairs.append((i, j))
            used_a.add(i)
            used_b.add(j)
    return pairs


def _zoom(matrix: np.ndarray) -> float:
    return math.sqrt(abs(float(np.linalg.det(matrix[:2, :2] / matrix[2, 2]))))


def _refit(
    matrix: np.ndarray, a: np.ndarray, b: np.ndarray, sizes: tuple[np.ndarray, np.ndarray], p: dict[str, Any]
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Refit on the pairs the transform makes (a homography once there are enough), while it pairs more."""
    search = float(p["search_tolerance"])
    pairs = _pairs(_apply(matrix, a), b, search, (*sizes, _zoom(matrix)), p)
    for _ in range(int(p["refinements"])):
        if len(pairs) < 3:
            break
        src = np.array([a[i] for i, _ in pairs], np.float64)
        dst = np.array([b[j] for _, j in pairs], np.float64)
        fitted: np.ndarray | None
        if len(pairs) >= 8:
            fitted, _ = cv2.findHomography(src, dst, cv2.RANSAC, float(p["final_tolerance"]))
        else:
            affine, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
            fitted = None if affine is None else np.vstack([affine, [0.0, 0.0, 1.0]])
        if fitted is None or plausible(fitted, p) is not None:
            break
        refitted = _pairs(_apply(fitted, a), b, search, (*sizes, _zoom(fitted)), p)
        if len(refitted) < len(pairs):
            break
        matrix, pairs = fitted, refitted
    return matrix, _pairs(_apply(matrix, a), b, float(p["final_tolerance"]), (*sizes, _zoom(matrix)), p)


def _hull_area(points: np.ndarray, fallback: float) -> float:
    """The area the spots spread over, where a spot put by chance could land on one of them."""
    if len(points) < 3:
        return fallback
    area = float(cv2.contourArea(cv2.convexHull(points.astype(np.float32))))
    return max(area, fallback * 0.05)


def _inside(points: np.ndarray, width: float, height: float) -> np.ndarray:
    return (points[:, 0] >= 0) & (points[:, 0] < width) & (points[:, 1] >= 0) & (points[:, 1] < height)


def _rank_agreement(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman's correlation: whether the darker spots of one photo are the darker ones of the other."""
    if len(x) < 3:
        return 0.0
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def _tail(k: int, n: int, chance: float) -> float:
    """P(X >= k) for X ~ Binomial(n, chance): k of n spots landing on a spot of the other photo by luck."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    chance = min(max(chance, 1e-12), 1 - 1e-12)
    logs = [
        math.lgamma(n + 1)
        - math.lgamma(i + 1)
        - math.lgamma(n - i + 1)
        + i * math.log(chance)
        + (n - i) * math.log1p(-chance)
        for i in range(k, n + 1)
    ]
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(value - top) for value in logs))


def _scale(short: float) -> np.ndarray:
    return np.array([[short, 0, 0], [0, short, 0], [0, 0, 1]], np.float64)


def match(
    spots_a: list[dict[str, Any]],
    size_a: tuple[int, int],
    spots_b: list[dict[str, Any]],
    size_b: tuple[int, int],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The transform from photo A's pixels to photo B's, from the spots found on each.

    Spots are as `candidates.detect` gives them: x and y as fractions of the photo's width and height,
    the diameter as a fraction of its short side, and the contrast. Returns the 3x3 matrix, the pairs
    of spot indices it lines up and the expected number of chance alignments as good (`nfa`); or an
    abstention with a reason.
    """
    p = {**PARAMS, **(params or {})}
    (wa, ha), (wb, hb) = size_a, size_b
    short_a, short_b = float(min(wa, ha)), float(min(wb, hb))
    a = np.array([[s["x"] * wa, s["y"] * ha] for s in spots_a], np.float64).reshape(-1, 2) / short_a
    b = np.array([[s["x"] * wb, s["y"] * hb] for s in spots_b], np.float64).reshape(-1, 2) / short_b
    sizes = (
        np.array([float(s["diameter"]) for s in spots_a], np.float64),
        np.array([float(s["diameter"]) for s in spots_b], np.float64),
    )
    darkness_a = np.array([float(s["contrast"]) for s in spots_a], np.float64)
    darkness_b = np.array([float(s["contrast"]) for s in spots_b], np.float64)
    width_a, height_a, width_b, height_b = wa / short_a, ha / short_a, wb / short_b, hb / short_b
    base: dict[str, Any] = {"method": "constellation", "matrix": None, "pairs": [], "nfa": None}
    if min(len(a), len(b)) < int(p["min_pairs"]):
        return {**base, "status": "abstained", "reason": "too_few_spots"}
    shape_a, corners_a = _triangles(a, p)
    shape_b, corners_b = _triangles(b, p)
    if len(shape_a) == 0 or len(shape_b) == 0:
        return {**base, "status": "abstained", "reason": "too_few_spots"}
    shape_distance = np.linalg.norm(shape_a[:, None, :] - shape_b[None, :, :], axis=2)
    ia, ib = np.nonzero(shape_distance < float(p["invariant_radius"]))
    if len(ia) > int(p["max_hypotheses"]):
        closest = np.argsort(shape_distance[ia, ib])[: int(p["max_hypotheses"])]
        ia, ib = ia[closest], ib[closest]
    factor, centre_a, centre_b = _similarities(a[corners_a[ia]], b[corners_b[ib]])
    zoom = np.abs(factor)
    keep = (zoom >= 1 / float(p["max_scale"])) & (zoom <= float(p["max_scale"]))
    keep &= np.degrees(np.abs(np.angle(factor))) <= float(p["max_rotation_deg"])
    factor, centre_a, centre_b = factor[keep], centre_a[keep], centre_b[keep]
    if len(factor) == 0:
        return {**base, "status": "abstained", "reason": "no_consistent_pattern"}
    tests = len(factor)

    # Score every hypothesis by the spots it brings within the search tolerance of a spot of B.
    za = a[:, 0] + 1j * a[:, 1]
    zb = b[:, 0] + 1j * b[:, 1]
    scores = np.zeros(tests, int)
    for start in range(0, tests, 512):
        end = start + 512
        mapped = factor[start:end, None] * (za[None, :] - centre_a[start:end, None]) + centre_b[start:end, None]
        nearest = np.abs(mapped[:, :, None] - zb[None, None, :]).min(axis=2)
        scores[start:end] = (nearest <= float(p["search_tolerance"])).sum(axis=1)

    # The chance that a spot put anywhere on the spotted skin of B lands within the tolerance of one.
    spread = _hull_area(b, width_b * height_b)
    chance = min(1.0, len(b) * math.pi * float(p["final_tolerance"]) ** 2 / spread)
    judged: list[tuple[float, np.ndarray, list[tuple[int, int]]]] = []
    for index in np.argsort(-scores)[: int(p["refined"])]:
        f, ca, cb = factor[index], centre_a[index], centre_b[index]
        turn = np.array([[f.real, -f.imag], [f.imag, f.real]])
        shift = np.array([cb.real, cb.imag]) - turn @ np.array([ca.real, ca.imag])
        start_matrix = np.vstack([np.hstack([turn, shift[:, None]]), [0.0, 0.0, 1.0]])
        matrix, pairs = _refit(start_matrix, a, b, sizes, p)
        landed = int(_inside(_apply(matrix, a), width_b, height_b).sum())
        judged.append((tests * _tail(len(pairs), landed, chance), matrix, pairs))
    judged.sort(key=lambda item: item[0])
    nfa, matrix, pairs = judged[0]
    base.update({"nfa": float(nfa), "pairs": [[i, j] for i, j in pairs]})
    if len(pairs) < int(p["min_pairs"]) or nfa > float(p["max_nfa"]):
        return {**base, "status": "abstained", "reason": "no_consistent_pattern"}
    # Of the spots both photos show (each photo's spots that fall inside the other's frame), a real
    # re-photograph pairs a good share; a chance alignment pairs a few among many.
    seen_in_b = int(_inside(_apply(matrix, a), width_b, height_b).sum())
    seen_in_a = int(_inside(_apply(np.linalg.inv(matrix), b), width_a, height_a).sum())
    if len(pairs) < float(p["min_share"]) * max(1, min(seen_in_b, seen_in_a)):
        return {**base, "status": "abstained", "reason": "too_few_paired"}
    pair_a = np.array([i for i, _ in pairs])
    pair_b = np.array([j for _, j in pairs])
    if _rank_agreement(darkness_a[pair_a], darkness_b[pair_b]) < float(p["min_darkness_agreement"]):
        return {**base, "status": "abstained", "reason": "darkness_disagrees"}
    # A different transform about as convincing means the pattern repeats: better not to guess.
    centre = np.array([[width_a / 2, height_a / 2]])
    for other_nfa, other, other_pairs in judged[1:]:
        if other_nfa > float(p["max_nfa"]) or len(other_pairs) < 0.8 * len(pairs):
            continue
        if float(np.linalg.norm(_apply(other, centre) - _apply(matrix, centre))) > float(p["ambiguity_distance"]):
            return {**base, "status": "abstained", "reason": "ambiguous_pattern"}
    problem = plausible(matrix, p)
    if problem:
        return {**base, "status": "abstained", "reason": problem}
    in_pixels = _scale(short_b) @ matrix @ np.linalg.inv(_scale(short_a))
    return {**base, "status": "aligned", "reason": None, "matrix": (in_pixels / in_pixels[2, 2]).tolist()}
