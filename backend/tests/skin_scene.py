# SPDX-License-Identifier: AGPL-3.0-only
"""Two visits to one mark, photographed with a known geometry: the ground truth for alignment tests.

A patch of skin is drawn once on a plane, in millimetres: tone that drifts, grain, a mesh of fine
lines, pores, a few freckles and one irregular mark. Each visit lays the reference card on it with
its own rotation and offset (the window around the mark, never quite the same way), grows its own
hairs, and photographs the plane with its own camera: distance, tilt, roll, framing and light.
Every step is a known transform, so the true map from one photo to the other is known exactly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from nevus.cv.card import APERTURE_RADIUS, WINDOW, draw_card
from nevus.cv.card_raster import RasterPainter, blank

SIZE_MM = 120.0
"""Side of the skin patch; the card fits on it at any rotation."""

Shot = dict[str, object]


@dataclass(frozen=True)
class Skin:
    seed: int = 1
    k: float = 24.0
    """Pixels per millimetre of the drawn plane."""
    tone: tuple[int, int, int] = (150, 175, 215)
    mark_mm: float = 2.2
    """Mean radius of the mark."""
    freckles: int = 18
    lines: float = 1.0
    """How strong the mesh of fine lines is; 0 for a smooth skin."""
    pores: float = 1.0
    """How many pores, relative to the usual."""


@dataclass(frozen=True)
class Visit:
    card: bool = True
    card_angle: float = 0.0
    """Rotation of the card on the skin, in degrees."""
    card_offset: tuple[float, float] = (0.0, 0.0)
    """Where the window's centre sits relative to the mark, in millimetres of skin."""
    distance_mm: float = 120.0
    focal_px: float = 3000.0
    tilt: tuple[float, float] = (0.0, 0.0)
    """Camera tilt about the x and y axes, in degrees."""
    roll: float = 0.0
    """Camera rotation about its axis, in degrees."""
    aim_mm: tuple[float, float] = (0.0, 0.0)
    """Where the camera looks, relative to the mark."""
    size: tuple[int, int] = (3200, 2400)
    hair_seed: int | None = 0
    hairs: int = 90
    growth: float = 1.0
    """The mark's radius relative to the first visit."""
    gain: float = 1.0
    white: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """Per-channel gains (B, G, R): the white balance."""
    gamma: float = 1.0
    blur: float = 0.0
    noise: float = 2.0
    jpeg: int = 90
    flip: bool = False
    """A photo of something else: the skin mirrored, so nothing truly lines up."""


