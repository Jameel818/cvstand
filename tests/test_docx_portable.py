"""Design shapes readable outside Microsoft Word (run 6).

LibreOffice showed modern-t2's Arabic skill bars missing, its sidebar short of
the page foot, and modern-t22's rail word horizontal and its rings without
arcs: every design shape was VML only. Each is now DrawingML (wps / wpg) in
mc:AlternateContent with the unchanged VML as mc:Fallback - the way Word
itself writes shapes since 2010.

And modern-t22's rail word is a PICTURE in the page header (fixed artwork:
not editable, never following the Fonts panel)."""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from lxml import etree
from PIL import Image

from app.exporters import docx_design
from app.exporters.docx import render_docx
from app.exporters.docx_dml import Sp, _geom

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
V = "{urn:schemas-microsoft-com:vml}"
EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
docx_design._load()
MODERN = sorted(docx_design.DESIGNS)
VML_SHAPES = {V + n for n in ("rect", "roundrect", "oval", "arc", "shape", "group", "line")}
CHOICES = {"en": dict(font_name="Playfair Display", font_heading="Lora", font_body="Inter",
                      font_name_size=40, font_heading_size=16, font_body_size=11),
           "ar": dict(font_name="Amiri", font_heading="Lateef", font_body="Noto Naskh Arabic",
                      font_name_size=40, font_heading_size=18, font_body_size=12)}


def _parts(blob: bytes) -> dict[str, etree._Element]:
    z = zipfile.ZipFile(io.BytesIO(blob))
    return {n: etree.fromstring(z.read(n)) for n in z.namelist()
            if re.fullmatch(r"word/(document|header\d+|footer\d+)\.xml", n)}


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", MODERN)
def test_every_design_shape_has_drawingml_with_a_vml_fallback(key, lang):
    parts = _parts(render_docx(AR if lang == "ar" else EN, key))
    n_alt = 0
    for name, root in parts.items():
        for pict in root.iter(W + "pict"):
            # no bare VML: every w:pict is the Fallback of an AlternateContent
            fb = pict.getparent()
            assert fb.tag == MC + "Fallback", (name, "VML outside mc:Fallback")
            alt = fb.getparent()
            choice = alt.find(MC + "Choice")
            assert choice is not None and choice.find(W + "drawing") is not None, name
            assert choice.get("Requires") in ("wps", "wpg"), name
            n_alt += 1
            # the two describe the same shapes: as many DrawingML shapes as VML ones
            n_vml = sum(1 for el in pict.iter() if el.tag in VML_SHAPES and el.tag != V + "group")
            n_dml = sum(1 for el in choice.iter()
                        if el.tag == "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}wsp")
            assert n_vml == n_dml, (name, n_vml, n_dml)
        # docPr ids unique within the part (Word repairs duplicates)
        ids = [el.get("id") for el in root.iter(WP + "docPr")]
        assert len(ids) == len(set(ids)), (name, "duplicate docPr id")
    assert n_alt, f"{key} {lang}: no design shapes found"


def test_ring_arcs_start_at_twelve_and_run_clockwise():
    # VML convention used by the designs: 0 deg = 12 o'clock, clockwise.
    # DrawingML: 0 = 3 o'clock, clockwise, 60000ths of a degree.
    g = _geom(Sp("arc", 0, 0, 10, 10, line="000000", start=0, end=144))     # 40 %
    assert 'name="adj1" fmla="val 16200000"' in g
    assert 'name="adj2" fmla="val 3240000"' in g                             # 414 - 360 = 54 deg


def test_roundrect_radius_matches_vml_arcsize():
    # VML arcsize = radius / (half the smaller side); DrawingML adj = radius / smaller side
    assert 'fmla="val 50000"' in _geom(Sp("roundRect", 0, 0, 100, 10, radius=1.0))
    assert 'fmla="val 25000"' in _geom(Sp("roundRect", 0, 0, 100, 10, radius=0.5))


# ---- modern-t22's rail word ----------------------------------------------------

