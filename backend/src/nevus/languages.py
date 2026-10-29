# SPDX-License-Identifier: AGPL-3.0-only
"""The languages neVus speaks: the interface, the emails, the reports. DEVELOPMENT.md says how to add one.

The order is the chooser's: English first, then Spanish and the other languages of Spain, then the rest
of Europe, then further out. The frontend keeps the same list (`frontend/src/lib/i18n/index.ts`).
"""

from __future__ import annotations

from typing import Literal, get_args

Language = Literal[
    "en", "es", "ca", "gl", "eu", "pt", "fr", "it", "de", "nl", "pl", "ru", "tr", "id", "zh", "ja", "ko", "hi", "ar"
]  # fmt: skip
LANGUAGES: tuple[str, ...] = get_args(Language)
DEFAULT_LANGUAGE = "en"
RTL_LANGUAGES = frozenset({"ar"})


def normalise(value: str | None) -> str:
    """The language to speak for a stored preference: English when it is missing or unknown."""
    return value if value in LANGUAGES else DEFAULT_LANGUAGE


def direction(value: str | None) -> str:
    """How the language is written, as an HTML dir attribute."""
    return "rtl" if value in RTL_LANGUAGES else "ltr"
