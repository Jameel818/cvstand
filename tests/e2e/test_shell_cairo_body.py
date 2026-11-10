"""Arabic interface text is Cairo 400 / 600; headings are not (user, 2026-11-10).

"Change ALL non-heading text to Cairo: paragraphs, lists, small text, form
inputs, helper text 400; buttons, nav links, labels, badges/bullets 600.
Headings: DO NOT change." Website shell only - the CV templates are iframes,
which the collector skips by construction.

Measured, not assumed: every visible text node on each Arabic page is read
with its computed family and weight. A heading-role element must keep the
face it had before this change; everything else must be Cairo at exactly 400
or 600. Some titles are not <h*> (`.sec > summary` in the builder, the
drawer's `.grp-label` and its card titles `.drawer .info b`) and would
silently have inherited the new body face, so they are pinned and checked.

English is covered elsewhere: test_font_roles.py (body Inter, no Arabic face)
and test_shell_cairo_weight.py (no Cairo on an English page).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/builder", "/account/sign-in"]

# Heading-role surfaces, with the (family, weight) they had before 2026-11-10.
# `None` weight = whatever the heading rules above set; only the family is held.
HEADINGS = {
    "h1, h2, h3, h4, h5, h6": ("Cairo", None),
    ".eyebrow": ("Cairo", "600"),
    ".stat-strip b": ("Cairo", "600"),
    ".faq summary": ("Cairo", "500"),
    ".sec > summary": ("IBM Plex Sans Arabic", "700"),
    ".drawer .info b": ("IBM Plex Sans Arabic", "700"),
}
HEADING_SEL = ", ".join([*HEADINGS, ".num", ".hero h1 *", ".sec > summary *",
                         ".drawer .grp-label"])

COLLECT = """(headingSel) => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.textContent.trim();
    if (!/[\\u0600-\\u06FF]/.test(t)) continue;         // Arabic text only
    const e = n.parentElement;
    if (e.closest('iframe, script, style, svg, .sr-only, option')) continue;
    if (!e.getBoundingClientRect().width) continue;
    if (e.matches(headingSel) || e.closest('.hero h1')) continue;
    const s = getComputedStyle(e);
    out.push([e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).trim().split(/\\s+/).join('.') : ''),
              s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), s.fontWeight, t.slice(0, 30)]);
  }
  return out;
}"""

FACE = """(sel) => Array.from(document.querySelectorAll(sel))
  .filter((e) => e.getBoundingClientRect().width && !e.closest('.hero'))
  .map((e) => { const s = getComputedStyle(e);
    return [s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), s.fontWeight]; })"""


def _open(page, server, path):
    page.context.add_cookies([{"name": "ui_lang", "value": "ar", "url": server.url}])
    page.goto(server.url + path, wait_until="networkidle")
    if path == "/builder":
        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
        # The template drawer: its picker cards carry titles and labels too,
        # and a first version of this change missed them (found by
        # test_shell_cairo_weight.py, which opens it).
        page.click("#open-drawer")
        page.wait_for_selector("#drawer.is-open .info b")


@pytest.mark.parametrize("path", PAGES)
def test_arabic_non_heading_text_is_cairo_400_or_600(page, live_server, path):
    _open(page, live_server, path)
    rows = page.evaluate(COLLECT, HEADING_SEL)
    assert len(rows) >= 5, f"the collector measured almost nothing on {path}: {rows}"
    wrong = [r for r in rows if r[1] != "Cairo" or r[2] not in ("400", "600")]
    assert not wrong, f"{path}: non-heading text not Cairo 400/600: {wrong[:8]}"


@pytest.mark.parametrize("path", PAGES)
def test_arabic_headings_keep_their_face(page, live_server, path):
    _open(page, live_server, path)
    for sel, (family, weight) in HEADINGS.items():
        for fam, w in page.evaluate(FACE, sel):
            assert fam == family, f"{path} {sel}: {fam} (should stay {family})"
            if weight:
                assert w == weight, f"{path} {sel}: weight {w} (should stay {weight})"


def test_arabic_prose_is_400_and_controls_are_600(page, live_server):
    """The two weights land on the right roles, read off named elements."""
    _open(page, live_server, "/")
    read = lambda sel: page.evaluate(FACE, sel)
    assert set(map(tuple, read(".hero-sub, .section-head p, .feature p"))) == {("Cairo", "400")}
    assert set(map(tuple, read(".site-nav a, .btn, .chip, .hero-trust span"))) == {("Cairo", "600")}

    _open(page, live_server, "/builder")
    assert set(map(tuple, read(".field label"))) == {("Cairo", "600")}
    assert set(map(tuple, read(".field input, .field textarea"))) == {("Cairo", "400")}
