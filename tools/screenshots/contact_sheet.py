# SPDX-License-Identifier: AGPL-3.0-only
"""Contact sheets of the screenshot gallery: one image per device and colour scheme, for a look at the design.

    uv run --project backend python tools/screenshots/contact_sheet.py frontend/.screenshots

Reads `<dir>/<device>/<name>-<scheme>.png` as `pnpm run shots` writes them and writes
`<dir>/contact-<device>-<scheme>.png`, every screen scaled to the same width and cut at a sensible height.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

WIDTH = {"phone": 300, "tablet": 420, "desktop": 640}
COLUMNS = {"phone": 6, "tablet": 4, "desktop": 3}
MAX_HEIGHT = 1500
LABEL = 22
GAP = 8


def sheet(folder: Path, scheme: str) -> Path | None:
    shots = sorted(folder.glob(f"*-{scheme}.png"))
    if not shots:
        return None
    width = WIDTH.get(folder.name, 400)
    columns = COLUMNS.get(folder.name, 4)
    tiles: list[tuple[str, Image.Image]] = []
    for path in shots:
        with Image.open(path) as image:
            resized = image.convert("RGB").resize((width, max(1, round(image.height * width / image.width))))
        cropped = resized.crop((0, 0, width, min(resized.height, MAX_HEIGHT)))
        tiles.append((path.stem.removesuffix(f"-{scheme}"), cropped))
    rows = [tiles[i : i + columns] for i in range(0, len(tiles), columns)]
    heights = [max(tile.height for _, tile in row) + LABEL for row in rows]
    canvas = Image.new("RGB", (columns * (width + GAP) + GAP, sum(heights) + GAP * (len(rows) + 1)), "#2a2a2a")
    draw = ImageDraw.Draw(canvas)
    y = GAP
    for row, height in zip(rows, heights, strict=True):
        x = GAP
        for name, tile in row:
            draw.text((x, y + 4), name, fill="#ffffff")
            canvas.paste(tile, (x, y + LABEL))
            x += width + GAP
        y += height + GAP
    out = folder.parent / f"contact-{folder.name}-{scheme}.png"
    canvas.save(out)
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("frontend/.screenshots")
    if not root.is_dir():
        print(f"{root} does not exist; run `pnpm run shots` in frontend/ first.", file=sys.stderr)
        return 1
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        for scheme in ("light", "dark"):
            out = sheet(folder, scheme)
            if out:
                print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
