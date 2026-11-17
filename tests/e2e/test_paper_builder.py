"""The builder's paper switch, in a real browser (feature/paper-size).

User decision, 2026-11-17: a CV with no `paper` field stays on LETTER; a NEW
CV starts on A4, or on Letter when the browser language is en-US / en-CA; the
user can switch. The preview page is the paper's height (1100 / 1202px), the
choice is saved in the résumé, and it survives a reload.

Every test runs on `deployed_server` (SERVER_STORE=0, the live mode: the
browser owns the résumé) unless it is about the local server's own file.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

from tests import samples

pytestmark = pytest.mark.e2e


def _open(browser, server, locale, lang="en", stored=None):
    ctx = browser.new_context(viewport={"width": 1440, "height": 950}, locale=locale)
    page = ctx.new_page()
    page.set_default_timeout(20_000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if stored is not None:
        page.goto(server.url + "/")
        page.evaluate("([k, v]) => localStorage.setItem(k, v)",
                      [f"cvstand:resume:{lang}", json.dumps(stored)])
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
    return ctx, page, errors


def _state(page):
    return page.evaluate("""() => ({
        stage: document.querySelector('#preview-stage').getBoundingClientRect().height
               / (new DOMMatrix(getComputedStyle(document.querySelector('#preview-stage')).transform).a || 1),
        frame: document.querySelector('#preview-frame').offsetHeight,
        pressed: [...document.querySelectorAll('#paper-switch .rb-seg')]
                 .filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.dataset.paper),
    })""")


def _tpl_height(page):
    return page.frame_locator("#preview-frame").locator(".tpl").evaluate("e => e.offsetHeight")


@pytest.mark.parametrize("locale,paper,h", [("en-GB", "a4", 1202), ("ar-SA", "a4", 1202),
                                            ("en-US", "letter", 1100), ("en-CA", "letter", 1100)])
def test_a_new_cv_starts_on_the_browser_default(browser, deployed_server, locale, paper, h):
    ctx, page, errors = _open(browser, deployed_server, locale)
    try:
        st = _state(page)
        assert st["pressed"] == [paper]
        assert round(st["frame"]) == h
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_have_css("height", f"{h}px")
        assert not errors
    finally:
        ctx.close()


def test_a_stored_cv_without_paper_stays_on_letter(browser, deployed_server):
    old = dict(samples.ENGLISH)
    old.pop("paper", None)
    ctx, page, errors = _open(browser, deployed_server, "en-GB", stored=old)
    try:
        assert _state(page)["pressed"] == ["letter"]
        assert _tpl_height(page) == 1100
        assert not errors
    finally:
        ctx.close()


def test_switching_saves_redraws_and_survives_reload(browser, deployed_server):
    ctx, page, errors = _open(browser, deployed_server, "en-US")
    try:
        assert _state(page)["pressed"] == ["letter"]
        page.click('#paper-switch .rb-seg[data-paper="a4"]')
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_have_css("height", "1202px")
        assert round(_state(page)["frame"]) == 1202
        expect(page.locator("#save-state")).to_have_text("Saved")
        stored = json.loads(page.evaluate("() => localStorage.getItem('cvstand:resume:en')"))
        assert stored["paper"] == "a4"
        page.reload()
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_have_css("height", "1202px")
        assert _state(page)["pressed"] == ["a4"]
        # Undo puts the page back
        page.click('#paper-switch .rb-seg[data-paper="letter"]')
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_have_css("height", "1100px")
        page.click("#undo-btn")
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_have_css("height", "1202px")
        assert _state(page)["pressed"] == ["a4"]
        assert not errors
    finally:
        ctx.close()


def test_the_switch_reads_in_arabic(browser, deployed_server):
    ctx, page, errors = _open(browser, deployed_server, "ar-SA", lang="ar")
    try:
        expect(page.locator("#paper-switch")).to_have_attribute("aria-label", "حجم الورق")
        expect(page.locator('#paper-switch .rb-seg[data-paper="letter"]')).to_have_text("Letter")
        assert _state(page)["pressed"] == ["a4"]
        assert not errors
    finally:
        ctx.close()


def test_local_server_cv_without_paper_stays_on_letter(browser, live_server, seed_resume):
    """SERVER_STORE=1: #resume-data is the user's own saved file, not a new
    CV - it must not be moved to A4 just because localStorage is empty."""
    mine = dict(samples.ENGLISH, name="Saved Before A4")
    mine.pop("paper", None)
    seed_resume(mine)
    ctx, page, errors = _open(browser, live_server, "en-GB")
    try:
        assert _state(page)["pressed"] == ["letter"]
        assert _tpl_height(page) == 1100
        assert not errors
    finally:
        ctx.close()
