"""Word fidelity run 7 - the user's review of the 24 Arabic Modern downloads.

- The PDF's auto-fit seats a page the chosen sizes made a little too long
  (gaps, then type down to 0.90); Word had none, so the 12pt-Details files
  spilled a side section onto page 2. docx_design.render now takes the same
  steps - block gaps and type only, the line spacing stays natural.
- Rounded corners: the masks overlap the block's edge (a hairline of the
  block's fill showed along its square outline in Word's print/PDF).
- t23: whole seam dots (no cell shading over them) and a rounded title pill;
  t21: the header card's corner masks hang above its inner table; t18/all
  ringed photos: the ring is the picture's OUTER edge; t10: the PDF's slider.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter

import pytest
from lxml import etree
from PIL import Image

from app.exporters import docx_design
from app.exporters.docx import render_docx
from app.exporters.word_designs import common

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
V = "{urn:schemas-microsoft-com:vml}"
EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
docx_design._load()
MODERN = sorted(docx_design.DESIGNS)
#: the user's Fonts panel for t1-t4 and t6-t16 (reproduced byte-for-byte in run 7)
USER = dict(font_body_size=12, font_body="Markazi Text")


def _data(lang, **kw):
    d = json.loads(json.dumps(AR if lang == "ar" else EN))
    d.update(kw)
    return d


def _xml(data, key) -> bytes:
    return zipfile.ZipFile(io.BytesIO(render_docx(data, key))).read("word/document.xml")


def _sizes(xml: bytes) -> Counter:
    return Counter(int(v) for v in re.findall(rb'<w:sz w:val="(\d+)"', xml))


def _lines(xml: bytes) -> Counter:
    return Counter(re.findall(rb'w:line="(\d+)"', xml))


@pytest.mark.parametrize("key", MODERN)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_default_demo_is_not_fitted(key, lang):
    """The demo at the template's own sizes is what run 6 measured: never
    rescaled. Exceptions: t16 Arabic's estimate runs 7pt long, it takes a gap
    step only, never type; t1 Arabic counts its side-gap squeeze as overflow
    since run 8 (its sections keep the PDF's spacing), a mild fit - Word
    measured 6.6% strict, one page."""
    doc, _ = docx_design.render(_data(lang), key, None)
    if (key, lang) == ("modern-t16", "ar"):
        assert doc.cvstand_fit is None or doc.cvstand_fit[1] == 1.0
    elif (key, lang) == ("modern-t1", "ar"):
        assert doc.cvstand_fit is None or (doc.cvstand_fit[0] >= 0.85
                                           and doc.cvstand_fit[1] >= 0.94)
    else:
        assert doc.cvstand_fit is None


@pytest.mark.parametrize("key", ["modern-t3", "modern-t4", "modern-t7", "modern-t9",
                                 "modern-t15", "modern-t16"])
def test_user_12pt_side_column_is_fitted(key):
    """The user's 12pt Markazi downloads that spilled in Word: fitted, within
    the floors, and estimated to end on page 1."""
    doc, res = docx_design.render(_data("ar", **USER), key, None)
    assert doc.cvstand_fit is not None
    gaps, type_k = doc.cvstand_fit
    assert gaps >= 0.85 and type_k >= 0.90
    assert docx_design.page_overflow_pt(doc, res) <= docx_design.TYPE_FIT_FLOOR_OK_PT


def test_fit_keeps_line_spacing_natural():
    """Natural spacing rule: the fit scales sizes and block gaps, never the
    line multiples (each stays the template's CSS line / the face's single)."""
    data = _data("ar", **USER)
    plain, _ = docx_design._render(data, "modern-t7", None)
    fitted, _ = docx_design._render(data, "modern-t7", None, 0.85, 0.90)
    to_xml = lambda d: etree.tostring(d.element.body)  # noqa: E731
    assert _lines(to_xml(plain)) == _lines(to_xml(fitted))
    a, b = _sizes(to_xml(plain)), _sizes(to_xml(fitted))
    assert max(b.elements()) < max(a.elements())         # the type came down
    assert b[2] == a[2]                                  # structural runs untouched


def test_long_cv_is_left_to_flow():
    """A main column far past the page is a long CV: nothing is scaled."""
    d = _data("en")
    d["experience"] = d["experience"] * 3
    doc, _ = docx_design.render(d, "modern-t16", None)
    assert doc.cvstand_fit is None


def test_corner_masks_overlap_the_block_edge():
    """Each mask is r + CORNER_OVERLAP_PT square and starts that far outside
    the block (t23's pill, Arabic)."""
    xml = _xml(_data("ar"), "modern-t23")
    root = etree.fromstring(xml)
    masks = [s for s in root.iter(V + "shape") if "qx" in (s.get("path") or "")
             or "qy" in (s.get("path") or "")]
    assert len(masks) >= 4
    for m in masks:
        st = dict(kv.split(":", 1) for kv in m.get("style").split(";") if ":" in kv)
        assert float(st["width"].rstrip("pt")) == pytest.approx(
            float(st["height"].rstrip("pt")))
        assert "l100," in m.get("path") or "l0,100" in m.get("path")
    tops = [m for m in masks if m.get("path").startswith("m0,0 l100,0")]
    assert tops and all("margin-top:-0.75pt" in m.get("style") for m in tops)


def test_t23_dots_are_not_under_cell_shading_and_pill_is_round():
    root = etree.fromstring(_xml(_data("ar"), "modern-t23"))
    body_tbl = root.find(f"{W}body/{W}tbl")
    first = body_tbl.find(f"{W}tr").findall(f"{W}tc")
    fills = [tc.find(f"{W}tcPr/{W}shd") for tc in first]
    assert all(f is None or f.get(W + "fill") in (None, "auto") for f in fills)
    # the title pill: a black cell with corner masks in the page colour
    pill = [tc for tc in root.iter(W + "tc")
            if (tc.find(f"{W}tcPr/{W}shd") is not None
                and tc.find(f"{W}tcPr/{W}shd").get(W + "fill") == "151517")]
    assert pill
    assert len([s for s in pill[0].iter(V + "shape") if s.get("fillcolor") == "#FFFFFF"]) == 4


def test_t21_header_corner_masks_hang_above_its_table():
    root = etree.fromstring(_xml(_data("ar"), "modern-t21"))
    head = root.find(f"{W}body/{W}tbl/{W}tr/{W}tc")
    kids = [k for k in head if k.tag in (W + "p", W + "tbl")]
    assert kids[0].tag == W + "p"
    assert len([s for s in kids[0].iter(V + "shape")]) == 2    # the two top masks


@pytest.mark.parametrize("key, ring", [("modern-t18", (255, 255, 255)),
                                       ("modern-t2", None)])
def test_photo_ring_is_the_outer_edge(key, ring):
    """No strip of the placeholder colour outside the ring (t18's second frame)."""
    z = zipfile.ZipFile(io.BytesIO(render_docx(_data("en"), key)))
    pics = [Image.open(io.BytesIO(z.read(n))).convert("RGBA") for n in z.namelist()
            if n.startswith("word/media/") and n.endswith(".png")]
    framed = [p for p in pics if p.width > 200]
    assert framed
    p = framed[0]
    if ring:                                    # rectangle: the very corner is ring
        assert p.getpixel((1, 1))[:3] == ring
        assert p.getpixel((p.width // 2, 1))[:3] == ring


def test_t10_skills_are_sliders():
    """A white knob ringed in the fill on each rated skill, as the PDF."""
    xml = _xml(_data("en"), "modern-t10")
    knobs = re.findall(rb'<v:oval [^>]*fillcolor="#FFFFFF" strokecolor="#38BDF8"', xml, re.I)
    rated = [s for s in EN["skills"] if s.get("level") or s.get("percent")]
    assert len(knobs) == len(rated) > 0


def test_corner_paths_cover_the_outer_strip():
    """The grown masks reach their full square along both outer edges."""
    for key, path in common._CORNER_OVER.items():
        p = path.format(k=100, a=7, b=93)
        assert p.startswith("m") and p.endswith("x e")
        assert "qx" in p or "qy" in p
