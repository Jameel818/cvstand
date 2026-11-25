"""What the real-Word audit (tools/word_audit.py, feature/word-audit) found,
checked in the documents on every run - no Word needed. Each test failed on
the code before that run (033c791).

    PAGE FOOT   a side column / card / column rule that the PDF carries to
                the page's foot reaches it in Word too, CV AND letter
                (modern-t21's card, modern-t1/t6's dividers)
    HEADERS     a header takes no room: no default header paragraph pushes a
                full-bleed band off the paper's top (modern-t13: 17-21px)
    PHOTO       the photo's frame (extent and crop) is the same in the CV and
                the cover letter (modern-t20), and in the PDF's letter
    ATS RULES   section rules stop with their section (ats-t18), a div rule
                keeps the gap above it and its own width (ats-t14, t10), a
                box drawn by its borders is drawn (ats-t9)
    LETTERS     the letter keeps the band's headline (modern-t14 AR), drops
                the rules of what it hides (modern-t8, t13, ats-t5 PDF) and
                sets its body where the PDF does (modern-t12)

What Word DRAWS (page counts, positions, the photo, every line) is checked
by the real-Word audit: `pytest --word tests/test_word_audit_real.py`.
"""
from __future__ import annotations

import copy
import io
import re
import zipfile

import pytest
from lxml import etree

from app import registry
from app.exporters.docx import render_docx
from tests import letter_samples as LS

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
KEYS = sorted(registry.ported_keys())
#: pt per canvas px: the 850px canvas is the page's width
PT_PX = {"letter": 612 / 850, "a4": 595.3 / 850}


def _data(lang, paper):
    d = copy.deepcopy(LS.with_letter(lang))
    d.pop("paper", None)
    if paper == "a4":
        d["paper"] = "a4"
    return d


