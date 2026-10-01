# SPDX-License-Identifier: AGPL-3.0-only
"""The printable sheet: two window cards, two strips, a 50 mm verification line and instructions."""

from __future__ import annotations

from typing import TypedDict

from nevus.cv.card import STRIP, WINDOW, draw_card
from nevus.pdf.simple import Document


class SheetText(TypedDict):
    title: str
    lines: list[str]
    line: str


TEXT: dict[str, SheetText] = {
    "en": {
        "title": "neVus reference card v1",
        "lines": [
            "Print at 100 % (actual size, no fit to page) on matte card or matte photo paper.",
            "Before first use, measure the line above with a ruler. It must be 50 mm.",
            "If it is not, enter what you measured in neVus (Settings > Reference card): measurements are corrected.",
            "Cut along the thin outline and cut out the 24 mm window. Place the window over the mark,",
            "flat on the skin, and photograph from above. Use the strip where the card cannot lie flat.",
            "Glossy paper and glossy lamination cause reflections that hide the markers.",
            "The card touches skin: keep it personal, wipe it with alcohol, replace it when worn.",
        ],
        "line": "50 mm",
    },
    "es": {
        "title": "Tarjeta de referencia neVus v1",
        "lines": [
            "Imprime al 100 % (tamaño real, sin ajustar a la página) en cartulina o papel fotográfico mate.",
            "Antes del primer uso, mide la línea de arriba con una regla. Debe medir 50 mm.",
            "Si no, introduce lo que mediste en neVus (Ajustes > Tarjeta de referencia): las medidas se corrigen.",
            "Recorta por el contorno fino y recorta la ventana de 24 mm. Pon la ventana sobre la marca,",
            "plana sobre la piel, y fotografía desde arriba. Usa la tira donde la tarjeta no quede plana.",
            "El papel brillante y el plastificado brillante producen reflejos que ocultan los marcadores.",
            "La tarjeta toca la piel: es personal, límpiala con alcohol y cámbiala cuando se gaste.",
        ],
        "line": "50 mm",
    },
}


def render_sheet(page: str = "a4", lang: str = "en") -> bytes:
    text = TEXT.get(lang, TEXT["en"])
    doc = Document(page)
    p = doc.new_page()
    width = doc.size[0]
    left = (width - 2 * WINDOW.width - 10.0) / 2
    p.text(width / 2, 20.0, text["title"], 5.0, bold=True, align="center")
    for i in range(2):
        draw_card(p, WINDOW, left + i * (WINDOW.width + 10.0), 30.0)
        draw_card(p, STRIP, left + i * (WINDOW.width + 10.0) + (WINDOW.width - STRIP.width) / 2, 95.0)
    # Verification line: the whole sheet is scaled by the same factor, so one line checks every card.
    y = 130.0
    x0 = width / 2 - 25.0
    p.stroke_gray(0.0)
    p.line_width(0.25)
    p.line(x0, y, x0 + 50.0, y)
    p.line(x0, y - 3.0, x0, y + 3.0)
    p.line(x0 + 50.0, y - 3.0, x0 + 50.0, y + 3.0)
    p.fill_gray(0.0)
    p.text(width / 2, y - 4.0, text["line"], 3.0, bold=True, align="center")
    for n, line in enumerate(text["lines"]):
        p.text(left, 145.0 + n * 6.0, line, 3.0)
    return doc.render(text["title"])
