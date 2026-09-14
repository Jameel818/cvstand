"""The shell on a phone.

WHY THIS FILE EXISTS
    Nothing had ever rendered this app below 900px. Every browser context in
    the suite was 1440x950 or 900x1200, and `app.css` had exactly two
    breakpoints, so the smallest thing anyone had ever looked at was a tablet.

    Measured 2026-09-14: **28 of 32** page x width x language combinations
    overflowed horizontally. Two rows that could not shrink caused all of it --
    `.site-header` sat at a 454px floor and `.builder-bar` at 475px -- so on
    any phone the page scrolled sideways and the download button was off the
    screen. For a CV builder sold into a mobile-first market that is not a
    rough edge, and no test could see it.

WHY THIS MEASURES ELEMENT EDGES AND NOT `scrollWidth`
    The fix includes `html { overflow-x: hidden }`, which is needed because the
    closed template drawer is `position: fixed` and translated off-canvas, and
    a translated fixed element still counts toward the document's scroll width.

    That clip also makes the obvious test USELESS: with overflow-x hidden,
    `documentElement.scrollWidth` collapses to the viewport width and reports
    success no matter how far an element sticks out. A gate written the obvious
    way would have passed vacuously from the moment the fix landed -- the exact
    failure this project keeps finding, where the instrument agrees with
    whatever it is pointed at.

    So this walks the element rects instead, which clipping does not hide.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/builder", "/account/sign-in"]
# iPhone SE (the narrowest phone still in real use), iPhone 14, a common
# Android, and the tablet width that already worked.
SIZES = [(320, 568), (390, 844), (412, 915), (768, 1024)]

# Elements wider than the viewport, with what is sticking out named, so a
# failure says which rule to fix rather than only that something is wrong.
FIND_OVERFLOW = """() => {
  const vw = window.innerWidth;
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    // Deliberately off-canvas panels: the drawer sits at translateX(100%)
    // until opened, and the scrim covers the viewport by design.
    if (el.closest('.drawer') || el.classList.contains('drawer-scrim')) return;
    // The preview stage is a fixed 850px page scaled by a transform, inside
    // its own scroller. Its LAYOUT width is meant to exceed the viewport.
    if (el.closest('.preview-stage') || el.classList.contains('preview-stage')) return;
    // The gallery, hero and drawer thumbnails are the same trick: a full
    // 850px resume iframe shrunk by a transform inside a container that
    // clips it (.tpl-thumb and friends are overflow:hidden). The LAYOUT box
    // is meant to exceed its parent; nothing of it is ever on screen.
    if (el.tagName === 'IFRAME' &&
        el.closest('.tpl-thumb, .hero-card, .drawer-item')) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const over = Math.round(Math.max(r.right - vw, -r.left));
    if (over > 1) {
      const c = typeof el.className === 'string' ? el.className.split(' ')[0] : '';
      out.push(`${el.tagName.toLowerCase()}${c ? '.' + c : ''} +${over}px`);
    }
  });
  return out.slice(0, 6);
}"""


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("path", PAGES)
def test_nothing_sticks_out_sideways(browser, live_server, path, size, lang):
    """Both languages, because RTL mirrors the whole shell: a row that fits
    when it grows to the right can still overflow when it grows to the left."""
    width, height = size
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": "ui_lang", "value": lang, "url": live_server.url}])
    page = ctx.new_page()
    try:
        page.goto(live_server.url + path)
        page.wait_for_load_state("domcontentloaded")
        offenders = page.evaluate(FIND_OVERFLOW)
        assert not offenders, (
            f"{path} at {width}x{height} ({lang}) has content off the side of "
            f"the screen: {offenders}"
        )
    finally:
        ctx.close()


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_header_still_works_at_phone_width(browser, live_server, lang):
    """An overflow test alone can be satisfied by hiding everything. The two
    things the header exists for have to survive the shrink."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_cookies([{"name": "ui_lang", "value": lang, "url": live_server.url}])
    page = ctx.new_page()
    try:
        page.goto(live_server.url + "/")
        for sel, what in (("a.logo", "the wordmark"),
                          (".site-header .btn", "the call to action"),
                          (".lang-switch", "the language switcher")):
            el = page.locator(sel).first
            assert el.is_visible(), f"{what} disappeared on a phone ({lang})"
            box = el.bounding_box()
            assert box and box["width"] > 0, f"{what} has no size ({lang})"
    finally:
        ctx.close()


def test_the_builder_bar_keeps_its_controls_on_a_phone(browser, live_server):
    """The download button is the point of the whole application. It was off
    the right-hand edge of a 390px screen before 2026-09-14."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    try:
        page.goto(live_server.url + "/builder")
        page.wait_for_load_state("domcontentloaded")
        for sel, what in (("#dl-toggle", "the download button"),
                          ("#open-drawer", "the template switcher"),
                          (".builder-bar .back", "the back link")):
            el = page.locator(sel).first
            assert el.is_visible(), f"{what} is not visible on a phone"
            box = el.bounding_box()
            assert box, f"{what} has no box"
            assert box["x"] >= -1 and box["x"] + box["width"] <= 391, (
                f"{what} is off the screen: x={box['x']:.0f} w={box['width']:.0f}"
            )
        # Tap targets: a control nobody can hit is not on the screen in any
        # sense that matters.
        dl = page.locator("#dl-toggle").bounding_box()
        assert dl["height"] >= 28, f"download button is {dl['height']:.0f}px tall"
    finally:
        ctx.close()
