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
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from molemapper_zones import GRID, PLACEMENTS, absolute_polygon, region_of, side_of

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = [
    ROOT / "backend" / "src" / "nevus" / "bodymap" / "zones.json",
    ROOT / "frontend" / "src" / "features" / "bodymap" / "zones.json",
]
VERSION = "nevus-body-map/1"
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


def silhouette() -> Polygon:
    head = ellipse(MID, 28.0, 20.0, 23.5)
    neck = Polygon([(MID - 10.0, 44), (MID + 10.0, 44), (MID + 10.0, 66), (MID - 10.0, 66)])
    # Right half of the trunk (screen left), mirrored below. Shoulder line, side, hip, crotch.
    trunk_right = [
        (MID, 62.0),
        (MID - 24.0, 63.5),
        (MID - 38.0, 68.5),
        (MID - 45.5, 77.0),
        (MID - 44.0, 92.0),
        (MID - 37.0, 106.0),
        (MID - 35.0, 122.0),
        (MID - 32.0, 148.0),
        (MID - 34.0, 168.0),
        (MID - 40.0, 190.0),
        (MID - 41.5, 208.0),
        (MID - 35.0, 224.0),
        (MID - 12.0, 228.0),
        (MID, 226.0),
    ]
    trunk = Polygon(trunk_right + [(W - x, y) for x, y in reversed(trunk_right[1:-1])])
    arm = chain([((MID - 35.5, 88.0), 11.0), ((MID - 58.0, 150.0), 8.5), ((MID - 75.0, 198.0), 6.5)])
    hand = capsule((MID - 76.0, 200.0), 7.5, (MID - 87.0, 232.0), 8.5)
    leg = chain(
        [
            ((MID - 23.0, 212.0), 19.5),
            ((MID - 23.0, 278.0), 13.0),
            ((MID - 24.0, 312.0), 12.5),
            ((MID - 23.0, 348.0), 7.5),
        ]
    )
    foot = capsule((MID - 23.0, 350.0), 8.0, (MID - 27.0, 389.0), 11.0)
    right_side = unary_union([arm, hand, leg, foot])
    body = unary_union([head, neck, trunk, right_side, mirror(right_side)])
    smooth = body.buffer(4.5, 32).buffer(-4.5, 32)  # closing: rounds the armpits, crotch and neck joins
    smooth = smooth.simplify(0.12, preserve_topology=True)
    assert isinstance(smooth, Polygon), type(smooth)
    return smooth


def to_path(geom: Polygon | MultiPolygon, precision: int = 1) -> str:
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    parts: list[str] = []
    for poly in polys:
        rings = [poly.exterior, *poly.interiors]
        for ring in rings:
            coords = list(ring.coords)[:-1]
            parts.append("M" + " ".join(f"{x:.{precision}f},{y:.{precision}f}" for x, y in coords) + "Z")
    return "".join(parts)


def build_zones(body: Polygon, view: str) -> list[dict]:
    placements = [p for p in PLACEMENTS if p[1] == view]
    placements.sort(key=lambda p: ORDER.index(region_of(p[0])))
    taken: Polygon | MultiPolygon = Polygon()
    regions: dict[str, Polygon | MultiPolygon] = {}
    for code, _v, _ox, _oy, _name, _shape in placements:
        hit = Polygon(absolute_polygon(code)).buffer(0)
        region = hit.intersection(body).difference(taken)
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
    result = []
    for code, _v, _ox, _oy, name, shape in placements:
        region = regions[code].buffer(0)
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
    result.sort(key=lambda z: z["code"])
    return result


def preview_svg(body: Polygon, zones: list[dict], view: str) -> str:
    palette = {"head": "#c9b7a3", "trunk": "#9fbfb9", "leg": "#b7c9a3", "arm": "#c9a3b7"}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {W:.0f} {H:.0f}" width="{W * 3:.0f}" height="{H * 3:.0f}">',
        f'<rect width="{W}" height="{H}" fill="#F6F1EA"/>',
    ]
    for z in zones:
        parts.append(f'<path d="{z["path"]}" fill="{palette[z["region"]]}" stroke="#F6F1EA" stroke-width="0.6"/>')
    parts.append(f'<path d="{to_path(body)}" fill="none" stroke="#2B2A28" stroke-width="0.8"/>')
    for z in zones:
        x, y = z["anchor"]
        parts.append(
            f'<text x="{x}" y="{y}" font-size="4" text-anchor="middle" fill="#2B2A28" '
            f'font-family="sans-serif">{z["code"]}</text>'
        )
    parts.append(f'<text x="4" y="8" font-size="6" fill="#2B2A28" font-family="sans-serif">{view}</text></svg>')
    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path, help="directory for preview renders (SVG; PNG with --png)")
    ap.add_argument("--png", action="store_true", help="also rasterise the previews")
    args = ap.parse_args()
    body = silhouette()
    body_path = to_path(body)
    views = {}
    zones = []
    for view in ("front", "back"):
        zs = build_zones(body, view)
        views[view] = {"silhouette": body_path, "zones": [z["code"] for z in zs]}
        zones.extend(zs)
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
        for view in ("front", "back"):
            svg = preview_svg(body, [z for z in zones if z["view"] == view], view)
            (args.preview / f"{view}.svg").write_text(svg + "\n")
            if args.png:
                import cairosvg

                cairosvg.svg2png(bytestring=svg.encode(), write_to=str(args.preview / f"{view}.png"))
        print(f"previews in {args.preview}")


if __name__ == "__main__":
    main()
