# /// script
# requires-python = ">=3.13"
# dependencies = ["shapely>=2.1", "cairosvg>=2.7"]
# ///
# SPDX-License-Identifier: AGPL-3.0-only
"""Build the neVus body map: silhouettes, zone regions and the shared zones.json.

The silhouette is neVus artwork: a flat, gender-neutral pictogram built from a
skeleton of tapered capsules that is unioned and rounded. The zone regions are
MoleMapper's hit polygons (see molemapper_zones.py) clipped to that silhouette;
any part of the silhouette no polygon covers is given to the neighbouring zone
with the longest shared edge, so the zones tile the figure exactly.

Usage: uv run tools/bodymap/build.py [--preview DIR]
Writes backend/src/nevus/bodymap/zones.json and frontend/src/features/bodymap/zones.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from itertools import pairwise
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from molemapper_zones import GRID, PLACEMENTS, absolute_polygon, region_of, side_of

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = [
    ROOT / "backend" / "src" / "nevus" / "bodymap" / "zones.json",
    ROOT / "frontend" / "src" / "features" / "bodymap" / "zones.json",
]
VERSION = "nevus-body-map/4"  # 2 the head view, 3 hands and feet, 4 hands and feet as one's own, head from below
W, H = GRID
MID = W / 2

# Order matters: trunk before limbs so that overlapping hit polygons favour the trunk.
ORDER = ["head", "trunk", "leg", "arm"]


def capsule(a: tuple[float, float], ra: float, b: tuple[float, float], rb: float) -> Polygon:
    """Tapered capsule: convex hull of two discs."""
    return unary_union([Point(a).buffer(ra, 32), Point(b).buffer(rb, 32)]).convex_hull


def chain(points: list[tuple[tuple[float, float], float]]) -> Polygon:
    parts = [capsule(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]) for i in range(len(points) - 1)]
    return unary_union(parts)


def ellipse(cx: float, cy: float, rx: float, ry: float) -> Polygon:
    return affinity.scale(Point(cx, cy).buffer(1, 64), rx, ry)


def mirror(geom: Polygon) -> Polygon:
    return affinity.scale(geom, xfact=-1, yfact=1, origin=(MID, 0))


# The arm's skeleton, for the arm on the left of the screen: shoulder joint, elbow and wrist, each with its radius.
# The arms hang from the ends of the shoulders, so the armpit's curve rises to just under the shoulder.
ARM = (((MID - 48.0, 88.0), 10.0), ((MID - 68.0, 150.0), 8.5), ((MID - 84.0, 198.0), 6.5))
FILLET = 4.5  # radius of the closing that rounds the joins, the armpit's curve among them
CORNER = 1.5  # radius of the round every corner left on an outline gets at the end
SMOOTH = 2.0  # reach of the smoothing the body's outlines get, so no bend shows as a vertex
GROIN = 226.0  # height of the groin, where the trunk ends between the legs; the buttocks reach down to it
CLEFT = (186.0, 216.0)  # the buttocks' cleft, from its top to its end, where the crotch's round begins
NAVEL = 179.0  # height of the navel, where the abdomen gives way to the pelvis (and, behind, the buttocks)
# The leg's skeleton, for the leg on the left of the screen: hip, knee, calf and ankle, each with its radius.
LEG = (
    ((MID - 23.0, 212.0), 19.5),
    ((MID - 23.0, 278.0), 13.0),
    ((MID - 24.0, 312.0), 12.5),
    ((MID - 23.0, 348.0), 7.5),
)


def arm_shape(side: int) -> Polygon:
    """An arm without its hand, as the silhouette draws it; `side` -1 for the arm on the left of the screen."""
    arm = chain(list(ARM))
    return arm if side == -1 else mirror(arm)


def figure() -> Polygon:
    """The figure both views start from, before the crotch is shaped: a skeleton of capsules, unioned and rounded."""
    head = ellipse(MID, 28.0, 20.0, 23.5)
    neck = Polygon([(MID - 10.0, 44), (MID + 10.0, 44), (MID + 10.0, 66), (MID - 10.0, 66)])
    # Right half of the trunk (screen left), mirrored below. Shoulder line, side, hip, crotch.
    trunk_right = [
        (MID, 62.0),
        (MID - 24.0, 63.5),
        (MID - 41.0, 68.5),
        (MID - 51.5, 77.0),
        (MID - 50.0, 92.0),
        (MID - 35.0, 104.0),
        (MID - 35.0, 122.0),
        (MID - 32.0, 148.0),
        (MID - 34.0, 168.0),
        (MID - 40.0, 190.0),
        (MID - 41.5, 208.0),
        (MID - 35.0, 224.0),
        (MID - 12.0, 228.0),
        (MID, GROIN),
    ]
    trunk = Polygon(trunk_right + [(W - x, y) for x, y in reversed(trunk_right[1:-1])])
    arm = arm_shape(-1)
    hand = capsule((MID - 85.0, 199.0), 6.0, (MID - 87.4, 206.5), 6.6)  # sketched only: kept small
    leg = chain(list(LEG))
    foot = capsule((MID - 23.0, 350.0), 8.0, (MID - 27.0, 389.0), 11.0)
    right_side = unary_union([arm, hand, leg, foot])
    body = unary_union([head, neck, trunk, right_side, mirror(right_side)])
    smooth = body.buffer(FILLET, 32).buffer(-FILLET, 32)  # closing: rounds the armpits, crotch and neck joins
    smooth = smooth.simplify(0.12, preserve_topology=True)
    assert isinstance(smooth, Polygon), type(smooth)
    return smooth


def crotch_round(shape: Polygon) -> Point:
    """The centre of the round the closing gives the crotch, where the legs part under the trunk."""
    return highest_round(shape, box(MID - 12, 200, MID + 12, 250))


def silhouette() -> Polygon:
    """The front's silhouette. The crotch's round rises to the height where the buttocks' cleft ends: from the round
    the closing gives it, the gap between the legs goes straight up to a round of the same radius."""
    shape = figure()
    crotch = crotch_round(shape)
    across = LineString([(MID - 12, crotch.y), (MID + 12, crotch.y)]).difference(shape)
    top = Point(MID, CLEFT[1] + FILLET - 0.1).buffer(FILLET - 0.1, 32)
    return smoothed(shape.difference(unary_union([across, top]).convex_hull))


def smoothed(shape: Polygon) -> Polygon:
    """An outline with no vertex anywhere: walked at an even step, each point is averaged with its neighbours along
    the way, weighted by a bell SMOOTH wide, so every bend becomes a curve."""
    ring = shape.exterior
    count = int(ring.length / 0.4)
    step = ring.length / count
    points = [ring.interpolate(index * step) for index in range(count)]
    reach = int(3 * SMOOTH / step)
    weights = [(offset, math.exp(-((offset * step) ** 2) / (2 * SMOOTH**2))) for offset in range(-reach, reach + 1)]
    total = sum(weight for _offset, weight in weights)
    averaged = [
        (
            sum(weight * points[(index + offset) % count].x for offset, weight in weights) / total,
            sum(weight * points[(index + offset) % count].y for offset, weight in weights) / total,
        )
        for index in range(count)
    ]
    smooth = Polygon(averaged).buffer(0).simplify(0.03, preserve_topology=True)
    assert isinstance(smooth, Polygon), type(smooth)
    return smooth


def rounded(shape: BaseGeometry, keep: BaseGeometry | None = None) -> Polygon:
    """An outline with every corner rounded, inward and outward, so it shows no vertex; what `keep` takes in is cut
    out again as it was, where a point or a narrow gap is the drawing."""
    smooth = shape.buffer(CORNER, 32).buffer(-CORNER, 32).buffer(-CORNER, 32).buffer(CORNER, 32)
    if keep is not None:
        smooth = smooth.difference(keep)
    smooth = smooth.simplify(0.05, preserve_topology=True)
    assert isinstance(smooth, Polygon), type(smooth)
    return smooth


def to_path(geom: Polygon | MultiPolygon, precision: int = 1) -> str:
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    parts: list[str] = []
    for poly in polys:
        if poly.interiors:
            poly = orient(poly)  # holes wound against the outline, so the default fill rule leaves them empty
        rings = [poly.exterior, *poly.interiors]
        for ring in rings:
            coords = despiked([(round(x, precision), round(y, precision)) for x, y in list(ring.coords)[:-1]])
            parts.append("M" + " ".join(f"{x:.{precision}f},{y:.{precision}f}" for x, y in coords) + "Z")
    return "".join(parts)


def despiked(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """A ring without the needles a cut leaves where two edges nearly coincide: a point where the ring turns back
    on itself (by more than 175°) is dropped, as is a point repeated."""
    points = list(coords)
    changed = True
    while changed and len(points) > 3:
        changed = False
        for i in range(len(points)):
            a, b, c = points[i - 1], points[i], points[(i + 1) % len(points)]
            if b in (a, c):
                del points[i]
                changed = True
                break
            back = abs(
                (math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])) + 180) % 360
                - 180
            )
            if back > 175:
                del points[i]
                changed = True
                break
    return points


# Zones the neVus map renames or adds to MoleMapper's: the limbs cut into bands a person can name (a knee, an
# ankle, a wrist), the armpits, and the parts of a person's anatomy, which only show when the profile sets them.
RENAMED = {
    "2250": "Left Dorsal Region",
    "2251": "Right Dorsal Region",
    "2300": "Left Lumbar Region",
    "2301": "Right Lumbar Region",
    "2600": "Left Heel",
    "2601": "Right Heel",
    "1400": "Right Thigh",
    "1401": "Left Thigh",
    "1450": "Right Knee",
    "1451": "Left Knee",
    "1500": "Right Shin",
    "1501": "Left Shin",
    "1550": "Right Ankle",
    "1551": "Left Ankle",
    "1750": "Right Forearm",
    "1751": "Left Forearm",
    "1800": "Right Wrist",
    "1801": "Left Wrist",
    "2400": "Left Thigh",
    "2401": "Right Thigh",
    "2450": "Left Back of Knee",
    "2451": "Right Back of Knee",
    "2500": "Left Calf",
    "2501": "Right Calf",
    "2550": "Left Ankle",
    "2551": "Right Ankle",
    "2800": "Left Wrist",
    "2801": "Right Wrist",
}
# Leg bands from the hip down: thigh, knee (back of the knee behind), shin (calf behind), ankle.
LEG_CUTS = (273.0, 300.0, 338.0)
LEGS = {
    "front": (("1400", "1450", "1500", "1550"), ("1401", "1451", "1501", "1551")),
    "back": (("2400", "2450", "2500", "2550"), ("2401", "2451", "2501", "2551")),
}
# The arm's bands, cut square to one axis from the shoulder joint to the wrist, so every dividing line runs
# parallel: where each band starts, as a height on that axis, in order down the arm.
ARM_BANDS = {
    "front": (("170", 84.0), ("175", 135.8), ("180", 176.0)),
    "back": (("270", 92.0), ("275", 128.0), ("278", 148.0), ("280", 178.0)),
}


def across_arm(y: float, side: int, after: bool) -> Polygon:
    """The half of the plane past (or before) the point of the arm's axis at height `y`, cut square to the axis
    from the shoulder joint to the wrist; `side` -1 for the arm on the left of the screen, 1 for the right."""
    (ax, ay), (bx, by) = ((MID + side * (MID - x), y) for (x, y), _radius in (ARM[0], ARM[-1]))
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    t = (y - ay) / (by - ay)
    px, py = ax + t * (bx - ax), ay + t * (by - ay)
    nx, ny = -uy * 500, ux * 500
    reach = 500 if after else -500
    return Polygon(
        [
            (px + nx, py + ny),
            (px - nx, py - ny),
            (px - nx + ux * reach, py - ny + uy * reach),
            (px + nx + ux * reach, py + ny + uy * reach),
        ]
    )


def highest_round(body: Polygon, near: Polygon) -> Point:
    """The centre of the round the closing in figure() gives a joint, in the gap that `near` takes in: the
    highest point a disc of the closing's radius reaches there."""
    centres = near.difference(body).buffer(-(FILLET - 0.1))
    polygons = centres.geoms if isinstance(centres, MultiPolygon) else [centres]
    return Point(min((point for polygon in polygons for point in polygon.exterior.coords), key=lambda p: p[1]))


