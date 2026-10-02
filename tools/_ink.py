"""Rendered INK height of a face (typography step 7, spec §4.1).

    with ink_page() as page:
        h = ink_height(page, "Cairo", 400, "محمد")      # px at font-size:100px

Canvas measureText().actualBoundingBoxAscent + actualBoundingBoxDescent: the
height the glyphs actually paint, not the line box a DOM rect would give.
The faces are the typography controls' own ('CVT <family>', from
app/static/fonts/typography.css), served from disk under a fake origin, so the
measure needs no running app.

The same measurement produced tools/fetch_fonts_ar.py's SIZE_ADJUST (Tajawal
114.2 %, Amiri 91.7 %), whose script was never committed; tools/
calibrate_fonts.py --instrument re-derives those two numbers from this module
before any number it prints is trusted (memory: measurement instrument
errors - point a new instrument at a known answer first).
"""
from __future__ import annotations

import mimetypes
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"
ORIGIN = "http://ink.local"

_PAGE = """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="/static/fonts/typography.css">
<canvas id="c" width="10" height="10"></canvas>"""

_MEASURE = """async ([family, weight, texts]) => {
  const font = `normal ${weight} 100px "${family}"`;
  await document.fonts.load(font, texts.join(""));
  if (!document.fonts.check(font, texts.join(""))) return null;
  const ctx = document.getElementById("c").getContext("2d");
  ctx.font = font;
  return texts.map(t => {
    const m = ctx.measureText(t);
    return m.actualBoundingBoxAscent + m.actualBoundingBoxDescent;
  });
}"""


@contextmanager
def ink_page():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        def serve(route):
            path = route.request.url.split(ORIGIN, 1)[1].split("?", 1)[0]
            if path == "/":
                return route.fulfill(body=_PAGE, content_type="text/html")
            f = (STATIC / path.removeprefix("/static/")).resolve()
            if STATIC not in f.parents or not f.is_file():
                return route.fulfill(status=404, body="")
            route.fulfill(body=f.read_bytes(),
                          content_type=mimetypes.guess_type(str(f))[0] or "font/woff2")

        page.route(f"{ORIGIN}/**", serve)
        page.goto(f"{ORIGIN}/")
        try:
            yield page
        finally:
            browser.close()


def ink_heights(page, family: str, weight: int, texts: list[str]) -> list[float] | None:
    """Ink height (px at 100px) of each text in 'CVT <family>' at `weight`;
    None when the face did not load (never a silent fallback's number)."""
    return page.evaluate(_MEASURE, [f"CVT {family}", weight, texts])


def ink_height(page, family: str, weight: int, text: str) -> float | None:
    got = ink_heights(page, family, weight, [text])
    return got[0] if got else None
