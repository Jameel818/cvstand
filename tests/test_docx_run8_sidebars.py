"""Word fidelity run 8 - sidebars solid on Word's SCREEN.

Word dims the header layer while the body is edited: a full-height colour
drawn only in the header showed pale above/below the table and as a light
line where it overhangs the coloured cell (the user's screenshots of t2 t3
t4 t20). docx_design.body_page_shapes copies the page shapes into body-level
paragraphs: page 1's set in the first, the every-page set in the last.

These fail if page 1's sidebar colour is anchored only in the header, if
the copy sits inside a table cell (Word keeps such a shape inside its cell),
or if any gap opens between the coloured side cell and the shape."""
from __future__ import annotations

import json

import pytest
from docx.oxml.ns import qn

from app.exporters import docx_design

EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
docx_design._load()
MODERN = sorted(docx_design.DESIGNS)
EMU_PT = 12700
WPS = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _render(key, lang):
    d = json.loads(json.dumps(AR if lang == "ar" else EN))
    return docx_design.render(d, key, None)[0]


def _rects(el):
    """(x_pt, w_pt, fill) of every page-placed filled rectangle under `el`."""
    out = []
    for anchor in el.iter(qn("wp:anchor")):
        ph = anchor.find(qn("wp:positionH"))
        if ph is None or ph.get("relativeFrom") != "page":
            continue
        geom = anchor.find(".//" + A + "prstGeom")
        fill = anchor.find(".//" + A + "solidFill/" + A + "srgbClr")
        if geom is None or geom.get("prst") != "rect" or fill is None:
            continue
        x = int(ph.find(qn("wp:posOffset")).text) / EMU_PT
        w = int(anchor.find(qn("wp:extent")).get("cx")) / EMU_PT
        h = int(anchor.find(qn("wp:extent")).get("cy")) / EMU_PT
        out.append((x, w, h, fill.get("val").upper()))
    return out


def _side_cell(doc):
    """(x_pt, w_pt, fill) of the full-height side cell, or None."""
    rtl = doc.element.body.find(".//" + qn("w:bidiVisual")) is not None
    for tbl in doc.element.body.findall(qn("w:tbl")):
        rows = tbl.findall(qn("w:tr"))
        if len(rows) < 3:
            continue
        ind = tbl.find(qn("w:tblPr") + "/" + qn("w:tblInd"))
        x = int(ind.get(qn("w:w"))) / 20 if ind is not None else 0.0   # inset (t5 t9 t24)
        for tc in rows[0].findall(qn("w:tc")):
            pr = tc.find(qn("w:tcPr"))
            w = int(pr.find(qn("w:tcW")).get(qn("w:w"))) / 20
            vm, shd = pr.find(qn("w:vMerge")), pr.find(qn("w:shd"))
            if vm is not None and vm.get(qn("w:val")) == "restart" and shd is not None \
                    and shd.get(qn("w:fill")) not in (None, "auto"):
                return ((612 - x - w) if rtl else x, w, shd.get(qn("w:fill")).upper())
            x += w
    return None


@pytest.mark.parametrize("key", MODERN)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_page1_colour_is_in_the_body(key, lang):
    doc = _render(key, lang)
    sec = doc.sections[0]
    hdr = sec.first_page_header if sec.different_first_page_header_footer else sec.header
    header_fills = {(round(x, 1), round(w, 1), f) for x, w, h, f in _rects(hdr._element)}
    if not header_fills or hdr._element.find(".//" + qn("pic:pic")) is not None:
        pytest.skip("no page shapes in the header (or t22's fixed rail picture)")
    body = doc.element.body
    first = body[0]
    assert first.tag == qn("w:p"), "the copies need a body-level paragraph, not a table cell"
    body_fills = {(round(x, 1), round(w, 1), f) for x, w, h, f in _rects(first)}
    assert header_fills <= body_fills, f"only in the header: {header_fills - body_fills}"


@pytest.mark.parametrize("key", MODERN)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_no_gap_between_side_cell_and_its_shape(key, lang):
    doc = _render(key, lang)
    cell = _side_cell(doc)
    if cell is None:
        pytest.skip("no shaded full-height side cell")
    cx, cw, fill = cell
    shapes = [(x, w) for x, w, h, f in _rects(doc.element.body[0]) if f == fill and h > 700]
    if not shapes:
        pytest.skip("the side colour is the cell's own (no page shape)")
    x, w = max(shapes, key=lambda s: s[1])
    assert x <= cx + 0.05 and x + w >= cx + cw - 0.05, (
        f"gap: shape {x:.2f}-{x + w:.2f}pt, cell {cx:.2f}-{cx + cw:.2f}pt")


def test_last_page_gets_the_every_page_set():
    """Page 2 of a two-page CV: the last paragraph carries the default
    header's shapes (the every-page set, never a first-page-only one)."""
    doc = _render("modern-t2", "en")
    body = doc.element.body
    last = [el for el in body if el.tag == qn("w:p")][-1]
    names = [d.get("name") for d in last.iter(qn("wp:docPr"))]
    assert names and all(n.endswith("_pn") for n in names)
    assert len(_rects(last)) == len(_rects(doc.sections[0].header._element))


def test_t22_rail_header_untouched():
    doc = _render("modern-t22", "ar")
    assert not [d for d in doc.element.body.iter(qn("wp:docPr"))
                if (d.get("name") or "").endswith(("_p1", "_pn"))]
