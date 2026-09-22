"""The interface language must hold ACROSS pages, not merely on each one.

WHAT THIS ADDS THAT THE EXISTING FILES DO NOT

    `test_ui_language.py::test_every_page_renders_in_both_languages` already
    checks each page in isolation, one request at a time. `test_journey_ar.py`
    drives one page deeply. Neither walks a visitor THROUGH the three public
    pages in a single browser session, which is where an interface language
    actually gets lost: the cookie is set on `/`, and `/templates` or
    `/builder` is then reached by a link, a back-button restore, or a
    bfcache hit that never re-renders the shell.

    A per-page test cannot see that. It issues a fresh request each time and
    so proves only that the renderer CAN produce Arabic — never that a person
    who chose Arabic on the landing page is still reading Arabic two clicks
    later.

THE LINE THIS FILE DOES NOT CROSS

    "Everything matches the interface language" is true of the SHELL and of
    the SHOWCASE cards, and it is deliberately false of the résumé in the
    builder's live preview, which follows the document's own `resume["lang"]`
    (app/i18n.py, tests/test_showcase_language.py). The sharp case is an
    Arabic CV read through an English interface: the CV must stay Arabic.

    So the showcase assertions here seed a document in the OPPOSITE language
    and still demand the cards follow the reader. That is the same rule stated
    from the other side, and it is what makes these tests capable of failing.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

from app.i18n import COOKIE, dir_for
from tests import samples

pytestmark = pytest.mark.e2e

#: The three pages a visitor actually moves between, in the order they do it.
JOURNEY = ["/", "/templates", "/builder"]


@pytest.fixture()
def ui_lang(page, live_server):
    """Set the interface language the way the switcher sets it."""
    def _set(code: str):
        page.context.add_cookies([{
            "name": COOKIE, "value": code, "url": live_server.url,
        }])
    return _set


def _shell(page):
    return page.locator("html")


# ---------------------------------------------- the shell, across the journey

@pytest.mark.parametrize("code", ["en", "ar"])
def test_the_interface_language_survives_the_whole_journey(
        page, live_server, ui_lang, code):
    """Chosen once on the landing page, still in force on the builder.

    Asserted on `<html dir>` and `<html lang>` rather than on any string,
    because those two attributes are what every logical CSS rule in app.css
    resolves against (base.html:6). A page that renders Arabic text inside an
    `ltr` shell is the failure this catches, and a string check would miss it.
    """
    ui_lang(code)
    for path in JOURNEY:
        page.goto(live_server.url + path)
        expect(_shell(page)).to_have_attribute("lang", code)
        expect(_shell(page)).to_have_attribute("dir", dir_for(code))


@pytest.mark.parametrize("code", ["en", "ar"])
def test_reaching_the_next_page_by_LINK_keeps_the_language(
        page, live_server, ui_lang, code):
    """The same three pages, but navigated the way a person navigates.

    `page.goto` re-issues a full request every time and so cannot observe a
    language lost to a client-side navigation or a restored page. Clicking is
    the path a visitor takes, and it is the one the previous test does not
    cover.
    """
    ui_lang(code)
    page.goto(live_server.url + "/")

    page.locator('a[href="/templates"]').first.click()
    page.wait_for_url("**/templates")
    expect(_shell(page)).to_have_attribute("lang", code)
    expect(_shell(page)).to_have_attribute("dir", dir_for(code))

    page.go_back()
    page.wait_for_url(live_server.url + "/")
    expect(_shell(page)).to_have_attribute("lang", code)


# ------------------------------------- the showcase cards follow the READER

@pytest.mark.parametrize("code,other", [("ar", samples.ENGLISH),
                                        ("en", samples.ARABIC)])
def test_the_showcase_cards_follow_the_reader_not_the_stored_document(
        page, live_server, ui_lang, seed_resume, code, other):
    """The gallery's résumé cards render in the INTERFACE language.

    The stored document is seeded in the opposite language on purpose. If the
    cards ever start reading `resume["lang"]` these assertions invert, which
    is the only way this test can earn its place — a card that happens to
    agree with the document proves nothing.
    """
    seed_resume(other)
    ui_lang(code)
    page.goto(live_server.url + "/templates")

    card = page.locator("iframe").first
    card.scroll_into_view_if_needed()
    doc = page.frame_locator("iframe").first.locator("html")
    expect(doc).to_have_attribute("dir", dir_for(code))


# ------------------------------------------- the builder's DEFAULT document

@pytest.mark.parametrize("code", ["en", "ar"])
def test_a_new_resume_opens_in_the_language_the_visitor_chose(
        page, live_server, ui_lang, no_document, code):
    """The whole point of the seed fix, asserted the way a visitor meets it.

    A visitor who picked Arabic in the header and then opened the builder must
    find an Arabic document already there. This was first closed while a
    `Résumé language` control still existed in Basics — a control they might
    never notice, and whose purpose was not obvious if they did. That control
    is gone now, so the seed is not merely the convenient path to a
    correctly-languaged résumé; it is the path.

    Asserted on the PREVIEW iframe's `dir`, not the shell's: the shell has
    followed the cookie all along, so a shell assertion would pass with the
    bug still present and prove nothing.
    """
    ui_lang(code)
    page.goto(live_server.url + "/builder")

    doc = page.frame_locator("#preview-frame").locator("html")
    expect(doc).to_have_attribute("dir", dir_for(code))


def test_the_seed_never_overrides_the_CONTENT_of_a_resume_that_exists(
        page, live_server, ui_lang, seed_resume):
    """What the seed may and may not touch, after the model changed.

    This test used to assert that an Arabic document opened through an English
    interface STAYS Arabic, and said in as many words that if the résumé were
    ever made to follow the interface, "the user would watch their CV change
    language because they changed the menu".

    That is now the behaviour, asked for on 2026-09-22 when the `Résumé
    language` control was removed as redundant. The warning was not wrong — it
    is the price, and here is exactly what it costs: an Arabic CV read through
    an English interface lays its Arabic text out left-to-right under English
    headings. Two things keep that rare rather than routine: a new document is
    seeded in the chosen language, and a visitor who chose nothing is read
    from their browser's `Accept-Language`. Someone who ends up in the mixed
    state switches the header, which is now the only language control there is.

    What must STILL never happen, and is the whole of this test now: the seed
    replacing a document that exists. The language may follow the reader; the
    words may not.
    """
    seed_resume(samples.ARABIC)
    ui_lang("en")
    page.goto(live_server.url + "/builder")

    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text(samples.ARABIC["name"].split(" ", 1)[-1])
    expect(page.locator("#f_name")).to_have_value(samples.ARABIC["name"])
    # ...and the language followed the reader, which is the new model.
    expect(page.frame_locator("#preview-frame").locator("html")).to_have_attribute(
        "dir", "ltr")