def _header_pictures(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    out = []
    for n in z.namelist():
        if not re.fullmatch(r"word/header\d+\.xml", n):
            continue
        root = etree.fromstring(z.read(n))
        rel_name = n.replace("word/", "word/_rels/") + ".rels"
        if rel_name not in z.namelist():
            continue
        rels = etree.fromstring(z.read(rel_name))
        target = {r.get("Id"): r.get("Target") for r in rels}
        for anchor in root.iter(WP + "anchor"):
            pr = anchor.find(WP + "docPr")
            if pr is None or pr.get("name") != "cvstand_rail":
                continue
            blip = next(anchor.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"))
            rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            out.append((anchor, z.read("word/" + target[rid])))
    return out


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_t22_rail_word_is_a_header_picture_behind_the_text(lang):
    blob = render_docx(AR if lang == "ar" else EN, "modern-t22")
    pics = _header_pictures(blob)
    assert len(pics) == 1
    anchor, png = pics[0]
    assert anchor.get("behindDoc") == "1"
    assert anchor.find(WP + "wrapNone") is not None
    assert anchor.find(WP + "positionH").get("relativeFrom") == "page"
    x = int(anchor.find(f"{WP}positionH/{WP}posOffset").text) / 12700
    w = int(anchor.find(WP + "extent").get("cx")) / 12700
    h = int(anchor.find(WP + "extent").get("cy")) / 12700
    # the PDF rail: the 215px strip at the start edge, full page height (1px = 0.72pt)
    assert w == pytest.approx(215 * 0.72, abs=0.1) and h == pytest.approx(792, abs=0.1)
    assert x == pytest.approx((850 - 215) * 0.72 if lang == "ar" else 0, abs=0.1)
    assert png == open(f"app/static/rails/modern-t22-{lang}.png", "rb").read()
    # and no text box, no editable rail text anywhere
    for root in _parts(blob).values():
        assert root.find(".//" + V + "textbox") is None
        assert root.find(".//" + W + "txbxContent") is None


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_t22_rail_word_ignores_every_font_choice(lang):
    base = AR if lang == "ar" else EN
    plain = _header_pictures(render_docx(base, "modern-t22"))[0]
    chosen = _header_pictures(render_docx(dict(base, **CHOICES[lang]), "modern-t22"))[0]
    assert plain[1] == chosen[1]
    for attr in ("cx", "cy"):
        assert plain[0].find(WP + "extent").get(attr) == chosen[0].find(WP + "extent").get(attr)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_t22_rail_word_fills_the_rail(lang):
    """The PDF rail track is 1043.5px; the word's ink must cover >= 95% of it
    (300 dpi picture: 3 px per CSS px), and stay inside the 215px strip."""
    im = Image.open(f"app/static/rails/modern-t22-{lang}.png")
    assert im.size == (215 * 3, 1100 * 3) and im.mode == "RGBA"
    l, t, r, b = im.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    assert (b - t) / 3 >= 0.95 * 1043.5, (lang, (b - t) / 3)
    assert l > 0 and r < im.width                     # not clipped by the strip


def test_the_estimator_measures_wrapped_shapes_as_before():
    """docx_measure read inline VML (w:pict) for a skill bar's height; run 6
    wraps it in mc:AlternateContent. The estimate must be what it was, or the
    near-one-page fit drifts silently (found while wrapping: every inline bar
    stopped counting)."""
    from app.exporters.docx_measure import Measure
    doc, resolved = docx_design.render(EN, "modern-t2", None)
    root = doc.element.body
    p = next(el for el in root.iter(W + "p")
             if el.find(f".//{MC}AlternateContent") is not None
             and el.find(f".//{MC}AlternateContent//{WP}inline") is not None)
    import copy
    q = copy.deepcopy(p)
    for alt in list(q.iter(MC + "AlternateContent")):
        alt.getparent().replace(alt, alt.find(f"{MC}Fallback/{W}pict"))
    m = Measure(resolved)
    assert m.paragraph(p, 200) == m.paragraph(q, 200) > 0