def armpit_curve(body: Polygon, side: int) -> Point:
    """The centre of the armpit's curve, the round of the joint of arm and trunk."""
    near = Polygon([(MID + side * 28, 80), (MID + side * 50, 80), (MID + side * 50, 150), (MID + side * 28, 150)])
    return highest_round(body, near)


def armpit(body: Polygon, side: int) -> Polygon:
    """The front's armpit: an oval whose lower end sits on the top of the armpit's curve, so the curve runs up into
    it, and whose top reaches the line between the arm and the shoulder."""
    curve = armpit_curve(body, side)
    top, bottom = armpit_top(side, "front").y, curve.y - FILLET + 2
    return ellipse(curve.x, (top + bottom) / 2, 7.5, (bottom - top) / 2)


def back_silhouette() -> Polygon:
    """The silhouette seen from behind. The feet point away, so under each ankle only the heel shows. There is no
    armpit to unroll, so the gap between each arm and the trunk runs on up to where the arm leaves the shoulder, along
    the arm's edge so the arm keeps its width. And the buttocks' rounds meet where the cleft ends, the gap between the
    legs opening under them. The gaps are cut once the outline is smooth, so their tips stay where they belong."""
    body = figure()
    (calf, calf_r), (ankle, ankle_r) = LEG[-2], LEG[-1]
    shin_and_heel = capsule(calf, calf_r, ankle, ankle_r).union(capsule(ankle, ankle_r, (ankle[0], ankle[1] + 14), 8.5))
    lower = unary_union([shin_and_heel, mirror(shin_and_heel)])
    cut = box(0, 330, W, H)
    body = smoothed(mend(unary_union([body.difference(cut), lower.intersection(cut)]), box(0, 0, W, H)))
    gaps = []
    for side in (-1, 1):
        curve = armpit_curve(body, side)
        arm = arm_shape(side)
        # The arm's inner edge, just under the line where the back's shoulder ends.
        top = armpit_top(side, "back").y + 1.6
        row = arm.intersection(LineString([(0, top), (W, top)])).bounds
        edge = row[2] if side == -1 else row[0]
        tip = Point(edge - side * 1.6, top).buffer(1.6, 32)  # tangent to the arm's edge
        gaps.append(unary_union([curve.buffer(FILLET - 0.1, 32), tip]).convex_hull.difference(arm))
    # Each buttock is a round lobe: an ellipse whose lowest point sits on the inner edge of its thigh at the groin,
    # where the fold is, and whose side passes through the cleft's end a little apart from the other lobe's, so the
    # notch between them shows from there.
    leg = chain(list(LEG))
    half = MID - leg.intersection(LineString([(0, GROIN), (MID, GROIN)])).bounds[2]
    tall = GROIN - CLEFT[1] + 3.0
    wide = half / math.sqrt(1 - (3.0 / tall) ** 2)
    rounds = unary_union([ellipse(MID + side * half, GROIN - tall, wide, tall) for side in (-1, 1)])
    under = box(MID - 12, CLEFT[1], MID + 12, crotch_round(body).y)
    notch = under.difference(rounds).difference(unary_union([leg, mirror(leg)]))
    # The notch keeps its point at the cleft's end; its foot, at the fold, is rounded like everything else.
    return rounded(body.difference(unary_union([*gaps, notch])), keep=notch.intersection(box(0, 0, W, GROIN - 2)))


