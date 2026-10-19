"""The cover letter (2026-10-18): off by default, one shared layout in every
template's identity, PDF + Word, EN + AR.

What the user asked for, and what each test here holds:
  - OFF = the CV's outputs are byte-identical to before the letter existed.
    The comparison against the PREVIOUS COMMIT was made once, in the run
    (294 outputs: preview HTML, PDF HTML and Word for 49 templates x EN/AR,
    plus 12 PDFs - all identical); what stays here is the invariant that
    proof rests on: a letter in the document, on or off, changes nothing the
    CV renders, and the CV path never sees the key.
  - ON = one page: the longest letter the form allows, in all 49 templates,
    in both languages (the PDF side is the browser suite's; the Word side is
    checked in real Word by the run's Word batch).
  - Downloads: "cv" (default) / "letter" / "both", PDF and Word.
"""
from __future__ import annotations

import copy
import io
import json
import re
import zipfile

import pytest
from lxml import etree

from app import create_app, letter, registry, schema
from app.exporters.docx import render_docx
from app.rendering import canvas_html, document_html
from app.schema import ResumeValidationError, normalize, validate
from tests import letter_samples as LS
from tests.test_docx_validity import SEQUENCES, W

KEYS = registry.ported_keys()


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ---- the data contract ----------------------------------------------------------

def test_a_resume_without_a_letter_is_still_valid_and_normalises_as_before():
    d = LS.resume("en")
    validate(d)
    assert "cover_letter" not in normalize(d)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_demo_letters_and_the_longest_letter_are_valid(lang):
    validate(LS.with_letter(lang))
    validate(LS.with_letter(lang, LS.longest(lang)))
    assert letter.demo(lang)["paragraphs"]


@pytest.mark.parametrize("bad", [
    {"subject": "x" * (schema.LETTER_FIELD_MAX + 1)},
    {"company_address": "x" * (schema.LETTER_ADDRESS_MAX + 1)},
    {"paragraphs": ["x" * (schema.LETTER_PARAGRAPH_MAX + 1)]},
    {"paragraphs": ["x"] * (schema.LETTER_MAX_PARAGRAPHS + 1)},
    {"enabled": "yes"},
    {"unknown": "field"},
])
def test_the_caps_that_keep_it_one_page_are_enforced(bad):
    d = LS.with_letter("en", dict(LS.demo_letter("en"), **bad))
    with pytest.raises(ResumeValidationError):
        validate(d)


def test_letter_of_drops_blank_paragraphs_and_signs_with_the_name():
    d = LS.with_letter("en", {"enabled": True, "paragraphs": ["  ", "One.", ""], "signature": " "})
    L = letter.letter_of(d)
    assert L["paragraphs"] == ["One."]
    assert L["signature"] == d["name"]


# ---- OFF: the CV is untouched ------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_cv_renders_the_same_with_a_letter_on_or_off(key, lang):
    plain = LS.resume(lang)
    for state in (False, True):
        d = LS.with_letter(lang, dict(LS.demo_letter(lang), enabled=state))
        assert canvas_html(d, key) == canvas_html(plain, key)
        assert document_html(d, key) == document_html(plain, key)


def _docx_parts(blob: bytes) -> dict:
    z = zipfile.ZipFile(io.BytesIO(blob))
    out = {}
    for n in z.namelist():
        b = z.read(n)
        if n == "word/fontTable.xml":     # a fresh obfuscation GUID per export
            b = re.sub(rb'w:fontKey="\{[0-9A-F-]+\}"', b"", b)
        if n.endswith(".odttf"):
            b = b[32:]
        # Shape ids and names come from process-wide counters (docx_dml
        # _next_id, docx_design _SHAPE_N): a SECOND render in one process
        # numbers them on from the first, letter or no letter. The run's
        # cross-commit check used one fresh process per side instead.
        b = re.sub(rb'((?:\bid|\bname)=")(cvstand_[A-Za-z_]*?)?\d+(?:_\d+)*"', rb'\1\2#"', b)
        out[n] = b
    return out


