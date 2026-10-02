# SPDX-License-Identifier: AGPL-3.0-only
"""The languages neVus speaks: the interface, the emails, the reports. DEVELOPMENT.md says how to add one."""

from __future__ import annotations

from typing import Literal, get_args

Language = Literal["en", "es", "pt"]
LANGUAGES: tuple[str, ...] = get_args(Language)
DEFAULT_LANGUAGE = "en"


def normalise(value: str | None) -> str:
    """The language to speak for a stored preference: English when it is missing or unknown."""
    return value if value in LANGUAGES else DEFAULT_LANGUAGE
