"""Phase 6: the app shell's interface language.

WHAT THIS PROTECTS

    Two languages live in this app and they are deliberately independent:

        the DOCUMENT language   resume["lang"]        what the resume says
        the INTERFACE language  the ui_lang cookie    what the reader prefers

    Editing an English resume from an Arabic interface is an ordinary case, so
    the two must be able to disagree - and the failure if they are wired
    together is silent: a level word picked in an Arabic UI would land in an
    English resume and be printed on the page.

    The shell has no golden gate (it is not a fixed-size canvas), so the
    English-is-unchanged guarantee rests on the same property phase 3 used: the
    msgid IS the English string, so `t()` is the identity in English.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest

from app import create_app
from app.i18n import COOKIE, UI_LANGS, dir_for, normalise
from app.labels import (
    LANGUAGE_LEVELS,
    SKILL_LEVELS,
    _AR,
    _key,
    _UI_AR,
    levels_for,
    ui_catalogue,
    ui_t,
)
from app.schema import LEVEL_DOTS

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "app" / "templates"
SHELL = ["base.html", "landing.html", "gallery.html", "builder.html"]
BUILDER_JS = ROOT / "app" / "static" / "js" / "builder.js"
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"

# `t('...')` / `t("...")` in a shell template, and `T("...")` in builder.js.
T_CALL = re.compile(r"""(?<![\w.])t\(\s*(?:"([^"]*)"|'([^']*)')\s*\)""")
JS_T_CALL = re.compile(r"""(?<![\w.])T\(\s*(?:"([^"]*)"|'([^']*)')\s*\)""")


def _msgids():
    out = {}
    for name in SHELL:
        src = (TPL / name).read_text(encoding="utf-8")
        for m in T_CALL.finditer(src):
            out.setdefault(m.group(1) if m.group(1) is not None else m.group(2), []).append(name)
    src = BUILDER_JS.read_text(encoding="utf-8")
    for m in JS_T_CALL.finditer(src):
        out.setdefault(m.group(1) if m.group(1) is not None else m.group(2), []).append("builder.js")
    return out


MSGIDS = _msgids()


@pytest.fixture()
def client():
    return create_app().test_client()


def test_the_shell_actually_uses_the_catalogue():
    """A guard on the guards: if the scan finds nothing, the rest pass
    vacuously."""
    assert len(MSGIDS) >= 100, f"only {len(MSGIDS)} shell msgids found"


def test_english_returns_the_msgid_verbatim():
    """The whole English-safety argument for the shell, as for the documents.

    Compared after unescaping, because `ui_t` returns Markup carrying the
    HTML-escaped form: "Modern & ATS-friendly" comes back as
    "Modern &amp; ATS-friendly", which is the same text and the same bytes the
    template held before phase 6.
    """
    for msgid in MSGIDS:
        assert html.unescape(str(ui_t(msgid, "en"))) == msgid, msgid


def test_every_shell_msgid_has_an_arabic_string():
    missing = sorted(m for m in MSGIDS
                     if m not in _UI_AR and _key(m) not in _UI_AR and _key(m) not in _AR)
    assert not missing, (
        "shell strings with no Arabic (they render English inside an Arabic "
        f"interface): {[(m, MSGIDS[m][:2]) for m in missing]}")


def test_builder_js_strings_survive_the_client_side_fold():
    """builder.js looks its strings up in a table keyed by the FOLDED msgid.

    The two catalogues behind that table are cased differently - `_UI_AR` holds
    "Full name" as written, `_AR` holds "contact" folded - so a table built from
    either alone silently misses half its entries. That shipped once: the
    builder's Contact section stayed English while Basics translated.
    """
    table = ui_catalogue("ar")
    src = BUILDER_JS.read_text(encoding="utf-8")
    missing = sorted({(m.group(1) or m.group(2)) for m in JS_T_CALL.finditer(src)
                      if _key(m.group(1) or m.group(2)) not in table})
    assert not missing, f"builder.js strings absent from the shipped table: {missing}"


def test_english_ships_no_translation_table():
    """The msgid IS the English string, so an identity table would only be a
    second place for English to drift."""
    assert ui_catalogue("en") == {}
    assert ui_catalogue("ar")


# --- the two languages must be able to disagree ---------------------------

