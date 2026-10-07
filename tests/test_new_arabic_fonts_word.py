"""The Arabic families added on 2026-10-07 reach the Word file.

For each family, an Arabic résumé that chooses it - for the Name and the
Headings (Beiruti, Changa, Zain) or for the Details (the other seven, and
Zain again) - downloads as a .docx that EMBEDS that family: the font table
names it, the embedded part de-obfuscates to the shipped TTF byte for byte,
and the TTF draws the Arabic alphabet (36 base letters). That Word then draws
with it is what tools/verify_word_embedding.py proves in real Word.

The browser half - each family drawing Arabic in the PDF - is
tests/e2e/test_new_arabic_fonts_pdf.py.
"""
from __future__ import annotations

import io
import zipfile

import pytest
from fontTools.ttLib import TTFont
from lxml import etree

from app.exporters import docx_font_embed as E
from app.exporters.docx import render_docx
from app.typography import face
from app.typography.faces import FONT_DIR
from app.typography.registry import OFFERED, offered_weights
from tests.samples import ARABIC

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

HEADINGS = ("Beiruti", "Changa", "Zain")
DETAILS = ("Parastoo", "Alyamama", "Cascadia Code", "Cascadia Mono", "Vazirmatn",
           "Estedad", "Zain")
ARABIC_LETTERS = set(range(0x0621, 0x063B)) | set(range(0x0641, 0x064B))

CASES = ([(f, "heading") for f in HEADINGS] + [(f, "body") for f in DETAILS])
IDS = [f"{f}-{role}" for f, role in CASES]


def test_the_families_are_offered_where_the_user_asked():
    for f in HEADINGS:
        assert f in OFFERED[("ar", "heading")] and f in OFFERED[("ar", "name")]
    for f in DETAILS:
        assert f in OFFERED[("ar", "body")]
    # Arabic only: no English dropdown lists them.
    for role in ("name", "heading", "body"):
        assert not set(HEADINGS + DETAILS) & set(OFFERED[("en", role)])


def _resume(family: str, role: str) -> tuple[dict, int]:
    """The résumé choosing `family` at its heaviest offered weight in the role
    (Headings: the Name follows them), and that weight."""
    w = max(offered_weights("ar", role, family))
    if role == "heading":
        return dict(ARABIC, font_heading=family, font_heading_weight=w), w
    return dict(ARABIC, font_body=family, font_body_weight=w), w


def _embedded(blob: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    table = etree.fromstring(parts["word/fontTable.xml"])
    rels = {r.get("Id"): r.get("Target")
            for r in etree.fromstring(parts["word/_rels/fontTable.xml.rels"])}
    out = []
    for font in table.iter(f"{W}font"):
        for tag, slot in (("embedRegular", "regular"), ("embedBold", "bold")):
            el = font.find(f"{W}{tag}")
            if el is not None:
                out.append({"name": font.get(f"{W}name"), "slot": slot,
                            "plain": E.obfuscate(parts["word/" + rels[el.get(f"{R}id")]],
                                                 el.get(f"{W}fontKey"))})
    return out


@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
@pytest.mark.parametrize("family,role", CASES, ids=IDS)
def test_the_chosen_family_is_embedded_in_word(family, role, key):
    data, w = _resume(family, role)
    f = face(family, w)
    slot = "bold" if f["word_bold"] else "regular"
    emb = [e for e in _embedded(render_docx(data, key))
           if e["name"] == f["word_family_name"] and e["slot"] == slot]
    assert emb, f"{family} {w} is not embedded in the {key} .docx"
    ttf = (FONT_DIR / f["ttf"]).read_bytes()
    assert emb[0]["plain"] == ttf, "the embedded part is not the shipped TTF"
    cmap = set(TTFont(io.BytesIO(ttf)).getBestCmap())
    assert ARABIC_LETTERS <= cmap, f"{family} {w} lacks Arabic letters"
