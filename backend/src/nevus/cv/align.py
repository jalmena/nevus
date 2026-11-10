# SPDX-License-Identifier: AGPL-3.0-only
"""Aligning two photographs of the same mark, and a difference map as a visual aid.

Two steps. A rough map first: when both photos show the reference card, its homographies (photo B
to millimetres to photo A) give the scale and the perspective exactly; otherwise SIFT features on
the skin are matched and a homography fitted with RANSAC, used only when enough matches agree, and
the analyzer abstains (and says why) when they do not: a wrong overlay is worse than no overlay.

Then the skin around the mark, because the card lines up the cards, not the skin: it may lie on the
skin at any angle and a little off at each visit. Inside a disc around the mark, with the card and
the hairs left out, the skin of photo B is turned and shifted (never zoomed, so a mark that grew
still shows it) until it lies on photo A's: a full turn search on the pigment, then ECC down to a
fraction of a pixel on the finer detail. The result is kept only when one way of laying the skin
clearly beats every other; else the rough map stands.

The difference map compares colour after alignment and exposure matching; it shows where to look
and measures nothing.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from nevus.cv.card import APERTURE_RADIUS
from nevus.cv.imageio import Img, resize_long_edge
from nevus.cv.normalise import card_named

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
VERSION = "1.2.0"
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
    # Closer matching when the quick one fails, then the skin around the mark: a disc of photo A drawn
    # into a square frame of refine_px, searched every turn_step_deg on the pigment (coarse_blur), laid
    # down through middle_blur to fine_blur, judged, and last fitted closest within `focus` of the mark.
    "detail_long_edge": 2400,
    "refine_px": 512,
    "window_inset": 0.85,
    "mark_region_mm": 8.0,
    "region_fraction": 0.2,
    "search_px": 128,
    "turn_step_deg": 15.0,
    "coarse_blur": 4.0,
    "middle_blur": 2.0,
    "fine_blur": 1.0,
    "proposals": 6,
    "focus": 0.5,
    "nudges_deg": [-6.0, -3.0, 3.0, 6.0],
    "min_skin_score": 0.1,
    "skin_margin": 1.25,
    "max_skin_shift": 0.6,
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


def anchored(matrix: list[list[float]], anchor_a: tuple[float, float], anchor_b: tuple[float, float]) -> dict[str, Any]:
    """The card alignment, shifted so that the mark itself coincides: the card may sit differently on the
    skin at each visit, and the mark, not the card, is what the two photos have in common."""
    m = np.asarray(matrix, np.float64)
    moved = cv2.perspectiveTransform(np.array([[anchor_b]], np.float64), m).reshape(2)
    dx, dy = float(anchor_a[0] - moved[0]), float(anchor_a[1] - moved[1])
    shift = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]])
    out = shift @ m
    return {
        "status": "aligned",
        "method": "card+mark",
        "reason": None,
        "matrix": (out / out[2, 2]).tolist(),
        "shift_px": [round(dx, 1), round(dy, 1)],
    }


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


Card = dict[str, Any]
Inside = Callable[[np.ndarray], np.ndarray]


def _card_body(card: Card | None, inset: float) -> Inside | None:
    """Which pixels show the card itself (with a margin for its edge and shadow), not skin."""
    if not card:
        return None
    geometry = card_named(str(card.get("card")))
    if geometry is None:
        return None
    h = np.asarray(card["homography"], np.float64)
    margin = 1.5
    cx, cy = geometry.centre
    aperture = APERTURE_RADIUS * inset if geometry.name == "window" else 0.0

    def body(points: np.ndarray) -> np.ndarray:
        mm = cv2.perspectiveTransform(points.reshape(-1, 1, 2).astype(np.float64), h).reshape(-1, 2)
        on = (
            (mm[:, 0] > -margin)
            & (mm[:, 0] < geometry.width + margin)
            & (mm[:, 1] > -margin)
            & (mm[:, 1] < geometry.height + margin)
        )
        out: np.ndarray = on & (np.hypot(mm[:, 0] - cx, mm[:, 1] - cy) >= aperture)
        return out

    return body


def skin_mask(image: Img, card: Card | None, inset: float = 0.85) -> np.ndarray | None:
    """Where a photo with the card shows skin: around the card and inside its window; None without a card."""
    body = _card_body(card, inset)
    if body is None:
        return None
    h, w = image.shape[:2]
    step = 4  # a coarse grid is enough for a mask that only steers feature detection
    ys, xs = np.mgrid[0:h:step, 0:w:step]
    points = np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float64)
    coarse = (~body(points)).reshape(xs.shape).astype(np.uint8)
    out: np.ndarray = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    return out


def _without_hairs(image: Img, mask: np.ndarray | None, p: dict[str, Any]) -> np.ndarray:
    """A feature mask for a whole photo, at the size features are matched: the skin, without its hairs."""
    small, _ = resize_long_edge(image, int(p["long_edge"]))
    h, w = small.shape[:2]
    if mask is None:
        valid = np.ones((h, w), bool)
    else:
        valid = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    grey = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
    out: np.ndarray = valid & ~_hairs(grey, valid, 0.0125 * max(h, w))
    return out


def _frame(centre: tuple[float, float], radius: float, n: int) -> np.ndarray:
    """Photo A's pixels -> an n x n frame on the disc of that centre and radius."""
    k = n / (2 * radius)
    return np.array([[k, 0, n / 2 - k * centre[0]], [0, k, n / 2 - k * centre[1]], [0, 0, 1.0]])


