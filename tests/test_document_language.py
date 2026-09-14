"""The builder's control for the DOCUMENT's language.

WHAT THIS PROTECTS

    `resume["lang"]` drives everything downstream - `dir`, the label
    catalogue, the Arabic font sheet, which of the four Word masters the
    export takes - and until this control existed it was reachable only by
    hand-editing `data/resume.json`. It is in the schema, every layer beneath
    it has been bilingual since phase 7, and there was no way to set it from
    the UI. So a bilingual user could type Arabic into the builder and the
    résumé still rendered `dir="ltr"` with English section headings under it:
    not a crash, the documented absent-means-English degrade, but the last
    English-only assumption left in the product.

    Two things here are easy to get wrong and silent when wrong.

    THE CONTROL MUST NOT READ THE INTERFACE LANGUAGE. The `ui_lang` cookie is
    the reader's preference and is deliberately independent (app/i18n.py).
    Wiring the control to it would look right in every case where the two
    agree - which is most of them - and would put an Arabic level word into an
    English résumé for the bilingual user the independence exists for.

    THE REMAP IS POSITIONAL. Changing the language offers to translate the
    level words already stored, and the client does that by index: `Expert` is
    `SKILL_LEVELS["en"][0]`, so it becomes `SKILL_LEVELS["ar"][0]`. That is
    only correct while the two lists are the same length and in the same
    order, which nothing in the data structure enforces. Reordering one list
    would silently demote every stored level. Hence the invariant tests below.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import create_app
from app.i18n import COOKIE
from app.labels import LANGUAGE_LEVELS, SKILL_LEVELS, _key, all_levels, levels_for
from app.schema import LEVEL_DOTS, SUPPORTED_LANGS, lang_of
from app.store import load_resume, save_resume

ROOT = Path(__file__).resolve().parent.parent
BUILDER_JS = (ROOT / "app" / "static" / "js" / "builder.js").read_text(encoding="utf-8")


def _code_only(src: str) -> str:
    """builder.js with its comments removed.

    The file explains the two languages at length, so `ui_lang` appears in
    prose several times. A guard that a word is ABSENT has to look at the code
    or it can never fail."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


BUILDER_CODE = _code_only(BUILDER_JS)


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.fixture()
def restore_resume():
    """Put the session's résumé back: these tests write to the store."""
    before = load_resume()
    yield
    save_resume(before)


def _payload(page: str) -> dict:
    return json.loads(re.search(
        r'<script id="i18n-data" type="application/json">(.*?)</script>',
        page, re.S).group(1))


# --- the invariant the client-side remap rests on -------------------------

@pytest.mark.parametrize("vocab", [SKILL_LEVELS, LANGUAGE_LEVELS])
def test_the_two_languages_offer_the_same_number_of_levels(vocab):
    sizes = {lang: len(words) for lang, words in vocab.items()}
    assert len(set(sizes.values())) == 1, f"ragged vocabularies: {sizes}"


def test_skill_levels_are_index_aligned_across_languages():
    """`Expert` is index 0, so it translates to index 0 - and index 0 has to
    mean the same strength in both languages, or the remap silently regrades
    every skill the user picked."""
    en, ar = SKILL_LEVELS["en"], SKILL_LEVELS["ar"]
    for i, (a, b) in enumerate(zip(en, ar)):
        assert LEVEL_DOTS[_key(a)] == LEVEL_DOTS[_key(b)], (
            f"index {i}: {a} is {LEVEL_DOTS[_key(a)]} dots, {b} is {LEVEL_DOTS[_key(b)]}")


def test_skill_levels_are_ordered_strongest_first():
    """The alignment test above only proves the two lists agree with each
    other. This one pins the order itself, so a reordering has to be a
    deliberate two-file change rather than a slip in one."""
    for lang, words in SKILL_LEVELS.items():
        dots = [LEVEL_DOTS[_key(w)] for w in words]
        assert dots == sorted(dots, reverse=True), f"{lang}: {words} -> {dots}"


def test_language_levels_translate_to_a_distinct_word():
    """A remap that produced the word it started from would be a no-op the
    user was asked to approve."""
    for i, (a, b) in enumerate(zip(LANGUAGE_LEVELS["en"], LANGUAGE_LEVELS["ar"])):
        assert a != b, f"index {i} is the same word in both languages: {a!r}"


# --- what the page ships --------------------------------------------------

def test_all_levels_covers_every_document_language():
    table = all_levels()
    assert set(table) == set(SUPPORTED_LANGS)
    for lang in SUPPORTED_LANGS:
        assert table[lang] == levels_for(lang)


def test_the_builder_ships_both_vocabularies(client):
    """The control re-offers the other language's words without a reload, so
    both lists have to be on the page before the switch happens."""
    payload = _payload(client.get("/builder").get_data(as_text=True))
    assert payload["levels_by_lang"]["en"]["skill"] == SKILL_LEVELS["en"]
    assert payload["levels_by_lang"]["ar"]["skill"] == SKILL_LEVELS["ar"]
    assert payload["levels_by_lang"]["ar"]["language"] == LANGUAGE_LEVELS["ar"]
    assert payload["doc_langs"] == list(SUPPORTED_LANGS)


def test_the_shipped_document_language_follows_the_file(client, restore_resume):
    resume = load_resume()
    resume["lang"] = "ar"
    save_resume(resume)
    payload = _payload(client.get("/builder").get_data(as_text=True))
    assert payload["doc_lang"] == "ar"
    assert payload["levels"]["skill"] == SKILL_LEVELS["ar"]


def test_an_absent_lang_is_shipped_as_english(client, restore_resume):
    """Absent-means-English is the degrade path that kept every pre-bilingual
    résumé working. The control has to show `English`, not a blank."""
    resume = load_resume()
    resume.pop("lang", None)
    save_resume(resume)
    assert lang_of(resume) == "en"
    payload = _payload(client.get("/builder").get_data(as_text=True))
    assert payload["doc_lang"] == "en"


def test_the_control_ignores_the_interface_language(client, restore_resume):
    """THE SHARP CASE: an English document read through an Arabic interface.

    The bilingual user this app is for applies to English-speaking employers
    from an Arabic UI. The form's LABELS follow the reader; the level words
    and the document language must not, because they are stored in the file
    and printed on the page."""
    resume = load_resume()
    resume.pop("lang", None)
    save_resume(resume)
    client.set_cookie(COOKIE, "ar")
    payload = _payload(client.get("/builder").get_data(as_text=True))
    assert payload["doc_lang"] == "en"
    assert payload["levels"]["skill"] == SKILL_LEVELS["en"]


# --- the control exists, and is wired to the document ---------------------

def test_the_basics_section_offers_the_control():
    assert 'F("lang"' in BUILDER_JS, "no `lang` field in the form spec"
    assert 'type: "doclang"' in BUILDER_JS
    assert "data-doc-lang" in BUILDER_JS


def test_changing_it_writes_the_document_not_the_cookie():
    """The interface switcher is a link to /lang/<code>; this control must
    never become a second one. A cookie write from the builder would tie the
    two languages together in exactly the place phase 6 kept them apart."""
    assert 'setPath(data, "lang"' in BUILDER_CODE
    assert "ui_lang" not in BUILDER_CODE
    assert "document.cookie" not in BUILDER_CODE


def test_the_remap_is_offered_rather_than_applied():
    """A level word is user content that gets printed. `LEVEL_DOTS` maps both
    vocabularies, so declining leaves a working résumé - the words just read
    in the other script. Rewriting them unasked would not."""
    assert "window.confirm" in BUILDER_JS
    assert "levelRemapPlan" in BUILDER_JS
