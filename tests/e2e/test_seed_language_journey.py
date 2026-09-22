"""Choosing العربية in the header must open the builder onto an ARABIC CV.

Reported from production 2026-09-22: the interface switched, the document did
not. `tests/test_builder_seed_language.py` holds the request-level half — the
seed the page ships and the file it must stop writing. This file holds the
three things only a browser can answer.

(The two halves cannot share a basename: `tests/` has no `__init__.py`, so two
modules named the same abort COLLECTION for the whole run — each passes alone
and together they do not even start.)

  1. The header link is wired to the thing that changed. The seed travels in
     `#resume-data`, but what the visitor sees is the iframe, and between the
     two sit localStorage and a re-render that a request test never runs.

  2. The production shape of the bug, which needs TWO visitors in one server
     process. With the seed persisted, the first request's language became the
     container's and no later visitor could change it by any means the UI
     offers. One visitor passes either way — that is why it was shipped.

  3. That a résumé you have already typed into is NOT swept away by switching
     the interface. Two languages live in this app and they are deliberately
     independent (app/i18n.py); the seed is the single exception, and it
     applies only where there is nothing to lose. A "fix" that reseeded on
     every switch would satisfy (1) by deleting the user's work.

All of it runs on `deployed_server` — SERVER_STORE=0 — because that is the
configuration the report came from and the only one where (2) is meaningful.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

from tests import samples

pytestmark = pytest.mark.e2e

STORE_KEY = "cvstand:resume"
AR_NAME = samples.ARABIC["name"]
EN_NAME = samples.ENGLISH["name"]
MINE = "Zahra Al-Mansouri"

#: The header's interface switcher (app/templates/base.html).
#:
#: It is NOT on /builder. The builder blanks the whole site header
#: (`{% block chrome %}{% endblock %}`) to give the preview the screen, so the
#: language is chosen on a shell page and carried in by the cookie — which is
#: the journey the report describes ("when the Arabic language is selected
#: THEN the user reaches the builder page") and therefore the one tested here.
AR_LINK = '.lang-switch a[lang="ar"]'


def _open_page(browser):
    pg = browser.new_context(viewport={"width": 1440, "height": 950}).new_page()
    pg.set_default_timeout(20_000)
    return pg


def _doc_html(page):
    """The PREVIEW's own <html>, not the shell's.

    The shell follows the cookie and would read `rtl` either way, so a test
    that looked at the outer page would pass while the résumé rendered
    left-to-right — the exact bug being chased.
    """
    return page.frame_locator("#preview-frame").locator("html")


def _stored(page):
    raw = page.evaluate(
        "() => { try { return localStorage.getItem('%s'); } catch (_) { return null; } }"
        % STORE_KEY)
    return json.loads(raw) if raw else None


# --------------------------------------------------------------- the report

def test_choosing_arabic_then_entering_the_builder_gives_an_arabic_document(page, deployed_server):
    """The reported journey, click for click, with nothing typed yet."""
    page.goto(deployed_server.url + "/")
    page.click(AR_LINK)
    assert page.locator("html").get_attribute("dir") == "rtl", "the shell switched"

    page.click('.site-header a.btn-primary')
    page.wait_for_url("**/builder")

    expect(page.locator("#f_name")).to_have_value(AR_NAME)
    assert _doc_html(page).get_attribute("dir") == "rtl"
    assert _doc_html(page).get_attribute("lang") == "ar"


def test_a_later_visitor_is_not_stuck_with_the_first_ones_language(browser, deployed_server):
    """THE production bug, in the shape it actually had.

    Visitor A arrives in English — on Railway that is whoever, or whatever,
    hit the container first. Visitor B arrives reading Arabic. Before the fix
    B got A's English sample, because A's request had written it to
    `data/resume.json` and the seed was never consulted again.

    Neither browser context can see the other's localStorage, so anything
    shared here came through the SERVER.
    """
    a = _open_page(browser)
    b = _open_page(browser)
    try:
        a.goto(deployed_server.url + "/builder")
        expect(a.locator("#f_name")).to_have_value(EN_NAME)

        b.goto(deployed_server.url + "/lang/ar?next=/builder")
        expect(b.locator("#f_name")).to_have_value(AR_NAME)
        assert _doc_html(b).get_attribute("dir") == "rtl"

        # ...and A, still reading English, is unaffected by B arriving.
        a.reload()
        expect(a.locator("#f_name")).to_have_value(EN_NAME)
    finally:
        a.context.close()
        b.context.close()


# ------------------------------------------------ what must NOT be swept away

def test_a_resume_you_have_typed_into_survives_the_switch(page, deployed_server):
    """The CONTENT survives; the language follows.

    This asserted the opposite until 2026-09-22, when the `Résumé language`
    control was removed as redundant: with no control, a document that did not
    follow the header would be one whose language could never be changed. What
    must never move is the text the user typed — that is what is asserted
    here, and `tests/e2e/test_language_switch.py` holds the rest.
    """
    page.goto(deployed_server.url + "/builder")
    page.fill("#f_name", MINE)
    expect(page.locator("#save-state")).to_have_text("Saved")

    page.goto(deployed_server.url + "/lang/ar?next=/builder")

    expect(page.locator("#f_name")).to_have_value(MINE)
    assert _stored(page)["name"] == MINE
    assert page.locator("html").get_attribute("dir") == "rtl", "the app switched"
    assert _doc_html(page).get_attribute("dir") == "rtl", "and the document with it"
