# SPDX-License-Identifier: AGPL-3.0-only
"""Every language neVus speaks says the same things: same keys, same placeholders, everywhere."""

from __future__ import annotations

import re

import pytest

from nevus.api import push
from nevus.languages import DEFAULT_LANGUAGE, LANGUAGES, normalise
from nevus.notify import calendar, email, webhooks
from nevus.reports import i18n

CATALOGUES = {
    "reports": i18n.TEXT,
    "email": email.TEXT,
    "calendar": calendar.TEXT,
    "webhooks": webhooks.TEXT,
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


def test_months_zone_names_and_the_push_greeting_cover_every_language() -> None:
    assert set(i18n.MONTHS) == set(LANGUAGES) and all(len(months) == 12 for months in i18n.MONTHS.values())
    names = i18n.zone_names()
    assert set(names) == set(LANGUAGES)
    assert all(set(names[language]) == set(names[DEFAULT_LANGUAGE]) for language in LANGUAGES)
    assert set(push.GREETING) == set(LANGUAGES)


def test_unknown_languages_fall_back_to_english() -> None:
    assert normalise(None) == "en" and normalise("xx") == "en" and normalise("pt") == "pt"
