"""The app shell's RTL geometry: the scaled résumé previews stay in frame.

WHAT THIS PROTECTS

    Three surfaces shrink a full 850×1100 résumé iframe into a small box with
    `transform: scale()` — the landing hero cards, the gallery thumbnails and
    the drawer minis. `transform` has no logical form, so `transform-origin:
    top left` stays a PHYSICAL corner in RTL. There the iframe's layout box
    hangs leftward from the right edge of its clipping box, and scaling toward
    the iframe's own top-left parks the shrunken render hundreds of pixels
    outside the `overflow: hidden` window.

    Found 2026-09-08 by looking at the running app in Arabic. Measured then:

        landing hero card ..... box [354,686]   drawn [-195,138]   0% visible
        gallery thumbnail ..... box [959,1225]  drawn [375,647]    0% visible
        drawer mini ........... box [327,389]   drawn [-462,-400]  0% visible

    So an Arabic reader saw 49 blank cards on the gallery, an empty hero, and
    an empty drawer — **every surface where a person chooses a template** —
    while the builder's own preview worked perfectly.

WHY NOTHING CAUGHT IT

    Each existing gate stops one step short of this:

      * `tests/test_rtl_mirroring.py` scans the résumé `.j2` files and renders
        `.tpl` canvases. `app/static/css/app.css` is not a résumé template and
        the shell is not an 850×1100 canvas, so neither half looks here.
      * the golden HTML and pixel gates only cover the résumé canvas.
      * `test_journey_ar.py::test_the_gallery_previews_an_arabic_resume`
        asserts on the `/preview` RESPONSE BODY, which was correct all along —
        all 49 iframes loaded and each had its `.tpl` in the DOM. Nothing
        raised, nothing 500'd, nothing was missing. The pixels were simply
        somewhere else.

    That is this project's signature failure shape, so the assertion here is
    deliberately geometric: not "did it load" but "is it ON SCREEN".

WHY OVERLAP RATHER THAN A SCREENSHOT

    A pixel baseline of the shell would have to be regenerated on every copy
    edit and every palette tweak, and would say "something moved" rather than
    "the preview is out of frame". The overlap fraction states the actual
    requirement and is stable against everything else.
"""
from __future__ import annotations

import pytest

from app.i18n import COOKIE

pytestmark = pytest.mark.e2e

#: (path, selector, how to reveal it, human name). Every place the shell
#: scales a résumé iframe down. `#preview-stage` is here too even though it has
#: never been broken — its origin is `top center`, which is direction-agnostic,
#: and pinning that is the cheapest way to notice if someone "tidies" it to
#: `top left` for consistency with the other three.
SURFACES = [
    ("/", ".hero-card iframe", None, "landing hero card"),
    ("/templates", ".tpl-thumb iframe", None, "gallery thumbnail"),
    ("/builder", "#preview-stage", None, "builder preview stage"),
    ("/builder", ".drawer-item .mini iframe", "#open-drawer", "drawer mini"),
]

#: How much of the scaled element must land inside its clipping box, measured
#: HORIZONTALLY — the axis direction actually swaps. Not 100: `scale(.32)` of
#: 850px is 272px against a 266px-wide card, so ~2% legitimately overhangs in
#: BOTH directions. The defect this guards against measured 0.
#:
#: The vertical fraction is reported in the failure message but NOT asserted:
#: every one of these surfaces clips vertically on purpose — a 1100px page at
#: .32 is 352px in a 340px box, and the builder's preview pane scrolls, which
#: put it at 82% in English and Arabic alike. Asserting it flagged a scrollbar
#: as a bidi defect.
MIN_VISIBLE_PCT = 90

_PROBE = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return {missing: true};
  // the box that clips it — the scaled iframe's own overflow:hidden parent
  const box = el.closest('.tpl-thumb, .hero-card, .mini, .preview-pane')
              || el.parentElement;
  const b = box.getBoundingClientRect(), i = el.getBoundingClientRect();
  const wide = Math.max(0, Math.min(b.right, i.right) - Math.max(b.left, i.left));
  const tall = Math.max(0, Math.min(b.bottom, i.bottom) - Math.max(b.top, i.top));
  return {
    origin: getComputedStyle(el).transformOrigin,
    box: [Math.round(b.left), Math.round(b.right)],
    drawn: [Math.round(i.left), Math.round(i.right)],
    visible_pct: i.width ? Math.round(100 * wide / i.width) : 0,
    tall_pct: i.height ? Math.round(100 * tall / i.height) : 0,
  };
}"""


def _measure(page, live_server, lang, path, selector, reveal):
    if lang != "en":
        page.context.add_cookies(
            [{"name": COOKIE, "value": lang, "url": live_server.url}])
    page.goto(live_server.url + path, wait_until="networkidle")
    if reveal:
        page.click(reveal)
    # the iframes are lazy and each is a real /preview render
    page.wait_for_timeout(3000)
    return page.evaluate(_PROBE, selector)


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("path,selector,reveal,name", SURFACES)
def test_a_scaled_preview_lands_inside_its_frame(page, live_server, lang,
                                                 path, selector, reveal, name):
    """The deliverable: in BOTH interface languages, the shrunken résumé is
    where the card says it is."""
    r = _measure(page, live_server, lang, path, selector, reveal)
    assert not r.get("missing"), f"{name}: {selector!r} is not on {path}"
    assert r["visible_pct"] >= MIN_VISIBLE_PCT, (
        f"{name} in {lang}: only {r['visible_pct']}% of the scaled preview is "
        f"inside its frame — box {r['box']}, drawn at {r['drawn']}, "
        f"transform-origin {r['origin']}. `transform` has no logical form; a "
        f"physical `transform-origin` needs a [dir=\"rtl\"] override in "
        f"app.css. (vertically: {r['tall_pct']}%)")


@pytest.mark.parametrize("path,selector,reveal,name", SURFACES)
def test_the_two_directions_frame_the_preview_alike(page, live_server,
                                                    path, selector, reveal, name):
    """Arabic must not merely be *acceptable* — it must match English.

    Asserted separately because a fix that dragged the preview back into frame
    by a few pixels, or that shrank it to fit, would satisfy the threshold
    above while looking different from the English card it is a translation
    of. Comparing the two directions states the real requirement: the same
    card, mirrored."""
    en = _measure(page, live_server, "en", path, selector, reveal)
    ar = _measure(page, live_server, "ar", path, selector, reveal)
    assert abs(en["visible_pct"] - ar["visible_pct"]) <= 2, (
        f"{name}: {en['visible_pct']}% of the preview is framed in English but "
        f"{ar['visible_pct']}% in Arabic")
