"""Per-template Word DESIGNS (app/exporters/docx_design.py,
docs/WORD_FIDELITY_AUDIT.md): the promises tests/test_docx_layouts.py checks
for the layout masters, checked here in a design's own terms. Real-Word
appearance is graded by eye (the audit); these guard the structure.

  CONTENT   every section the template shows is there under its own heading
            words; an empty section leaves no heading.
  SKILLS    name AND level as real text; one graphic per RATED skill; an
            unrated skill has none.
  COLOUR    every run's colour reads on the fill behind it.
  PHOTO     a photo lands in the document when the résumé has one.
  ARABIC    the section and every table mirror; digits, e-mails and "$3.2M"
            are NOT marked right-to-left (Word reorders them: audit X13).
  FONTS     every face the text draws is embedded.
"""
from __future__ import annotations

import copy
import io
import re
import zipfile

import pytest
from lxml import etree

from app.exporters import docx_design
from app.exporters.docx import render_docx
from app.exporters.docx_layout import contrast
from app.labels import reset_lang, set_lang, t
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
docx_design._load()
KEYS = sorted(docx_design.DESIGNS)
SAMPLES = {"en": ENGLISH, "ar": ARABIC}

#: The heading words each design draws (its template's own, from the catalogue).
HEADINGS = {
    "modern-t2": ["ABOUT ME", "EDUCATION", "SKILLS", "LANGUAGE", "CERTIFICATIONS",
                  "EXPERIENCE"],
    "modern-t8": ["ABOUT ME", "PERSONAL SKILLS", "CONTACT", "EDUCATION", "WORK EXPERIENCE",
                  "ALSO"],
}


def _doc(blob: bytes):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return etree.fromstring(z.read("word/document.xml")), z.namelist()


def _text(el) -> str:
    return "".join(x.text or "" for x in el.iter(f"{W}t"))


def _label(key_text: str, lang: str) -> str:
    tok = set_lang(lang)
    try:
        return str(t(key_text))
    finally:
        reset_lang(tok)


@pytest.fixture(scope="module")
def exports():
    return {(k, lang): render_docx(SAMPLES[lang], k) for k in KEYS for lang in SAMPLES}


def test_every_design_has_its_heading_list():
    assert set(HEADINGS) == set(KEYS)


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_section_appears_under_the_templates_own_heading(exports, key, lang):
    doc, _ = _doc(exports[key, lang])
    # a ruled heading ends in spaces + a tab (the rule's leader)
    paras = [_text(p).strip("  	") for p in doc.iter(f"{W}p")]
    for h in HEADINGS[key]:
        assert _label(h, lang) in paras, f"{key} {lang}: no {h!r} heading"


@pytest.mark.parametrize("key", KEYS)
def test_an_empty_section_leaves_no_heading(key):
    data = copy.deepcopy(ENGLISH)
    data["skills"] = []
    doc, _ = _doc(render_docx(data, key))
    paras = [_text(p) for p in doc.iter(f"{W}p")]
    for h in ("SKILLS", "PERSONAL SKILLS"):
        assert h not in paras


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_skills_keep_name_and_level_as_text(exports, key, lang):
    doc, _ = _doc(exports[key, lang])
    text = _text(doc)
    for sk in SAMPLES[lang]["skills"]:
        assert sk["name"] in text
        level = f"{sk['percent']}%" if key == "modern-t2" else sk["level"]
        assert level in text, f"{key}: {sk['name']} has no level text"


def _graphics(doc) -> int:
    """Skill graphics: dot runs (●) and bar fills (shaded cells/paragraphs
    with no text beside a skill)."""
    dots = sum(1 for r in doc.iter(f"{W}r") if "●" in _text(r))
    return dots


@pytest.mark.parametrize("key", KEYS)
def test_an_unrated_skill_has_no_graphic(key):
    data = copy.deepcopy(ENGLISH)
    base = _doc(render_docx(data, key))[0]
    data["skills"].append({"name": "Unrated Thing", "level": ""})
    doc = _doc(render_docx(data, key))[0]
    assert "Unrated Thing" in _text(doc)
    assert _graphics(doc) == _graphics(base)
    # and no "0%" / empty bar beside it
    assert "0%" not in re.sub(r"\d0%", "", _text(doc))


def _fill_behind(run, side_fill: str | None) -> str:
    for a in run.iterancestors():
        if a.tag == f"{W}p":
            shd = a.find(f"{W}pPr/{W}shd")
            if shd is not None and shd.get(f"{W}fill") not in (None, "auto"):
                return shd.get(f"{W}fill")
        if a.tag == f"{W}tc":
            shd = a.find(f"{W}tcPr/{W}shd")
            if shd is not None and shd.get(f"{W}fill") not in (None, "auto"):
                return shd.get(f"{W}fill")
            if a.find(f"{W}tcPr/{W}vMerge") is not None and side_fill:
                return side_fill
    return "FFFFFF"


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_run_reads_on_its_fill(exports, key, lang):
    doc, _ = _doc(exports[key, lang])
    bad = []
    for r in doc.iter(f"{W}r"):
        txt = _text(r).strip()
        col = r.find(f"{W}rPr/{W}color")
        if not txt or col is None or set(txt) <= set("●○"):
            continue                 # the dots are the graphic, drawn as in the PDF
        bg = _fill_behind(r, None)
        if contrast(col.get(f"{W}val"), bg) < 3.0:
            bad.append((txt[:20], col.get(f"{W}val"), bg))
    assert not bad, bad


@pytest.mark.parametrize("key", KEYS)
def test_a_photo_lands_in_the_document(key, tmp_path, monkeypatch):
    from PIL import Image
    from app.exporters import docx as D
    monkeypatch.setattr(D, "UPLOADS_DIR", tmp_path)
    Image.new("RGB", (60, 80), "#556677").save(tmp_path / "me.png")
    data = copy.deepcopy(ENGLISH)
    data["photo_url"] = "/uploads/me.png"
    doc, names = _doc(render_docx(data, key))
    assert any(n.startswith("word/media/") for n in names)
    assert doc.find(f".//{W}drawing") is not None


@pytest.mark.parametrize("key", KEYS)
def test_arabic_mirrors_and_keeps_digits_left_to_right(exports, key):
    doc, _ = _doc(exports[key, "ar"])
    assert doc.find(f"{W}body/{W}sectPr/{W}bidi") is not None
    for tbl in doc.iter(f"{W}tbl"):
        assert tbl.find(f"{W}tblPr/{W}bidiVisual") is not None
    arabic = re.compile(r"[؀-ۿ]")
    for r in doc.iter(f"{W}r"):
        txt = _text(r)
        if txt.strip() and not arabic.search(txt) and r.find(f"{W}rPr/{W}rtl") is not None:
            assert set(txt) <= set("●○"), f"{txt!r} is marked RTL: Word reorders it"
    en, _ = _doc(exports[key, "en"])
    assert en.find(f".//{W}bidiVisual") is None and en.find(f".//{W}rtl") is None


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_face_the_text_draws_is_embedded(exports, key, lang):
    with zipfile.ZipFile(io.BytesIO(exports[key, lang])) as z:
        fonts = [n for n in z.namelist() if n.startswith("word/fonts/")]
        table = z.read("word/fontTable.xml").decode("utf-8")
    assert fonts, "no embedded fonts"
    assert table.count("embedRegular") + table.count("embedBold") >= len(fonts) // 2
