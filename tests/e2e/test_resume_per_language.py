"""Regression for the 2026-10-07 report: on localhost, Arabic templates
"sometimes lose their Arabic details" and "sometimes show English text
instead of Arabic".

ROOT CAUSE (two, found by reproducing it in Chromium):

  1. The browser kept ONE résumé ("cvstand:resume") for both languages, and
     the page's seed - the demo CV in the chosen language - was used only
     while that slot was empty. So what the Arabic builder showed depended on
     what had last been done in English: one English edit, and every Arabic
     template rendered the English text; an English edit after an Arabic one
     overwrote the only copy of the Arabic CV. "Sometimes", because it needed
     an edit (or a download) in the other language first.
  2. The service worker served /static/ code cache-first under a VERSION that
     was to be bumped by hand and never was (2026-09-14 on), so a browser that
     had loaded the site once kept running that day's builder.js - from
     before the document followed the header language. Fresh profiles
     (incognito) did not have it, which is why it came and went.
     tests/test_pwa.py holds the request-level half of (2).

Every test runs on `deployed_server` (SERVER_STORE=0): `run.py`'s default,
the live-like mode the report came from.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

from tests import samples

pytestmark = pytest.mark.e2e

AR_NAME = samples.ARABIC["name"]
EN_NAME = samples.ENGLISH["name"]


def _builder(page, server, lang):
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()


def _preview(page):
    return page.frame_locator("#preview-frame").locator(".tpl")


def _slot(page, lang):
    raw = page.evaluate(f"() => localStorage.getItem('cvstand:resume:{lang}')")
    return json.loads(raw) if raw else None


def _saved(page):
    expect(page.locator("#save-state")).to_have_text(
        "Saved" if page.locator("html").get_attribute("lang") == "en" else "تم الحفظ")


def test_an_english_edit_does_not_put_english_text_in_the_arabic_builder(page, deployed_server):
    """Symptom 1, as reported: English text inside the Arabic templates."""
    _builder(page, deployed_server, "en")
    page.fill("#f_title", "Product Designer")
    _saved(page)

    _builder(page, deployed_server, "ar")
    expect(page.locator("#f_name")).to_have_value(AR_NAME)
    expect(_preview(page)).not_to_contain_text("Product Designer")
    expect(_preview(page)).not_to_contain_text(EN_NAME.split()[0])


def test_an_english_edit_does_not_erase_the_arabic_cv(page, deployed_server):
    """Symptom 2, as reported: the Arabic details lost. The NAME is edited
    because every template prints it (modern-t1 has no job title); it is
    checked by one token, since several templates split a name in two."""
    mine_ar, mine_en = "سارة الحربي", "Lina Haddad"
    _builder(page, deployed_server, "ar")
    page.fill("#f_name", mine_ar)
    _saved(page)

    _builder(page, deployed_server, "en")
    expect(page.locator("#f_name")).to_have_value(EN_NAME)
    page.fill("#f_name", mine_en)
    _saved(page)

    _builder(page, deployed_server, "ar")
    expect(page.locator("#f_name")).to_have_value(mine_ar)
    expect(_preview(page)).to_contain_text("الحربي")
    expect(_preview(page)).not_to_contain_text("Haddad")
    assert _slot(page, "ar")["name"] == mine_ar
    assert _slot(page, "en")["name"] == mine_en


def test_each_language_survives_a_reload_and_a_new_tab(browser, deployed_server):
    ctx = browser.new_context()
    try:
        a = ctx.new_page()
        _builder(a, deployed_server, "ar")
        a.fill("#f_title", "مديرة فنية")
        _saved(a)
        a.reload()
        expect(a.locator("#f_title")).to_have_value("مديرة فنية")
        b = ctx.new_page()                       # a new tab, same browser
        _builder(b, deployed_server, "ar")
        expect(b.locator("#f_title")).to_have_value("مديرة فنية")
    finally:
        ctx.close()


def test_a_fresh_profile_gets_each_languages_own_demo(browser, deployed_server):
    """Incognito: nothing stored, so each language opens its own demo CV."""
    ctx = browser.new_context()
    try:
        p = ctx.new_page()
        _builder(p, deployed_server, "ar")
        expect(p.locator("#f_name")).to_have_value(AR_NAME)
        _builder(p, deployed_server, "en")
        expect(p.locator("#f_name")).to_have_value(EN_NAME)
    finally:
        ctx.close()


@pytest.mark.parametrize("written_in,doc_lang_said", [("en", "ar"), ("ar", "ar"), ("en", "en")])
def test_the_old_shared_slot_moves_to_the_language_it_is_written_in(
        page, deployed_server, written_in, doc_lang_said):
    """A browser that used the app before the fix holds "cvstand:resume". It
    moves once, by its TEXT - the old boot code stamped `lang` with whatever
    the header said, so an English CV opened once in Arabic says "ar"."""
    doc = dict(samples.ENGLISH if written_in == "en" else samples.ARABIC,
               title="LEGACY-MARK", lang=doc_lang_said)
    page.goto(deployed_server.url + "/")
    page.evaluate("d => localStorage.setItem('cvstand:resume', JSON.stringify(d))", doc)

    _builder(page, deployed_server, "ar")
    assert page.evaluate("() => localStorage.getItem('cvstand:resume')") is None
    assert _slot(page, written_in)["title"] == "LEGACY-MARK"
    expected_ar_title = "LEGACY-MARK" if written_in == "ar" else samples.ARABIC["title"]
    expect(page.locator("#f_title")).to_have_value(expected_ar_title)


def test_the_old_slot_never_overwrites_a_document_already_there(page, deployed_server):
    page.goto(deployed_server.url + "/")
    page.evaluate("""() => {
        localStorage.setItem('cvstand:resume:ar', JSON.stringify({name: 'ليلى', title: 'الأحدث'}));
        localStorage.setItem('cvstand:resume', JSON.stringify({name: 'سارة', title: 'الأقدم'}));
    }""")
    _builder(page, deployed_server, "ar")
    expect(page.locator("#f_title")).to_have_value("الأحدث")