def _warp(image: Img, to_frame: np.ndarray, n: int) -> Img:
    """The part of a photo that lands in the frame, shrunk by area first so that the warp does not alias."""
    corners = np.array([[[0, 0]], [[n, 0]], [[n, n]], [[0, n]]], np.float64)
    back = cv2.perspectiveTransform(corners, np.linalg.inv(to_frame)).reshape(-1, 2)
    h, w = image.shape[:2]
    x0, y0 = (max(0, int(v) - 2) for v in np.floor(back.min(axis=0)))
    x1, y1 = (min(limit, int(v) + 2) for v, limit in zip(np.ceil(back.max(axis=0)), (w, h), strict=True))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return np.zeros((n, n, 3), np.uint8)
    crop = image[y0:y1, x0:x1]
    span = float(np.ptp(back, axis=0).max())
    factor = min(1.0, 1.5 * n / max(span, 1.0))
    small = crop if factor >= 1.0 else cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    sx, sy = crop.shape[1] / small.shape[1], crop.shape[0] / small.shape[0]
    small_to_photo = np.array([[sx, 0, x0], [0, sy, y0], [0, 0, 1.0]])
    out: Img = cv2.warpPerspective(small, to_frame @ small_to_photo, (n, n), flags=cv2.INTER_LINEAR)
    return out


def _valid(shape: tuple[int, ...], frame_to_photo: np.ndarray, body: Inside | None, n: int) -> np.ndarray:
    """Frame pixels that show this photo's skin: inside the photo and off its card."""
    ys, xs = np.mgrid[0:n, 0:n]
    points = np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float64) + 0.5
    photo = cv2.perspectiveTransform(points.reshape(-1, 1, 2), frame_to_photo).reshape(-1, 2)
    h, w = shape[:2]
    ok = (photo[:, 0] >= 1) & (photo[:, 0] < w - 1) & (photo[:, 1] >= 1) & (photo[:, 1] < h - 1)
    if body is not None:
        ok &= ~body(photo)
    out: np.ndarray = ok.reshape(n, n)
    return out