def shoulder_cap(side: int, view: str, trunk: str) -> Polygon:
    """The side of the shoulder's line the shoulder lies on. The line runs along the one between the shoulder and
    the arm, as far as the arm's inner edge, then rises to the top corner of MoleMapper's chest (or upper back) zone
    and on along that zone's top edge; it is rounded where it turns, so the shoulder makes no corner."""
    inner = armpit_top(side, view)
    (ax, ay), (bx, by) = ((MID + side * (MID - x), y) for (x, y), _radius in (ARM[0], ARM[-1]))
    length = math.hypot(bx - ax, by - ay)
    outward = (-(by - ay) / length, (bx - ax) / length)
    if outward[0] * side < 0:
        outward = (-outward[0], -outward[1])
    outer = (inner.x + outward[0] * 40, inner.y + outward[1] * 40)
    polygon = absolute_polygon(trunk)
    corner = min((point for point in polygon if abs(point[0] - MID) > 20), key=lambda point: point[1])
    # The top edge's other end: the highest point nearer the middle, the farthest from it on a tie.
    nearer = (point for point in polygon if abs(point[0] - MID) < abs(corner[0] - MID))
    along = min(nearer, key=lambda point: (point[1], -abs(point[0] - MID)))
    rise = (along[1] - corner[1]) / (along[0] - corner[0])
    middle = (MID, corner[1] + rise * (MID - corner[0]))
    line = chaikin([outer, (inner.x, inner.y), corner, middle], 5)
    return Polygon([(outer[0], -10), *line, (MID, -10)])


def chaikin(points: list[tuple[float, float]], times: int) -> list[tuple[float, float]]:
    """A polyline with its corners cut `times` over, a quarter of each segment at a time: a smooth curve through
    its ends."""
    for _ in range(times):
        cut = [points[0]]
        for (x0, y0), (x1, y1) in pairwise(points):
            cut += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        points = [*cut[:1], *cut[2:-1], points[-1]]
    return points


def armpit_top(side: int, view: str) -> Point:
    """The point where the line between the shoulder and the arm meets the arm's inner edge, in a view."""
    shoulder_line = across_arm(ARM_BANDS[view][0][1], side, after=True).exterior
    edge = arm_shape(side).exterior
    crossings = shoulder_line.intersection(edge)
    points = crossings.geoms if hasattr(crossings, "geoms") else [crossings]
    # Of the two points where the line crosses the arm, the one nearer the trunk.
    return max(points, key=lambda point: -side * point.x)


def mend(geom: BaseGeometry, body: Polygon, beside: BaseGeometry | None = None) -> BaseGeometry:
    """A union with the hairline cracks closed that it leaves where MoleMapper's edges almost meet, kept off the
    zones `beside` it."""
    mended = geom.buffer(0.01, join_style=2).buffer(-0.01, join_style=2).intersection(body)
    return polygonal(mended if beside is None else mended.difference(beside))


def beside(regions: dict[str, BaseGeometry], *codes: str) -> BaseGeometry:
    """All the zones but these."""
    return unary_union([region for code, region in regions.items() if code not in codes])


def polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Only the area of a geometry: the stray lines and points an overlay can leave beside it are dropped."""
    return geom.buffer(0) if geom.geom_type == "GeometryCollection" else geom


def reshape(regions: dict[str, Polygon | MultiPolygon], view: str, body: Polygon) -> list[tuple[str, str]]:
    """Cut the limbs into named bands and carve the armpits, in place; returns the zones it adds, code and name."""
    added: list[tuple[str, str]] = []
    # The abdomen (the lower back, behind) reaches down to the navel's height, where the pelvis or the buttocks begin.
    prefix = "1" if view == "front" else "2"
    # The four are cut afresh from their union, so no sliver of one half survives along the old line.
    lower_trunk = {f"{prefix}30{n}": (n, 0.0, NAVEL) for n in "01"} | {f"{prefix}35{n}": (n, NAVEL, H) for n in "01"}
    others = beside(regions, *lower_trunk)
    whole = mend(unary_union([regions[code] for code in lower_trunk]), body, others)
    for code, (n, top, bottom) in lower_trunk.items():
        left, right = (0.0, MID) if n == "0" else (MID, W)
        regions[code] = whole.intersection(box(left, top, right, bottom))
    if view == "back":
        # The buttocks reach down to the groin's height, beside the crotch's notch, and each thigh starts there;
        # the two are cut apart again at the middle, where the thighs' polygons may cross it.
        above = box(0, 0, W, GROIN)
        thighs = [code for leg in LEGS[view] for code in leg]
        raised = unary_union([regions[code].intersection(above) for code in thighs])
        for code in thighs:
            regions[code] = regions[code].difference(above)
        both = unary_union([regions["2350"], regions["2351"], raised])
        whole = mend(both, body, beside(regions, "2350", "2351", *thighs))
        regions["2350"], regions["2351"] = whole.intersection(box(0, 0, MID, H)), whole.intersection(box(MID, 0, W, H))
    cuts = (0.0, *LEG_CUTS, float(H))
    for leg in LEGS[view]:
        whole = unary_union([regions[code] for code in leg])
        for code, top, bottom in zip(leg, cuts[:-1], cuts[1:], strict=True):
            regions[code] = whole.intersection(Polygon([(0, top), (W, top), (W, bottom), (0, bottom)]))
    for side in (-1, 1):
        n = "0" if side == -1 else "1"
        shoulder, trunk = f"{prefix}65{n}", f"{prefix}25{n}"
        bands = [(f"{code}{n}", y) for code, y in ARM_BANDS[view]]
        codes = [shoulder, *(code for code, _ in bands if code in regions)]
        whole = mend(unary_union([regions[code] for code in codes]), body, beside(regions, *codes))
        # The shoulder is the cap above one smooth line. The arm is what lies under it within the arm's own edge,
        # and anything on the arm's side below the armpit's curve, where arm and trunk part.
        curve = armpit_curve(body, side)
        parted = Polygon(
            [(curve.x, curve.y), (curve.x + side * 400, curve.y), (curve.x + side * 400, H + 10), (curve.x, H + 10)]
        )
        cap = shoulder_cap(side, view, trunk)
        arm = whole.difference(cap).intersection(unary_union([arm_shape(side).buffer(0.3), parted]))
        # The chest's (or the back's) top corner, where the line rounds it, goes to the shoulder above the line.
        corner = regions[trunk].intersection(cap)
        regions[trunk] = polygonal(regions[trunk].difference(cap))
        regions[shoulder] = mend(unary_union([whole.intersection(cap), corner]), body, beside(regions, *codes))
        rest = whole.difference(arm).difference(regions[shoulder])
        for index, (code, start) in enumerate(bands):
            # The first band starts at the shoulder's line; each of the others where the arm's axis reaches it.
            band = arm if index == 0 else arm.intersection(across_arm(start, side, True))
            if index + 1 < len(bands):  # every band but the last ends where the next starts
                band = band.intersection(across_arm(bands[index + 1][1], side, False))
            regions[code] = band
            if code not in codes:
                added.append((code, "Left Forearm" if side == -1 else "Right Forearm"))
        # What is left lies between the arm and the chest or the back, and joins it, the same on both sides; a bit
        # that does not touch it joins the neighbour it shares most edge with.
        for piece in getattr(rest, "geoms", [rest]):
            if not isinstance(piece, Polygon) or piece.area == 0:
                continue

            def shared(code: str, piece: Polygon = piece) -> float:
                return piece.boundary.intersection(regions[code].boundary.buffer(0.01)).length

            nearest = trunk if shared(trunk) > 0.5 else max((shoulder, bands[0][0]), key=shared)
            regions[nearest] = mend(unary_union([regions[nearest], piece]), body, beside(regions, nearest))
    if view == "front":
        # The armpits: the lower end of the long joint between the arm and the chest, under the shoulder.
        for side, code, name in ((-1, "1660", "Right Armpit"), (1, "1661", "Left Armpit")):
            pit = armpit(body, side).intersection(body)
            for other in regions:
                regions[other] = regions[other].difference(pit)
            regions[code] = pit
            added.append((code, name))
    # Crumbs the cuts leave apart from their zone join the neighbour they share most edge with.
    for code in list(regions):
        pieces = sorted(
            (piece for piece in getattr(regions[code], "geoms", []) if isinstance(piece, Polygon)),
            key=lambda piece: piece.area,
            reverse=True,
        )
        if len(pieces) < 2 or any(crumb.area >= 1 for crumb in pieces[1:]):
            continue
        regions[code] = pieces[0]
        for crumb in pieces[1:]:
            nearest = max(
                (other for other in regions if other != code),
                key=lambda other: crumb.boundary.intersection(regions[other].boundary.buffer(0.01)).length,
            )
            regions[nearest] = unary_union([regions[nearest], crumb])
    return added


def part_zones() -> list[tuple[str, str, str, Polygon]]:
    """The parts of a person's anatomy as zones of their own, laid over the zones under them and shown only when
    the person's profile sets the part: code, name, part, shape."""
    breasts = [
        ("1260", "Right Breast", "breasts", Point(MID - 18.5, 110).buffer(14, 64)),
        ("1261", "Left Breast", "breasts", Point(MID + 18.5, 110).buffer(14, 64)),
    ]
    penis = capsule((MID, 219.4), 3.4, (MID, 228), 3.1)
    testicles = unary_union([ellipse(MID - 4.6, 222, 5.2, 6), ellipse(MID + 4.6, 222, 5.2, 6)])
    return [*breasts, ("1370", "Penis", "penis", penis), ("1371", "Scrotum", "penis", testicles.difference(penis))]


