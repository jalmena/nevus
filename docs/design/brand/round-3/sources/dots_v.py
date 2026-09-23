#!/usr/bin/env python3
"""Generate the round-3 variations of mark E (observations forming a V that converges on the mark).

Canvas 256, 8-unit grid; vertex dot at (128, 186); arm dots placed along the V at fixed distances from
the vertex; sizes progress by area where the variant asks for it. Writes light, dark and bare variants.
"""
import math, pathlib, sys

OUT = pathlib.Path(sys.argv[1])
LIGHT = dict(paper="#F6F1EA", ink="#2B2A28", accent="#1F6F6B")
DARK = dict(paper="#17161A", ink="#EDE8E0", accent="#5FB3AE")
VERTEX = (128.0, 186.0)


def arm_points(distances, half_angle_deg):
    a = math.radians(half_angle_deg)
    pts = []
    for d in distances:
        dx, dy = d * math.sin(a), d * math.cos(a)
        pts.append((VERTEX[0] - dx, VERTEX[1] - dy))
        pts.append((VERTEX[0] + dx, VERTEX[1] - dy))
    return pts


def svg(name, label, dots, vertex_r, colours, container=True, ring=None):
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="{label}">']
    if container:
        lines.append(f'<rect width="256" height="256" rx="56" fill="{colours["paper"]}"/>')
    lines.append(f'<g fill="{colours["ink"]}">')
    for (x, y), r in dots:
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>')
    lines.append("</g>")
    if ring:
        lines.append(f'<circle cx="{VERTEX[0]:.1f}" cy="{VERTEX[1]:.1f}" r="{ring[0]:.1f}" fill="none" stroke="{colours["ink"]}" stroke-width="{ring[1]:.1f}"/>')
    lines.append(f'<circle cx="{VERTEX[0]:.1f}" cy="{VERTEX[1]:.1f}" r="{vertex_r:.1f}" fill="{colours["accent"]}"/>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def area_series(r_top, r_vertex, steps):
    """Radii growing by equal area steps from r_top to r_vertex over `steps` steps."""
    a0, a1 = math.pi * r_top ** 2, math.pi * r_vertex ** 2
    return [math.sqrt((a0 + (a1 - a0) * i / steps) / math.pi) for i in range(steps + 1)]


variants = {}
# E1 — five equal observations, V opening 60 degrees
pts = arm_points([74, 148], 30)
variants["e1-five-equal"] = ("E1: five equal observations converging on the mark", [(p, 15.0) for p in pts], 23.0, None)
# E2 — five observations growing by area towards the mark (time)
radii = area_series(11.0, 23.0, 2)  # top, middle, vertex
pts_far, pts_near = arm_points([148], 30), arm_points([74], 30)
variants["e2-five-growing"] = ("E2: observations grow towards the mark", [(p, radii[0]) for p in pts_far] + [(p, radii[1]) for p in pts_near], radii[2], None)
# E3 — three observations (small-size glyph)
pts = arm_points([100], 30)
variants["e3-three"] = ("E3: three observations", [(p, 17.0) for p in pts], 24.0, None)
# E4 — seven observations, denser trail
pts = arm_points([50, 100, 150], 30)
variants["e4-seven"] = ("E4: seven observations", [(p, 12.0) for p in pts], 22.0, None)
# E5 — narrower opening (44 degrees), five equal
pts = arm_points([74, 148], 22)
variants["e5-five-narrow"] = ("E5: narrower V", [(p, 15.0) for p in pts], 23.0, None)
# E6 — five growing with the current observation ringed
variants["e6-growing-ringed"] = ("E6: growing observations, current one ringed", [(p, radii[0]) for p in pts_far] + [(p, radii[1]) for p in pts_near], 15.0, (25.0, 7.0))

for key, (label, dots, vr, ring) in variants.items():
    (OUT / f"mark-{key}.svg").write_text(svg(key, label, dots, vr, LIGHT, True, ring))
    (OUT / f"mark-{key}-dark.svg").write_text(svg(key, label, dots, vr, DARK, True, ring))
    (OUT / f"mark-{key}-bare.svg").write_text(svg(key, label, dots, vr, LIGHT, False, ring))
    (OUT / f"mark-{key}-bare-dark.svg").write_text(svg(key, label, dots, vr, DARK, False, ring))
print("variants:", ", ".join(variants))
