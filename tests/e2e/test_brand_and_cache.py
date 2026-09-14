"""The brand in a real browser, and the service worker's cache rename.

WHY THESE ARE NOT COVERED ELSEWHERE

    `tests/test_brand.py` asserts the brand through the Flask test client. That
    proves the SERVER emits it; it cannot prove a reader SEES it. A stylesheet
    rule, a failed font, or a script error can leave correct HTML rendering an
    invisible header, and no route-level test can tell.

    The cache half has no coverage anywhere, and it is the code most likely to
    be wrong, because it is the code that was changed most recently and cannot
    run outside a browser at all. On 2026-09-14 the shell cache was renamed
    `resumecraft-*` -> `cvstand-*` and `VERSION` went v1 -> v2. A service
    worker's cleanup step only deletes keys it RECOGNISES, so renaming the
    prefix without keeping the old one strands every cache a browser already
    holds -- forever, invisibly, and on the users who visited earliest.

    `test_offline.py` proves the app works with no network. It never inspects
    what is in the cache or what was evicted from it, which is a different
    question.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

from app import brand

pytestmark = pytest.mark.e2e

# The pages that render the full shell. The builder deliberately empties the
# `chrome` and `footer` blocks (builder.html:4-5), so it has no wordmark --
# see tests/test_brand.py's module docstring.
CHROME_PAGES = ["/", "/templates", "/account/sign-in"]


def _set_ui_lang(page, live_server, lang: str) -> None:
    page.context.add_cookies(
        [{"name": "ui_lang", "value": lang, "url": live_server.url}]
    )


# --------------------------------------------------------------- the brand ---

@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("path", CHROME_PAGES)
def test_the_wordmark_is_actually_visible(page, live_server, path, lang):
    """Not "is in the HTML" -- visible, with real layout and real fonts."""
    _set_ui_lang(page, live_server, lang)
    page.goto(live_server.url + path)

    marks = page.locator("a.logo span", has_text=brand.HEAD)
    expect(marks.first).to_be_visible()

    box = marks.first.bounding_box()
    assert box and box["width"] > 20 and box["height"] > 8, (
        f"the wordmark occupies no space on {path} ({lang}): {box}"
    )
    assert brand.NAME in marks.first.inner_text().replace("\n", "")


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_tagline_is_visible_and_follows_the_interface(page, live_server, lang):
    """It carries a CSS class that did not exist before 2026-09-14. A class
    with no rule behind it still renders -- just as muted fine print, which is
    the one thing the disambiguating line must not be."""
    _set_ui_lang(page, live_server, lang)
    page.goto(live_server.url + "/")

    tagline = page.locator("p.footer-tagline")
    tagline.scroll_into_view_if_needed()
    expect(tagline).to_be_visible()

    text = tagline.inner_text().strip()
    assert text, "the tagline element is empty"
    if lang == "ar":
        assert "stand out" not in text.lower(), "the Arabic footer shows English"
    else:
        assert "stand out" in text.lower(), text


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_contact_address_is_a_real_link(page, live_server, lang):
    """The sign-in page tells locked-out people to get in touch. Before
    2026-09-14 it named no address at all -- there was no `mailto:` anywhere
    under app/. Password reset still does not exist, so this link is the only
    way out of a locked account."""
    _set_ui_lang(page, live_server, lang)
    page.goto(live_server.url + "/account/sign-in")

    link = page.locator(f'a[href="mailto:{brand.SUPPORT_EMAIL}"]').first
    link.scroll_into_view_if_needed()
    expect(link).to_be_visible()
    assert brand.SUPPORT_EMAIL in link.inner_text()


# ------------------------------------------------------- the service worker ---

def _wait_for_sw(page, live_server):
    """Register the worker and wait for it to control the page."""
    page.goto(live_server.url + "/")
    page.wait_for_function(
        "() => navigator.serviceWorker && navigator.serviceWorker.ready",
        timeout=15000,
    )
    page.evaluate("() => navigator.serviceWorker.ready")


def _cache_keys(page) -> list[str]:
    return page.evaluate("async () => await caches.keys()")


def _cold_origin(page, live_server):
    """Return the origin to the state of a browser that has never been here.

    THE SWEEP ONLY RUNS ON `activate`, AND `activate` ONLY FIRES FOR A WORKER
    THAT IS NOT ALREADY RUNNING. Seeding a stale cache under an
    already-activated worker and reloading does nothing: there is no further
    activation, so cleanup never runs again and the seed survives for reasons
    that have nothing to do with the filter being tested.

    That made the first version of these tests ORDER-DEPENDENT -- they passed
    alone and failed in the full suite, where `test_offline.py` had already
    registered a worker for this origin. Unregistering first makes the next
    visit a genuine install-and-activate, which is the only state in which the
    assertion means anything.
    """
    page.goto(live_server.url + "/")
    page.evaluate("""async () => {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r => r.unregister()));
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
    }""")
    assert _cache_keys(page) == [], "failed to return the origin to a cold state"


def test_the_shell_is_cached_under_the_current_prefix(page, live_server):
    # Cold, because this asserts the ABSENCE of old-prefix caches and the two
    # tests below deliberately create some.
    _cold_origin(page, live_server)
    _wait_for_sw(page, live_server)
    page.wait_for_function(
        "async () => (await caches.keys()).some(k => k.startsWith('cvstand-'))",
        timeout=15000,
    )
    keys = _cache_keys(page)
    assert any(k.startswith("cvstand-") for k in keys), keys
    assert not any(k.startswith("resumecraft-") for k in keys), (
        f"the worker is still writing caches under the OLD prefix: {keys}"
    )


def test_a_cache_left_under_the_old_prefix_is_swept_away(page, live_server):
    """The regression this file exists for.

    Seed a cache exactly as a browser that visited before the rename would
    hold one, then let the worker activate. A cleanup filter that only knows
    the new prefix leaves it there permanently -- there is no later event that
    would ever revisit it, and no user-visible symptom until the day stale
    assets are served.
    """
    _cold_origin(page, live_server)
    # Seed and confirm in ONE evaluate. Split across two calls this races the
    # worker: activation can sweep the entry between them, and the test then
    # reports "seeding failed" for the exact behaviour it is asserting.
    seeded = page.evaluate("""async () => {
        const c = await caches.open('resumecraft-shell-v1');
        await c.put('/stale-probe', new Response('stale'));
        return (await caches.keys()).includes('resumecraft-shell-v1');
    }""")
    assert seeded, "could not create the pre-rename cache to be swept"

    # Now a FRESH worker installs and activates over the seeded state.
    _wait_for_sw(page, live_server)
    page.reload()
    page.wait_for_function(
        "async () => !(await caches.keys()).includes('resumecraft-shell-v1')",
        timeout=15000,
    )

    keys = _cache_keys(page)
    assert "resumecraft-shell-v1" not in keys, (
        "a pre-rename cache survived activation - sw.js's cleanup filter only "
        f"deletes keys it recognises, so it must sweep BOTH prefixes: {keys}"
    )
    assert any(k.startswith("cvstand-") for k in keys), keys


def test_a_superseded_version_of_the_current_prefix_is_swept_too(page, live_server):
    """The ordinary case the rename must not have broken: VERSION is bumped by
    hand (sw.js:35) because Flask serves /static with no content hash, so
    every bump depends on this same cleanup running."""
    _cold_origin(page, live_server)
    seeded = page.evaluate("""async () => {
        const c = await caches.open('cvstand-shell-v0');
        await c.put('/old-probe', new Response('old'));
        return (await caches.keys()).includes('cvstand-shell-v0');
    }""")
    assert seeded, "could not create the superseded cache to be swept"
    _wait_for_sw(page, live_server)
    page.reload()
    page.wait_for_function(
        "async () => !(await caches.keys()).includes('cvstand-shell-v0')",
        timeout=15000,
    )
    assert "cvstand-shell-v0" not in _cache_keys(page)
