"""The language the visitor selects holds EVERYWHERE until they select the
other one themselves (user, 2026-10-08).

"On ANY page ... every page of the site ... across all pages, links, the
templates gallery, the builder, downloads, error pages, new tabs and return
visits ... Nothing may switch it automatically (not the browser language, not
a URL default, not a page's own default). Store the choice in a long-lived
cookie."

HOW IT IS STORED: one first-party cookie, `ui_lang` (app/i18n.py), set only
by /lang/<code> - the switcher's link - for a year, SameSite=Lax, path /. Every
page view renews the year (tests/test_language_cookie.py), so a returning
visitor is never quietly handed back to their browser's language.

THE ADVERSARY in every test here is the BROWSER LANGUAGE: each context
announces the OTHER language in Accept-Language (and navigator.language), so
a page that consulted it instead of the choice would flip - which is exactly
the automatic switch the user forbade. The choice is made from three
different places (landing header, gallery header, builder bar) to prove "on
ANY page".

deployed_server (SERVER_STORE=0): run.py's live-like mode and production.
"""
from __future__ import annotations

import json
import re
import time

import pytest
from playwright.sync_api import expect

from app.i18n import COOKIE

pytestmark = pytest.mark.e2e

OTHER = {"en": "ar", "ar": "en"}
LOCALE = {"en": "en-US", "ar": "ar-SA"}
DIR = {"en": "ltr", "ar": "rtl"}
#: Every page a visitor can open, with a link or by typing it. The error page
#: is a real 404 path; the preview is what the gallery's cards render.
PAGES = ["/", "/templates", "/templates?cat=modern", "/templates?cat=ats", "/builder",
         "/account/sign-in", "/account/sign-up", "/no-such-page"]


def _context(browser, against: str):
    """A browser that says it reads `against` - the language NOT chosen."""
    return browser.new_context(locale=LOCALE[against],
                               extra_http_headers={"Accept-Language": LOCALE[against]})


def _assert_page_in(page, lang, where):
    html = page.locator("html")
    assert html.get_attribute("lang") == lang, f"{where}: <html lang> is {html.get_attribute('lang')}"
    assert html.get_attribute("dir") == DIR[lang], f"{where}: dir flipped"
    current = page.locator('.lang-switch a[aria-current="true"]')
    if current.count():
        assert current.first.get_attribute("lang") == lang, f"{where}: switcher shows the other language"


def _choose(page, server, lang, on):
    """Click the switcher the visitor sees on `on` - not a URL shortcut."""
    page.goto(server.url + on)
    page.locator(f'.lang-switch a[lang="{lang}"]').first.click()
    page.wait_for_load_state("load")
    _assert_page_in(page, lang, f"right after choosing on {on}")


@pytest.mark.parametrize("on", ["/", "/templates", "/builder"])
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_the_choice_holds_on_every_page_whatever_the_browser_says(browser, deployed_server, lang, on):
    ctx = _context(browser, against=OTHER[lang])
    try:
        page = ctx.new_page()
        if on == "/builder":
            # the builder bar has its own switcher (it blanks the site header)
            page.goto(deployed_server.url + "/builder")
            page.locator(f'.lang-switch-bar a[lang="{lang}"]').click()
            page.wait_for_url(re.compile(r"/builder"))
            _assert_page_in(page, lang, "builder, right after choosing")
        else:
            _choose(page, deployed_server, lang, on)
        for path in PAGES:
            resp = page.goto(deployed_server.url + path)
            if path == "/no-such-page":
                assert resp.status == 404
                expect(page.locator("h1")).to_be_visible()
            _assert_page_in(page, lang, path)
        # what a gallery card / the hero render: the showcase in the choice
        page.goto(deployed_server.url + "/preview?template_key=modern-t1&showcase=1")
        assert page.locator("html").get_attribute("lang") == lang, "a template preview flipped"
        # the installable app names itself in the choice too
        m = json.loads(page.goto(deployed_server.url + "/manifest.webmanifest").text())
        assert m["lang"] == lang
    finally:
        ctx.close()


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_new_tabs_and_return_visits_keep_it(browser, deployed_server, lang, tmp_path):
    ctx = _context(browser, against=OTHER[lang])
    try:
        page = ctx.new_page()
        _choose(page, deployed_server, lang, "/templates")
        tab = ctx.new_page()                                   # a new tab
        tab.goto(deployed_server.url + "/")
        _assert_page_in(tab, lang, "new tab")
        state = ctx.storage_state(path=str(tmp_path / "state.json"))
        cookie = next(c for c in state["cookies"] if c["name"] == COOKIE)
        assert cookie["value"] == lang
        assert cookie["expires"] > time.time() + 300 * 86400, "not a long-lived cookie"
    finally:
        ctx.close()
    # a return visit: a fresh browser window carrying only what was stored
    back = browser.new_context(storage_state=str(tmp_path / "state.json"),
                               locale=LOCALE[OTHER[lang]],
                               extra_http_headers={"Accept-Language": LOCALE[OTHER[lang]]})
    try:
        page = back.new_page()
        for path in ("/", "/builder", "/templates"):
            page.goto(deployed_server.url + path)
            _assert_page_in(page, lang, f"return visit {path}")
    finally:
        back.close()


def test_switching_keeps_the_page_and_its_filter(browser, deployed_server):
    """A link back to where the visitor was - query string included."""
    ctx = _context(browser, against="ar")
    try:
        page = ctx.new_page()
        page.goto(deployed_server.url + "/templates?cat=ats")
        page.locator('.lang-switch a[lang="ar"]').click()
        page.wait_for_load_state("load")
        assert page.url.endswith("/templates?cat=ats")
        _assert_page_in(page, "ar", "after switching on a filtered gallery")
    finally:
        ctx.close()


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_downloads_are_in_the_chosen_language(browser, deployed_server, lang):
    """The PDF and the Word file are the document on screen, and the
    document is the chosen language's own CV (per-language store)."""
    ctx = _context(browser, against=OTHER[lang])
    try:
        page = ctx.new_page()
        _choose(page, deployed_server, lang, "/")
        page.goto(deployed_server.url + "/builder")
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
        for kind in ("pdf", "docx"):
            sent = []
            page.route(f"**/export/{kind}", lambda r: (sent.append(r.request.post_data),
                                                        r.fulfill(status=200, body=b"x")))
            page.click("#dl-toggle")
            page.click(f"#dl-{kind}")
            page.wait_for_timeout(400)
            page.unroute(f"**/export/{kind}")
            # an English document may omit `lang` (absent means English)
            assert json.loads(sent[-1])["data"].get("lang", "en") == lang, kind
    finally:
        ctx.close()


def test_only_the_switcher_changes_it(browser, deployed_server):
    """No page, URL or default may flip it: a visit to every page, then the
    cookie is still the choice - and changing it takes the switcher."""
    ctx = _context(browser, against="en")
    try:
        page = ctx.new_page()
        _choose(page, deployed_server, "ar", "/")
        for path in PAGES + ["/preview?template_key=ats-t1&showcase=1"]:
            page.goto(deployed_server.url + path)
        assert [c["value"] for c in ctx.cookies() if c["name"] == COOKIE] == ["ar"]
        _choose(page, deployed_server, "en", "/templates")
        assert [c["value"] for c in ctx.cookies() if c["name"] == COOKIE] == ["en"]
    finally:
        ctx.close()
