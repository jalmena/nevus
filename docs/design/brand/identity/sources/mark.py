#!/usr/bin/env python3
"""The neVus mark: a divider (measuring compass) whose points hold the mark between its points.

Geometry as approved in round 5, unchanged: 256 grid, legs of stroke 18 from the tips (64,70) and (192,70)
towards the hinge at (128,190), tip balls of radius 11, hinge disc of radius 18, the accent mark of radius 21 at
(128,84). The only addition (2026-09-23): a hole of exactly half the hinge's diameter (radius 9) in the
inverse colour of the strokes. So that the hole shows the background and not the legs, each leg ends with a
square cut 12 units short of the hinge centre: the cut lies entirely under the disc (its corners are 15 units
from the centre, the disc reaches 18) and clear of the hole (9), so the outer silhouette is identical to the
original drawing. The tip end of each leg is covered by its ball. Light, dark and bare variants are written."""
import math, pathlib, sys

OUT = pathlib.Path(sys.argv[1])
LIGHT = dict(paper="#F6F1EA", ink="#2B2A28", accent="#1F6F6B")
DARK = dict(paper="#17161A", ink="#EDE8E0", accent="#5FB3AE")
VX, VY = 128.0, 190.0        # hinge centre
HINGE_R, HOLE_R = 18.0, 9.0  # hole = half the diameter
TIPS = ((64.0, 70.0), (192.0, 70.0))
TIP_R, STROKE = 11.0, 18.0
DOT = (128.0, 84.0, 21.0)
STOP = 12.0                  # legs end this far from the hinge centre, under the disc


def leg(tip):
    dx, dy = VX - tip[0], VY - tip[1]
    n = math.hypot(dx, dy)
    ex, ey = VX - dx / n * STOP, VY - dy / n * STOP
    return f'<line x1="{tip[0]:g}" y1="{tip[1]:g}" x2="{ex:.2f}" y2="{ey:.2f}"/>'


def body(c):
    return (f'<g stroke="{c["ink"]}" stroke-width="{STROKE:g}" stroke-linecap="butt">{leg(TIPS[0])}{leg(TIPS[1])}</g>'
            f'<circle cx="{TIPS[0][0]:g}" cy="{TIPS[0][1]:g}" r="{TIP_R:g}" fill="{c["ink"]}"/>'
            f'<circle cx="{TIPS[1][0]:g}" cy="{TIPS[1][1]:g}" r="{TIP_R:g}" fill="{c["ink"]}"/>'
            f'<circle cx="{VX:g}" cy="{VY:g}" r="{HINGE_R:g}" fill="{c["ink"]}"/>'
            f'<circle cx="{VX:g}" cy="{VY:g}" r="{HOLE_R:g}" fill="{c["paper"]}"/>'
            f'<circle cx="{DOT[0]:g}" cy="{DOT[1]:g}" r="{DOT[2]:g}" fill="{c["accent"]}"/>')


def svg(label, c, container):
    rect = f'<rect width="256" height="256" rx="56" fill="{c["paper"]}"/>' if container else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="{label}">'
            f'{rect}{body(c)}</svg>\n')


label = "neVus: a divider holding the mark between its points; the hinge carries a hole of half its diameter"
(OUT / "mark.svg").write_text(svg(label, LIGHT, True))
(OUT / "mark-dark.svg").write_text(svg(label, DARK, True))
(OUT / "mark-bare.svg").write_text(svg(label, LIGHT, False))
(OUT / "mark-bare-dark.svg").write_text(svg(label, DARK, False))
# letter box when the mark stands in for the V: ink extents x 53..203, y 59..208
print("letter box: 53,59,150,149")