def build_zones(body: Polygon, view: str) -> list[dict]:
    placements = [p for p in PLACEMENTS if p[1] == view]
    placements.sort(key=lambda p: ORDER.index(region_of(p[0])))
    taken: Polygon | MultiPolygon = Polygon()
    regions: dict[str, Polygon | MultiPolygon] = {}
    for code, _v, _ox, _oy, _name, _shape in placements:
        hit = Polygon(absolute_polygon(code)).buffer(0)
        region = polygonal(hit.intersection(body).difference(taken))
        regions[code] = region
        taken = unary_union([taken, region])
    # Give every uncovered sliver to the neighbour that shares the longest edge with it.
    leftover = body.difference(taken)
    pieces = (
        list(leftover.geoms) if isinstance(leftover, MultiPolygon) else ([leftover] if not leftover.is_empty else [])
    )
    for piece in pieces:
        best, best_len = None, -1.0
        for code, region in regions.items():
            shared = piece.boundary.intersection(region.boundary.buffer(0.01)).length
            if shared > best_len:
                best, best_len = code, shared
        assert best is not None
        regions[best] = unary_union([regions[best], piece])
    if view == "front":
        # The pubis, between the legs at the front (map 4): not one of MoleMapper's zones, so it is carved out of
        # the pelvis and the tops of the thighs around it. A small rounded triangle low between the groin's lines.
        triangle = Polygon([(91, 192), (125, 192), (116, 213), (108, 224), (100, 213)])
        pubis = triangle.intersection(box(0, 207.6, W, H)).buffer(2, join_style=1).intersection(body)
        regions = {code: region.difference(pubis) for code, region in regions.items()}
        regions["1360"] = pubis
        placements = [*placements, ("1360", view, 0.0, 0.0, "Pubic Area", 0)]
    added = reshape(regions, view, body)
    placements = [*placements, *((code, view, 0.0, 0.0, name, 0) for code, name in added)]
    result = []
    for code, _v, _ox, _oy, molemapper_name, shape in placements:
        name = RENAMED.get(code, molemapper_name)
        region = regions[code].buffer(0)
        # Rings a hair wide, left by rounding where zones meet, would draw as specks; holes as well.
        region = unary_union(
            [
                Polygon(piece.exterior, [hole for hole in piece.interiors if Polygon(hole).area >= 0.05])
                for piece in getattr(region, "geoms", [region])
                if piece.area >= 0.05
            ]
        )
        rp = region.representative_point()
        result.append(
            {
                "code": code,
                "view": view,
                "side": side_of(code, view, name),
                "region": region_of(code),
                "name": name,
                "molemapper_shape": shape,
                "path": to_path(region),
                "anchor": [round(rp.x, 1), round(rp.y, 1)],
                "bbox": [round(v, 1) for v in region.bounds],
            }
        )
    # Sanity: exact tiling, no overlaps.
    union = unary_union(list(regions.values()))
    assert abs(union.area - body.area) < 1e-6, (union.area, body.area)
    codes = list(regions)
    for i, a in enumerate(codes):
        for b in codes[i + 1 :]:
            overlap = regions[a].intersection(regions[b]).area
            assert overlap < 1e-6, (a, b, overlap)
    if view == "front":
        for code, name, part, shape in part_zones():
            rp = shape.representative_point()
            result.append(
                {
                    "code": code,
                    "view": view,
                    "side": side_of(code, view, name),
                    "region": region_of(code),
                    "name": name,
                    "molemapper_shape": 0,
                    "path": to_path(shape),
                    "anchor": [round(rp.x, 1), round(rp.y, 1)],
                    "bbox": [round(v, 1) for v in shape.bounds],
                    "part": part,
                }
            )
    result.sort(key=lambda z: z["code"])
    return result


def preview_svg(body: Polygon, zones: list[dict], view: str, details: str = "") -> str:
    palette = {"head": "#c9b7a3", "trunk": "#9fbfb9", "leg": "#b7c9a3", "arm": "#c9a3b7"}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {W:.0f} {H:.0f}" width="{W * 3:.0f}" height="{H * 3:.0f}">',
        f'<rect width="{W}" height="{H}" fill="#F6F1EA"/>',
    ]
    for z in zones:
        parts.append(f'<path d="{z["path"]}" fill="{palette[z["region"]]}" stroke="#F6F1EA" stroke-width="0.6"/>')
    parts.append(f'<path d="{to_path(body)}" fill="none" stroke="#2B2A28" stroke-width="0.8"/>')
    if details:
        parts.append(f'<path d="{details}" fill="none" stroke="#2B2A28" stroke-width="0.6" stroke-linecap="round"/>')
    for z in zones:
        x, y = z["anchor"]
        parts.append(
            f'<text x="{x}" y="{y}" font-size="4" text-anchor="middle" fill="#2B2A28" '
            f'font-family="sans-serif">{z["code"]}</text>'
        )
    parts.append(f'<text x="4" y="8" font-size="6" fill="#2B2A28" font-family="sans-serif">{view}</text></svg>')
    return "".join(parts)


HEAD_NAMES = {
    "3150": "Left Profile",
    "3151": "Right Profile",
    "3170": "Top of Head",
    "3171": "Face: Front",
    "3172": "Occipital",
    "3173": "Chin",
}


# The head view unfolds the head like a cube: a row of the back of the head, the left profile, the face and the
# right profile, with the top of the head above the face and the head seen from below under it. Four heads side by
# side fit the view's width at this scale.
HEAD_SCALE = 0.70
HEAD_GAP = 6.0