@pytest.mark.parametrize("key", ["ats-t1", "modern-t1", "modern-t4", "modern-t13", "ats-t7"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_cv_word_file_is_the_same_with_a_letter_off(key, lang):
    off = LS.with_letter(lang, dict(LS.demo_letter(lang), enabled=False))
    assert _docx_parts(render_docx(off, key)) == _docx_parts(render_docx(LS.resume(lang), key))


# ---- the letter page -------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_template_draws_the_letter_in_its_identity(key, lang):
    d = LS.with_letter(lang)
    html = letter.canvas_html(d, key)
    th = letter.theme(key, lang)
    assert 'class="tpl cv-letter' in html
    for text in (d["name"], d["cover_letter"]["subject"], d["cover_letter"]["paragraphs"][0]):
        assert text.replace("&", "&amp;") in html
    assert th["page"] in html and th["accent"] in html
    if th["head_bg"]:
        assert f"background:{th['head_bg']}" in html
    if th["rail"]:
        assert 'class="cl-rail"' in html and th["rail"]["bg"] in html
    # role hooks the font ribbon and the Arabic policy target
    assert 'class="cv-name"' in html and 'class="cv-section"' in html


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_letter_colours_read_on_their_surface(key, lang):
    th = letter.theme(key, lang)
    surface = th["head_bg"] or th["page"]
    assert letter.contrast(th["name"], surface) >= 3
    assert letter.contrast(th["contact"], surface) >= 4.5
    assert letter.contrast(th["heading"], th["page"]) >= 4.5      # 14px bold: not large text
    assert letter.contrast(th["title"], surface) >= 4.5
    assert letter.contrast(th["text"], th["page"]) >= 4.5


def test_the_arabic_letter_is_right_to_left_with_its_phone_isolated():
    d = LS.with_letter("ar")
    doc = letter.document_html(d, "modern-t4")
    assert '<html lang="ar" dir="rtl">' in doc
    assert "⁦" + d["contact"]["phone"] + "⁩" in doc


def test_a_letter_with_only_some_fields_renders():
    d = LS.with_letter("en", {"enabled": True, "paragraphs": ["Only this."]})
    html = letter.canvas_html(d, "modern-t13")
    assert "Only this." in html and 'class="cv-section"' not in html


def test_letter_markup_is_escaped():
    d = LS.with_letter("en", dict(LS.demo_letter("en"), subject="<img src=x onerror=alert(1)>"))
    html = letter.canvas_html(d, "ats-t1")
    assert "<img src=x" not in html and "&lt;img src=x" in html


def test_letter_themes_cover_every_template_in_both_languages():
    themes = letter._themes()
    assert set(themes) == set(KEYS)
    assert all(set(v) == {"en", "ar"} for v in themes.values())


@pytest.mark.slow
def test_letter_themes_json_is_fresh():
    """Measured, not transcribed: a template that changed its colours since
    letter_themes.json was written fails here (re-run the tool)."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(root / "tools" / "build_letter_themes.py"), "--check"],
                       capture_output=True, text=True, cwd=root)
    assert r.returncode == 0, r.stdout + r.stderr


# ---- the API --------------------------------------------------------------------

def test_render_route_returns_the_letter_when_asked(client):
    d = LS.with_letter("en")
    j = client.post("/api/render", json={"data": d, "template_key": "modern-t4", "doc": "letter"}).get_json()
    assert j["ok"] and "cv-letter" in j["doc"]
    cv = client.post("/api/render", json={"data": d, "template_key": "modern-t4"}).get_json()
    assert "cv-letter" not in cv["doc"] and cv["doc"] == document_html(d, "modern-t4")


@pytest.mark.parametrize("route", ["/export/pdf", "/export/docx"])
def test_export_refuses_a_letter_the_resume_does_not_have(client, route):
    off = LS.with_letter("en", dict(LS.demo_letter("en"), enabled=False))
    for part in ("letter", "both"):
        r = client.post(route, json={"data": off, "template_key": "ats-t1", "part": part})
        assert r.status_code == 422
    r = client.post(route, json={"data": LS.with_letter("en"), "template_key": "ats-t1", "part": "nope"})
    assert r.status_code == 422


@pytest.mark.parametrize("part,suffix", [("letter", "_cover_letter"), ("both", "_cv_and_cover_letter")])
def test_docx_route_names_the_download_by_part(client, part, suffix):
    r = client.post("/export/docx", json={"data": LS.with_letter("en"), "template_key": "ats-t1",
                                          "part": part})
    assert r.status_code == 200
    assert f'filename=Wren_Ashworth{suffix}.docx' in r.headers["Content-Disposition"]


# ---- Word -----------------------------------------------------------------------

def _xml(blob: bytes, name="word/document.xml"):
    return etree.fromstring(zipfile.ZipFile(io.BytesIO(blob)).read(name))


def _schema_ordered(root, label):
    for prop, order in SEQUENCES.items():
        for el in root.iter(f"{W}{prop}"):
            seen = [c.tag[len(W):] for c in el if c.tag.startswith(W)]
            pos = [order.index(t) for t in seen if t in order]
            assert pos == sorted(pos), f"{label}: <w:{prop}> out of schema order: {seen}"


def _text(root) -> str:
    return "".join(t.text or "" for t in root.iter(f"{W}t"))


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_word_letter_alone_is_one_section_valid_and_editable(key, lang):
    d = LS.with_letter(lang)
    root = _xml(render_docx(d, key, "letter"))
    _schema_ordered(root, f"{key} {lang}")
    assert len(root.findall(f".//{W}sectPr")) == 1
    text = _text(root)
    L = d["cover_letter"]
    for s in (d["name"], L["subject"], L["greeting"], L["closing"]):
        assert s.replace(" ", "") in text.replace(" ", "")
    for para in L["paragraphs"]:
        assert para in text                     # real, editable text runs
    if lang == "ar":
        assert root.find(f".//{W}sectPr/{W}bidi") is not None
        assert root.find(f".//{W}pPr/{W}bidi") is not None


@pytest.mark.parametrize("key", ["ats-t1", "modern-t1", "modern-t4", "modern-t13", "modern-t21", "ats-t7"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_word_cv_plus_letter_puts_the_letter_in_its_own_section(key, lang):
    d = LS.with_letter(lang)
    blob = render_docx(d, key, "both")
    root = _xml(blob)
    _schema_ordered(root, f"{key} {lang} both")
    sects = root.findall(f".//{W}sectPr")
    assert len(sects) >= 2
    last = sects[-1]
    # the letter's page starts a new page and has headers of its own: none of
    # the CV's page shapes (sidebar, band) can reach it
    refs = last.findall(f"{W}headerReference")
    assert refs and last.find(f"{W}titlePg") is None
    assert all(r.get(f"{W}type") != "first" for r in refs)
    cv_only = render_docx(LS.resume(lang), key)
    assert d["cover_letter"]["subject"] in _text(root)
    assert _text(_xml(cv_only)) in _text(root)          # the CV is all there, first


@pytest.mark.parametrize("key", ["modern-t13", "modern-t4", "modern-t3", "ats-t1"])
@pytest.mark.parametrize("part", ["letter", "both"])
def test_every_arabic_letter_paragraph_is_right_to_left(key, part):
    """Found in real Word (run 10): the letter's FIRST element missed its RTL
    properties, and a bidiVisual band slid off the page. Every paragraph of
    the letter is bidi; the one-cell band is not a mirrored table; the rest
    (the accent rule) are."""
    root = _xml(render_docx(LS.with_letter("ar"), key, part))
    kids = list(root.find(f"{W}body"))
    start = max((i + 1 for i, e in enumerate(kids)
                 if e.tag == f"{W}p" and e.find(f".//{W}sectPr") is not None), default=0)
    paras = [p for e in kids[start:] for p in e.iter(f"{W}p")]
    assert paras and all(p.find(f"{W}pPr/{W}bidi") is not None for p in paras)
    th = letter.theme(key, "ar")
    tables = [t for e in kids[start:] for t in e.iter(f"{W}tbl")]
    mirrored = [t.find(f"{W}tblPr/{W}bidiVisual") is not None for t in tables]
    assert mirrored == ([False] if th["head_bg"] else [True])


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_word_letter_embeds_the_faces_it_draws(lang):
    z = zipfile.ZipFile(io.BytesIO(render_docx(LS.with_letter(lang), "modern-t4", "letter")))
    assert any(n.startswith("word/fonts/") for n in z.namelist())


def test_word_letter_follows_the_chosen_fonts():
    d = LS.with_letter("en")
    d["font_heading"] = "Montserrat"
    styles = zipfile.ZipFile(io.BytesIO(render_docx(d, "ats-t1", "letter"))).read("word/styles.xml")
    assert b"Montserrat" in styles


# ---- the letter is always its OWN page (run 11) ------------------------------------

def _bullet(lang: str) -> str:
    """Text only the CV carries: its first experience bullet."""
    return LS.resume(lang)["experience"][0]["bullets"][0]


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_word_cv_plus_letter_starts_the_letter_on_a_new_page(key, lang):
    """"CV + cover letter" in Word: everything of the letter comes after the
    CV's last section break, and the letter's section starts on a NEW page
    (w:type absent = nextPage, or nextPage itself - never continuous, which
    would let the letter run on under the CV)."""
    d = LS.with_letter(lang)
    subject = d["cover_letter"]["subject"]
    root = _xml(render_docx(d, key, "both"))
    kids = list(root.find(f"{W}body"))
    breaks = [i for i, e in enumerate(kids)
              if e.tag == f"{W}p" and e.find(f"{W}pPr/{W}sectPr") is not None]
    assert breaks, f"{key} {lang}: no section break between the CV and the letter"
    cut = breaks[-1]
    cv_text = "".join(_text(e) for e in kids[:cut + 1])
    letter_text = "".join(_text(e) for e in kids[cut + 1:])
    assert _bullet(lang) in cv_text and _bullet(lang) not in letter_text
    assert subject in letter_text and subject not in cv_text
    start = kids[-1].find(f"{W}type")
    assert kids[-1].tag == f"{W}sectPr"
    assert start is None or start.get(f"{W}val") == "nextPage", f"{key} {lang}"


@pytest.mark.parametrize("key", ["ats-t1", "modern-t3", "modern-t4", "modern-t13"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_word_letter_alone_carries_no_cv(key, lang):
    d = LS.with_letter(lang)
    root = _xml(render_docx(d, key, "letter"))
    assert len(root.findall(f".//{W}sectPr")) == 1
    assert d["cover_letter"]["subject"] in _text(root)
    assert _bullet(lang) not in _text(root)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_preview_draws_the_letter_as_its_own_page(lang):
    """The preview's letter is a separate document (its own iframe, /api/render
    doc=letter): one `.tpl` page holding no CV, while the CV's page holds
    none of the letter."""
    d = LS.with_letter(lang)
    lhtml = letter.canvas_html(d, "modern-t4")
    assert lhtml.count('class="tpl ') == 1
    assert d["cover_letter"]["subject"] in lhtml and _bullet(lang) not in lhtml
    assert d["cover_letter"]["subject"] not in canvas_html(d, "modern-t4")
