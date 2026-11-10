"""The PDF page is exactly US Letter, the same page as Word (2026-11-10).

Before this, page.pdf() printed the 850x1100px canvas at Chromium's 0.75pt
per CSS px: a 637.92 x 824.88pt page, ~4% larger than Letter, with every size
4% larger than the Word file's. Now the canvas is printed on Letter at scale
0.96, so a template px is 0.72pt in the PDF exactly as in Word
(docx_design.PX).

Two ways to get this wrong, both measured while choosing the fix:
  - the page stays 637.92 x 824.88 because the document's own
    `@page { size: 850px 1100px }` wins while prefer_css_page_size is on;
  - the page is Letter but the content is scaled TWICE (0.9216): with
    prefer_css_page_size off, Chromium already shrinks the 850px page to the
    paper by itself, and a `scale` on top of that shrinks it again.
So this checks the paper AND the size of the text on it: the largest text in
the PDF must be the largest CSS font size on the canvas x 0.72pt.

Cover letters go through the same printer, so `part` letter and both are
checked too, EN and AR, Modern and ATS. Exports go through the real route
(POST /export/pdf on the live server), never render_pdf() in-process: that
would enter sync_playwright a second time in this session
(tests/test_suite_invariants.py).
"""
from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request

import pytest
from pypdf import PdfReader

from app.rendering import document_html
from tests import letter_samples as LS

pytestmark = pytest.mark.e2e

LETTER = (612.0, 792.0)
PX_PT = 0.72                                   # docx_design.PX: Word's rule

CASES = [(key, lang, "cv", 1)
         for key in ("modern-t1", "modern-t22", "ats-t1", "ats-t22")
         for lang in ("en", "ar")] + [
         (key, lang, part, pages)
         for key in ("modern-t1", "ats-t22")
         for lang in ("en", "ar")
         for part, pages in (("letter", 1), ("both", 2))]


def _export(live_server, data, key, part) -> bytes:
    """POST /export/pdf, waiting out the rate limit (Retry-After) like
    test_pdf_fonts.py does."""
    req = urllib.request.Request(
        live_server.url + "/export/pdf",
        data=json.dumps({"data": data, "template_key": key, "part": part}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                return res.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(float(exc.headers.get("Retry-After") or 10))
    raise AssertionError("PDF export stayed rate-limited")


def _largest_text_pt(reader) -> float:
    sizes = []
    reader.pages[0].extract_text(
        visitor_text=lambda t, cm, tm, fd, fs: sizes.append(fs * tm[0] * cm[0]) if t.strip() else None)
    return max(sizes)


@pytest.mark.parametrize("key,lang,part,pages", CASES)
def test_every_page_is_exactly_us_letter(live_server, key, lang, part, pages):
    r = PdfReader(io.BytesIO(_export(live_server, LS.with_letter(lang), key, part)))
    assert len(r.pages) == pages, f"{key} {lang} {part}: {len(r.pages)} pages"
    for i, pg in enumerate(r.pages):
        size = (round(float(pg.mediabox.width), 2), round(float(pg.mediabox.height), 2))
        assert size == LETTER, f"{key} {lang} {part} page {i + 1}: {size} pt, not Letter"


@pytest.mark.parametrize("key", ["modern-t1", "ats-t22"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_a_template_px_is_072pt_in_the_pdf(live_server, page, key, lang):
    """Not scaled twice, not left at 0.75: the largest text (the name) prints
    at its canvas px x 0.72, the Word export's rule."""
    data = LS.with_letter(lang)
    pt = _largest_text_pt(PdfReader(io.BytesIO(_export(live_server, data, key, "cv"))))
    page.set_content(document_html(data, key, for_pdf=True), wait_until="networkidle")
    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
    page.emulate_media(media="print")
    px = page.evaluate("""() => Math.max(...[...document.querySelectorAll('.tpl *')]
        .filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
        .map((e) => parseFloat(getComputedStyle(e).fontSize)))""")
    assert pt == pytest.approx(px * PX_PT, abs=0.05), (
        f"{key} {lang}: largest text {pt:.3f}pt, canvas {px}px -> expected {px * PX_PT:.3f}pt "
        f"(0.75/px would be {px * 0.75:.3f}, double-scaled {px * 0.6912:.3f})")
