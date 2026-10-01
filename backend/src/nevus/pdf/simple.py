# SPDX-License-Identifier: AGPL-3.0-only
"""A minimal PDF 1.4 writer: filled and stroked paths, circles and text in the standard fonts.

Coordinates are millimetres from the top-left corner of the page, the way the card specification
is written; the writer converts to PDF points (1/72 inch) with the origin at the bottom left.
Text uses Helvetica with WinAnsiEncoding, which covers English and Spanish without embedding a font.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field

MM = 72.0 / 25.4
PAGE_SIZES_MM = {"a4": (210.0, 297.0), "letter": (215.9, 279.4)}
_KAPPA = 4 * (math.sqrt(2) - 1) / 3


def _num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def _escape(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


@dataclass
class Page:
    width_mm: float
    height_mm: float
    ops: list[bytes] = field(default_factory=list)

    # --- coordinate helpers -----------------------------------------------------------------------
    def _pt(self, x: float, y: float) -> str:
        return f"{_num(x * MM)} {_num((self.height_mm - y) * MM)}"

    def _op(self, text: str | bytes) -> None:
        self.ops.append(text if isinstance(text, bytes) else text.encode("ascii"))

    # --- state ------------------------------------------------------------------------------------
    def fill_gray(self, level: float) -> None:
        self._op(f"{_num(level)} g")

    def fill_rgb(self, r: float, g: float, b: float) -> None:
        self._op(f"{_num(r)} {_num(g)} {_num(b)} rg")

    def stroke_gray(self, level: float) -> None:
        self._op(f"{_num(level)} G")

    def line_width(self, mm: float) -> None:
        self._op(f"{_num(mm * MM)} w")

    # --- shapes -----------------------------------------------------------------------------------
    def rect(self, x: float, y: float, w: float, h: float, *, fill: bool = True, stroke: bool = False) -> None:
        self._op(f"{_num(x * MM)} {_num((self.height_mm - y - h) * MM)} {_num(w * MM)} {_num(h * MM)} re")
        self._paint(fill, stroke)

    def rects(self, boxes: list[tuple[float, float, float, float]]) -> None:
        """Fill several rectangles as one path: no hairline seams where they touch."""
        for x, y, w, h in boxes:
            self._op(f"{_num(x * MM)} {_num((self.height_mm - y - h) * MM)} {_num(w * MM)} {_num(h * MM)} re")
        self._op("f")

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._op(f"{self._pt(x1, y1)} m {self._pt(x2, y2)} l S")

    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None:
        k = r * _KAPPA
        self._op(f"{self._pt(cx + r, cy)} m")
        for x1, y1, x2, y2, x3, y3 in (
            (cx + r, cy - k, cx + k, cy - r, cx, cy - r),
            (cx - k, cy - r, cx - r, cy - k, cx - r, cy),
            (cx - r, cy + k, cx - k, cy + r, cx, cy + r),
            (cx + k, cy + r, cx + r, cy + k, cx + r, cy),
        ):
            self._op(f"{self._pt(x1, y1)} {self._pt(x2, y2)} {self._pt(x3, y3)} c")
        self._paint(fill, stroke)

    def _paint(self, fill: bool, stroke: bool) -> None:
        self._op("B" if fill and stroke else "f" if fill else "S" if stroke else "n")

    def text(self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left") -> None:
        font = "F2" if bold else "F1"
        size = size_mm * MM
        width = text_width(text, size_mm, bold) if align != "left" else 0.0
        dx = -width if align == "right" else -width / 2 if align == "center" else 0.0
        self.ops.append(
            f"BT /{font} {_num(size)} Tf {self._pt(x + dx, y)} Td (".encode("ascii") + _escape(text) + b") Tj ET"
        )


# Helvetica advance widths (per 1000 em) for the printable ASCII range; enough for centring labels.
_HELV = [
    "278",
    "278",
    "355",
    "556",
    "556",
    "889",
    "667",
    "191",
    "333",
    "333",
    "389",
    "584",
    "278",
    "333",
    "278",
    "278",
    "556",
    "556",
    "556",
    "556",
    "556",
    "556",
    "556",
    "556",
    "556",
    "556",
    "278",
    "278",
    "584",
    "584",
    "584",
    "556",
    "1015",
    "667",
    "667",
    "722",
    "722",
    "667",
    "611",
    "778",
    "722",
    "278",
    "500",
    "667",
    "556",
    "833",
    "722",
    "778",
    "667",
    "778",
    "722",
    "667",
    "611",
    "722",
    "667",
    "944",
    "667",
    "667",
    "611",
    "278",
    "278",
    "278",
    "469",
    "556",
    "333",
    "556",
    "556",
    "500",
    "556",
    "556",
    "278",
    "556",
    "556",
    "222",
    "222",
    "500",
    "222",
    "833",
    "556",
    "556",
    "556",
    "556",
    "333",
    "500",
    "278",
    "556",
    "500",
    "722",
    "500",
    "500",
    "500",
    "334",
    "260",
    "334",
    "584",
]


def text_width(text: str, size_mm: float, bold: bool = False) -> float:
    total = 0
    for char in text:
        code = ord(char)
        total += int(_HELV[code - 32]) if 32 <= code < 32 + len(_HELV) else 556
    factor = 1.06 if bold else 1.0
    return total / 1000 * size_mm * factor


class Document:
    def __init__(self, page_size: str = "a4") -> None:
        self.size = PAGE_SIZES_MM[page_size]
        self.pages: list[Page] = []

    def new_page(self) -> Page:
        page = Page(*self.size)
        self.pages.append(page)
        return page

    def render(self, title: str = "neVus") -> bytes:
        objects: list[bytes] = []

        def add(body: bytes) -> int:
            objects.append(body)
            return len(objects)

        catalog = add(b"")  # placeholder, filled below
        pages_id = add(b"")
        font_regular = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font_bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        kids: list[int] = []
        width_pt, height_pt = self.size[0] * MM, self.size[1] * MM
        for page in self.pages:
            stream = zlib.compress(b"\n".join(page.ops))
            content = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
            kids.append(
                add(
                    (
                        f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {_num(width_pt)} {_num(height_pt)}] "
                        f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
                        f"/Contents {content} 0 R >>"
                    ).encode("ascii")
                )
            )
        objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
        objects[pages_id - 1] = (
            f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode("ascii")
        )
        info = add(b"<< /Title (" + _escape(title) + b") /Producer (neVus) >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode("ascii")
        out += (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
        return bytes(out)
