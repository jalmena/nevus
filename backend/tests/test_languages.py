# SPDX-License-Identifier: AGPL-3.0-only
"""Every language neVus speaks says the same things: same keys, same placeholders, everywhere."""

from __future__ import annotations

import re

import pytest

from nevus.api import push
from nevus.cv import card_mesh, card_sheet
from nevus.languages import DEFAULT_LANGUAGE, LANGUAGES, direction, normalise
from nevus.notify import calendar, email, webhooks
from nevus.reports import i18n

CATALOGUES = {
    "reports": {language: i18n.catalogue(language)["text"] for language in LANGUAGES},
    "email": email.TEXT,
    "calendar": calendar.TEXT,
    "webhooks": webhooks.TEXT,
    "sheet": {language: {**text, "lines": " ".join(text["lines"])} for language, text in card_sheet.TEXT.items()},
    "print_note": {
        language: {"title": title, **{f"p{n}": p for n, p in enumerate(paragraphs)}}
        for language, (title, paragraphs) in card_mesh.README_TEXT.items()
    },
}


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


@pytest.mark.parametrize("name", sorted(CATALOGUES))
def test_each_catalogue_has_every_language_with_the_same_keys_and_placeholders(name: str) -> None:
    catalogue = CATALOGUES[name]
    assert set(catalogue) == set(LANGUAGES), name
    reference = catalogue[DEFAULT_LANGUAGE]
    for language in LANGUAGES:
        texts = catalogue[language]
        assert set(texts) == set(reference), (name, language)
        for key, text in texts.items():
            assert text.strip(), (name, language, key)
            assert _placeholders(text) == _placeholders(reference[key]), (name, language, key)


def test_formats_zone_names_and_the_push_greeting_cover_every_language() -> None:
    for language in LANGUAGES:
        formats = i18n.catalogue(language)
        assert len(formats["months"]) == 12 and len(formats["months_short"]) == 12, language
        assert isinstance(formats["decimal_comma"], bool), language
        for pattern in (formats["date"], formats["short_date"]):
            assert {"{day}", "{month}", "{year}"} <= set(re.findall(r"\{\w+\}", pattern)), (language, pattern)
        assert card_sheet.render_sheet("a4", language).startswith(b"%PDF"), language
        assert card_mesh.readme(language).strip(), language
    names = i18n.zone_names()
    assert set(names) == set(LANGUAGES)
    assert all(set(names[language]) == set(names[DEFAULT_LANGUAGE]) for language in LANGUAGES)
    assert set(push.GREETING) == set(LANGUAGES)


def test_unknown_languages_fall_back_to_english() -> None:
    assert normalise(None) == "en" and normalise("xx") == "en" and normalise("pt") == "pt"


def test_languages_have_a_direction() -> None:
    assert direction("ar") == "rtl" and direction("en") == "ltr" and direction(None) == "ltr"
