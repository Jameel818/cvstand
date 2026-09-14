"""The whole product renders with no network.

Session 7 self-hosted the 11 font families so the *résumé documents* would stop
depending on a CDN. The **app shell** kept its `fonts.googleapis.com` link, and
a render-blocking stylesheet on an unreachable host does not fail fast: every
page sat at ~21s before Chromium gave up on the request. Nothing caught it —
tests/test_fonts.py only inspects the document render paths, and a developer
with working internet never sees it.

So: block every non-local request and assert the pages still work.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/templates?cat=modern", "/builder"]


@pytest.fixture()
def offline_page(page, live_server):
    """Fail — not hang — on anything that leaves the machine, so an external
    dependency shows up as an assertion instead of a slow test."""
    external: list[str] = []

    def guard(route, request):
        if request.url.startswith(live_server.url):
            route.continue_()
        else:
            external.append(request.url)
            route.abort()

    page.route("**/*", guard)
    page.external = external
    return page


@pytest.mark.parametrize("path", PAGES)
def test_pages_load_with_no_network(offline_page, live_server, path):
    offline_page.goto(live_server.url + path, wait_until="load")
    assert not offline_page.external, (
        f"{path} reaches off-machine: {offline_page.external}")


def test_the_shell_paints_in_its_real_face_offline(offline_page, live_server):
    """A missing webfont is silent — the text just renders in a fallback. Inter
    is the UI face; if the stylesheet did not resolve, this is a system sans."""
    offline_page.goto(live_server.url + "/", wait_until="load")
    offline_page.wait_for_function("document.fonts.ready.then(() => true)")
    loaded = offline_page.evaluate(
        "() => Array.from(document.fonts).filter(f => f.status === 'loaded')"
        ".map(f => f.family)")
    assert "Inter" in loaded, f"UI font never loaded; got {sorted(set(loaded))}"


def test_the_builder_preview_is_self_contained_offline(offline_page, live_server):
    """The preview is an iframe `srcdoc`, so it inherits the page's base URL and
    resolves /static/fonts/fonts.css. If that ever regressed to the CDN the
    résumé would silently render in a fallback face — the exact failure mode
    fonts_inline.css exists to prevent on the PDF path."""
    offline_page.goto(live_server.url + "/builder", wait_until="load")
    canvas = offline_page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Ashworth")
    assert not offline_page.external, offline_page.external
