# SPDX-License-Identifier: AGPL-3.0-only
"""NFR-LAN-01: what neVus says describes sizes, dates, differences and uncertainty, never conditions or risk.

Every user-facing catalogue (the app's, the emails', the reports') and the report templates are checked
for disease names, risk vocabulary and medical prompts. Saying what neVus does not do is allowed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest

from nevus.notify import email
from nevus.reports import i18n

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

FORBIDDEN = {
    "en": [
        r"melanomas?",
        r"carcinomas?",
        r"cancer\w*",
        r"malignan\w*",
        r"benign\w*",
        r"tumou?rs?",
        r"neoplas\w*",
        r"suspicious\w*",
        r"dangerous\w*",
        r"risk\w*",
        r"urgent\w*",
        r"abcde",
        r"see (?:a|your) (?:doctor|dermatologist)",
        r"consult (?:a|your) (?:doctor|dermatologist)",
        r"diagnos\w*",
    ],
    "es": [
        r"melanomas?",
        r"carcinomas?",
        r"c[aá]ncer\w*",
        r"malign\w*",
        r"benign\w*",
        r"tumor\w*",
        r"neoplasi\w*",
        r"sospechos\w*",
        r"peligros\w*",
        r"riesgos?",
        r"urgente\w*",
        r"abcde",
        r"acud\w* (?:al|a tu|a un) m[eé]dico",
        r"consult\w* (?:a|con) (?:un|tu) m[eé]dico",
        r"diagn[oó]stic\w*",
    ],
}
# Statements of what neVus does not do, including the app's intended-use statement word for word.
ALLOWED = [
    "it does not diagnose, screen for, or assess the risk of any disease",
    "no diagnostica, no criba ni evalúa el riesgo de ninguna enfermedad",
    "does not diagnose",
    "not a diagnostic tool",
    "no diagnostica",
    "no es una herramienta de diagnóstico",
    "no es una herramienta diagnóstica",
]


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _offences(text: str, language: str) -> list[str]:
    lowered = text.lower()
    for phrase in ALLOWED:
        lowered = lowered.replace(phrase, " ")
    return [m.group(0) for p in FORBIDDEN[language] for m in re.finditer(rf"\b{p}\b", lowered)]


def _catalogues() -> Iterator[tuple[str, str, str]]:
    for language in ("en", "es"):
        for text in _strings(email.TEXT[language]):
            yield f"email/{language}", language, text
        for text in _strings(i18n.TEXT[language]):
            yield f"reports/{language}", language, text
        locale = FRONTEND / f"src/lib/i18n/locales/{language}.json"
        if locale.is_file():
            for text in _strings(json.loads(locale.read_text())):
                yield f"app/{language}", language, text
    for template in files("nevus.reports").joinpath("templates").iterdir():
        text = re.sub(r"\{[{%].*?[%}]\}", " ", template.read_text(encoding="utf-8"), flags=re.S)
        for language in ("en", "es"):
            yield f"template/{template.name}", language, text


def test_user_facing_text_is_descriptive() -> None:
    found = [
        f"{where}: {word!r} in {text[:80]!r}"
        for where, language, text in _catalogues()
        for word in _offences(text, language)
    ]
    assert found == []


@pytest.mark.parametrize(
    ("text", "language"),
    [("Higher risk", "en"), ("looks suspicious", "en"), ("Posible melanoma", "es"), ("riesgo alto", "es")],
)
def test_the_check_would_catch_it(text: str, language: str) -> None:
    assert _offences(text, language)


def test_saying_what_nevus_does_not_do_is_fine() -> None:
    assert _offences("It does not diagnose or assess any condition.", "en") == []
    assert _offences("No diagnostica ni evalúa ninguna afección.", "es") == []