def head_figures() -> dict[str, tuple[Polygon, list[BaseGeometry]]]:
    """Each head pictogram with its landmarks, at full size around its own centre.

    The top of the head has a small point marking the forehead and the ears at its sides; the profiles keep
    MoleMapper's layout (the left side of the face on the left, nose pointing that way). The head seen from
    below has the nose at the front and a round hole where the neck is, not a place for a mark.
    """
    nose = Polygon([(-7, 0), (0, -9), (7, 0)]).buffer(3, join_style=1)
    crown = Point(0, 0).buffer(34, 64)
    top_ears = [ear_from_behind(crown, side * 34, -4, side) for side in (-1, 1)]
    nose_from_above = affinity.translate(affinity.rotate(nose, 180, origin=(0, 0)), 0, 33)
    top = unary_union([crown, nose_from_above, *(shape for shape, _base in top_ears)])
    top_marks: list[BaseGeometry] = [base for _shape, base in top_ears]

    face = unary_union([ellipse(0, 0, 33, 43), ellipse(-34, 2, 6, 11), ellipse(34, 2, 6, 11)])
    face_marks: list[BaseGeometry] = [
        LineString([(-9, 25), (-4, 27), (4, 27), (9, 25)]),  # the mouth
    ]
    for side in (-1, 1):
        face_marks += [ellipse(side * 12, -8, 5.5, 2.6), Point(side * 12, -8).buffer(1.2, 16)]  # an eye
        face_marks.append(ellipse(side * 3.6, 12, 1.5, 1.0))  # a nostril
        face_marks.append(ear(side * 35.5, 2, 2.6, 6.2, -side)[1])  # the bowl only: the outline is the rim

    profile_nose = Polygon([(0, -6), (-10, 5), (0, 10)]).buffer(3, join_style=1)
    left = unary_union([ellipse(0, 0, 25, 41), affinity.translate(profile_nose, -23, -2)])
    left_marks: list[BaseGeometry] = [
        ellipse(-11.5, -10, 2.4, 1.9),
        LineString([(-20.5, 24), (-13, 25.5)]),
        *ear(6, 2, 4.5, 8, -1),  # the face, and the nose, to the left
    ]
    right = affinity.scale(left, -1, 1, origin=(0, 0))
    right_marks = [affinity.scale(g, -1, 1, origin=(0, 0)) for g in left_marks]

    # Narrow at the chin, broad at the skull behind it; the jaw runs round from ear to ear.
    skull = unary_union([ellipse(0, 6, 31, 27), ellipse(0, -12, 21, 21)]).convex_hull
    below = unary_union([skull, affinity.translate(nose, 0, -32)]).difference(Point(0, 8).buffer(12, 64))
    below_marks: list[BaseGeometry] = [
        ellipse(-3, -35, 1.5, 1.1),
        ellipse(3, -35, 1.5, 1.1),
        arc(0, 2, 23, 24, 180, 360, 1),
        ear_behind(-31, 4, -1),
        ear_behind(31, 4, 1),
    ]

    skull = ellipse(0, 0, 33, 41)  # round: the nape is on the back of the body
    back_ears = [ear_from_behind(skull, side * 33, -2, side) for side in (-1, 1)]
    back = unary_union([skull, *(shape for shape, _base in back_ears)])
    back_marks: list[BaseGeometry] = [base for _shape, base in back_ears]

    return {
        "3170": (top, top_marks),
        "3171": (face, face_marks),
        "3150": (left, left_marks),
        "3151": (right, right_marks),
        "3173": (below, below_marks),
        "3172": (back, back_marks),
    }


def head_view() -> tuple[dict[str, Polygon], list[BaseGeometry]]:
    """The six head pictograms laid out like an unfolded cube, scaled to fit, with their landmarks."""
    figures = {code: (shape.buffer(0.8).buffer(-0.8), marks) for code, (shape, marks) in head_figures().items()}
    s = HEAD_SCALE

    def extent(code: str) -> tuple[float, float, float, float]:
        return figures[code][0].bounds

    # The middle row, left to right, centred across the view.
    row = ["3172", "3150", "3171", "3151"]
    width = sum(extent(c)[2] - extent(c)[0] for c in row) * s + HEAD_GAP * (len(row) - 1)
    x = (W - width) / 2
    centre_x: dict[str, float] = {}
    for code in row:
        minx, _, maxx, _ = extent(code)
        centre_x[code] = x - minx * s
        x += (maxx - minx) * s + HEAD_GAP
    # The top above the face and the head from below under it, in the face's column; the three rows centred down.
    for code in ("3170", "3173"):
        centre_x[code] = centre_x["3171"]
    middle = [extent(c) for c in row]
    top_height = extent("3170")[3] * s  # below its centre, down to the point of the nose
    face_top = min(e[1] for e in middle) * s
    middle_bottom = max(e[3] for e in middle if e is not extent("3172")) * s
    middle_y = top_height - face_top + HEAD_GAP * 1.5
    below_y = middle_y + middle_bottom - extent("3173")[1] * s + HEAD_GAP * 1.5
    total_top, total_bottom = extent("3170")[1] * s, below_y + extent("3173")[3] * s
    shift = (H - (total_bottom - total_top)) / 2 - total_top
    centre_y = {"3170": shift, "3173": below_y + shift, **{code: middle_y + shift for code in row}}

    shapes: dict[str, Polygon] = {}
    marks: list[BaseGeometry] = []
    for code, (shape, its_marks) in figures.items():

        def place(g: BaseGeometry, code: str = code) -> BaseGeometry:
            return affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), centre_x[code], centre_y[code])

        shapes[code] = place(shape)  # type: ignore[assignment]
        marks += [place(g) for g in its_marks]
    return shapes, marks


DETAIL_NAMES = {
    "3210": "Right Palm",
    "3211": "Left Palm",
    "3220": "Back of Right Hand",
    "3221": "Back of Left Hand",
    "3310": "Sole of Right Foot",
    "3311": "Sole of Left Foot",
    "3320": "Top of Right Foot",
    "3321": "Top of Left Foot",
}


def digit(base: tuple[float, float], angle: float, length: float, rb: float, rt: float) -> Polygon:
    """A finger or a toe: a tapered capsule from its base, leaning `angle` degrees from straight up."""
    a = math.radians(angle)
    return capsule(base, rb, (base[0] + length * math.sin(a), base[1] - length * math.cos(a)), rt)


def nail(base: tuple[float, float], angle: float, length: float, rt: float) -> Polygon:
    """The nail of a finger or a toe drawn by `digit` with the same numbers: an oval just behind its tip."""
    a = math.radians(angle)
    tip = (base[0] + (length - 0.15 * rt) * math.sin(a), base[1] - (length - 0.15 * rt) * math.cos(a))
    return affinity.rotate(ellipse(tip[0], tip[1], 0.55 * rt, 0.75 * rt), angle, origin=tip)


def hand(thumb_left: bool) -> tuple[Polygon, MultiPolygon]:
    """An open hand, fingers up and spread, centred on the origin; the thumb on the left or on the right.

    The palm and the back of the hand are the skin of a hand unrolled onto the page, so between them they
    cover all of it: the fingers and the thumb are a little wider than in a photo, to take in their sides, and
    the palm reaches past the little finger, to take in the edge of the hand that rests on a table. Drawn
    as a left hand with the thumb on the left and mirrored for the other.
    """
    palm = Polygon([(-12.5, -12), (12.5, -12), (15.5, 2), (14.5, 14), (-11.5, 14), (-15, 7)]).buffer(4.2, join_style=1)
    knuckle = (-14 - 13 * math.sin(math.radians(55)), 4 - 13 * math.cos(math.radians(55)))
    # Index, middle, ring and little finger, then the thumb's last joint: base, lean, length, radii.
    fingers = [
        ((-10.2, -12), -15, 29, 4.0, 3.6),
        ((-3.4, -14), -3, 33, 4.1, 3.7),
        ((3.6, -13.5), 10, 30.5, 4.0, 3.6),
        ((10.6, -10), 24, 24, 3.8, 3.4),
        (knuckle, -40, 12, 5.6, 4.8),
    ]
    thumb = [ellipse(-12, 4.5, 7.5, 10), digit((-14, 4), -55, 13, 6.4, 5.6)]
    joined = (
        unary_union([palm, *(digit(*f) for f in fingers), *thumb]).buffer(0.6, join_style=1).buffer(-0.6, join_style=1)
    )
    left = Polygon(joined.exterior)
    nails = MultiPolygon([nail(base, angle, length, rt) for base, angle, length, _rb, rt in fingers])
    if thumb_left:
        return left, nails
    return affinity.scale(left, -1, 1, origin=(0, 0)), affinity.scale(nails, -1, 1, origin=(0, 0))


