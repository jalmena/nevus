#!/usr/bin/env python3
"""The neVus symbol: a divider (measuring compass) whose points hold the mark between them.
Version 2 (2026-09-23): the hinge at the vertex carries a pivot hole in the inverse colour of the strokes,
drawn as a ring so it works on any background. 256 grid, stroke 18, round caps and joins."""
import pathlib, sys
OUT = pathlib.Path(sys.argv[1])
LIGHT = dict(paper="#F6F1EA", ink="#2B2A28", accent="#1F6F6B")
DARK = dict(paper="#17161A", ink="#EDE8E0", accent="#5FB3AE")

def body(c):
    return (f'<g fill="none" stroke="{c["ink"]}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M64 70 L128 190 L192 70"/></g>'
            f'<circle cx="64" cy="70" r="11" fill="{c["ink"]}"/><circle cx="192" cy="70" r="11" fill="{c["ink"]}"/>'
            f'<circle cx="128" cy="190" r="13" fill="none" stroke="{c["ink"]}" stroke-width="10"/>'  # hinge: ring, hole of the background colour
            f'<circle cx="128" cy="84" r="21" fill="{c["accent"]}"/>')

def svg(label, c, container):
    rect = f'<rect width="256" height="256" rx="56" fill="{c["paper"]}"/>' if container else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="{label}">'
            f'{rect}{body(c)}</svg>\n')

label = "neVus mark: a divider holding the mark between its points, with a pivot hole at the hinge"
(OUT / "mark-divider.svg").write_text(svg(label, LIGHT, True))
(OUT / "mark-divider-dark.svg").write_text(svg(label, DARK, True))
(OUT / "mark-divider-bare.svg").write_text(svg(label, LIGHT, False))
(OUT / "mark-divider-bare-dark.svg").write_text(svg(label, DARK, False))
print("divider v2 written")
