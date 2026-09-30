"""The Word LAYOUTS: each Modern template's shape in Word (docs/WORD_LAYOUTS_PLAN.md).

What a layout promises, checked in the package (these run everywhere;
tools/verify_word_embedding.py checks the same files in real Word):

  MAPPING     every Modern template has a measured layout of the approved
              archetype; ATS never does; a template on a layout exports from
              the layout master (and its RTL twin in Arabic).
  STRUCTURE   the layout table's grid is exactly its columns (docxtpl widens
              an outer grid to the widest NESTED row - the bug that put every
              cell 5 grid columns wide), widths fill the page, the side column
              sits on its side, and in Arabic every table mirrors (bidiVisual)
              and the full-height side fill moves to the right.
  CONTENT     every section the template shows is there once, under the
              template's own heading words, in the cell and order its PDF
              uses; a section the résumé leaves empty leaves no heading.
  SKILLS      name AND level as real text; bars where the PDF has bars (one
              bar per RATED skill), dots where it has dots or rings; an
              unrated skill gets no graphic at all.
  COLOUR      every cell's text reads on its own fill (4.5:1 body text, 3:1
              headings/names) - white text never lands on a light band.
  FONTS       every face the text draws is embedded (step 6 still holds).
"""
from __future__ import annotations

import copy
import io
import re
import zipfile

import pytest
from lxml import etree

from app import registry
from app.exporters import docx_layout as DL
from app.exporters.docx import _master_for, render_docx
from app.exporters.docx_design import has_design
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
V = "{urn:schemas-microsoft-com:vml}"
MODERN = [k for k in registry.ported_keys() if k.startswith("modern-")]
ON = [k for k in MODERN if DL.spec_for(k) and not has_design(k)]
#: ON lists the templates EXPORTED through the layout masters. A template with
#: its own Word design (app/exporters/docx_design.py) is checked for the same
#: promises in its own terms by tests/test_docx_designs.py.
SAMPLES = {"en": ENGLISH, "ar": ARABIC}

#: docs/WORD_LAYOUTS_PLAN.md §3, approved by the user 2026-09-29.
PLAN = {
    "sidebar": {2, 3, 4, 5, 9, 10, 15, 16, 17, 20, 23, 24},
    "band": {7, 8, 11, 13, 14, 18, 21},
    "open": {1, 6, 12, 22},
    "gutter": {19},
}


