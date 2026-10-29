# SPDX-License-Identifier: AGPL-3.0-only
"""Report wording in every language neVus speaks, and the number and date formats of each language.

Each language is a file in `locales/`: its wording, month names, date patterns and decimal mark."""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import cache
from importlib.resources import files
from typing import Any

from nevus.languages import normalise

NBSP = "\u00a0"


@cache
def catalogue(language: str) -> dict[str, Any]:
    """One language's wording and formats, read from `locales/<language>.json`."""
    raw = files("nevus.reports").joinpath(f"locales/{language}.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    return data


class Words:
    """The catalogue and formats of one language, as handed to the templates."""

    def __init__(self, language: str) -> None:
        self.language = normalise(language)
        self.catalogue = catalogue(self.language)
        self.text: dict[str, str] = self.catalogue["text"]

    def __call__(self, key: str, **values: object) -> str:
        return self.text[key].format(**values)

    def number(self, value: float, digits: int = 1, sign: bool = False) -> str:
        text = f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
        if text.startswith("-"):
            text = "\u2212" + text[1:]  # a real minus sign
        return text.replace(".", ",") if self.catalogue["decimal_comma"] else text

    def mm(self, value: float, sigma: float | None = None, sign: bool = False) -> str:
        if sigma is None:
            return f"{self.number(value, sign=sign)}{NBSP}mm"
        return f"{self.number(value, sign=sign)}{NBSP}±{NBSP}{self.number(max(sigma, 0.1))}{NBSP}mm"

    def area(self, value: float, sigma: float | None = None) -> str:
        if sigma is None:
            return f"{self.number(value)}{NBSP}mm²"
        return f"{self.number(value)}{NBSP}±{NBSP}{self.number(max(sigma, 0.1))}{NBSP}mm²"

    def percent(self, fraction: float) -> str:
        return f"{self.number(fraction * 100, 1)}{NBSP}%"

    def day(self, value: date | datetime | None) -> str:
        if value is None:
            return self("unknown")
        month = self.catalogue["months"][value.month - 1]
        return str(self.catalogue["date"]).format(day=value.day, month=month, year=value.year)

    def short_day(self, value: date | datetime) -> str:
        month = self.catalogue["months_short"][value.month - 1]
        return str(self.catalogue["short_date"]).format(day=value.day, month=month, year=value.year)

    def zone(self, code: str) -> str:
        return zone_names()[self.language].get(code, code)


@cache
def zone_names() -> dict[str, dict[str, str]]:
    """The interface's zone names, copied here so reports do not depend on the frontend (a test keeps them equal)."""
    raw = files("nevus.reports").joinpath("zone_names.json").read_text(encoding="utf-8")
    data: dict[str, dict[str, str]] = json.loads(raw)
    return data
