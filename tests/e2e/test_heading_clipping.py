"""No heading is clipped - Arabic first, English too (user, 2026-10-08).

The report: part of "دقائق" in the Arabic landing heading was cut off. The
cause: the Arabic hero (and the gallery title) are OUTLINED SVG - each word a
path inside an <svg> whose viewBox is the face's ascent+descent - and an
inline <svg> clips to its box by default. Arabic ink goes past that box: the
tail of the final ق reached 21.6 units below it, 12px on screen. The fix is
"overflow: visible" on those SVGs (app.css), which moves nothing.

The check is geometric, so it does not depend on one word or one page. For
every heading-like element, each line's glyph INK (canvas measureText on the
element's own font, placed on the line's box) is compared with every ancestor
that hides overflow; for each outlined SVG, the path's bounds with its
viewBox. Wholly scrolled-away text and the visually-hidden screen-reader copy
are not clipping and are skipped.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

PAGES = ["/", "/templates", "/builder", "/account/sign-in", "/account/sign-up", "/no-such-page"]

JS = r"""() => {
  const SEL = 'h1,h2,h3,h4,h5,h6,summary,.eyebrow,.stat-strip b,.tpl-name,.drawer header h3,.rb-caption,legend,.logo,.hero-sub,.blurb';
  const ctx = document.createElement('canvas').getContext('2d');
  const out = [];
  const clips = (el) => { const a = []; for (let p = el; p && p !== document.documentElement; p = p.parentElement) {
      const cs = getComputedStyle(p);
      const hides = (v) => v === 'hidden' || v === 'clip';   // auto/scroll = scrolled, not cut
      if (p.classList.contains('sr-only')) continue;          // visually hidden on purpose
      if (hides(cs.overflowX) || hides(cs.overflowY) || cs.webkitLineClamp !== 'none')
        a.push([p, p.getBoundingClientRect(), cs]); } return a; };
  for (const el of document.querySelectorAll(SEL)) {
    if (!el.offsetParent || el.closest('iframe') || el.closest('.sr-only')) continue;
    const cs = getComputedStyle(el);
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n; (n = walker.nextNode());) {
      if (!n.textContent.trim()) continue;
      const pcs = getComputedStyle(n.parentElement);
      ctx.font = `${pcs.fontStyle} ${pcs.fontWeight} ${pcs.fontSize} ${pcs.fontFamily}`;
      const m = ctx.measureText(n.textContent.trim());
      const r = document.createRange(); r.selectNodeContents(n);
      for (const lr of r.getClientRects()) {
        const inkTop = lr.top + (m.fontBoundingBoxAscent - m.actualBoundingBoxAscent);
        const inkBot = lr.top + m.fontBoundingBoxAscent + m.actualBoundingBoxDescent;
        for (const [p, b, ccs] of clips(n.parentElement)) {
          const top = b.top + parseFloat(ccs.borderTopWidth), bot = b.bottom - parseFloat(ccs.borderBottomWidth);
          if (inkBot <= top || inkTop >= bot) continue;     // wholly scrolled away, not cut
          const cut = Math.max(top - inkTop, inkBot - bot);
          if (cut > 0.5) out.push({text: n.textContent.trim().slice(0, 40), tag: el.tagName + '.' + el.className,
              by: (p.tagName + '.' + p.className).slice(0, 40), cutPx: +cut.toFixed(1)});
        }
      }
    }
  }
  for (const s of document.querySelectorAll('svg.outlined')) {
    const vb = s.viewBox.baseVal, g = s.querySelector('g'), bb = g.getBBox();
    const t = g.transform.baseVal.consolidate(); const dy = t ? t.matrix.f : 0, dx = t ? t.matrix.e : 0;
    const over = Math.max(-(bb.y + dy), bb.y + dy + bb.height - vb.height, -(bb.x + dx), bb.x + dx + bb.width - vb.width);
    if (over > 0.5 && getComputedStyle(s).overflow !== 'visible')
      out.push({text: '(outlined svg)', tag: 'svg', by: 'svg viewBox', cutPx: +(over * s.getBoundingClientRect().height / vb.height).toFixed(1)});
  }
  return out;
}"""


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)], ids=["desktop", "phone"])
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_no_heading_is_clipped(browser, deployed_server, lang, viewport):
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    try:
        page = ctx.new_page()
        page.goto(f"{deployed_server.url}/lang/{lang}?next=/")
        found = {}
        for path in PAGES:
            page.goto(deployed_server.url + path)
            page.wait_for_load_state("networkidle")
            page.evaluate("() => document.fonts.ready")
            if path == "/builder":
                page.click("#open-drawer")
                page.wait_for_timeout(400)
            res = page.evaluate(JS)
            if res:
                found[path] = res
        assert not found, f"clipped heading ink: {found}"
    finally:
        ctx.close()


def test_the_instrument_sees_a_clipped_outlined_heading(page, deployed_server):
    """Calibration: with the fix undone, the check must find the cut "دقائق"."""
    page.goto(f"{deployed_server.url}/lang/ar?next=/")
    page.wait_for_load_state("networkidle")
    page.add_style_tag(content=".hero-outlined svg { overflow: hidden !important; }")
    res = page.evaluate(JS)
    assert any(r["tag"] == "svg" and r["cutPx"] > 8 for r in res), res