def _parts(blob: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return {n: etree.fromstring(z.read(n)) for n in z.namelist()
                if n.endswith(".xml") and n.startswith("word/")}


@pytest.fixture(scope="module")
def exports():
    return {(k, lang): render_docx(SAMPLES[lang], k) for k in ON for lang in SAMPLES}


def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{W}t"))


def _outer(doc):
    return doc.find(f"{W}body/{W}tbl")


def _style_ids(p) -> set[str]:
    return {rs.get(f"{W}val") for rs in p.iter(f"{W}rStyle")}


# ---- mapping --------------------------------------------------------------------

def test_every_modern_template_has_a_layout_of_its_approved_archetype():
    layouts = DL.layouts()
    assert set(layouts) == set(MODERN)
    for arche, blocks in PLAN.items():
        for n in blocks:
            assert layouts[f"modern-t{n}"]["archetype"] == arche


def test_ats_templates_never_take_a_layout():
    for k in registry.ported_keys():
        if k.startswith("ats-"):
            assert DL.spec_for(k) is None
            assert _master_for(registry.get(k), ENGLISH) == "ats_standard.docx"


@pytest.mark.parametrize("key", ON)
def test_a_layout_template_exports_from_the_layout_master(key):
    tpl = registry.get(key)
    en, ar = _master_for(tpl, ENGLISH), _master_for(tpl, ARABIC)
    assert en in ("modern_layout.docx", "modern_gutter.docx")
    assert ar == en.replace(".docx", "_rtl.docx")


# ---- structure ------------------------------------------------------------------

@pytest.mark.parametrize("key", [k for k in ON if DL.layouts()[k]["archetype"] != "gutter"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_layout_table_has_its_own_grid_and_fills_the_page(exports, key, lang):
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    tbl = _outer(doc)
    L = DL.layouts()[key][lang]
    cols = [int(c.get(f"{W}w")) for c in tbl.findall(f"{W}tblGrid/{W}gridCol")]
    assert len(cols) == (2 if L["side_w"] else 1), f"grid {cols}: docxtpl widened it"
    assert sum(cols) == DL.PAGE_W
    for tr in tbl.findall(f"{W}tr"):
        spans = [int((tc.find(f"{W}tcPr/{W}gridSpan") is not None
                      and tc.find(f"{W}tcPr/{W}gridSpan").get(f"{W}val")) or 1)
                 for tc in tr.findall(f"{W}tc")]
        assert sum(spans) == len(cols), "a row does not fill the grid"
    if L["side_w"]:
        side_w = DL.side_width(L)
        assert side_w in cols
        assert side_w >= round(L["side_w"] * DL.PAGE_W), "never narrower than the template's"
        first = cols[0] == side_w
        assert first == (DL.layouts()[key]["side"] == "start"), "side column on the wrong side"


@pytest.mark.parametrize("key", ON)
def test_arabic_mirrors_every_table_english_none(exports, key):
    for lang, want in (("en", False), ("ar", True)):
        doc = _parts(exports[(key, lang)])["word/document.xml"]
        tbls = list(doc.iter(f"{W}tbl"))
        assert tbls
        for t in tbls:
            assert (t.find(f"{W}tblPr/{W}bidiVisual") is not None) == want


@pytest.mark.parametrize("key", [k for k in ON if DL.layouts()[k]["en"]["side_bg"]])
def test_the_side_fill_runs_the_full_page_height_on_its_side(exports, key):
    """A shape in the header, behind the text, on every page: the fill reaches
    the page edges however long the résumé runs. On the right in Arabic."""
    spec = DL.layouts()[key]
    for lang in ("en", "ar"):
        parts = _parts(exports[(key, lang)])
        L = spec[lang]
        rects = [r for n, x in parts.items() if "header" in n for r in x.iter(f"{V}rect")]
        side = [r for r in rects if r.get("fillcolor", "").lstrip("#").upper() == L["side_bg"]
                and "height:792" in r.get("style", "")]
        assert side, f"{lang}: no full-height side fill"
        style = side[0].get("style")
        x = float(re.search(r"margin-left:([\d.]+)pt", style).group(1))
        w = float(re.search(r"width:([\d.]+)pt", style).group(1))
        at_left = x < 1
        at_right = abs(x + w - DL.PAGE_W_PT) < 1
        start = spec["side"] == "start"
        assert (at_left if start != (lang == "ar") else at_right), f"{lang}: fill on the wrong side"
        # and the cells themselves are filled too (a reader may ignore headers)
        fills = {s.get(f"{W}fill") for s in _outer(parts["word/document.xml"]).iter(f"{W}shd")}
        assert L["side_bg"] in fills


# ---- page breaks ----------------------------------------------------------------
#
# Word ignores keep-with-next between paragraphs inside a table cell that
# breaks across pages (real Word, 2026-09-30: modern-t5 in Arabic left its
# "Certifications" heading alone at the foot of page 1). It does honour a
# row that cannot split, so the main column is one cantSplit row per block.

def test_blocks_keep_a_heading_with_its_content_and_split_jobs():
    items = [{"k": "name"}, {"k": "title"},
             {"k": "summary", "label": "Profile"}, {"k": "achievements"},
             {"k": "experience", "label": "Experience", "jobs": ["a", "b", "c"]},
             {"k": "skills", "label": "Skills"}]
    got = DL.blocks(items)
    assert [[i["k"] for i in b] for b in got] == [
        ["name", "title"], ["summary", "achievements"],
        ["experience"], ["experience"], ["experience"], ["skills"]]
    assert got[2][0]["label"] == "Experience" and got[2][0]["jobs"] == ["a"]
    assert "label" not in got[3][0] and got[3][0]["jobs"] == ["b"]


@pytest.mark.parametrize("key", [k for k in ON if DL.layouts()[k]["archetype"] != "gutter"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_each_main_block_is_a_row_that_cannot_split(exports, key, lang):
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    tbl = _outer(doc)
    L = DL.layouts()[key][lang]
    body = [tr for tr in tbl.findall(f"{W}tr")
            if tr.find(f"{W}tc/{W}tcPr/{W}vMerge") is not None or not L["side_w"]]
    if L["side_w"]:
        merges = [tr.find(f"{W}tc/{W}tcPr/{W}vMerge").get(f"{W}val") for tr in body]
        assert merges[0] == "restart" and set(merges[1:]) <= {"continue"}, merges
    jobs = len(SAMPLES[lang]["experience"])
    assert len(body) >= jobs + 1, "every job its own row"
    heading_ids = {"CVHeading", "CVSideHeading", "CVTopSideHeading", "CVTopMainHeading"}
    for tr in body:
        assert tr.find(f"{W}trPr/{W}cantSplit") is not None
        for tc in tr.findall(f"{W}tc"):
            texts = [p for p in tc.findall(f"{W}p") if _text(p).strip()]
            if texts and _style_ids(texts[-1]) & heading_ids and len(texts) > 0:
                # a heading may end its CELL only in the side column, which
                # is one merged cell and flows on
                assert tc.find(f"{W}tcPr/{W}vMerge") is not None, (
                    f"heading {_text(texts[-1])!r} ends its row")


GUTTER = [k for k in ON if DL.layouts()[k]["archetype"] == "gutter"]


@pytest.mark.parametrize("key", GUTTER)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_gutter_puts_each_label_beside_its_section_in_unbreakable_rows(exports, key, lang):
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    tbl = doc.findall(f"{W}body/{W}tbl")[-1]
    rows = tbl.findall(f"{W}tr")
    labels = [DL._item(i, lang)["text"] for c in DL.layouts()[key][lang]["cells"].values()
              for i in c if i.get("label")]
    jobs = len(SAMPLES[lang]["experience"])
    assert len(rows) == len(labels) + jobs - 1, "a row per section, and per job"
    seen = []
    for tr in rows:
        assert tr.find(f"{W}trPr/{W}cantSplit") is not None
        label_cell, content = tr.findall(f"{W}tc")
        text = _text(label_cell).strip()
        if text:
            seen.append(text)
            assert _text(content).strip(), f"label {text!r} beside an empty cell"
    assert seen == labels
    assert [len(c.findall(f"{W}gridCol")) for c in [tbl.find(f"{W}tblGrid")]] == [2]


@pytest.mark.parametrize("key", ON)
def test_a_timeline_template_marks_each_job_with_an_accent_bar(exports, key):
    from app.exporters import docx_theme
    spec = DL.layouts()[key]
    for lang in ("en", "ar"):
        doc = _parts(exports[(key, lang)])["word/document.xml"]
        roles = [p for p in doc.iter(f"{W}p") if "CVRole" in _style_ids(p) and _text(p).strip()]
        assert len(roles) == len(SAMPLES[lang]["experience"])
        accent = docx_theme.resolve(SAMPLES[lang], key)["accent"]
        edge = "right" if lang == "ar" else "left"   # the START edge, in Word's physical terms
        for p in roles:
            bar = p.find(f"{W}pPr/{W}pBdr/{W}{edge}")
            if spec["timeline"]:
                assert bar is not None and bar.get(f"{W}color") == accent, f"{lang}: no timeline bar"
            else:
                assert p.find(f"{W}pPr/{W}pBdr") is None, f"{lang}: a timeline bar on a template without one"


# ---- content --------------------------------------------------------------------

def _labels(key: str, lang: str) -> list[tuple[str, str]]:
    out = []
    for cell, items in DL.layouts()[key][lang]["cells"].items():
        for it in items:
            if it.get("label"):
                out.append((it["k"], DL._item(it, lang)["text"]))
    return out


@pytest.mark.parametrize("key", ON)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_section_appears_once_under_the_templates_own_heading(exports, key, lang):
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    paras = ["".join(t.text or "" for t in p.iter(f"{W}t")).strip() for p in doc.iter(f"{W}p")]
    for kind, heading in _labels(key, lang):
        assert paras.count(heading) == 1, f"{kind}: heading {heading!r} x{paras.count(heading)}"


@pytest.mark.parametrize("key", ON)
def test_an_empty_section_leaves_no_heading(key):
    for lang, data in SAMPLES.items():
        for kind, heading in _labels(key, lang):
            if kind in ("contact",):
                continue
            thin = copy.deepcopy(data)
            thin[kind] = [] if isinstance(thin.get(kind), list) else ""
            doc = _parts(render_docx(thin, key))["word/document.xml"]
            paras = ["".join(t.text or "" for t in p.iter(f"{W}t")).strip()
                     for p in doc.iter(f"{W}p")]
            assert heading not in paras, f"{lang} {kind}: orphan heading {heading!r}"


@pytest.mark.parametrize("key", ON)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_sections_sit_in_their_measured_cell_order(exports, key, lang):
    """Within the main column, headings come in the PDF's order."""
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    order = [DL._item(i, lang)["text"] for i in DL.layouts()[key][lang]["cells"]["main"]
             if i.get("label")]
    seen = [t for t in ("".join(x.text or "" for x in p.iter(f"{W}t")).strip()
                        for p in doc.iter(f"{W}p")) if t in order]
    assert seen == order


# ---- skills ---------------------------------------------------------------------

def _bars(doc):
    return [t for t in doc.iter(f"{W}tbl") if len(t.findall(f"{W}tblGrid/{W}gridCol")) == 5]


@pytest.mark.parametrize("key", ON)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_skills_follow_the_template_bars_or_dots_with_real_text(exports, key, lang):
    data = SAMPLES[lang]
    doc = _parts(exports[(key, lang)])["word/document.xml"]
    text = _text(doc)
    for sk in data["skills"]:
        assert sk["name"] in text and sk["level"] in text
    from app.schema import dots_for
    rated = [s for s in data["skills"] if dots_for(s.get("level", ""))]
    if DL.layouts()[key]["skills"] == "bars":
        assert len(_bars(doc)) == len(rated), "one bar per rated skill"
        fills = {s.get(f"{W}fill") for b in _bars(doc) for s in b.iter(f"{W}shd")}
        fills |= {e.get(f"{W}color") for b in _bars(doc) for e in b.iter(f"{W}left", f"{W}right")}
        assert not fills & {"BA0001", "BA0002"}, "a bar kept its placeholder colour"
    else:
        assert not _bars(doc)
        assert "●" in text


@pytest.mark.parametrize("key", ON)
def test_an_unrated_skill_has_no_graphic(key):
    data = copy.deepcopy(ENGLISH)
    data["skills"] = [{"name": "Unrated Thing", "level": ""}]
    doc = _parts(render_docx(data, key))["word/document.xml"]
    assert "Unrated Thing" in _text(doc)
    assert not _bars(doc)
    line = next(p for p in doc.iter(f"{W}p") if "Unrated Thing" in _text(p))
    assert "●" not in _text(line) and "○" not in _text(line)


# ---- colour ---------------------------------------------------------------------

def _style_colour(styles, sid: str) -> str | None:
    for st in styles.iter(f"{W}style"):
        if st.get(f"{W}styleId") == sid:
            c = st.find(f"{W}rPr/{W}color")
            return c.get(f"{W}val") if c is not None else None
    return None


def _para_fill(styles, sid: str) -> str | None:
    for st in styles.iter(f"{W}style"):
        if st.get(f"{W}styleId") == sid:
            s = st.find(f"{W}pPr/{W}shd")
            return s.get(f"{W}fill") if s is not None else None
    return None


@pytest.mark.parametrize("key", [k for k in ON if DL.layouts()[k]["archetype"] != "gutter"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_cells_text_reads_on_its_own_fill(exports, key, lang):
    parts = _parts(exports[(key, lang)])
    doc, styles = parts["word/document.xml"], parts["word/styles.xml"]
    checked = 0
    for tc in _outer(doc).iter(f"{W}tc"):
        if tc.getparent().getparent() is not _outer(doc):
            continue                                   # a nested chip / bar cell
        shd = tc.find(f"{W}tcPr/{W}shd")
        cell_bg = shd.get(f"{W}fill") if shd is not None else "FFFFFF"
        for p in tc.iter(f"{W}p"):
            if not _text(p).strip():
                continue
            # a ribbon heading or a contact pill stands on its paragraph
            # style's own fill, not on the cell's
            ps = p.find(f"{W}pPr/{W}pStyle")
            bg = _para_fill(styles, ps.get(f"{W}val")) if ps is not None else None
            bg = bg or cell_bg
            for sid in _style_ids(p):
                colour = _style_colour(styles, sid)
                if colour:
                    need = 4.5 if sid.endswith(("Text", "Bold")) else 3.0
                    assert DL.contrast(colour, bg) >= need - 0.01, (
                        f"{sid} {colour} on {bg}: {DL.contrast(colour, bg):.2f}")
                    checked += 1
    assert checked


# ---- fonts ----------------------------------------------------------------------

@pytest.mark.parametrize("key", ON)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_face_the_text_draws_is_embedded(exports, key, lang):
    parts = _parts(exports[(key, lang)])
    doc, styles, table = (parts["word/document.xml"], parts["word/styles.xml"],
                          parts["word/fontTable.xml"])
    used = set()
    for r in doc.iter(f"{W}r"):
        if not _text(r).strip():
            continue
        rs = r.find(f"{W}rPr/{W}rStyle")
        sid = rs.get(f"{W}val") if rs is not None else "Normal"
        for st in styles.iter(f"{W}style"):
            if st.get(f"{W}styleId") == sid:
                f = st.find(f"{W}rPr/{W}rFonts")
                if f is not None:
                    used.add(f.get(f"{W}ascii"))
    embedded = {f.get(f"{W}name") for f in table.iter(f"{W}font")
                if f.find(f"{W}embedRegular") is not None or f.find(f"{W}embedBold") is not None}
    missing = used - embedded
    assert not missing, f"drawn but not embedded: {missing}"


# ---- the photo ------------------------------------------------------------------

@pytest.mark.parametrize("key", [k for k in ON if DL.layouts()[k]["en"]["photo"]])
def test_the_photo_lands_in_its_cell_at_its_size_and_shape(key, tmp_path, monkeypatch):
    from PIL import Image
    from app.exporters import docx as D
    photo = tmp_path / "me.jpg"
    Image.new("RGB", (400, 500), (200, 120, 90)).save(photo)
    monkeypatch.setattr(D, "UPLOADS_DIR", tmp_path)
    data = dict(ENGLISH, photo_url="/uploads/me.jpg")
    with zipfile.ZipFile(io.BytesIO(render_docx(data, key))) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(media) == 1
        img = Image.open(io.BytesIO(z.read(media[0])))
        doc = etree.fromstring(z.read("word/document.xml"))
    L = DL.layouts()[key]["en"]
    assert (img.mode == "RGBA") == L["photo"]["round"], "round photo = cut to a circle"
    ext = doc.find(f".//{{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}}extent")
    assert abs(int(ext.get("cx")) / 36000 - L["photo"]["mm"]) < 1, "photo size"
