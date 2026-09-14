"""Document language + direction (bilingual AR/EN, phase 1).

WHY THIS FILE EXISTS
    `lang` is deliberately OPTIONAL and absent-means-English, because every
    résumé written before bilingual support exists has no `lang` key and must
    keep validating and rendering exactly as it did. These tests pin that
    promise down, so a later tightening of the schema cannot quietly orphan an
    existing file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.rendering import document_html
from app.schema import (
    DEFAULT_LANG,
    ResumeValidationError,
    dir_of,
    dots_for,
    lang_of,
    normalize,
    validate,
)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------- back-compat

def test_the_shipped_sample_has_no_lang_key():
    """If this ever fails the rest of the back-compat tests are testing nothing."""
    assert "lang" not in SAMPLE


def test_a_resume_without_lang_still_validates():
    validate(SAMPLE)


def test_a_resume_without_lang_is_english_ltr():
    assert lang_of(SAMPLE) == "en"
    assert dir_of(SAMPLE) == "ltr"


def test_normalize_defaults_lang_and_dir():
    r = normalize({"name": "A", "title": "B"})
    assert r["lang"] == "en"
    assert r["dir"] == "ltr"


# ------------------------------------------------------------- the ar path

def test_arabic_resume_is_rtl():
    ar = dict(SAMPLE, lang="ar")
    validate(ar)
    assert lang_of(ar) == "ar"
    assert dir_of(ar) == "rtl"
    assert normalize(ar)["dir"] == "rtl"


@pytest.mark.parametrize("lang,expected_dir", [("en", "ltr"), ("ar", "rtl")])
def test_document_html_carries_lang_and_dir(lang, expected_dir):
    doc = document_html(dict(SAMPLE, lang=lang), "ats-t3")
    assert f'<html lang="{lang}" dir="{expected_dir}">' in doc


def test_unsupported_lang_is_rejected_by_the_schema():
    """An enum, not a free string: a typo must not silently render as English."""
    with pytest.raises(ResumeValidationError):
        validate(dict(SAMPLE, lang="fr"))


@pytest.mark.parametrize("bogus", ["", "  ", None, "FR", 7, []])
def test_lang_of_degrades_to_english_rather_than_raising(bogus):
    """validate() is the gate, but rendering must never 500 on a bad value —
    the same degrade-not-explode contract every other field here follows."""
    assert lang_of({"lang": bogus}) == DEFAULT_LANG
    assert dir_of({"lang": bogus}) == "ltr"


def test_lang_is_case_and_space_insensitive():
    assert lang_of({"lang": "  AR "}) == "ar"


# ------------------------------------------------------------- level words

@pytest.mark.parametrize("english,arabic,dots", [
    ("Expert", "خبير", 5),
    ("Advanced", "متقدم", 4),
    ("Proficient", "متمكن", 3),
    ("Foundational", "أساسي", 2),
])
def test_arabic_level_words_resolve_to_the_same_dots(english, arabic, dots):
    """Additive, not a replacement — which is why no stored résumé needs
    migrating when a user switches a document to Arabic."""
    assert dots_for(english) == dots
    assert dots_for(arabic) == dots


def test_an_unmapped_level_word_is_still_unrated_in_both_languages():
    assert dots_for("Fluent") == 0
    assert dots_for("طلاقة") == 0