def _parts(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return {n: z.read(n) for n in z.namelist()}


def _doc(parts):
    return etree.fromstring(parts["word/document.xml"])


def _text(el):
    return "".join(t.text or "" for t in el.iter(f"{W}t"))


def _page_h_px(paper):
    return (841.9 if paper == "a4" else 792) / PT_PX[paper]


def _anchor(parts, name, paper):
    """(y_px, h_px) of the page-anchored shape `name` in the body (the copy
    body_page_shapes makes) - the first one."""
    doc = _doc(parts)
    for a in doc.iter(f"{WP}anchor"):
        pr = a.find(f"{WP}docPr")
        # the body's copy (body_page_shapes names it <name>_p<N>)
        if pr is not None and (pr.get("name") or "").startswith(name + "_p"):
            y = int(a.find(f"{WP}positionV/{WP}posOffset").text)
            h = int(a.find(f"{WP}extent").get("cy"))
            k = 12700 * PT_PX[paper]
            return y / k, h / k
    return None


# ---------------------------------------------------------------- PAGE FOOT

FOOT = {  # shape name -> (template, px above the page foot where the PDF's ends)
    "cvstand_sidecard": ("modern-t21", 24),
    "cvstand_t1rule": ("modern-t1", 56),
    "cvstand_t6rule": ("modern-t6", 48),
}


@pytest.mark.parametrize("name", sorted(FOOT))
@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("paper", ["letter", "a4"])
@pytest.mark.parametrize("part", ["cv", "letter"])
def test_columns_reach_the_page_foot(name, lang, paper, part):
    key, foot = FOOT[name]
    parts = _parts(render_docx(_data(lang, paper), key, part))
    got = _anchor(parts, name, paper)
    assert got is not None, f"{key} {part}: no {name} - the column stops with its text"
    y, h = got
    assert abs(y + h - (_page_h_px(paper) - foot)) <= 1.5, (key, part, y + h)


# ---------------------------------------------------------------- HEADERS

@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_headers_take_no_room(key, lang):
    """Every header paragraph is a tiny one (a default header paragraph is
    ~14pt tall at distance 0 and pushes the page's first line down)."""
    for part in ("cv", "letter"):
        parts = _parts(render_docx(_data(lang, "letter"), key, part))
        for n, xml in parts.items():
            if not re.fullmatch(r"word/header\d+\.xml", n):
                continue
            for p in etree.fromstring(xml).iter(f"{W}p"):
                sz = p.find(f"{W}pPr/{W}rPr/{W}sz")
                assert sz is not None and int(sz.get(f"{W}val")) <= 2, (key, lang, part, n)


# ---------------------------------------------------------------- PHOTO

PHOTO_KEYS = ["modern-t2", "modern-t3", "modern-t4", "modern-t5", "modern-t7", "modern-t8",
              "modern-t10", "modern-t11", "modern-t14", "modern-t15", "modern-t16", "modern-t17",
              "modern-t18", "modern-t20", "modern-t21", "modern-t24"]


def _frame(parts):
    doc = _doc(parts)
    for pic in doc.iter("{http://schemas.openxmlformats.org/drawingml/2006/picture}pic"):
        box = next(a for a in pic.iterancestors() if a.tag in (f"{WP}inline", f"{WP}anchor"))
        ext = box.find(f"{WP}extent")
        src = pic.find(f".//{A}srcRect")
        return (ext.get("cx"), ext.get("cy"), etree.tostring(src) if src is not None else b"")
    return None


@pytest.mark.parametrize("key", PHOTO_KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("paper", ["letter", "a4"])
def test_photo_frame_is_the_cvs_in_the_letter(key, lang, paper, tmp_path, monkeypatch):
    from PIL import Image
    from app.exporters import docx as D
    monkeypatch.setattr(D, "UPLOADS_DIR", tmp_path)
    Image.new("RGB", (600, 600), "#556677").save(tmp_path / "me.png")
    d = _data(lang, paper)
    d["photo_url"] = "/uploads/me.png"
    cv = _frame(_parts(render_docx(d, key, "cv")))
    letter = _frame(_parts(render_docx(d, key, "letter")))
    assert cv is not None and cv == letter, (key, lang, paper, cv, letter)


def test_pdf_letter_keeps_a_shrinking_photos_column_in_place():
    """modern-t20's photo SHRINKS with its column's content: the PDF letter
    keeps that column hidden in place, so the photo is the CV's size."""
    from app import letter as L
    import lxml.html as LH
    for lang in ("en", "ar"):
        tpl = LH.fromstring(L.document_html(_data(lang, "a4"), "modern-t20", for_pdf=True))
        photo = next(e for e in tpl.iter() if "cv-photo" in (e.get("class") or ""))
        col = photo.getparent()
        hidden = [e for e in col.iter() if "visibility:hidden" in (e.get("style") or "").replace(" ", "")]
        assert hidden, lang


# ---------------------------------------------------------------- ATS RULES

def _body_paras(parts):
    return [p for p in _doc(parts).find(f"{W}body") if p.tag == f"{W}p"]


def _bdr(p, edge):
    return p.find(f"{W}pPr/{W}pBdr/{W}{edge}")


def _before(p):
    sp = p.find(f"{W}pPr/{W}spacing")
    return int(sp.get(f"{W}before", 0)) if sp is not None else 0


ATS = [k for k in KEYS if k.startswith("ats-")]


def _odd(p):
    ind = p.find(f"{W}pPr/{W}ind")
    return int(ind.get(f"{W}right", 0)) % 2 if ind is not None else 0


@pytest.mark.parametrize("key", ATS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_ats_side_rules_stop_with_their_section(key, lang):
    """A left/right paragraph border runs through the space before the next
    bordered paragraph: two sections 14px apart drew one unbroken rule
    (ats-t18). The gap goes into an unbordered paragraph."""
    paras = _body_paras(_parts(render_docx(_data(lang, "letter"), key, "cv")))
    for edge in ("left", "right"):
        for a, b in zip(paras, paras[1:]):
            if _bdr(a, edge) is not None and _bdr(b, edge) is not None:
                # a new section: docx_ats splits Word's border groups by an
                # end indent 1 twip odd/even
                if _odd(a) != _odd(b):
                    assert _before(b) == 0, (key, lang, _text(b)[:30])


def _rules(parts):
    """Empty paragraphs drawing a rule (a bottom border and no words)."""
    return [p for p in _body_paras(parts) if not _text(p).strip() and _bdr(p, "bottom") is not None]


@pytest.mark.parametrize("key", ["ats-t10", "ats-t14", "ats-t6", "ats-t13", "ats-t3"])
def test_ats_div_rules_keep_the_gap_above(key):
    parts = _parts(render_docx(_data("en", "letter"), key, "cv"))
    rules = _rules(parts)
    assert rules, key
    assert all(_before(p) > 0 for p in rules), key


def test_ats_t14_accent_rule_has_its_own_width():
    rule = _rules(_parts(render_docx(_data("en", "letter"), "ats-t14", "cv")))[0]
    ind = rule.find(f"{W}pPr/{W}ind")
    end = int(ind.get(f"{W}right", 0)) if ind is not None else 0
    # 74px of a ~722px measure: the rest is indent
    assert end > 8000, end


def test_ats_t9_double_rule_is_drawn():
    for lang in ("en", "ar"):
        paras = _body_paras(_parts(render_docx(_data(lang, "letter"), "ats-t9", "cv")))
        assert any(not _text(p).strip() and _bdr(p, "top") is not None and _bdr(p, "bottom") is not None
                   for p in paras), lang


# ---------------------------------------------------------------- LETTERS

def test_letter_band_keeps_the_headline_ar():
    """The Arabic demo's summary opens with its title: blanking the summary's
    words in the band took the headline too (modern-t14, t17)."""
    d = _data("ar", "letter")
    for key in ("modern-t14", "modern-t17"):
        assert d["title"] in _text(_doc(_parts(render_docx(d, key, "letter")))), key


def _band_tables_without_words_have_borders(parts):
    for tbl in _doc(parts).iter(f"{W}tbl"):
        if not _text(tbl).strip() and (tbl.find(f".//{W}tblBorders/{W}bottom") is not None):
            b = tbl.find(f".//{W}tblBorders/{W}bottom")
            if b.get(f"{W}val") not in ("nil", "none"):
                return True
    return False


def test_letter_drops_the_rules_of_hidden_chips():
    for lang in ("en", "ar"):
        parts = _parts(render_docx(_data(lang, "letter"), "modern-t8", "letter"))
        assert not _band_tables_without_words_have_borders(parts), lang
        # modern-t13: the band's rule over the chips goes with them
        doc = _doc(_parts(render_docx(_data(lang, "letter"), "modern-t13", "letter")))
        first = doc.find(f"{W}body/{W}tbl")
        assert not [p for p in first.iter(f"{W}p") if not _text(p).strip()
                    and _bdr(p, "bottom") is not None], lang


def test_t12_letter_body_beside_the_contact_list():
    for lang in ("en", "ar"):
        d = _data(lang, "letter")
        doc = _doc(_parts(render_docx(d, "modern-t12", "letter")))
        email = d["contact"]["email"]
        row = next(tr for tr in doc.iter(f"{W}tr") if email in _text(tr)
                   and tr.find(f".//{W}tbl") is None)
        assert d["cover_letter"]["recipient_name"] in _text(row), lang
        assert "CONTACT" not in _text(doc) and "التواصل" not in _text(doc), lang


def test_pdf_letter_drops_emptied_section_rules():
    """ats-t5's sections are drawn by a border-top: emptied below the body,
    they printed two grey lines under the signature."""
    from app import letter as L
    import lxml.html as LH
    for lang in ("en", "ar"):
        tpl = LH.fromstring(L.document_html(_data(lang, "a4"), "ats-t5", for_pdf=True))
        after, left = False, []
        for e in tpl.iter():
            if not isinstance(e.tag, str):
                continue
            if "cl-sign" in (e.get("class") or ""):
                after = True
                continue
            if after and len(e) == 0 and not (e.text or "").strip() and "border" in (e.get("style") or ""):
                left.append(e)
        assert not left, lang


@pytest.mark.parametrize("key", ["modern-t8", "modern-t13", "modern-t14", "modern-t17"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_letter_band_keeps_the_cvs_height(key, lang):
    """The band's hidden summary/chips keep their lines' height in the
    letter: one blank line stood for the summary's three and modern-t17's
    letter band came out shorter than its CV's (the PDF hides in place)."""
    from docx.oxml.ns import qn
    from app.exporters import docx_design as D
    from app.exporters import docx_letter as DL
    from app.exporters.docx_measure import Measure
    d = _data(lang, "letter")
    full, res = D.render(d, key, None)
    letter, _ = DL.design_letter_doc(d, key)
    m = Measure(res)

    def band(doc):
        box = DL._band_box(doc)
        return m.block(box, D._cell_w(box.find(qn("w:tcPr"))))
    assert abs(band(full) - band(letter)) <= 1.0, (band(full), band(letter))