def test_interface_language_does_not_touch_the_document(client):
    """An Arabic interface must not relabel an English resume.

    The English résumé is written HERE rather than assumed. Without this the
    test passed in a full run and failed when run alone — it needed an earlier
    test to have left a document behind, and when none had, the seed rule
    (session 2026-09-16) created an ARABIC one from the `ar` cookie, so the
    level words came back Arabic and the assertion below fired.

    Both outcomes were correct behaviour. The test simply never stated the
    premise its own name depends on: there has to BE an English resume for an
    Arabic interface to leave alone. `tests/conftest.py` already wipes the rate
    limits and the user table per test for exactly this reason - the résumé
    file is the one piece of shared state that was left implicit.
    """
    from app import store
    from tests import samples

    client.set_cookie(COOKIE, "ar")
    store.save_resume(samples.ENGLISH)
    page = client.get("/builder").get_data(as_text=True)
    assert 'lang="ar" dir="rtl"' in page          # the shell mirrored
    payload = json.loads(re.search(
        r'<script id="i18n-data" type="application/json">(.*?)</script>',
        page, re.S).group(1))
    # ...but the level words follow the RESUME, which is English
    assert payload["levels"]["skill"] == SKILL_LEVELS["en"]


def test_level_words_follow_the_resume_not_the_reader():
    """Whatever the user picks is STORED and printed, so it must match the
    document's language, not the interface's."""
    assert levels_for("ar")["skill"] == SKILL_LEVELS["ar"]
    assert levels_for("en")["skill"] == SKILL_LEVELS["en"]
    assert levels_for("klingon")["skill"] == SKILL_LEVELS["en"]


def test_every_offered_skill_level_maps_to_a_dot_count():
    """The builder used to offer skill and LANGUAGE levels in one list of
    eight, so a skill could be set to "Fluent" - a word LEVEL_DOTS does not
    map, and which is not "unrated" either, so the macros drew five dots with
    zero filled beside it. Separate lists make that unreachable from the UI.
    """
    for lang, words in SKILL_LEVELS.items():
        unmapped = [w for w in words if _key(w) not in LEVEL_DOTS]
        assert not unmapped, f"{lang}: skill levels with no dot count: {unmapped}"
    for lang, words in LANGUAGE_LEVELS.items():
        overlap = set(words) & set(SKILL_LEVELS[lang]) - {"Basic", "أساسي"}
        assert not overlap, f"{lang}: level word in both lists: {overlap}"


# --- the cookie -----------------------------------------------------------

def test_switching_language_sets_the_cookie_and_returns_the_reader(client):
    r = client.get("/lang/ar?next=/builder")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/builder")
    assert f"{COOKIE}=ar" in r.headers.get("Set-Cookie", "")


def test_an_unknown_language_falls_back_rather_than_being_trusted(client):
    """The cookie is user-editable input like any other."""
    assert normalise("klingon") == "en"
    assert normalise(None) == "en"
    client.set_cookie(COOKIE, "klingon")
    assert 'lang="en" dir="ltr"' in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize("bad", ["https://evil.example.com", "//evil.example.com"])
def test_the_switch_refuses_an_off_site_redirect(client, bad):
    """An open redirect is worth refusing even in a local single-user tool,
    because the habit is what carries into a deployed one."""
    r = client.get(f"/lang/en?next={bad}")
    assert r.headers["Location"] in ("/", "http://localhost/")


def test_dir_is_derived_not_guessed():
    assert dir_for("ar") == "rtl"
    assert all(dir_for(x) in ("ltr", "rtl") for x in UI_LANGS)


# --- the shell mirrors ----------------------------------------------------

def test_app_css_has_no_physical_directional_property():
    """The shell mirrors on `dir` alone, which only works if every rule is
    logical. A `margin-left` added later pins one element to the wrong side and
    nothing raises."""
    css = APP_CSS.read_text(encoding="utf-8")
    # ignore the RTL block's own overrides, which are direction-scoped already
    body = css.split("/* ---------------------------------------------------------------------------\n   RTL.")[0]
    offenders = []
    for prop in ("padding-left", "padding-right", "margin-left", "margin-right",
                 "border-left", "border-right", "left", "right"):
        for m in re.finditer(r"(?<![\w-])" + prop + r"\s*:", body):
            offenders.append(f"{prop}: at char {m.start()}")
    for m in re.finditer(r"float\s*:\s*(left|right)\b", body):
        offenders.append("float: " + m.group(1))
    assert not offenders, f"app.css keeps physical directional rules: {offenders}"


@pytest.mark.parametrize("page", ["/", "/templates", "/builder"])
def test_every_page_renders_in_both_languages(client, page):
    for lang in UI_LANGS:
        client.set_cookie(COOKIE, lang)
        r = client.get(page)
        assert r.status_code == 200, f"{page} in {lang}"
        assert f'lang="{lang}" dir="{dir_for(lang)}"' in r.get_data(as_text=True)
