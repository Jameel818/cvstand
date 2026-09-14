"""The résumé belongs to the browser, proved through a browser.

`tests/test_stateless.py` gates the server half — POST carries the document,
nothing is stored, and the shared-file routes can be switched off. It cannot
prove the half that matters to a visitor: that what they type is theirs, stays
theirs across a reload, and is invisible to the next person to open the site.

That claim needs two independent browser contexts, which is what
`test_a_second_visitor_does_not_see_the_first_ones_resume` uses. A second
context is a genuinely separate storage partition — the same thing two people
on two laptops have, and the exact case the single `data/resume.json` could
never survive.

Note what is NOT asserted here: that the server forgot. It never knew.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

STORE_KEY = "cvstand:resume"
MINE = "Zahra Al-Mansouri"


def _stored(page):
    raw = page.evaluate(
        "() => { try { return localStorage.getItem('%s'); } catch (_) { return null; } }"
        % STORE_KEY
    )
    return json.loads(raw) if raw else None


def _type_name(page, value):
    """Set the name and wait for autosave to report it landed."""
    page.fill("#f_name", value)
    expect(page.locator("#save-state")).to_have_text("Saved")


def test_what_you_type_is_stored_in_this_browser(page, live_server):
    page.goto(live_server.url + "/builder")
    _type_name(page, MINE)
    assert _stored(page)["name"] == MINE


def test_it_survives_a_reload(page, live_server):
    """The stored copy must WIN over the seed the page ships.

    If the seed won, every reload would silently discard the user's work while
    looking like it had loaded fine — the worst shape this bug could take.
    """
    page.goto(live_server.url + "/builder")
    _type_name(page, MINE)
    page.reload()
    expect(page.locator("#f_name")).to_have_value(MINE)


def test_a_second_visitor_does_not_see_the_first_ones_resume(browser, deployed_server):
    """The whole point of the migration — and it needs the DEPLOYED server.

    Two contexts are two storage partitions, i.e. two people. With the résumé
    in `data/resume.json` this was impossible to satisfy: whoever saved last
    owned the document, and the other visitor opened the builder to find a
    stranger's name in it.

    Run against the DEFAULT server this fails, and instructively: the browser
    store is in place, visitor A still autosaves a mirror into the shared file,
    and `/builder` seeds the page from that file — so B inherits A's résumé
    through the seed rather than through the store. Fixing the store without
    the seed would have looked complete and leaked anyway, which is why
    `CVSTAND_SERVER_STORE=0` is a deployment requirement and not a
    preference. See `tests/e2e/conftest.py::deployed_server`.
    """
    first = browser.new_context(viewport={"width": 1440, "height": 950})
    second = browser.new_context(viewport={"width": 1440, "height": 950})
    try:
        p1 = first.new_page()
        p1.set_default_timeout(20_000)
        p1.goto(deployed_server.url + "/builder")
        _type_name(p1, MINE)

        p2 = second.new_page()
        p2.set_default_timeout(20_000)
        p2.goto(deployed_server.url + "/builder")

        expect(p2.locator("#f_name")).not_to_have_value(MINE)
        assert _stored(p2) is None or _stored(p2)["name"] != MINE
        # and the first visitor is undisturbed by the second arriving
        p1.reload()
        expect(p1.locator("#f_name")).to_have_value(MINE)
    finally:
        first.close()
        second.close()


def test_the_deployed_server_refuses_to_hold_a_resume(deployed_server):
    """The routes that read or write the one shared file must be unreachable.

    Belt and braces with `tests/test_stateless.py`, which asserts the same
    through the Flask test client. This one proves the ENV VAR actually
    reaches a real server process — a flag that is only ever monkeypatched in
    unit tests is a flag nothing proves is wired up.
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        deployed_server.url + "/export/docx?template_key=ats-t1", method="GET")
    try:
        urllib.request.urlopen(req, timeout=20)
        raise AssertionError("the deployed server exported the shared résumé")
    except urllib.error.HTTPError as exc:
        assert exc.code == 405, f"expected 405, got {exc.code}"


def test_the_export_sends_what_is_on_screen(page, live_server):
    """The download POSTs the document rather than asking the server for "the"
    résumé. Two things ride on that: with more than one visitor the GET could
    return somebody else's CV, and even alone it left a window between the
    save and the read in which the export could disagree with the preview."""
    page.goto(live_server.url + "/builder")
    _type_name(page, MINE)

    sent = {}

    def capture(route):
        sent["body"] = route.request.post_data_json
        route.fulfill(status=200, content_type="application/pdf", body=b"%PDF-1.4 stub")

    page.route("**/export/pdf", capture)
    page.click("#dl-toggle")
    with page.expect_download():
        page.click("#dl-pdf")

    assert sent["body"], "the export did not send the résumé"
    assert sent["body"]["data"]["name"] == MINE
    assert sent["body"]["template_key"]


def test_a_browser_that_stores_nothing_still_works(page, live_server):
    """Storage is where the résumé lives, not a precondition for the app.

    A private window with site data blocked THROWS on both read and write. The
    builder must still open, still render, still export — the user simply loses
    the document when they close the tab, which is a fair trade and is what the
    save indicator tells them.
    """
    page.add_init_script(
        "Object.defineProperty(window, 'localStorage', {"
        "  value: { getItem: () => { throw new Error('denied'); },"
        "           setItem: () => { throw new Error('denied'); },"
        "           removeItem: () => {} } });"
    )
    page.goto(live_server.url + "/builder")

    expect(page.locator("#f_name")).to_be_visible()
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
    page.fill("#f_name", MINE)
    # It cannot claim to have saved what it could not store.
    expect(page.locator("#save-state")).to_have_class("save-state is-unsaved")
