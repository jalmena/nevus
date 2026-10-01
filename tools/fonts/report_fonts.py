# SPDX-License-Identifier: AGPL-3.0-only
"""Make the static Epilogue faces the PDF reports embed, from the interface's variable font.

PDF/A needs every font embedded, and a variable font is not reliably rendered in PDF viewers, so the
report gets three static instances (400, 500, 600) cut down to the characters reports use. Run from
the repository root with the backend environment: `uv run --project backend python tools/fonts/report_fonts.py`.
Epilogue is under the SIL Open Font License 1.1 with no reserved font name; the licence travels with it.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "frontend/public/fonts/Epilogue-Variable.woff2"
LICENCE = ROOT / "frontend/public/fonts/OFL-Epilogue.txt"
TARGET = ROOT / "backend/src/nevus/reports/fonts"
WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600}
# Latin with Spanish, typographic punctuation, arrows, and the signs measurements use (plus-minus,
# superscript two, multiplication, degree, approximately, less/greater or equal, minus).
UNICODES = [
    *range(0x20, 0x7F),
    *range(0xA0, 0x100),
    *range(0x2010, 0x2028),
    0x2030,
    0x2039,
    0x203A,
    0x2044,
    0x20AC,
    *range(0x2190, 0x2194),
    0x2212,
    0x2248,
    0x2264,
    0x2265,
]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, weight in WEIGHTS.items():
        font = TTFont(SOURCE)
        static = instancer.instantiateVariableFont(font, {"wght": weight}, updateFontNames=True)
        options = subset.Options()
        options.layout_features = ["*"]  # keep tabular figures, kerning and ligatures
        options.name_IDs = ["*"]
        options.notdef_outline = True
        options.flavor = None
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=UNICODES)
        subsetter.subset(static)
        buffer = io.BytesIO()
        static.save(buffer)
        path = TARGET / f"Epilogue-{name}.ttf"
        path.write_bytes(buffer.getvalue())
        print(f"{path.relative_to(ROOT)}: {len(buffer.getvalue()) // 1024} KiB")
    shutil.copyfile(LICENCE, TARGET / "OFL-Epilogue.txt")


if __name__ == "__main__":
    main()