def _noise(rng: np.random.Generator, shape: tuple[int, int], sigma_px: float) -> np.ndarray:
    """Smooth noise of unit spread; drawn small and enlarged when it is smooth anyway (it is quicker)."""
    shrink = max(1, int(sigma_px // 4))
    small = (max(4, shape[0] // shrink), max(4, shape[1] // shrink))
    raw = cv2.GaussianBlur(rng.normal(0, 1, small).astype(np.float32), (0, 0), sigma_px / shrink)
    out = cv2.resize(raw, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC) if shrink > 1 else raw
    spread = float(out.std()) + 1e-6
    result: np.ndarray = out / spread
    return result


def skin_plane(skin: Skin, growth: float = 1.0) -> np.ndarray:
    """The patch with its mark (BGR, float32); hairs come per visit. The mark is at the centre."""
    rng = np.random.default_rng(skin.seed)
    n = round(SIZE_MM * skin.k)
    k = skin.k
    base = np.array(skin.tone, np.float32)
    img = np.empty((n, n, 3), np.float32)
    img[:] = base
    shade = 1 + 0.05 * _noise(rng, (n, n), 6 * k) + 0.02 * _noise(rng, (n, n), 1.2 * k)
    img *= shade[..., None]
    img += 4.0 * rng.normal(0, 1, (n, n, 1)).astype(np.float32)
    if skin.lines > 0:
        lines = np.zeros((n, n), np.float32)
        for family in (25.0, 115.0):
            for _ in range(int(SIZE_MM * SIZE_MM / 2.5)):
                cx, cy = rng.uniform(0, n, 2)
                angle = math.radians(family + rng.normal(0, 12))
                length = rng.uniform(0.6, 2.2) * k
                dx, dy = math.cos(angle) * length / 2, math.sin(angle) * length / 2
                cv2.line(lines, (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy)), 1.0, 1, cv2.LINE_AA)
        img *= (1 - 0.07 * skin.lines * cv2.GaussianBlur(lines, (0, 0), 0.6))[..., None]
    pore = tuple(float(c) for c in base * 0.84)
    for _ in range(int(SIZE_MM * SIZE_MM * 2.5 * skin.pores)):
        cx, cy = rng.uniform(0, n, 2)
        cv2.circle(img, (int(cx), int(cy)), max(1, round(rng.uniform(0.04, 0.09) * k)), pore, -1)
    centre = n / 2
    for _ in range(skin.freckles):
        while True:
            fx, fy = rng.uniform(0.1 * n, 0.9 * n, 2)
            if math.hypot(fx - centre, fy - centre) > (skin.mark_mm * 1.6 + 1.5) * k:
                break
        size = rng.uniform(0.25, 0.8) * k
        half = int(2 * size) + 2
        x0, y0 = int(fx) - half, int(fy) - half
        drawn = np.zeros((2 * half, 2 * half), np.float32)
        axes = (int(size), int(size * rng.uniform(0.6, 1)))
        cv2.ellipse(drawn, (half, half), axes, rng.uniform(0, 180), 0, 360, 1.0, -1)
        spot = cv2.GaussianBlur(drawn, (0, 0), size / 3)
        img[y0 : y0 + 2 * half, x0 : x0 + 2 * half] *= (1 - rng.uniform(0.12, 0.25) * spot)[..., None]
    # The mark: a lobed outline, darker towards its middle, mottled.
    harmonics = [(order, rng.uniform(0.04, 0.16), rng.uniform(0, 2 * math.pi)) for order in (2, 3, 4, 5)]
    stretch = rng.uniform(1.0, 1.35)
    turn = rng.uniform(0, math.pi)
    angles = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    radius = skin.mark_mm * growth * k * (1 + sum(a * np.cos(o * angles + p) for o, a, p in harmonics))
    xs, ys = radius * np.cos(angles) * stretch, radius * np.sin(angles) / stretch
    rx = xs * math.cos(turn) - ys * math.sin(turn) + centre
    ry = xs * math.sin(turn) + ys * math.cos(turn) + centre
    mark = np.zeros((n, n), np.uint8)
    cv2.fillPoly(mark, [np.column_stack([rx, ry]).round().astype(np.int32)], 255, cv2.LINE_AA)
    soft = cv2.GaussianBlur(mark.astype(np.float32) / 255, (0, 0), 0.12 * k)
    inner = cv2.erode(mark, np.ones((3, 3), np.uint8), iterations=max(1, int(0.6 * k)))
    core = cv2.GaussianBlur(inner.astype(np.float32) / 255, (0, 0), 0.5 * k)
    mottle = 0.08 * _noise(np.random.default_rng(skin.seed + 100), (n, n), 0.2 * k)
    brown = np.array((60, 80, 120), np.float32)
    depth = np.clip(0.55 * soft + 0.3 * core + mottle * soft, 0, 1)[..., None]
    out: np.ndarray = img * (1 - depth) + brown * depth * 0.9
    return out


def _hairs(visit: Visit, k: float, n: int) -> np.ndarray:
    """A darkness map of this visit's hairs: long thin curves, roughly along one direction."""
    out = np.zeros((n, n), np.float32)
    if visit.hair_seed is None or visit.hairs == 0:
        return out
    rng = np.random.default_rng(visit.hair_seed + 7)
    for _ in range(visit.hairs):
        x, y = rng.uniform(0.2 * n, 0.8 * n, 2)
        angle = math.radians(40 + rng.normal(0, 15))
        bend = rng.normal(0, 0.03)
        points = []
        for _ in range(int(rng.uniform(8, 25) / 0.5)):
            points.append((x, y))
            x += math.cos(angle) * 0.5 * k
            y += math.sin(angle) * 0.5 * k
            angle += bend
        width = max(1, round(0.07 * k))
        cv2.polylines(out, [np.array(points, np.int32)], False, float(rng.uniform(0.6, 0.9)), width, cv2.LINE_AA)
    return out


def _card(k: float) -> tuple[np.ndarray, np.ndarray]:
    """The window card drawn at k pixels per millimetre, and where it is opaque (not the aperture)."""
    raster = blank(WINDOW.width, WINDOW.height, k)
    draw_card(RasterPainter(raster, k), WINDOW, 0.0, 0.0, cut_aperture=True)
    opaque = np.full(raster.shape[:2], 255, np.uint8)
    cx, cy = WINDOW.centre
    cv2.circle(opaque, (round(cx * k), round(cy * k)), round(APERTURE_RADIUS * k), 0, -1, cv2.LINE_AA)
    return raster, opaque


def card_on_skin(visit: Visit) -> np.ndarray:
    """Card millimetres -> skin millimetres, with the mark at the origin of the skin's frame."""
    a = math.radians(visit.card_angle)
    rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    cx, cy = WINDOW.centre
    shift = np.array(visit.card_offset) - rot @ np.array([cx, cy])
    return np.array([[rot[0, 0], rot[0, 1], shift[0]], [rot[1, 0], rot[1, 1], shift[1]], [0, 0, 1]])


def camera(visit: Visit) -> np.ndarray:
    """Skin millimetres (mark at the origin) -> photo pixels: a pinhole looking at the aim point."""
    tx, ty = (math.radians(v) for v in visit.tilt)
    rx = np.array([[1, 0, 0], [0, math.cos(tx), -math.sin(tx)], [0, math.sin(tx), math.cos(tx)]])
    ry = np.array([[math.cos(ty), 0, math.sin(ty)], [0, 1, 0], [-math.sin(ty), 0, math.cos(ty)]])
    r = math.radians(visit.roll)
    rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    rotation = rz @ rx @ ry
    aim = np.array([visit.aim_mm[0], visit.aim_mm[1], 0.0])
    t = -rotation @ aim + np.array([0, 0, visit.distance_mm])
    w, h = visit.size
    intrinsics = np.array([[visit.focal_px, 0, w / 2], [0, visit.focal_px, h / 2], [0, 0, 1]])
    m = intrinsics @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
    out: np.ndarray = m / m[2, 2]
    return out


def photograph(skin: Skin, visit: Visit, plane: np.ndarray | None = None) -> Shot:
    """One visit's photo and its truth: skin millimetres -> photo pixels, and the mark's centre in the photo."""
    k = skin.k
    world = plane if plane is not None else skin_plane(skin, visit.growth)
    n = world.shape[0]
    world = world * (1 - 0.75 * _hairs(visit, k, n)[..., None])
    to_raster = np.array([[k, 0, n / 2], [0, k, n / 2], [0, 0, 1]])  # skin mm -> plane pixels
    if visit.card:
        raster, opaque = _card(k)
        to_plane = to_raster @ card_on_skin(visit) @ np.diag([1 / k, 1 / k, 1.0])
        drawn = cv2.warpPerspective(raster, to_plane, (n, n), flags=cv2.INTER_LINEAR).astype(np.float32)
        alpha = cv2.warpPerspective(opaque, to_plane, (n, n), flags=cv2.INTER_LINEAR).astype(np.float32) / 255
        world = world * (1 - alpha[..., None]) + drawn * alpha[..., None]
    if visit.flip:
        world = world[:, ::-1].copy()
    truth = camera(visit)
    w, h = visit.size
    to_photo = truth @ np.linalg.inv(to_raster)
    photo = cv2.warpPerspective(world, to_photo, (w, h), flags=cv2.INTER_LINEAR, borderValue=(120, 140, 170))
    photo = photo * visit.gain * np.array(visit.white, np.float32)
    photo = 255 * (np.clip(photo, 0, 255) / 255) ** visit.gamma
    if visit.blur > 0:
        photo = cv2.GaussianBlur(photo, (0, 0), visit.blur)
    photo += np.random.default_rng(skin.seed * 31 + 5).normal(0, visit.noise, photo.shape).astype(np.float32)
    ok, buffer = cv2.imencode(".jpg", np.clip(photo, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, visit.jpeg])
    assert ok
    centre = cv2.perspectiveTransform(np.array([[[0.0, 0.0]]]), truth).reshape(2)
    return {
        "photo": cv2.imdecode(buffer, cv2.IMREAD_COLOR),
        "truth": truth,
        "mark_px": (float(centre[0]), float(centre[1])),
    }


def truth_b_to_a(a: Shot, b: Shot) -> np.ndarray:
    m = np.asarray(a["truth"]) @ np.linalg.inv(np.asarray(b["truth"]))
    out: np.ndarray = m / m[2, 2]
    return out


def error_mm(matrix: list[list[float]] | np.ndarray, a: Shot, b: Shot, radius_mm: float = 9.0) -> tuple[float, float]:
    """How far an estimated B -> A map puts B's skin from where it truly lies in A, around the mark (mean, max)."""
    angles = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    rings = (radius_mm / 3, 2 * radius_mm / 3, radius_mm)
    skin_pts = [(0.0, 0.0)] + [(r * math.cos(t), r * math.sin(t)) for r in rings for t in angles]
    pts = np.array(skin_pts, np.float64).reshape(-1, 1, 2)
    in_b = cv2.perspectiveTransform(pts, np.asarray(b["truth"]))
    in_a = cv2.perspectiveTransform(pts, np.asarray(a["truth"]))
    guess = cv2.perspectiveTransform(in_b, np.asarray(matrix, np.float64))
    one = cv2.perspectiveTransform(np.array([[[0.0, 0.0]], [[1.0, 0.0]]]), np.asarray(a["truth"])).reshape(2, 2)
    mm_per_px = 1 / float(np.linalg.norm(one[1] - one[0]))
    dist = np.linalg.norm((guess - in_a).reshape(-1, 2), axis=1) * mm_per_px
    return float(dist.mean()), float(dist.max())
