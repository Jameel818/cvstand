"""The A4 PDF page is Chromium's A4, 594.96 x 841.92pt (feature/paper-size).

Not ISO's 595.28 x 841.89: Chromium quantises the PDF page and cannot emit
that, whatever @page says (measured: mm, pt, in, px and "A4" all give
594.96 x 841.92 - the page Chrome's own "Save as PDF > A4" makes). 0.32pt
off, inside ISO 216's +-2mm; the check below holds it to 0.5pt of ISO too.

The twin of test_pdf_letter_page.py. An A4 CV keeps the 850px-wide canvas,
1202px tall, printed at 594.96 / 637.5 = 0.93327 so a template px is
0.69996pt, Word's 0.70033 to 0.05% (app/paper.py). Same two ways to get it wrong: the document's own
@page wins and the page is 850x1202 CSS px, or the content is scaled twice.
So the paper AND the size of the largest text are checked.

The Letter test is left exactly as it was: a CV with no `paper` field is
Letter, and its page did not move.

Exports go through the real route on the live server, never render_pdf()
in-process (tests/test_suite_invariants.py).
"""
from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from app.paper import A4
from app.rendering import document_html
from tests import letter_samples as LS
from tests.e2e.test_pdf_letter_page import _export, _largest_text_pt

pytestmark = pytest.mark.e2e

A4_PT = A4.pdf_pt                         # (594.96, 841.92)
ISO_A4 = (595.28, 841.89)

CASES = [(key, lang, "cv", 1)
         for key in ("modern-t1", "modern-t15", "modern-t22", "ats-t1", "ats-t22")
         for lang in ("en", "ar")] + [
         (key, lang, part, pages)
         for key in ("modern-t1", "ats-t22")
         for lang in ("en", "ar")
         for part, pages in (("letter", 1), ("both", 2))]


def _a4(lang):
    d = LS.with_letter(lang)
    d["paper"] = "a4"
    return d


@pytest.mark.parametrize("key,lang,part,pages", CASES)
def test_every_a4_page_is_exactly_a4(live_server, key, lang, part, pages):
    r = PdfReader(io.BytesIO(_export(live_server, _a4(lang), key, part)))
    assert len(r.pages) == pages, f"{key} {lang} {part}: {len(r.pages)} pages"
    for i, pg in enumerate(r.pages):
        size = (round(float(pg.mediabox.width), 2), round(float(pg.mediabox.height), 2))
        assert size == A4_PT, f"{key} {lang} {part} page {i + 1}: {size} pt, not A4"
        assert all(abs(a - b) < 0.5 for a, b in zip(size, ISO_A4))


@pytest.mark.parametrize("key", ["modern-t1", "ats-t22"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_an_a4_template_px_is_070033pt(live_server, page, key, lang):
    data = _a4(lang)
    pt = _largest_text_pt(PdfReader(io.BytesIO(_export(live_server, data, key, "cv"))))
    page.set_content(document_html(data, key, for_pdf=True), wait_until="networkidle")
    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
    page.emulate_media(media="print")
    px = page.evaluate("""() => Math.max(...[...document.querySelectorAll('.tpl *')]
        .filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
        .map((e) => parseFloat(getComputedStyle(e).fontSize)))""")
    # 0.69996pt per px on Chromium's sheet, Word's 0.70033 to 0.05%
    assert pt == pytest.approx(px * A4.pt_per_px, abs=0.05), (
        f"{key} {lang}: largest text {pt:.3f}pt, canvas {px}px -> expected "
        f"{px * A4.pt_per_px:.3f}pt (Letter's 0.72 would be {px * 0.72:.3f})")
