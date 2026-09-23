#!/usr/bin/env python3
"""Round-4 symbol concepts for neVus, constructed on the 256 grid. Fresh directions after the dot-V family was declined:
S1 divider (a measuring compass holding the mark between its points), S2 seal (a dated record stamp with the V),
S3 eye (observation: an almond whose lower lid is the V). Light, dark and bare variants."""
import math, pathlib, sys
OUT = pathlib.Path(sys.argv[1])
LIGHT = dict(paper="#F6F1EA", ink="#2B2A28", accent="#1F6F6B")
DARK = dict(paper="#17161A", ink="#EDE8E0", accent="#5FB3AE")

def wrap(label, body, c, container):
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="{label}">'
    rect = f'<rect width="256" height="256" rx="56" fill="{c["paper"]}"/>' if container else ""
    return head + rect + body(c) + "</svg>\n"

def s1(c):
    # divider: legs from a hinge at the bottom to two points at the top; the mark sits between the points
    return (f'<g fill="none" stroke="{c["ink"]}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M64 70 L128 190 L192 70"/></g>'
            f'<circle cx="128" cy="190" r="17" fill="{c["ink"]}"/>'
            f'<circle cx="64" cy="70" r="11" fill="{c["ink"]}"/><circle cx="192" cy="70" r="11" fill="{c["ink"]}"/>'
            f'<circle cx="128" cy="84" r="21" fill="{c["accent"]}"/>')

def s2(c):
    # tag: a specimen label whose lower end is the V; the mark sits on the label
    return (f'<path d="M84 48 H172 V176 L128 214 L84 176 Z" fill="none" stroke="{c["ink"]}" stroke-width="18" stroke-linejoin="round"/>'
            f'<circle cx="128" cy="112" r="22" fill="{c["accent"]}"/>')

def s3(c):
    # eye: upper lid an arc, lower lid the V, the mark as the pupil
    return (f'<g fill="none" stroke="{c["ink"]}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M36 136 Q128 30 220 136"/>'
            f'<path d="M36 136 L128 184 L220 136"/></g>'
            f'<circle cx="128" cy="126" r="24" fill="{c["accent"]}"/>')

concepts = {"s1-divider": ("S1: a divider holds the mark between its points", s1),
            "s2-tag": ("S2: a specimen tag whose lower end is the V", s2),
            "s3-eye": ("S3: an eye whose lower lid is the V", s3)}
for key, (label, fn) in concepts.items():
    (OUT / f"mark-{key}.svg").write_text(wrap(label, fn, LIGHT, True))
    (OUT / f"mark-{key}-dark.svg").write_text(wrap(label, fn, DARK, True))
    (OUT / f"mark-{key}-bare.svg").write_text(wrap(label, fn, LIGHT, False))
    (OUT / f"mark-{key}-bare-dark.svg").write_text(wrap(label, fn, DARK, False))
print("concepts:", ", ".join(concepts))
