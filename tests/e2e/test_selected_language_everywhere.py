"""Pick a language once, and every page AND every template opens in it.

The requirement in the user's words (2026-09-22): "the language of the whole
webpages and the default language [of] the whole opened templates [should]
follow the language selected by the user."

Two nouns, and the word between them is what keeps this honest:

  webpages   the shell — nav, buttons, form labels, direction. Follows the
             selection, always. There is nothing of the user's in it.
  templates  the CV. Follows the selection as its DEFAULT — what a template
             opens in when the visitor has no document of their own yet.
             A résumé they have already typed into keeps its own language,
             because by then the language is theirs, not a default.

Everything here is one browser context that selects العربية exactly once, on
the landing page, the way a visitor does — then never mentions language again.
Every later assertion is about something the app decided on its own.

Runs on `deployed_server` (SERVER_STORE=0): that is production's configuration,
where the document lives in the browser and the seed is all the server has.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

from app.labels import ui_t
from tests import samples

pytestmark = pytest.mark.e2e

AR_NAME = samples.ARABIC["name"]
EN_NAME = samples.ENGLISH["name"]
#: Templates put the given and family name in separate elements, so a frame's
#: textContent reads "ليلىخليل" with no space in it. Matching one token is
#: what makes these assertions about the LANGUAGE rather than about a
#: layout's choice of markup.
AR_FIRST = AR_NAME.split()[0]

#: Shell strings, taken from the catalogue rather than spelled out — a
#: translation that changes must not need this file edited, and a msgid that
#: loses its translation must fail here rather than silently read English.
AR = {s: str(ui_t(s, "ar")) for s in
      ("Templates", "Build my résumé", "Download", "Full name")}


@pytest.fixture()
def arabic_visitor(browser, deployed_server):
    """A new visitor who selects العربية once, on the landing page."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 950})
    pg = ctx.new_page()
    pg.set_default_timeout(20_000)
    pg.goto(deployed_server.url + "/")
    pg.click('.lang-switch a[lang="ar"]')
    yield pg
    ctx.close()


def _doc(page, selector="#preview-frame"):
    return page.frame_locator(selector).locator("html")


# ------------------------------------------------------------- the webpages

def test_every_shell_page_is_in_the_selected_language(arabic_visitor, deployed_server):
    pg = arabic_visitor
    for path, marker in (("/", AR["Build my résumé"]),
                         ("/templates", AR["Templates"]),
                         ("/account/sign-up", AR["Build my résumé"])):
        pg.goto(deployed_server.url + path)
        assert pg.locator("html").get_attribute("dir") == "rtl", path
        assert pg.locator("html").get_attribute("lang") == "ar", path
        expect(pg.locator("body")).to_contain_text(marker)


def test_the_builder_form_is_in_the_selected_language(arabic_visitor, deployed_server):
    """The builder generates its form in the browser from a table the page
    ships, so its labels are the one part of the shell a server-side render
    cannot prove."""
    arabic_visitor.goto(deployed_server.url + "/builder")
    expect(arabic_visitor.locator("body")).to_contain_text(AR["Full name"])
    expect(arabic_visitor.locator("body")).to_contain_text(AR["Download"])


# ------------------------------------------------------------- the templates

def test_the_showcased_templates_are_in_the_selected_language(arabic_visitor, deployed_server):
    """The landing hero and the gallery cards. These are a demonstration of a
    layout, so they follow the reader with nothing else to consider."""
    pg = arabic_visitor
    pg.goto(deployed_server.url + "/")
    expect(pg.locator("iframe").first).to_be_visible()
    expect(pg.frame_locator("iframe >> nth=0").locator(".tpl")).to_contain_text(AR_FIRST)

    pg.goto(deployed_server.url + "/templates")
    cards = pg.locator(".card-grid iframe")
    assert cards.count() >= 6
    for i in range(6):
        frame = pg.frame_locator(".card-grid iframe >> nth=%d" % i)
        expect(frame.locator(".tpl")).to_contain_text(AR_FIRST)


def test_a_template_opened_from_the_gallery_opens_in_the_selected_language(
        arabic_visitor, deployed_server):
    """"Use this" is how a visitor actually arrives at the builder."""
    pg = arabic_visitor
    pg.goto(deployed_server.url + "/templates")
    pg.locator(".use-btn").first.click()
    pg.wait_for_url("**/builder")

    expect(pg.locator("#f_name")).to_have_value(AR_NAME)
    expect(pg.locator("#f_lang")).to_have_value("ar")
    assert _doc(pg).get_attribute("dir") == "rtl"


def test_switching_template_in_the_drawer_keeps_the_selected_language(
        arabic_visitor, deployed_server):
    """The drawer minis render the document in this browser, one iframe each.
    A template switch must not be a way back into English."""
    pg = arabic_visitor
    pg.goto(deployed_server.url + "/builder")
    pg.click("#open-drawer")
    mini = pg.locator("#drawer-body iframe[data-mini]").first
    expect(mini).to_be_visible()
    expect(pg.frame_locator("#drawer-body iframe[data-mini] >> nth=0")
             .locator(".tpl")).to_contain_text(AR_FIRST)

    pg.locator("#drawer-body .mini").first.click()
    assert _doc(pg).get_attribute("dir") == "rtl"


# ------------------------------------------- default, not "overwrite yours"

def test_a_resume_already_typed_into_keeps_its_own_language(
        page, deployed_server):
    """The line the word "default" draws.

    This visitor has an English CV they have typed into. Selecting العربية
    translates the app around it — nav, buttons, form labels, direction — and
    leaves the DOCUMENT alone: the content is English, and Arabic headings
    over English text would be worse than the mixed pair the user chose. The
    `Résumé language` control in Basics is how they change it, deliberately.
    """
    page.goto(deployed_server.url + "/builder")
    page.fill("#f_name", EN_NAME)
    expect(page.locator("#save-state")).to_have_text("Saved")

    page.goto(deployed_server.url + "/lang/ar?next=/builder")

    assert page.locator("html").get_attribute("dir") == "rtl", "the app switched"
    expect(page.locator("body")).to_contain_text(AR["Full name"])
    expect(page.locator("#f_name")).to_have_value(EN_NAME)
    assert _doc(page).get_attribute("dir") == "ltr", "the document is theirs"
