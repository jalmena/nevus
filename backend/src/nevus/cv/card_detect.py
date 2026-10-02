# SPDX-License-Identifier: AGPL-3.0-only
"""Find the reference card in a photo: marker corners, homography to millimetres, scale, tilt, patches.

The homography maps image pixels onto the card plane in millimetres, so a mark seen through the
window is measured in that plane and perspective is corrected, not ignored. Tilt is estimated from
the anisotropy of the mapping at the card centre (a plane tilted by t shortens one axis by cos t),
which needs no camera model; beyond the limit the measurement is flagged and a retake suggested.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

from nevus.cv.card import CARDS, DICTIONARY, CardGeometry, marker_corners_mm
from nevus.cv.imageio import Img

NAME = "scale.card"
VERSION = "1.0.0"
PARAMS: dict[str, Any] = {"tilt_limit_deg": 15.0, "min_marker_px": 40.0}


def _detector() -> Any:
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICTIONARY), params)


def apply_h(h: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, np.float64).reshape(-1, 1, 2)
    return np.asarray(cv2.perspectiveTransform(pts, h)).reshape(-1, 2)


def local_jacobian(h: np.ndarray, at: tuple[float, float]) -> np.ndarray:
    x, y = at
    base, dx, dy = apply_h(h, np.array([[x, y], [x + 1.0, y], [x, y + 1.0]]))
    return np.column_stack([dx - base, dy - base])


def detect(image: Img, params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**PARAMS, **(params or {})}
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    corners, ids, _ = _detector().detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return {"found": False, "ids": [], "flags": []}
    detected = [
        (int(i), np.asarray(c, np.float64).reshape(4, 2))
        for c, i in zip(corners, np.asarray(ids).flatten(), strict=True)
    ]
    best: tuple[CardGeometry, dict[int, np.ndarray]] | None = None
    for card in CARDS:
        members = _best_instance(card, [(i, q) for i, q in detected if i in card.markers])
        if len(members) >= 2 and (best is None or len(members) > len(best[1])):
            best = (card, members)
    if best is None:
        return {"found": False, "ids": sorted({i for i, _ in detected}), "flags": []}
    card, members = best
    src = np.concatenate([members[i] for i in sorted(members)])
    dst = np.asarray([pt for i in sorted(members) for pt in marker_corners_mm(card, i)], np.float64)
    h, _ = cv2.findHomography(src, dst, 0)
    if h is None:
        return {"found": False, "ids": sorted(members), "flags": []}
    sides = [float(np.linalg.norm(q[k] - q[(k + 1) % 4])) for q in members.values() for k in range(4)]
    return _describe(image, card, h, src, dst, sorted(members), min(sides), p)


def _best_instance(card: CardGeometry, found: list[tuple[int, np.ndarray]]) -> dict[int, np.ndarray]:
    """Group markers into one physical card. Several cards (or a whole printed sheet) may be in view.

    Each marker's own corners give a homography for its card; the markers that sit where that
    homography predicts their siblings belong to the same card. The largest consistent group wins.
    """
    best: dict[int, np.ndarray] = {}
    best_side = 0.0
    for marker_id, quad in found:
        mm = np.asarray(marker_corners_mm(card, marker_id), np.float64)
        h_mm_to_px, _ = cv2.findHomography(mm, quad, 0)
        if h_mm_to_px is None:
            continue
        side = float(np.mean([np.linalg.norm(quad[k] - quad[(k + 1) % 4]) for k in range(4)]))
        members = {marker_id: quad}
        for other_id, other in found:
            if other_id in members:
                continue
            predicted = apply_h(h_mm_to_px, np.array([card.markers[other_id]]))[0]
            if np.linalg.norm(predicted - other.mean(axis=0)) < 0.6 * side:
                members[other_id] = other
        if len(members) > len(best) or (len(members) == len(best) and side > best_side):
            best, best_side = members, side
    return best


def _describe(
    image: Img,
    card: CardGeometry,
    h: np.ndarray,
    src: np.ndarray,
    dst: np.ndarray,
    used: list[int],
    marker_px: float,
    p: dict[str, Any],
) -> dict[str, Any]:
    residual = float(np.sqrt(np.mean(np.sum((apply_h(h, src) - dst) ** 2, axis=1))))
    centre_px = apply_h(np.linalg.inv(h), np.array([card.centre]))[0]
    jac = local_jacobian(h, (float(centre_px[0]), float(centre_px[1])))
    s_max, s_min = np.linalg.svd(jac, compute_uv=False)
    mm_per_px = float(math.sqrt(s_max * s_min))
    tilt = math.degrees(math.acos(min(1.0, float(s_min / s_max))))
    flags: list[str] = []
    if tilt > float(p["tilt_limit_deg"]):
        flags.append("tilted")
    if marker_px < float(p["min_marker_px"]):
        flags.append("card_small")
    return {
        "found": True,
        "card": card.name,
        "ids": sorted(used),
        "homography": h.tolist(),
        "centre_px": [round(float(centre_px[0]), 2), round(float(centre_px[1]), 2)],
        "mm_per_px": round(mm_per_px, 6),
        "residual_mm": round(residual, 4),
        "sigma_fit": round(residual / card.baseline, 6),
        "tilt_deg": round(tilt, 2),
        "marker_px": round(marker_px, 1),
        "patches": {
            "grey": _patch(image, h, card.grey),
            "white": _patch(image, h, card.white),
        },
        "flags": flags,
    }


def _patch(image: Img, h: np.ndarray, rect: tuple[float, float, float, float]) -> list[int] | None:
    x, y, w, hgt = rect
    inset = 1.0  # stay away from the printed edges
    quad_mm = np.array(
        [
            [x + inset, y + inset],
            [x + w - inset, y + inset],
            [x + w - inset, y + hgt - inset],
            [x + inset, y + hgt - inset],
        ]
    )
    quad_px = apply_h(np.linalg.inv(h), quad_mm).astype(np.int32)
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, quad_px, 1)
    if mask.sum() < 4 or image.ndim != 3:
        return None
    pixels = image[mask.astype(bool)]
    b, g, r = np.median(pixels, axis=0)
    return [int(r), int(g), int(b)]
