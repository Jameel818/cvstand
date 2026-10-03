"""Render modern-t22's rail word ("RESUME" / "سيرة ذاتية") as the PICTURE the
Word export places in the page header (run 6, user requirement).

The rail word is fixed artwork: never editable, never following the Fonts
panel, identical in Word, LibreOffice and Google Docs, and it must not wrap
or break. A text box did all of those things wrong outside Word (LibreOffice
set it horizontal and broken into lines). So the Word export carries the rail
exactly as the PDF draws it: this tool renders the template's own rail
(the same HTML and CSS the PDF prints, fonts inlined) with everything else
hidden, on a transparent background, at 300 dpi (the page is 850 CSS px =
8.5 in, so x3), clipped to the 215px rail strip, full page height.

    venv/Scripts/python tools/build_t22_rail.py           # write the PNGs
    venv/Scripts/python tools/build_t22_rail.py --check   # exit 1 if stale

Output: app/static/rails/modern-t22-{en,ar}.png (app/static/**/*.png ships
in the image; .dockerignore drops every other PNG).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.rendering import document_html  # noqa: E402

OUT = ROOT / "app" / "static" / "rails"
RAIL_W, PAGE_W, PAGE_H, SCALE = 215, 850, 1100, 3
SAMPLES = {"en": ROOT / "data" / "demo_resume.json", "ar": ROOT / "data" / "demo_resume_ar.json"}
ONLY_RAIL = """<style>
  html, body, .tpl { background: transparent !important; box-shadow: none !important; }
  .tpl * { visibility: hidden !important; }
  .tpl .vrail, .tpl .vrail * { visibility: visible !important; }
  .tpl *:not(.vrail):not(.vrail *) { background: transparent !important; border-color: transparent !important; }
</style>"""


def render(lang: str) -> bytes:
    from playwright.sync_api import sync_playwright
    data = json.loads(SAMPLES[lang].read_text(encoding="utf-8"))
    html = document_html(data, "modern-t22", for_pdf=True).replace("</head>", ONLY_RAIL + "</head>")
    x = PAGE_W - RAIL_W if lang == "ar" else 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": PAGE_W, "height": PAGE_H}, device_scale_factor=SCALE)
        pg.set_content(html, wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
        pg.emulate_media(media="print")
        png = pg.screenshot(clip={"x": x, "y": 0, "width": RAIL_W, "height": PAGE_H},
                            omit_background=True)
        b.close()
    return png


def _same(a: bytes, b: bytes) -> bool:
    """Pixel comparison (PNG bytes can differ with identical pixels)."""
    from PIL import Image, ImageChops
    A = Image.open(io.BytesIO(a)).convert("RGBA")
    B = Image.open(io.BytesIO(b)).convert("RGBA")
    if A.size != B.size:
        return False
    d = ImageChops.difference(A, B).convert("L").point(lambda v: 255 if v > 40 else 0)
    return d.histogram()[255] <= 0.001 * A.width * A.height


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "ar"):
        png = render(lang)
        path = OUT / f"modern-t22-{lang}.png"
        if check:
            if not path.exists() or not _same(path.read_bytes(), png):
                stale.append(path.name)
        else:
            path.write_bytes(png)
            print(f"wrote {path.relative_to(ROOT)} ({len(png) // 1024} KB)")
    if check:
        print(("STALE " + ", ".join(stale) + ": re-run tools/build_t22_rail.py") if stale
              else "OK  t22 rail pictures match the template")
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
