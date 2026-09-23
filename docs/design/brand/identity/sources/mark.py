#!/usr/bin/env python3
"""neVus symbol, version 3 (2026-09-23), weight matched to the wordmark letters. A divider (measuring compass) whose points hold the mark between them.
The hinge at the vertex is a disc of radius 20 with a hole of radius 10 (exactly half the diameter) in the inverse
colour of the strokes; the legs stop at the hinge so nothing shows through the hole. 256 grid, stroke 18, round caps."""
import math, pathlib, sys
OUT = pathlib.Path(sys.argv[1])
LIGHT = dict(paper="#F6F1EA", ink="#2B2A28", accent="#1F6F6B")
DARK = dict(paper="#17161A", ink="#EDE8E0", accent="#5FB3AE")
VX, VY, R = 128.0, 190.0, 26.0           # hinge centre and outer radius
TIPS = ((64.0, 70.0), (192.0, 70.0))     # points of the divider
DOT = (128.0, 84.0, 24.0)                # the mark between the points
STOP = R + 6.0                            # legs end this far from the hinge centre (round caps reach R - 5)

def leg(tip):
    dx, dy = VX - tip[0], VY - tip[1]
    n = math.hypot(dx, dy)
    ex, ey = VX - dx / n * STOP, VY - dy / n * STOP
    return f'<line x1="{tip[0]:g}" y1="{tip[1]:g}" x2="{ex:.2f}" y2="{ey:.2f}"/>'

def body(c, hole_colour):
    return (f'<g stroke="{c["ink"]}" stroke-width="26" stroke-linecap="round">{leg(TIPS[0])}{leg(TIPS[1])}</g>'
            f'<circle cx="{TIPS[0][0]:g}" cy="{TIPS[0][1]:g}" r="15" fill="{c["ink"]}"/><circle cx="{TIPS[1][0]:g}" cy="{TIPS[1][1]:g}" r="15" fill="{c["ink"]}"/>'
            f'<circle cx="{VX:g}" cy="{VY:g}" r="{R:g}" fill="{c["ink"]}"/>'
            f'<circle cx="{VX:g}" cy="{VY:g}" r="{R/2:g}" fill="{hole_colour}"/>'
            f'<circle cx="{DOT[0]:g}" cy="{DOT[1]:g}" r="{DOT[2]:g}" fill="{c["accent"]}"/>')

def svg(label, c, container):
    rect = f'<rect width="256" height="256" rx="56" fill="{c["paper"]}"/>' if container else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="{label}">'
            f'{rect}{body(c, c["paper"])}</svg>\n')

label = "neVus: a divider holding the mark between its points; the hinge carries a hole of half its diameter"
(OUT / "mark.svg").write_text(svg(label, LIGHT, True))
(OUT / "mark-dark.svg").write_text(svg(label, DARK, True))
(OUT / "mark-bare.svg").write_text(svg(label, LIGHT, False))
(OUT / "mark-bare-dark.svg").write_text(svg(label, DARK, False))
# letter box of the divider when it stands in for the V: ink extents x 53..203, y 59..210
print("letter box: 49,55,158,161")