def _hairs(grey: np.ndarray, valid: np.ndarray, min_length: float) -> np.ndarray:
    """Hairs: thin dark ridges, longer than any pore (min_length pixels), a little widened.

    Across a dark ridge the image curves up sharply and along it hardly at all (the Hessian's two
    eigenvalues), which tells a hair from a pore or a freckle even where it crosses them. Hairs grow,
    fall and lie differently at every visit, so they are left out of the fit rather than matched."""
    found = np.zeros(grey.shape, bool)
    for sigma in (1.0, 1.8):
        s = cv2.GaussianBlur(grey, (0, 0), sigma)
        dxx = cv2.Sobel(s, cv2.CV_32F, 2, 0, ksize=3)
        dyy = cv2.Sobel(s, cv2.CV_32F, 0, 2, ksize=3)
        dxy = cv2.Sobel(s, cv2.CV_32F, 1, 1, ksize=3)
        root = np.sqrt((dxx - dyy) ** 2 + 4 * dxy**2)
        across = 0.5 * (dxx + dyy + root)
        along = 0.5 * (dxx + dyy - root)
        strength = across * sigma**2
        level = float(np.percentile(strength[valid], 90)) if valid.any() else 0.0
        found |= (across > 0) & (np.abs(along) < 0.35 * across) & (strength > max(level, 4.0))
    found &= valid
    count, labels, stats, _ = cv2.connectedComponentsWithStats(found.astype(np.uint8), connectivity=8)
    # A hair is long and thin (its second moments), and crossing hairs make a wide, sparse net; the dots
    # of a mark's network, where they touch, make a small round cluster, which stays.
    ys, xs = np.nonzero(labels)
    which = np.asarray(labels[ys, xs], np.intp)
    sums = [np.bincount(which, weights=w, minlength=count) for w in (np.ones_like(xs), xs, ys)]
    number = np.maximum(sums[0], 1)
    mx, my = sums[1] / number, sums[2] / number
    dx, dy = xs - mx[which], ys - my[which]
    cxx, cyy, cxy = (np.bincount(which, weights=w, minlength=count) / number for w in (dx * dx, dy * dy, dx * dy))
    root = np.sqrt((cxx - cyy) ** 2 + 4 * cxy**2)
    major, minor = np.sqrt(np.maximum((cxx + cyy + root) / 2, 0)), np.sqrt(np.maximum((cxx + cyy - root) / 2, 0))
    extent = np.maximum(stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT])
    sparse = stats[:, cv2.CC_STAT_AREA] < 0.2 * stats[:, cv2.CC_STAT_WIDTH] * stats[:, cv2.CC_STAT_HEIGHT]
    thin = (4 * major >= min_length) & (major >= 3 * np.maximum(minor, 0.5))
    long = thin | (sparse & (extent >= 2.5 * min_length))
    long[0] = False
    grown = cv2.dilate(long[labels].astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    out: np.ndarray = grown.astype(bool)
    return out


def _skin(frame: Img, valid: np.ndarray, n: int) -> np.ndarray:
    """The frame's pixels that show skin: valid, without the hairs."""
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    out: np.ndarray = valid & ~_hairs(grey, valid, n / 25)
    return out


def _texture(frame: Img, skin: np.ndarray, n: int, blur: float) -> np.ndarray:
    """The skin's texture, comparable between visits: shading removed, each part as loud as any other.

    Zero off the skin, so the card's ring, the edge of a photo or a hair cannot pull the fit. `blur`
    sets the finest detail kept: the relief of the skin catches the light differently at each visit."""
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    weight = skin.astype(np.float32)
    sigma = n / 16
    low = cv2.GaussianBlur(grey * weight, (0, 0), sigma) / np.maximum(cv2.GaussianBlur(weight, (0, 0), sigma), 1e-3)
    band = cv2.GaussianBlur((grey - low) * weight, (0, 0), blur) * weight
    spread = float(band[skin].std()) if skin.any() else 0.0
    if spread <= 1e-6:
        return band
    # The mark, far darker than its surroundings, would otherwise carry the fit alone, and a mark fits
    # itself turned about its own centre: local contrast is evened out, and the extremes clipped.
    near = n / 64
    local = np.sqrt(
        cv2.GaussianBlur(band * band, (0, 0), near) / np.maximum(cv2.GaussianBlur(weight, (0, 0), near), 1e-3)
    )
    out: np.ndarray = np.clip(band / (local + 0.5 * spread), -3.0, 3.0) * weight
    return out


def _score(ta: np.ndarray, wa: np.ndarray, tb: np.ndarray, wb: np.ndarray, r: np.ndarray, n: int) -> float:
    """Normalised correlation of A's texture with B's moved by r (B frame -> A frame), where both show skin."""
    moved = cv2.warpAffine(tb, r[:2], (n, n), flags=cv2.INTER_LINEAR)
    cover = cv2.warpAffine(wb, r[:2], (n, n), flags=cv2.INTER_LINEAR) * wa
    if cover.sum() < 0.3 * wa.sum():
        return -1.0
    a, b = ta * cover, moved * cover
    denominator = math.sqrt(float((a * ta).sum()) * float((b * moved).sum()))
    return float((a * moved).sum()) / denominator if denominator > 0 else -1.0


def _rigid(turn_deg: float, shift: tuple[float, float], n: int) -> np.ndarray:
    """B frame -> A frame: a turn about the frame's centre, then a shift."""
    m = np.vstack([cv2.getRotationMatrix2D((n / 2, n / 2), turn_deg, 1.0), [0, 0, 1]])
    m[0, 2] += shift[0]
    m[1, 2] += shift[1]
    return m


def _correlate(a: np.ndarray, b: np.ndarray) -> tuple[tuple[float, float], float]:
    """The shift d that best lays b on a (b's x lands on a's x + d), by plain cross-correlation.

    Not phase correlation: whitening the spectrum lifts the finest detail, the skin's relief, which
    changes with the light between visits; plain correlation is carried by the pigment."""
    m = a.shape[0]
    size = 2 * m
    product = np.fft.rfft2(a, (size, size)) * np.conj(np.fft.rfft2(b, (size, size)))
    corr = np.fft.irfft2(product, (size, size))
    y, x = np.unravel_index(int(np.argmax(corr)), corr.shape)
    dy, dx = (int(y) - size if y > m else int(y)), (int(x) - size if x > m else int(x))
    energy = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return (float(dx), float(dy)), float(corr[y, x]) / energy if energy > 0 else 0.0


def _turns(ta: np.ndarray, tb: np.ndarray, p: dict[str, Any], n: int) -> list[np.ndarray]:
    """Rigid guesses (B frame -> A frame) over a full turn: at each angle, the best shift."""
    m = int(p["search_px"])
    small_a = cv2.resize(ta, (m, m), interpolation=cv2.INTER_AREA)
    small_b = cv2.resize(tb, (m, m), interpolation=cv2.INTER_AREA)
    out = []
    for angle in np.arange(0.0, 360.0, float(p["turn_step_deg"])):
        turned = cv2.warpAffine(small_b, cv2.getRotationMatrix2D((m / 2, m / 2), float(angle), 1.0), (m, m))
        (dx, dy), _ = _correlate(small_a, turned)
        out.append(_rigid(float(angle), (dx * n / m, dy * n / m), n))
    return out


def _keypoints(fa: Img, va: np.ndarray, fb: Img, vb: np.ndarray, n: int) -> np.ndarray | None:
    """A rigid guess from SIFT matches between the two frames, if enough agree."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    sift = cv2.SIFT.create(nfeatures=1500)
    ga = clahe.apply(cv2.cvtColor(fa, cv2.COLOR_BGR2GRAY))
    gb = clahe.apply(cv2.cvtColor(fb, cv2.COLOR_BGR2GRAY))
    kp_a, desc_a = sift.detectAndCompute(ga, va.astype(np.uint8) * 255)
    kp_b, desc_b = sift.detectAndCompute(gb, vb.astype(np.uint8) * 255)
    if desc_a is None or desc_b is None or len(kp_a) < 6 or len(kp_b) < 6:
        return None
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc_b, desc_a, k=2)
    good = [m for m, k in (pair for pair in pairs if len(pair) == 2) if m.distance < 0.8 * k.distance]
    if len(good) < 6:
        return None
    src = np.array([kp_b[m.queryIdx].pt for m in good], np.float64)
    dst = np.array([kp_a[m.trainIdx].pt for m in good], np.float64)
    similar, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if similar is None or inliers is None or int(inliers.sum()) < 6:
        return None
    turn = math.degrees(math.atan2(similar[1, 0], similar[0, 0]))
    # Keep the turn, drop the zoom: the scale comes from the card (or the first fit), never from the mark.
    rigid = _rigid(-turn, (0.0, 0.0), n)
    keep = inliers.ravel().astype(bool)
    moved = cv2.transform(src[keep].reshape(-1, 1, 2), rigid[:2]).reshape(-1, 2)
    shift = (dst[keep] - moved).mean(axis=0)
    rigid[0, 2] += shift[0]
    rigid[1, 2] += shift[1]
    return rigid


def _polish(
    ta: np.ndarray,
    va: np.ndarray,
    tb: np.ndarray,
    vb: np.ndarray,
    guess: np.ndarray,
    levels: tuple[int, ...] = (4, 2, 1),
) -> np.ndarray | None:
    """ECC on the textures, coarse to fine, from a guess (B frame -> A frame); None if it does not converge.

    B is first turned by the guess, so that ECC only polishes a small residue: its rigid model reads the
    angle back through an arcsine and cannot hold a turn past a quarter. Only pixels that show skin in
    both frames count, so neither the card nor the edge of a photo pulls."""
    n = ta.shape[0]
    turned = cv2.warpAffine(tb, guess[:2], (n, n), flags=cv2.INTER_LINEAR)
    turned_valid = cv2.warpAffine(vb.astype(np.uint8), guess[:2], (n, n), flags=cv2.INTER_NEAREST)
    warp = np.eye(2, 3, dtype=np.float32)  # ECC wants A frame -> turned B frame
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5)
    mask_a = va.astype(np.uint8)
    for size in (n // step for step in levels):
        k = size / n
        level = warp.copy()
        level[:, 2] *= k
        a = cv2.resize(ta, (size, size), interpolation=cv2.INTER_AREA)
        b = cv2.resize(turned, (size, size), interpolation=cv2.INTER_AREA)
        ma = cv2.resize(mask_a, (size, size), interpolation=cv2.INTER_NEAREST)
        mb = cv2.resize(turned_valid, (size, size), interpolation=cv2.INTER_NEAREST)
        try:
            _, found = cv2.findTransformECCWithMask(a, b, ma, mb, level, cv2.MOTION_EUCLIDEAN, criteria, 3)
        except cv2.error:
            return None
        warp = np.asarray(found, np.float32).copy()
        warp[:, 2] /= k
    residue = np.vstack([warp.astype(np.float64), [0, 0, 1]])
    out: np.ndarray = np.linalg.inv(residue) @ guess
    return out


def _same(m1: np.ndarray, m2: np.ndarray, n: int, degrees: float = 4.0, fraction: float = 0.04) -> bool:
    """Whether two rigid maps of the frame agree: within some degrees and some fraction of the frame."""
    turn = math.degrees(math.atan2(m1[1, 0], m1[0, 0]) - math.atan2(m2[1, 0], m2[0, 0]))
    centre = np.array([n / 2, n / 2, 1.0])
    apart = float(np.linalg.norm((m1 @ centre)[:2] - (m2 @ centre)[:2]))
    return abs((turn + 180) % 360 - 180) < degrees and apart < fraction * n


def refine(
    image_a: Img,
    image_b: Img,
    matrix: list[list[float]],
    centre: tuple[float, float],
    radius: float,
    card_a: Card | None = None,
    card_b: Card | None = None,
    params: dict[str, Any] | None = None,
    mark: tuple[float, float] | None = None,
) -> dict[str, Any] | None:
    """A rough B -> A map made exact on the skin: a turn and a shift, never a zoom.

    `centre` and `radius` give the disc of photo A to work on (the card's window, or around the mark);
    `mark` is where the mark itself is in photo A, if known, for the last and closest fit. None when
    no way of laying the skin clearly beats the others: then the rough map is the better guess."""
    p = {**PARAMS, **(params or {})}
    n = int(p["refine_px"])
    start = np.asarray(matrix, np.float64)
    to_frame = _frame(centre, radius, n)
    frame_b = to_frame @ start
    fa, fb = _warp(image_a, to_frame, n), _warp(image_b, frame_b, n)
    disc = np.zeros((n, n), np.uint8)
    cv2.circle(disc, (n // 2, n // 2), n // 2 - 1, 1, -1)
    inset = float(p["window_inset"])
    va = _valid(image_a.shape, np.linalg.inv(to_frame), _card_body(card_a, inset), n) & disc.astype(bool)
    vb = _valid(image_b.shape, np.linalg.inv(frame_b), _card_body(card_b, inset), n)
    if va.sum() < 0.3 * disc.sum() or vb.sum() < 0.3 * disc.sum():
        return None
    # Coarse, on the pigment: every turn converges somewhere; a round mark fits itself at any angle, so
    # this only proposes. Fine, on the skin's own detail: each distinct proposal is laid to a pixel and
    # judged there, and the best must stand clear of the next best before it is believed.
    sa, sb = _skin(fa, va, n), _skin(fb, vb, n)
    ca, cb = _texture(fa, sa, n, float(p["coarse_blur"])), _texture(fb, sb, n, float(p["coarse_blur"]))
    guesses = [np.eye(3), *_turns(ca, cb, p, n)]
    keyed = _keypoints(fa, sa, fb, sb, n)
    if keyed is not None:
        guesses.append(keyed)
    coarse: list[tuple[float, np.ndarray]] = []
    for guess in guesses:
        polished = _polish(ca, sa, cb, sb, guess, (4,))
        if polished is not None:
            coarse.append((_score(ca, sa.astype(np.float32), cb, sb.astype(np.float32), polished, n), polished))
    coarse.sort(key=lambda item: item[0], reverse=True)
    proposals: list[np.ndarray] = []
    for _, m in coarse:
        if not any(_same(m, other, n) for other in proposals):
            proposals.append(m)
    # Down through a middle scale: the finest detail only pulls the right way from close by.
    da, db = _texture(fa, sa, n, float(p["middle_blur"])), _texture(fb, sb, n, float(p["middle_blur"]))
    ta, tb = _texture(fa, sa, n, float(p["fine_blur"])), _texture(fb, sb, n, float(p["fine_blur"]))
    wa, wb = sa.astype(np.float32), sb.astype(np.float32)

    def descend(start: np.ndarray) -> tuple[float, np.ndarray] | None:
        middle = _polish(da, sa, db, sb, start, (2, 1))
        fine = _polish(ta, sa, tb, sb, middle, (1,)) if middle is not None else None
        return (_score(ta, wa, tb, wb, fine, n), fine) if fine is not None else None

    judged = [found for found in map(descend, proposals[: int(p["proposals"])]) if found is not None]
    if not judged:
        return None
    judged.sort(key=lambda item: item[0], reverse=True)
    # Real skin has neighbouring optima a few degrees apart: start again on either side of the best.
    nudged = [descend(_rigid(float(d), (0.0, 0.0), n) @ judged[0][1]) for d in p["nudges_deg"]]
    judged.extend(found for found in nudged if found is not None)
    judged.sort(key=lambda item: item[0], reverse=True)
    score, r = judged[0]
    # A rival is another way to lay the skin, not the same way a little off: that one shares the mark.
    rival = max((other for other, m in judged[1:] if not _same(m, r, n, 20.0, 0.15)), default=0.0)
    if score < float(p["min_skin_score"]) or score < float(p["skin_margin"]) * max(rival, 0.0):
        return None
    # Last, the mark and the skin right around it: skin stretches between visits, so a rigid fit cannot
    # be exact across the whole window, and the mark is where it must be.
    at = to_frame @ np.array([*(mark or centre), 1.0])
    focus = np.zeros((n, n), np.uint8)
    cv2.circle(focus, (round(at[0]), round(at[1])), round(float(p["focus"]) * n / 2), 1, -1)
    near = _polish(ta, sa & focus.astype(bool), tb, sb, r, (2, 1))
    if near is not None and _same(near, r, n, 8.0, 0.08):
        r = near
    moved = r @ np.array([n / 2, n / 2, 1.0])
    if math.hypot(moved[0] - n / 2, moved[1] - n / 2) > float(p["max_skin_shift"]) * n / 2:
        return None
    out = np.linalg.inv(to_frame) @ r @ to_frame @ start
    return {
        "matrix": (out / out[2, 2]).tolist(),
        "skin_score": round(score, 3),
        "skin_rival": round(rival, 3),
        "turn_deg": round(math.degrees(math.atan2(r[1, 0], r[0, 0])), 2),
    }


def _region(
    card_a: Card | None,
    card_b: Card | None,
    anchor_a: tuple[float, float] | None,
    start: np.ndarray,
    shape: tuple[int, ...],
    p: dict[str, Any],
) -> tuple[tuple[float, float], float] | None:
    """The disc of photo A to refine on: the card's window, else around the mark."""
    inset = float(p["window_inset"])
    if card_a and card_a.get("card") == "window":
        cx, cy = card_a["centre_px"]
        return (float(cx), float(cy)), APERTURE_RADIUS * inset / float(card_a["mm_per_px"])
    if card_b and card_b.get("card") == "window":
        # Photo B's window, carried into A by the rough map.
        cx, cy = card_b["centre_px"]
        centre = cv2.perspectiveTransform(np.array([[[cx, cy]]], np.float64), start).reshape(2)
        zoom = math.sqrt(abs(float(np.linalg.det(start[:2, :2] / start[2, 2]))))
        return (float(centre[0]), float(centre[1])), APERTURE_RADIUS * inset / float(card_b["mm_per_px"]) * zoom
    if anchor_a is None:
        return None
    if card_a:
        return anchor_a, float(p["mark_region_mm"]) / float(card_a["mm_per_px"])
    return anchor_a, float(p["region_fraction"]) * min(shape[:2])


def align_photos(
    image_a: Img,
    image_b: Img,
    card_a: Card | None,
    card_b: Card | None,
    anchor_a: tuple[float, float] | None = None,
    anchor_b: tuple[float, float] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Photo B onto photo A. The cards give the scale and the perspective when both photos have one, feature
    matches on the skin otherwise; either way the skin around the mark then gives the exact turn and shift."""
    p = {**PARAMS, **(params or {})}
    if card_a and card_b:
        start = from_cards(card_a["homography"], card_b["homography"])
        if anchor_a is not None and anchor_b is not None:
            start = anchored(start["matrix"], anchor_a, anchor_b)
    else:
        inset = float(p["window_inset"])
        mask_a, mask_b = skin_mask(image_a, card_a, inset), skin_mask(image_b, card_b, inset)
        start = from_features(image_a, image_b, p, mask_a, mask_b)
        if start["status"] != "aligned":
            # Closer, and without the hairs: a close-up against the small window of a photo with the card.
            detail = {**p, "long_edge": int(p["detail_long_edge"])}
            hairless_a, hairless_b = _without_hairs(image_a, mask_a, detail), _without_hairs(image_b, mask_b, detail)
            start = from_features(image_a, image_b, detail, hairless_a, hairless_b)
            if start["status"] != "aligned":
                return start
    rough = np.asarray(start["matrix"], np.float64)
    region = _region(card_a, card_b, anchor_a, rough, image_a.shape, p)
    refined = refine(image_a, image_b, start["matrix"], *region, card_a, card_b, p, anchor_a) if region else None
    if refined is None:
        return {**start, "refined": False}
    method = "card+skin" if card_a and card_b else start["method"]
    return {**start, **refined, "method": method, "refined": True}


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
