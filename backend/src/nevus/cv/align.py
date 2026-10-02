# SPDX-License-Identifier: AGPL-3.0-only
"""Aligning two photographs of the same mark, and a difference map as a visual aid.

When both photos show the reference card, the card's own homographies align them exactly (photo B
to millimetres to photo A). Otherwise SIFT features on contrast-equalised grey images are matched
and a homography fitted with RANSAC; the result is used only when enough matches agree, and the
analyzer abstains (and says why) when they do not: a wrong overlay is worse than no overlay.
The difference map compares colour after alignment and exposure matching; it shows where to look
and measures nothing.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from nevus.cv.imageio import Img, resize_long_edge

# Why an alignment was refused, as codes the interface translates.
REASONS = (
    "too_little_detail",
    "too_few_matches",
    "no_consistent_alignment",
    "matches_disagree",
    "mirrored",
    "distance",
    "angle",
)

NAME = "align"
VERSION = "1.0.0"
PARAMS: dict[str, Any] = {
    "long_edge": 1600,
    "ratio": 0.75,
    "ransac_px": 4.0,
    "min_inliers": 25,
    "min_inlier_ratio": 0.25,
    "max_scale": 2.5,
    "max_perspective": 0.002,
    "overlay_long_edge": 2048,
    "diff_long_edge": 1024,
    "diff_full_scale": 25.0,
}


def _scale_matrix(s: float) -> np.ndarray:
    return np.array([[s, 0, 0], [0, s, 0], [0, 0, 1]], np.float64)


def from_cards(card_a: list[list[float]], card_b: list[list[float]]) -> dict[str, Any]:
    """Each card homography maps its photo to millimetres; B -> mm -> A."""
    h_a = np.asarray(card_a, np.float64)
    h_b = np.asarray(card_b, np.float64)
    matrix = np.linalg.inv(h_a) @ h_b
    return {"status": "aligned", "method": "card", "reason": None, "matrix": (matrix / matrix[2, 2]).tolist()}


def plausible(matrix: np.ndarray, p: dict[str, Any]) -> str | None:
    """Reject transforms no hand-held re-photograph produces: huge zoom, mirror, strong perspective."""
    affine = matrix[:2, :2] / matrix[2, 2]
    det = float(np.linalg.det(affine))
    if det <= 0:
        return "mirrored"
    scale = math.sqrt(det)
    if not 1 / float(p["max_scale"]) <= scale <= float(p["max_scale"]):
        return "distance"
    if max(abs(matrix[2, 0]), abs(matrix[2, 1])) / abs(matrix[2, 2]) > float(p["max_perspective"]):
        return "angle"
    return None


def _mask_for(mask: np.ndarray | None, shape: tuple[int, ...]) -> np.ndarray | None:
    if mask is None:
        return None
    resized = cv2.resize(mask.astype(np.uint8) * 255, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return resized if resized.any() else None


def from_features(
    image_a: Img,
    image_b: Img,
    params: dict[str, Any] | None = None,
    mask_a: np.ndarray | None = None,
    mask_b: np.ndarray | None = None,
) -> dict[str, Any]:
    """The transform from B to A. With masks (of any size), only features inside them are matched:
    on the skin, say, so that a background seen in both photos cannot line them up."""
    p = {**PARAMS, **(params or {})}
    small_a, sa = resize_long_edge(image_a, int(p["long_edge"]))
    small_b, sb = resize_long_edge(image_b, int(p["long_edge"]))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_a = clahe.apply(cv2.cvtColor(small_a, cv2.COLOR_BGR2GRAY))
    gray_b = clahe.apply(cv2.cvtColor(small_b, cv2.COLOR_BGR2GRAY))
    sift = cv2.SIFT.create(nfeatures=4000)
    kp_a, desc_a = sift.detectAndCompute(gray_a, _mask_for(mask_a, gray_a.shape))
    kp_b, desc_b = sift.detectAndCompute(gray_b, _mask_for(mask_b, gray_b.shape))
    base: dict[str, Any] = {"method": "features", "matrix": None, "matches": 0, "inliers": 0, "inlier_ratio": 0.0}
    if desc_a is None or desc_b is None or len(kp_a) < 8 or len(kp_b) < 8:
        return {**base, "status": "abstained", "reason": "too_little_detail"}
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc_b, desc_a, k=2)
    good = [m for m, n in (pair for pair in pairs if len(pair) == 2) if m.distance < float(p["ratio"]) * n.distance]
    base["matches"] = len(good)
    if len(good) < int(p["min_inliers"]):
        return {**base, "status": "abstained", "reason": "too_few_matches"}
    src = np.array([kp_b[m.queryIdx].pt for m in good], np.float32).reshape(-1, 1, 2)
    dst = np.array([kp_a[m.trainIdx].pt for m in good], np.float32).reshape(-1, 1, 2)
    small_matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, float(p["ransac_px"]))
    if small_matrix is None or mask is None:
        return {**base, "status": "abstained", "reason": "no_consistent_alignment"}
    inliers = int(mask.sum())
    ratio = inliers / len(good)
    base.update({"inliers": inliers, "inlier_ratio": round(ratio, 3)})
    if inliers < int(p["min_inliers"]) or ratio < float(p["min_inlier_ratio"]):
        return {**base, "status": "abstained", "reason": "matches_disagree"}
    # Back to full-resolution coordinates: full_a = S_a^-1 * small_a, small_b = S_b * full_b.
    matrix = np.linalg.inv(_scale_matrix(sa)) @ small_matrix @ _scale_matrix(sb)
    matrix /= matrix[2, 2]
    problem = plausible(matrix, p)
    if problem:
        return {**base, "status": "abstained", "reason": problem}
    return {**base, "status": "aligned", "reason": None, "matrix": matrix.tolist()}


def difference(
    image_a: Img, image_b: Img, matrix: list[list[float]], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Photo B redrawn in photo A's frame, and a map of where their colours differ.

    Both are WebP with transparency, so the parts of A that B does not cover stay empty instead of
    being filled with something that was never photographed. The overlay has the size of A's full
    rendition; the map is smaller, since it is blurred anyway.
    """
    p = {**PARAMS, **(params or {})}
    big_a, sa = resize_long_edge(image_a, int(p["overlay_long_edge"]))
    h, w = big_a.shape[:2]
    full = np.asarray(matrix, np.float64)
    # Shrink B by area averaging first, to the size it will have in A's frame, so the warp itself
    # barely resamples: a warp that also downsizes aliases the skin texture into false differences.
    zoom = math.sqrt(abs(float(np.linalg.det(full[:2, :2] / full[2, 2]))))
    factor = min(1.0, sa * zoom)
    small_b = (
        image_b if factor >= 1.0 else cv2.resize(image_b, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    )
    to_a = _scale_matrix(sa) @ full @ np.linalg.inv(_scale_matrix(factor))  # small B -> big A
    warped = cv2.warpPerspective(small_b, to_a, (w, h), flags=cv2.INTER_LINEAR)
    covered = cv2.warpPerspective(np.full(small_b.shape[:2], 255, np.uint8), to_a, (w, h), flags=cv2.INTER_LINEAR)
    diff_a, _ = resize_long_edge(big_a, int(p["diff_long_edge"]))
    dh, dw = diff_a.shape[:2]
    diff_b = warped if (dw, dh) == (w, h) else cv2.resize(warped, (dw, dh), interpolation=cv2.INTER_AREA)
    # Only where B fully covers the pixel: partly covered border pixels are blends with black.
    valid = cv2.resize(covered, (dw, dh), interpolation=cv2.INTER_AREA) > 250
    lab_a = cv2.cvtColor(diff_a, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_b = cv2.cvtColor(diff_b, cv2.COLOR_BGR2LAB).astype(np.float32)
    if valid.sum() > 100:
        for channel in range(3):  # exposure and white balance: match B's statistics to A's
            a_vals, b_vals = lab_a[..., channel][valid], lab_b[..., channel][valid]
            gain = (a_vals.std() + 1e-3) / (b_vals.std() + 1e-3)
            lab_b[..., channel] = (lab_b[..., channel] - b_vals.mean()) * gain + a_vals.mean()
    delta = np.sqrt(((lab_a - lab_b) ** 2).sum(axis=2))
    delta = cv2.GaussianBlur(delta, (0, 0), 2.0)
    delta[~valid] = 0
    level = np.clip(delta / float(p["diff_full_scale"]), 0, 1)
    heat = np.zeros((dh, dw, 4), np.uint8)
    # One hue, light to dark, transparent where nothing differs (sequential encoding of magnitude).
    teal = np.array([136, 148, 11], np.float32)  # #0b9488 in BGR
    dark = np.array([60, 70, 8], np.float32)
    heat[..., :3] = (teal + (dark - teal) * level[..., None]).astype(np.uint8)
    heat[..., 3] = (level * 220).astype(np.uint8)
    overlay = np.dstack([warped, covered])
    ok_overlay, overlay_webp = cv2.imencode(".webp", overlay, [cv2.IMWRITE_WEBP_QUALITY, 85])
    ok_heat, heat_webp = cv2.imencode(".webp", heat, [cv2.IMWRITE_WEBP_QUALITY, 80])
    if not ok_overlay or not ok_heat:
        raise ValueError("could not encode the comparison images")
    return {
        "overlay": overlay_webp.tobytes(),
        "heatmap": heat_webp.tobytes(),
        "width": w,
        "height": h,
        "coverage": round(float(valid.mean()), 3),
        "mean_difference": round(float(delta[valid].mean()) if valid.any() else 0.0, 2),
    }
