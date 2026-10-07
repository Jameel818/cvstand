"""modern-t4 "Ribbon Sidebar" ("شريط جانبي بأوشحة"): in Arabic the ribbons'
folded ends mirror (user, 2026-10-07).

Each clay ribbon overhangs the rail by 14px and folds back behind the page:
a dark triangle under the overhang whose straight edge lies against the
rail's edge. That edge is the triangle's inline START - left in English,
right in Arabic. The position mirrored already (inset-inline-end); the
SHAPE did not, because clip-path and the Word VML path are physical, so the
Arabic folds pointed outwards. English is correct and must not move.
"""
from __future__ import annotations

import io
import re
import zipfile

from app.exporters.docx import render_docx
from app.rendering import canvas_html
from tests.samples import ARABIC, ENGLISH

LTR_FOLD = "clip-path:polygon(0 0, 100% 0, 0 100%)"
RTL_FOLD = "clip-path:polygon(0 0, 100% 0, 100% 100%)"


def _folds_html(data):
    return re.findall(r"clip-path:polygon\([^)]*\)", canvas_html(data, "modern-t4"))


def _folds_word(data):
    with zipfile.ZipFile(io.BytesIO(render_docx(data, "modern-t4"))) as z:
        xml = "".join(z.read(n).decode("utf-8") for n in z.namelist()
                      if n.startswith("word/") and n.endswith(".xml"))
    # Both of Word's copies: the VML fallback path and the DrawingML geometry
    # Word 2010+ actually draws (its third point is the fold's inner corner).
    vml = re.findall(r'path="(m0,0 l14,0 l(?:0|14),8 x e)"', xml)
    dml = re.findall(r'<a:path w="14" h="8"><a:moveTo><a:pt x="0" y="0"/></a:moveTo>'
                     r'<a:lnTo><a:pt x="14" y="0"/></a:lnTo><a:lnTo><a:pt x="(\d+)" y="8"/>', xml)
    assert len(vml) == len(dml), (vml, dml)
    return [f"{v}|dml-x{d}" for v, d in zip(vml, dml)]


def test_english_folds_are_unchanged():
    folds = _folds_html(ENGLISH)
    assert len(folds) == 4 and set(folds) == {LTR_FOLD}
    assert set(_folds_word(ENGLISH)) == {"m0,0 l14,0 l0,8 x e|dml-x0"}


def test_arabic_folds_are_mirrored_in_the_pdf_and_preview():
    folds = _folds_html(ARABIC)
    assert len(folds) == 4, folds
    assert set(folds) == {RTL_FOLD}, "an Arabic ribbon fold still faces outwards"


def test_arabic_folds_are_mirrored_in_word():
    folds = _folds_word(ARABIC)
    assert folds, "the Word ribbons lost their folds"
    assert set(folds) == {"m0,0 l14,0 l14,8 x e|dml-x14"}, folds
