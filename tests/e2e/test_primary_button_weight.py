"""Blue (primary) buttons are one step lighter in the ARABIC interface only
(user, 2026-10-18): Tajawal 800 -> 700. English stays Inter 600.

Every page that has a primary button is visited; every visible one is read.
700, not 600: the shell ships Tajawal 700 and 800 only, so a declared 600
would be drawn from the 700 file - the test reads the computed weight AND
that the face is Tajawal, so a missing face cannot pass as "lighter".
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/builder", "/account/sign-in", "/account/sign-up", "/no-such-page"]

READ = """() => Array.from(document.querySelectorAll('.btn-primary'))
  .filter((e) => e.offsetParent !== null)
  .map((e) => { const s = getComputedStyle(e);
    return [e.id || e.textContent.trim().slice(0, 30), s.fontFamily.split(',')[0].replace(/["']/g, ''), s.fontWeight]; })"""


@pytest.mark.parametrize("lang,face,weight", [("ar", "Tajawal", "700"), ("en", "Inter", "600")])
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


def test_arabic_outline_buttons_keep_their_weight(page, deployed_server):
    """Only the blue ones moved."""
    page.goto(f"{deployed_server.url}/lang/ar?next=/")
    others = page.evaluate("""() => Array.from(document.querySelectorAll('.btn:not(.btn-primary)'))
      .filter((e) => e.offsetParent !== null).map((e) => getComputedStyle(e).fontWeight)""")
    assert others and set(others) == {"800"}, others