def foot(big_toe_left: bool, ankle: bool = False) -> tuple[Polygon, MultiPolygon]:
    """A foot, toes up, centred on the origin; the big toe on the left or on the right; with `ankle`, seen from above.

    Broad at the ball, narrowing to a round heel; the big toe's inner edge runs on from the foot's and it stands
    a little apart, the other toes step down towards the outer edge, each free of the next as on a real foot.
    Seen from above, the leg stands on it: a round hole where the ankle is says which side this is, and is not
    a place for a mark. Drawn with the big toe on the left and mirrored for the other.
    """
    # The front edge sits high under the middle toes and drops by the little one, so every toe stands free.
    ball = Polygon(
        [
            (-15.5, -13),
            (-15.5, -6),
            (-12.4, 12),
            (13.0, 14),
            (15.8, -1),
            (14.5, -5),
            (10.5, -11),
            (5, -13.5),
            (-1, -14.5),
        ]
    ).buffer(2.5, join_style=1)
    body = unary_union([ball, ellipse(0.5, 39, 10.5, 12)]).convex_hull
    toes = [
        ((-11.2, -13), -3.8, 18.5, 6.9, 6.2),
        ((-1.5, -15.5), 4.8, 14.5, 3.3, 2.9),
        ((4.8, -14.5), 10.5, 12.8, 3.1, 2.7),
        ((10.5, -12), 17.2, 10.8, 2.9, 2.6),
        ((14.6, -6.5), 24, 9.5, 2.7, 2.4),
    ]
    joined = unary_union([body, *(digit(*t) for t in toes)]).buffer(0.3, join_style=1).buffer(-0.3, join_style=1)
    left = Polygon(joined.exterior)  # no pinholes where the toes meet the foot
    if ankle:
        left = left.difference(Point(0.5, 37).buffer(8.5, 64))
    nails = MultiPolygon([nail(base, angle, length, rt) for base, angle, length, _rb, rt in toes])
    # A slender foot, long for its width; mirrored for the other.
    sx = 0.92 if big_toe_left else -0.92
    return affinity.scale(left, sx, 1, origin=(0, 0)), affinity.scale(nails, sx, 1, origin=(0, 0))


def detail_views() -> tuple[dict[str, dict[str, Polygon]], dict[str, list[BaseGeometry]]]:
    """Hands and feet as a person looks at their own, the left one on the left of the screen. The upper row is
    the backs of the hands (thumbs inward) and the tops of the feet, the lower one the palms (thumbs outward)
    and the soles; big toes point inward in both. The interface tints the upper row, and the upper row carries
    the nails, so no caption is needed. Returns the zone shapes and, per view, the details drawn over them."""
    left_x, right_x = MID - 52, MID + 52

    def place(
        drawn: tuple[Polygon, MultiPolygon], x: float, y: float, scale: float, nails: list[BaseGeometry] | None = None
    ) -> Polygon:
        """The outline scaled and centred on (x, y) by its bounding box; its nails moved with it when asked."""
        outline, its_nails = (affinity.scale(g, scale, scale, origin=(0, 0)) for g in drawn)
        minx, miny, maxx, maxy = outline.bounds
        dx, dy = x - (minx + maxx) / 2, y - (miny + maxy) / 2
        if nails is not None:
            nails.append(affinity.translate(its_nails, dx, dy))
        return affinity.translate(outline, dx, dy)

    hand_nails: list[BaseGeometry] = []
    foot_nails: list[BaseGeometry] = []
    hands = {
        "3221": place(hand(thumb_left=False), left_x, 105, 1.25, hand_nails),
        "3220": place(hand(thumb_left=True), right_x, 105, 1.25, hand_nails),
        "3211": place(hand(thumb_left=True), left_x, 285, 1.25),
        "3210": place(hand(thumb_left=False), right_x, 285, 1.25),
    }
    feet = {
        "3321": place(foot(big_toe_left=False, ankle=True), left_x, 105, 1.1, foot_nails),
        "3320": place(foot(big_toe_left=True, ankle=True), right_x, 105, 1.1, foot_nails),
        "3311": place(foot(big_toe_left=False), left_x, 290, 1.1),
        "3310": place(foot(big_toe_left=True), right_x, 290, 1.1),
    }
    return {"hands": hands, "feet": feet}, {"hands": hand_nails, "feet": foot_nails}


def body_details(view: str) -> list[BaseGeometry]:
    """Landmarks that help place a mark, each on the view it belongs to: nipples and navel on the front, the
    cleft of the buttocks on the back. The head, hands and feet are only sketched here, so nothing goes on them."""
    if view == "front":
        return [
            Point(MID - 18.5, 110).buffer(1.9, 32),
            Point(MID + 18.5, 110).buffer(1.9, 32),
            ellipse(MID, NAVEL, 1.5, 2.3),
        ]
    return [LineString([(MID, CLEFT[0]), (MID, CLEFT[1])])]


def part_details(part: str) -> list[BaseGeometry]:
    """One part of a person's anatomy that the front view adds, in thin lines over the one silhouette all bodies
    share; the parts are chosen one by one, so any body can be drawn: the lower curve of each breast, centred on
    its nipple; the cleft of the vulva; the penis springing from the top of a scrotum shaped by the two testicles."""
    if part == "breasts":
        return [arc(MID + side * 18.5, 110, 14, 14, 15, 165, -1) for side in (-1, 1)]
    if part == "vulva":
        return [LineString([(MID, 212.5), (MID, CLEFT[1])])]  # down to the crotch's round
    # The penis springs from the top of the scrotum and hangs a little below it, in front of it.
    penis = capsule((MID, 219.4), 3.4, (MID, 228), 3.1)
    # The scrotum takes the shape of the two testicles in it, and shows at the penis's sides.
    testicles = unary_union([ellipse(MID - 4.6, 222, 5.2, 6), ellipse(MID + 4.6, 222, 5.2, 6)])
    return [penis, LineString(testicles.exterior.coords).difference(penis)]


