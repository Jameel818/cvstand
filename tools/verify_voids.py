"""Unexplained vertical voids: space the stylesheet never asked for.

WHAT THIS PROTECTS

    `justify-content:space-between` on a column of FIXED height hands every
    pixel of leftover space to the gaps between its children. That looks
    correct for exactly one content volume — the one the reference image
    happened to have — and wrong for every other. It is not a porting mistake
    anyone can see in the source: the declaration is three words long and the
    defect only appears once real content is shorter than the frame.

    Measured 2026-09-18 across all 49 templates, this found one real defect:
    `modern-t2`'s main column declared a 22px row-gap and rendered 157px twice,
    270px of void between the contact block, the stat band and EXPERIENCE. It
    is fixed, and this is what stops it coming back anywhere.

WHY IT MEASURES A DISCREPANCY, NOT A PROPERTY

    Grepping for `space-between` finds the cause of ONE instance and misses
    every other route to the same result — `margin-top:auto`, a stray large
    margin, an `align-content` on a grid. What they share is a RENDERED gap
    the stylesheet never declares, so that difference is what gets measured.

    It also keeps the check honest in the other direction: `modern-t2`'s
    SIDEBAR is still `space-between` and is not flagged, because its content
    fills the height and the distributed slack is a few pixels. The property
    is not the defect; the void is.

WHAT COUNTS AS EXPLAINED

    The declared `row-gap`, plus the larger of the two adjoining margins —
    which is what a collapsed margin contributes. Anything beyond that by more
    than SLACK is space nothing asked for.

    SLACK is 40px: wide enough that ordinary sub-pixel and margin-collapse
    noise cannot trip it, narrow enough to catch a void a reader would notice.
    `modern-t2`'s excess measured 135px, comfortably clear of both edges.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rendering import document_html        # noqa: E402

#: A rendered gap exceeding what the stylesheet declares by more than this is
#: not a design decision. See the module docstring for how it was chosen.
SLACK = 40

_JS = r"""(SLACK) => {
  const out = [];
  document.querySelectorAll('.tpl *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display !== 'flex' || cs.flexDirection !== 'column') return;
    const kids = [...el.children].filter(k => {
      const r = k.getBoundingClientRect();
      return r.height > 0 && r.width > 0;
    });
    if (kids.length < 2) return;
    const declared = parseFloat(cs.rowGap) || 0;
    for (let i = 1; i < kids.length; i++) {
      const prev = kids[i - 1].getBoundingClientRect();
      const cur = kids[i].getBoundingClientRect();
      const gap = cur.top - prev.bottom;
      // Adjoining margins collapse, so the LARGER of the two is what a
      // correctly-styled gap can legitimately add.
      const mb = parseFloat(getComputedStyle(kids[i - 1]).marginBottom) || 0;
      const mt = parseFloat(getComputedStyle(kids[i]).marginTop) || 0;
      const explained = declared + Math.max(mb, mt);
      if (gap - explained > SLACK) {
        out.push({
          excess: +(gap - explained).toFixed(1),
          gap: +gap.toFixed(1),
          explained: +explained.toFixed(1),
          justify: cs.justifyContent,
          after: (kids[i - 1].textContent || '').trim().slice(0, 30)
                 .replace(/\s+/g, ' '),
        });
      }
    }
  });
  return out;
}"""


def scan(page, data: dict, key: str) -> list[dict]:
    """Every unexplained void in one template, worst first."""
    # for_pdf=True inlines the fonts: set_content()'s base URL is about:blank,
    # so a relative font URL fetches nothing and every metric shifts.
    page.set_content(document_html(data, key, for_pdf=True),
                     wait_until="networkidle")
    return sorted(page.evaluate(_JS, SLACK), key=lambda h: -h["excess"])


def plant_a_void(page) -> list[dict]:
    """The control: put a void on the page and confirm the scan sees it.

    `.tpl` is itself a flex container, so a child with a plain `height` is
    squashed to its content and plants nothing at all — the first version of
    this control reported the instrument blind when the instrument was fine.
    `flex-shrink:0` with `min-height` is what actually makes the frame.
    """
    page.evaluate("""() => {
      const d = document.createElement('div');
      d.id = '__void_control';
      d.style.cssText = 'display:flex;flex-direction:column;'
        + 'justify-content:space-between;min-height:600px;'
        + 'flex-shrink:0;gap:4px';
      d.innerHTML = '<div style="height:20px">TOP</div>'
                  + '<div style="height:20px">BOTTOM</div>';
      document.querySelector('.tpl').appendChild(d);
    }""")
    return [h for h in page.evaluate(_JS, SLACK) if h["after"] == "TOP"]


def report(key: str, hits: list[dict]) -> str:
    lines = [f"{key} has {len(hits)} unexplained vertical void(s):"]
    for h in hits[:3]:
        lines.append(
            f"  {h['excess']}px beyond the {h['explained']}px the stylesheet "
            f"declares (gap {h['gap']}px, justify-content:{h['justify']}) "
            f"after {h['after']!r}"
        )
    lines.append(f"  reproduce: venv/Scripts/python tools/verify_voids.py {key}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    from app import registry
    from tests.samples import ENGLISH

    keys = argv[1:] or sorted(registry.ported_keys())
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(viewport={"width": 900, "height": 1200}).new_page()
        for key in keys:
            hits = scan(pg, ENGLISH, key)
            if hits:
                bad += 1
                print(report(key, hits))
            else:
                print(f"{key}: clean")
        b.close()
    print(f"\n{bad} of {len(keys)} have an unexplained void > {SLACK}px")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
