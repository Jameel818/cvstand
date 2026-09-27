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
from app.exporters.docx import render_docx
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


def _body_paragraphs(doc):
    """Paragraphs with text, in order, outside tables (the chip row's cells
    use the heading style for their metrics, and a cell cannot break)."""
    out = []
    for p in doc.iter(f"{W}p"):
        if any(a.tag == f"{W}tbl" for a in p.iterancestors()):
            continue
        if "".join(t.text or "" for t in p.iter(f"{W}t")).strip():
            out.append(p)
    return out


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


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_headings_and_job_titles_keep_with_what_follows(key, data):
    paras = _body_paragraphs(_xml(render_docx(data, key), "word/document.xml"))
    headings = roles = 0
    for i, p in enumerate(paras):
        style = _style_of(p)
        if style == "CVHeading":
            headings += 1
            assert _keeps_next(p), f"heading {''.join(p.itertext())!r} can be orphaned"
        elif style == "CVRole":
            roles += 1
            assert _keeps_next(p), f"job title {''.join(p.itertext())!r} can split"
            nxt = paras[i + 1]
            if _style_of(nxt) != "CVRole":  # its company/date line, when there is one
                assert _keeps_next(nxt), "the company/date line can part from its bullets"
    assert headings >= 5 and roles >= 1, "the sample reaches headings and jobs"