def arc(
    cx: float, cy: float, rx: float, ry: float, start: float, end: float, facing: int, steps: int = 24
) -> LineString:
    """Part of an ellipse, from `start` to `end` degrees (0 at the back, away from the face; clockwise on screen).
    `facing` is -1 when the face is to the left, 1 when it is to the right."""
    return LineString(
        [
            (
                cx - facing * rx * math.cos(math.radians(start + (end - start) * i / steps)),
                cy + ry * math.sin(math.radians(start + (end - start) * i / steps)),
            )
            for i in range(steps + 1)
        ]
    )


def ear(cx: float, cy: float, rx: float, ry: float, facing: int) -> list[LineString]:
    """An ear, as the familiar sign for one: its rim from the front of the top, over the back and down round the
    lobe, and inside it the curve of the bowl, both open towards the face."""
    return [
        arc(cx, cy, rx, ry, -150, 125, facing),
        arc(cx - facing * 0.15 * rx, cy + 0.12 * ry, 0.5 * rx, 0.5 * ry, -115, 95, facing),
    ]


def ear_from_behind(head: Polygon, x: float, y: float, side: int) -> tuple[Polygon, BaseGeometry]:
    """An ear seen from behind or from above, standing out from the side of the head: a shape of its own, with a
    smooth rim, to join to the head so a tap on it counts, and the line where it meets the head, to draw."""
    rim = chaikin([(x, y - 12), (x + side * 4, y - 8), (x + side * 6, y - 1), (x + side * 4.5, y + 6), (x, y + 10)], 4)
    shape = Polygon([*rim, (x - side * 3, y + 10), (x - side * 3, y - 12)])
    return shape, head.exterior.intersection(shape)


def ear_behind(x: float, y: float, side: int) -> LineString:
    """An ear seen from behind or below: its rim standing out from the side of the head; `side` -1 left, 1 right."""
    return LineString([(x, y - 12), (x + side * 4, y - 8), (x + side * 6, y - 1), (x + side * 4.5, y + 6), (x, y + 10)])


def detail_path(geoms: list[BaseGeometry], precision: int = 1) -> str:
    """The details as one SVG path: outlines closed, lines open."""
    parts: list[str] = []
    for geom in geoms:
        for whole in getattr(geom, "geoms", [geom]):
            part = whole.simplify(0.08)  # a tenth of a unit is far below a screen pixel; the path stays small
            if isinstance(part, LineString):
                coords = [f"{x:.{precision}f},{y:.{precision}f}" for x, y in part.coords]
                parts.append("M" + " L".join(coords))
            else:
                parts.append(to_path(part, precision))
    return "".join(parts)


def build_detail(view: str, shapes: dict[str, Polygon]) -> tuple[Polygon | MultiPolygon, list[dict]]:
    zones = []
    for code, shape in sorted(shapes.items()):
        rp = shape.representative_point()
        name = DETAIL_NAMES[code]
        zones.append(
            {
                "code": code,
                "view": view,
                "side": side_of(code, view, name.split(" of ")[-1]),
                "region": "arm" if view == "hands" else "leg",
                "name": name,
                "molemapper_shape": 0,
                "path": to_path(shape),
                "anchor": [round(rp.x, 1), round(rp.y, 1)],
                "bbox": [round(v, 1) for v in shape.bounds],
            }
        )
    return unary_union(list(shapes.values())), zones


def build_head() -> tuple[Polygon | MultiPolygon, list[dict], list[BaseGeometry]]:
    shapes, marks = head_view()
    zones = []
    for code, shape in sorted(shapes.items()):
        rp = shape.representative_point()
        name = HEAD_NAMES[code]
        zones.append(
            {
                "code": code,
                "view": "head",
                "side": side_of(code, "head", name.split(": ")[-1]),
                "region": "head",
                "name": name,
                "molemapper_shape": 15 if code in ("3150", "3151") else 0 if code == "3173" else 17,
                "path": to_path(shape),
                "anchor": [round(rp.x, 1), round(rp.y, 1)],
                "bbox": [round(v, 1) for v in shape.bounds],
            }
        )
    return unary_union(list(shapes.values())), zones, marks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path, help="directory for preview renders (SVG; PNG with --png)")
    ap.add_argument("--png", action="store_true", help="also rasterise the previews")
    args = ap.parse_args()
    body = silhouette()
    outlines = {"front": body, "back": back_silhouette()}
    views = {}
    zones = []
    for view in ("front", "back"):
        zs = build_zones(outlines[view], view)
        views[view] = {
            "silhouette": to_path(outlines[view]),
            "zones": [z["code"] for z in zs],
            "details": detail_path(body_details(view)),
        }
        if view == "front":
            views[view]["details_by_part"] = {
                part: detail_path(part_details(part)) for part in ("breasts", "vulva", "penis")
            }
        zones.extend(zs)
    head, head_zones, head_marks = build_head()
    views["head"] = {
        "silhouette": to_path(head),
        "zones": [z["code"] for z in head_zones],
        "details": detail_path(head_marks),
    }
    zones.extend(head_zones)
    outlines["head"] = head
    shapes_by_view, nails_by_view = detail_views()
    for view, shapes in shapes_by_view.items():
        outline, detail_zones = build_detail(view, shapes)
        views[view] = {
            "silhouette": to_path(outline),
            "zones": [z["code"] for z in detail_zones],
            "details": detail_path(nails_by_view[view]),
        }
        zones.extend(detail_zones)
        outlines[view] = outline
    zones.sort(key=lambda z: z["code"])
    payload = {
        "version": VERSION,
        "viewBox": [0, 0, W, H],
        "attribution": (
            "Zone identifiers, names and hit polygons derived from MoleMapper (Oregon Health & Science University, "
            "BSD 3-Clause; see THIRD_PARTY_NOTICES.md). Silhouette and zone geometry by the neVus project."
        ),
        "views": views,
        "zones": zones,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    payload_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    for out in OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    print(f"wrote {len(zones)} zones, silhouette {len(body.exterior.coords)} points, hash {payload_hash}")
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        for view in ("front", "back", "head", "hands", "feet"):
            outline = outlines[view]
            svg = preview_svg(outline, [z for z in zones if z["view"] == view], view, views[view]["details"])
            (args.preview / f"{view}.svg").write_text(svg + "\n")
            if args.png:
                import cairosvg

                cairosvg.svg2png(bytestring=svg.encode(), write_to=str(args.preview / f"{view}.png"))
        print(f"previews in {args.preview}")


if __name__ == "__main__":
    main()
