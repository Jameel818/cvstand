"""Measure how much room each template's letter page leaves for the letter's
BODY into app/letter_capacity.json.

    venv/Scripts/python tools/build_letter_capacity.py          # write
    venv/Scripts/python tools/build_letter_capacity.py --check  # compare, exit 1 if stale

The letter page is the CV's own page with the CV content taken out
(app/letter.py letterhead_canvas): its letterhead is the template's header
block and its body sits in the column that held the CV's jobs. That column
is 714px wide in a single-column template and as narrow as ~330px beside a
side column; the letterhead above it takes 120-420px of the 1100px page. So
the same letter needs a smaller type size in some templates to stay one
page (the PDF's autofit only tightens so far). Both numbers come out of
layout, so they are MEASURED here in Chromium, never guessed:

    w   the body's text width (px, its own padding out)
    h   the page height left from the body's top to the page's bottom inset

letter.body_px() turns the letter's length and this capacity into the size.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import letter, registry  # noqa: E402
from tests import letter_samples as LS  # noqa: E402

OUT = letter.CAPACITY_PATH

_MEASURE = r"""() => {
  const tpl = document.querySelector('.tpl');
  const body = document.querySelector('.cl-body');
  const T = tpl.getBoundingClientRect(), B = body.getBoundingClientRect();
  const pad = parseFloat(getComputedStyle(tpl).paddingBottom) || 0;
  const cs = getComputedStyle(body);
  const w = B.width - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
  return {w: Math.round(w), h: Math.round(T.bottom - B.top - Math.max(24, pad))};
}"""


def measure() -> dict:
    from playwright.sync_api import sync_playwright
    out: dict = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 850, "height": 1100})
        for key in registry.ported_keys():
            out[key] = {}
            for lang in ("en", "ar"):
                # the measurement must not depend on the size it decides: the
                # body is laid out at the reference size
                html = letter.document_html(LS.with_letter(lang), key, for_pdf=True,
                                            body_px=letter.BODY_SIZES[0][1])
                page.set_content(html, wait_until="networkidle")
                out[key][lang] = page.evaluate(_MEASURE)
        b.close()
    return {"templates": out}


def main(argv: list[str]) -> int:
    got = measure()
    if "--check" in argv:
        old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
        if old != got:
            print(f"{OUT.name} is stale - run tools/build_letter_capacity.py")
            return 1
        print(f"{OUT.name} is current")
        return 0
    OUT.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(got['templates'])} templates)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
