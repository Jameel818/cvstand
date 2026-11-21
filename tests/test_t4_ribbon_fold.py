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

import pytest

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


# ---- 2026-10-08: Arabic ribbons as tall as the English ones ----------------
# The ribbon is padding + one line of its label. The Arabic faces' own line is
# 1.5-1.9x their size against Archivo's 1.088x, so every Arabic ribbon came
# out ~8px taller in the PDF and in Word (measured 48-49px vs 40-41px). The
# Arabic label now takes Archivo's line. tests/e2e/test_t4_ribbon_height.py
# measures the rendered heights.

def test_arabic_ribbon_labels_take_the_english_line():
    html_ar = canvas_html(ARABIC, "modern-t4")
    html_en = canvas_html(ENGLISH, "modern-t4")
    assert html_ar.count("line-height:1.088;") == 4
    assert "line-height:1.088;" not in html_en, "the English ribbon moved"


def _ribbon_paragraphs(data):
    with zipfile.ZipFile(io.BytesIO(render_docx(data, "modern-t4"))) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # each ribbon label paragraph carries its overhang and its fold (VML path)
    return xml, [m.group(0) for m in re.finditer(
        r"<w:p>(?:(?!</w:p>).)*?m0,0 l14,0 l(?:0|14),8 x e(?:(?!</w:p>).)*?</w:p>", xml, re.S)]


def test_arabic_word_ribbons_take_the_english_line():
    """2026-10-08: the Arabic label takes Archivo's 1.088 line (tighter than its
    face's single), so the Arabic ribbon is as tall as the English one."""
    _, paras = _ribbon_paragraphs(ARABIC)
    lines = [int(re.search(r'<w:spacing [^>]*w:line="(\d+)"', p).group(1)) for p in paras]
    assert len(lines) == 4 and all(v < 240 for v in lines), lines


# ---- 2026-11-20: the English Word ribbon taller than its overhang -----------
# (user's modern-t4-en-cv-LETTER.docx). Word draws the label in "Archivo Black"
# at Word's single line, which is that file's Windows line: 1.51em for the
# embedded face (archivo-900.ttf), 1.347em for Google's Archivo Black where it
# is installed (it is, on the machine that reported it). The overhang and fold
# were fixed at the CSS 1.088 line, so the ribbon ran 5-8px past the overhang
# and the fold sat on the ribbon. Now the ribbon ROW is exactly the PDF's
# height and the overhang and fold are placed from that same number, whatever
# face Word picks.

@pytest.mark.parametrize("paper", ["letter", "a4"])
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_word_ribbon_overhang_and_fold_match_the_ribbon_height(data, paper):
    """The overhang is exactly as tall as its ribbon and the fold starts at the
    ribbon's bottom: the ribbon row is pinned to that same height (exact)."""
    data = dict(data, paper=paper)
    xml, paras = _ribbon_paragraphs(data)
    rows = [int(v) / 20 for v in re.findall(r'<w:trHeight w:val="(\d+)" w:hRule="exact"/>', xml)]
    assert len(paras) == 4 and len(rows) == 4, (len(paras), rows)
    for p, row_pt in zip(paras, rows):
        hs = [float(v) for v in re.findall(r"height:([0-9.]+)pt", p)]
        tops = [float(v) for v in re.findall(r"margin-top:([0-9.]+)pt", p)]
        assert len(hs) == 2 and len(tops) == 2, (hs, tops)
        overhang_h, fold_top = hs[0], tops[1]
        assert abs(overhang_h - row_pt) < 0.06, (overhang_h, row_pt)
        assert abs(fold_top - row_pt) < 0.06, (fold_top, row_pt)
        assert tops[0] == 0.0
