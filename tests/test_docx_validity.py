"""OOXML schema-order validation for the generated Word masters.

WHY THIS FILE EXISTS
    w:pPr / w:rPr / w:tblPr are ordered SEQUENCES in the OOXML schema, not bags.
    An element appended to the end of one is well-formed XML but schema-invalid,
    and Word refuses to open the document ("unreadable content"). python-docx
    and lxml parse such a file without complaint, so a round-trip test — reopen
    it, read the text back — passes on a document nobody can open. The first cut
    of the masters shipped three such violations and every structural test was
    green.

    So: assert child order directly, against the CT_* sequences from the spec.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTERS = sorted((ROOT / "word_masters").glob("*.docx"))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# ECMA-376 CT_PPr / CT_RPr / CT_TblPr child order.
SEQUENCES = {
    "pPr": ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
            "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd",
            "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
            "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
            "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
            "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl",
            "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"),
    "rPr": ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
            "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
            "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
            "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
            "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
            "eastAsianLayout", "specVanish", "oMath"),
    "tblPr": ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual",
              "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
              "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
              "tblCellMar", "tblLook", "tblCaption", "tblDescription"),
    # Added when the RTL masters landed: `w:bidi` goes in the SECTION properties
    # too, and that element was not order-checked before.
    "sectPr": ("footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
               "pgBorders", "lnNumType", "pgNumType", "cols", "formProt",
               "vAlign", "noEndnote", "titlePg", "textDirection", "bidi",
               "rtlGutter", "docGrid", "printerSettings", "sectPrChange"),
}


def _document_xml(path: Path) -> bytes:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml")


@pytest.mark.parametrize("master", MASTERS, ids=lambda p: p.name)
def test_master_is_a_valid_ooxml_package(master):
    with zipfile.ZipFile(master) as z:
        names = z.namelist()
        assert z.testzip() is None, "corrupt zip entry"
    for required in ("[Content_Types].xml", "word/document.xml", "_rels/.rels"):
        assert required in names, f"missing package part {required}"
    etree.fromstring(_document_xml(master))  # raises if not well-formed


@pytest.mark.parametrize("master", MASTERS, ids=lambda p: p.name)
@pytest.mark.parametrize("prop", sorted(SEQUENCES))
def test_property_children_follow_schema_order(master, prop):
    """Word rejects the whole document if any one of these is out of order."""
    order = SEQUENCES[prop]
    root = etree.fromstring(_document_xml(master))
    checked = 0
    for el in root.iter(f"{W}{prop}"):
        seen = [c.tag[len(W):] for c in el if c.tag.startswith(W)]
        known = [(order.index(t), t) for t in seen if t in order]
        positions = [i for i, _ in known]
        assert positions == sorted(positions), (
            f"{master.name}: <w:{prop}> children out of schema order — "
            f"got {[t for _, t in known]}, "
            f"expected {[t for _, t in sorted(known)]}. Word will refuse to "
            f"open this file."
        )
        checked += 1
    assert checked or prop == "tblPr", f"no <w:{prop}> found to check"


@pytest.mark.parametrize("key", ["ats-t1", "modern-t1"])
def test_rendered_export_is_valid_too(key):
    """The master is what we author; the RENDERED file is what a user opens.
    docxtpl re-serialises the package, so validate that end of the pipe too."""
    import io
    import json

    from app.exporters.docx import render_docx

    sample = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(io.BytesIO(render_docx(sample, key))) as z:
        assert z.testzip() is None
        assert "word/document.xml" in z.namelist()
        root = etree.fromstring(z.read("word/document.xml"))
    for prop, order in SEQUENCES.items():
        for el in root.iter(f"{W}{prop}"):
            seen = [c.tag[len(W):] for c in el if c.tag.startswith(W)]
            positions = [order.index(t) for t in seen if t in order]
            assert positions == sorted(positions), (
                f"{key}: rendered <w:{prop}> out of schema order: {seen}"
            )


def test_masters_exist():
    """Four: one per (category, direction).

    The RTL pair is a separate FILE rather than a switch inside the LTR one - a
    .docx has no conditional layout - so a missing one is a missing export, not
    a degraded one.
    """
    assert {m.name for m in MASTERS} == {
        "ats_standard.docx", "modern_editorial.docx",
        "ats_standard_rtl.docx", "modern_editorial_rtl.docx",
    }
