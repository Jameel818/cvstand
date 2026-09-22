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

    THE CONTROL IS GONE (2026-09-22). It let a résumé carry a language of its
    own, independent of the interface. The independence was real - a bilingual
    applicant writing an English CV from an Arabic UI - but in front of an
    actual user the control restated a choice already made in the header, and
    the user removed it.

    So the document follows the interface now, and the file has been rewritten
    around that: what used to be "the control must not read the interface
    language" is now "there is no control, and the document adopts the chosen
    language on boot". What is LOST is the Arabic-interface-English-résumé
    pair, which is no longer expressible. That is a product decision, recorded
    here rather than discovered later.

    The one guard that survives unchanged: `builder.js` still must not parse
    `document.cookie`. The language reaches it in the payload, computed once,
    server-side - two places that can disagree is how this kind of thing rots.

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


@pytest.mark.parametrize("stored", ["en", "ar", None])
def test_the_shipped_document_language_is_the_one_the_visitor_CHOSE(
        client, restore_resume, stored):
    """It used to follow the FILE. It follows the reader's choice now, and the
    parametrisation is the point: whatever `lang` the stored document carries
    — including none at all — the page ships the chosen language, because that
    is the only one the visitor can see a reason for."""
    resume = load_resume()
    resume.pop("lang", None)
    if stored:
        resume["lang"] = stored
    save_resume(resume)

    client.set_cookie(COOKIE, "ar")
    payload = _payload(client.get("/builder").get_data(as_text=True))
    assert payload["doc_lang"] == "ar"
    assert payload["levels"]["skill"] == SKILL_LEVELS["ar"]


def test_no_language_chosen_still_means_english(client, restore_resume):
    """Absent-means-English is the degrade path that kept every pre-bilingual
    résumé working, and it now hangs off `current_lang()` instead of the file.
    An English-browser visitor who has chosen nothing gets English."""
    resume = load_resume()
    resume.pop("lang", None)
    save_resume(resume)
    assert lang_of(resume) == "en"
    body = client.get("/builder", headers={"Accept-Language": "en-GB,en;q=0.9"})
    payload = _payload(body.get_data(as_text=True))
    assert payload["doc_lang"] == "en"


# --- the control is GONE, and that is the claim ---------------------------

def test_the_basics_section_no_longer_offers_a_language_control():
    """Removed 2026-09-22 as useless: it restated the choice already made in
    the header. Asserted by absence because a redundant control is the kind of
    thing that grows back — and because its removal is only safe while the
    test below holds."""
    assert 'F("lang"' not in BUILDER_JS, "the Résumé language field is back"
    assert 'type: "doclang"' not in BUILDER_JS
    assert "data-doc-lang" not in BUILDER_JS


def test_the_document_adopts_the_chosen_language_on_boot():
    """WHAT MAKES REMOVING THE CONTROL SAFE.

    A control that is gone and a language that is stuck are different things.
    Someone who wrote an English CV and then switched the header has a stored
    document in the other language and, with the control removed, no way back
    — unless the document follows. This is that line, guarded as code rather
    than as a comment, because deleting it would leave a silent trap rather
    than a visible break."""
    assert 'if ((data.lang || "en") !== docLang)' in BUILDER_CODE
    assert 'setPath(data, "lang", docLang)' in BUILDER_CODE


def test_the_builder_still_never_reads_the_cookie():
    """The language reaches the client in the PAYLOAD (`I18N.doc_lang`), which
    the server computed. That the two languages are now one does not make
    `document.cookie` the client's business: parsing it here would put the
    decision in two places that can disagree."""
    assert "ui_lang" not in BUILDER_CODE
    assert "document.cookie" not in BUILDER_CODE


def test_the_remap_is_applied_without_asking():
    """The inverse of what this asserted before, deliberately.

    The old control raised `window.confirm` because the user had just picked
    something and a level word is printed content. There is nothing to ask
    now: the remap runs on page load, where a dialog would be an ambush, and
    it is lossless — switch back and the words come back. Only values that ARE
    in the old vocabulary move; anything typed by hand is in neither list and
    is left alone."""
    assert "levelRemapPlan" in BUILDER_JS
    assert "window.confirm" not in BUILDER_CODE
