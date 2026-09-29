"""Word content FLOWS - it is not squeezed onto one page (typography step 6).

User decision (2026-09-27): with the fonts embedded, a Word file may run to a
second page. That is accepted. What is a failure is what a page break must
never do, and what line spacing must never do:

    EXACT SPACING   "Exactly" line spacing (or an exact row height) can clip
                    glyphs - Arabic marks first - and overlap lines. Every
                    paragraph stays on Word's Auto rule.
    ORPHAN HEADING  a section heading left alone at the bottom of a page:
                    every heading keeps with the next paragraph.
    SPLIT JOB       a job title parted from its company/date line: the title
                    keeps with next, and so does that line (with its first
                    bullet).
    WIDOW / ORPHAN  one line of a paragraph alone across a break: Normal has
                    widow/orphan control, which every paragraph inherits.

These read the package, so they run everywhere; tools/verify_word_embedding.py
checks the same rules in real Word, against where the pages actually break.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from app import registry
from app.exporters import docx_layout
from app.exporters.docx import render_docx
from app.schema import lang_of
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KEYS = registry.ported_keys()
MASTERS = sorted((Path(__file__).resolve().parents[1] / "word_masters").glob("*.docx"))


def _xml(blob: bytes, part: str):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return etree.fromstring(z.read(part))


def _style_of(p) -> str | None:
    for r in p.iter(f"{W}r"):
        if "".join(t.text or "" for t in r.iter(f"{W}t")).strip():
            rs = r.find(f"{W}rPr/{W}rStyle")
            return rs.get(f"{W}val") if rs is not None else None
    return None


def _keeps_next(p) -> bool:
    return p.find(f"{W}pPr/{W}keepNext") is not None


def _grid_cols(tbl) -> int:
    return len(tbl.findall(f"{W}tblGrid/{W}gridCol"))


def _body_paragraphs(doc):
    """Paragraphs with text, in order, that flow down the page: in the body,
    or in a Word LAYOUT's cells (docs/WORD_LAYOUTS_PLAN.md: the side and
    main columns are table cells, at most 2 across). Not in the chip row or a
    skill bar (4-5 cells across): the chips use the heading style for their
    metrics, and such a row cannot break."""
    out = []
    for p in doc.iter(f"{W}p"):
        if any(a.tag == f"{W}tbl" and _grid_cols(a) > 2 for a in p.iterancestors()):
            continue
        if "".join(t.text or "" for t in p.iter(f"{W}t")).strip():
            out.append(p)
    return out


#: A section heading's character style: the role style, or a layout cell's own.
HEADING_STYLES = {"CVHeading", "CVTopSideHeading", "CVTopMainHeading", "CVSideHeading"}


@pytest.mark.parametrize("master", MASTERS, ids=lambda p: p.name)
def test_normal_has_widow_orphan_control(master):
    styles = _xml(master.read_bytes(), "word/styles.xml")
    normal = next(s for s in styles.iter(f"{W}style") if s.get(f"{W}styleId") == "Normal")
    assert normal.find(f"{W}pPr/{W}widowControl") is not None


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_no_exact_spacing_anywhere(key, data):
    blob = render_docx(data, key)
    for part in ("word/document.xml", "word/styles.xml"):
        root = _xml(blob, part)
        for sp in root.iter(f"{W}spacing"):
            assert sp.get(f"{W}lineRule") in (None, "auto"), (
                f"{part}: lineRule={sp.get(f'{W}lineRule')} can clip glyphs")
        for h in root.iter(f"{W}trHeight"):
            assert h.get(f"{W}hRule") != "exact", "an exact row height can clip"


def _row_of(p):
    """The layout table row a paragraph sits in (outermost 1-2 column table)."""
    rows = [a for a in p.iterancestors() if a.tag == f"{W}tr"
            and _grid_cols(a.getparent()) <= 2]
    return rows[-1] if rows else None


def _in_side_column(p) -> bool:
    return any(a.tag == f"{W}tc" and a.find(f"{W}tcPr/{W}vMerge") is not None
               for a in p.iterancestors())


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_headings_and_job_titles_keep_with_what_follows(key, data):
    """The body masters (ATS, single-column Modern) keep a heading and a job
    title with what follows by KEEP-WITH-NEXT. A Word LAYOUT cannot: inside a
    table Word ignores it within a breaking cell and chains each row to the
    next across rows (real Word, 2026-09-30). There the guarantee is the
    ROW: every heading and job title shares a cannot-split row with what
    follows it, and nothing in the table keeps with next."""
    doc = _xml(render_docx(data, key), "word/document.xml")
    paras = _body_paragraphs(doc)
    layout = docx_layout.spec_for(key) is not None
    if layout:
        tables = [t for t in doc.iter(f"{W}tbl") if _grid_cols(t) <= 2]
        chained = [p for t in tables for p in t.iter(f"{W}p") if _keeps_next(p)]
        assert not chained, "keep-with-next in a layout table chains its rows"
    headings = roles = 0
    for i, p in enumerate(paras):
        style = _style_of(p)
        if style in HEADING_STYLES or style == "CVRole":
            headings += style in HEADING_STYLES
            roles += style == "CVRole"
            what = "heading" if style in HEADING_STYLES else "job title"
            if not layout:
                assert _keeps_next(p), f"{what} {''.join(p.itertext())!r} can be orphaned"
                if style == "CVRole" and _style_of(paras[i + 1]) != "CVRole":
                    assert _keeps_next(paras[i + 1]), "the company/date line can part from its bullets"
                continue
            if _in_side_column(p):
                continue                 # one merged cell down the page; flows on
            row = _row_of(p)
            assert row is not None and row.find(f"{W}trPr/{W}cantSplit") is not None, (
                f"{what} {''.join(p.itertext())!r} is not in a row that cannot split")
            nxt = paras[i + 1] if i + 1 < len(paras) else None
            assert nxt is not None and _row_of(nxt) is row, (
                f"{what} {''.join(p.itertext())!r} ends its row")
    spec = docx_layout.spec_for(key)
    if spec and spec["archetype"] != "gutter":
        # a Word LAYOUT shows exactly the headings its template's PDF shows
        want = sum(1 for c in docx_layout.layouts()[key][lang_of(data)]["cells"].values()
                   for i in c if i.get("label"))
        assert headings == want and roles >= 1, f"{headings} headings, the layout has {want}"
    else:
        assert headings >= 5 and roles >= 1, "the sample reaches headings and jobs"
