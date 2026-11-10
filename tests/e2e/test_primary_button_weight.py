"""Buttons in the ARABIC interface are Cairo 600 (user, 2026-11-10), every
variant; this replaces Tajawal 700 for the blue ones (2026-10-18) and 800 for
the outline ones. English stays Inter 600.

Every page that has a primary button is visited; every visible one is read.
Cairo is the vendored variable face (wght 200-1000), so 600 is a real weight;
the test reads the computed weight AND the face.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/builder", "/account/sign-in", "/account/sign-up", "/no-such-page"]

READ = """() => Array.from(document.querySelectorAll('.btn-primary'))
  .filter((e) => e.offsetParent !== null)
  .map((e) => { const s = getComputedStyle(e);
    return [e.id || e.textContent.trim().slice(0, 30), s.fontFamily.split(',')[0].replace(/["']/g, ''), s.fontWeight]; })"""


@pytest.mark.parametrize("lang,face,weight", [("ar", "Cairo", "600"), ("en", "Inter", "600")])
def test_every_primary_button(page, deployed_server, lang, face, weight):
    page.goto(f"{deployed_server.url}/lang/{lang}?next=/")
    seen = 0
    for path in PAGES:
        page.goto(deployed_server.url + path)
        page.wait_for_load_state("domcontentloaded")
        for label, fam, w in page.evaluate(READ):
            assert (fam, w) == (face, weight), f"{lang} {path} {label!r}: {fam} {w}"
            seen += 1
    assert seen >= 10, "fewer primary buttons than the pages carry"


def test_arabic_outline_buttons_are_cairo_600_too(page, deployed_server):
    """Every button variant, not just the blue ones (2026-11-10)."""
    page.goto(f"{deployed_server.url}/lang/ar?next=/")
    others = page.evaluate("""() => Array.from(document.querySelectorAll('.btn:not(.btn-primary)'))
      .filter((e) => e.offsetParent !== null).map((e) => { const s = getComputedStyle(e);
        return s.fontFamily.split(',')[0].replace(/["']/g, '') + ' ' + s.fontWeight; })""")
    assert others and set(others) == {"Cairo 600"}, others
