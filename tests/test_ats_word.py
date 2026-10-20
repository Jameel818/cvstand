"""The ATS rules for every ATS Word file (user, 2026-10-20) - they come
before looks (app/exporters/docx_ats.py):

    BODY TEXT ONLY   every word of the CV in the body flow: no text boxes, no
                     floating shapes, nothing in headers or footers, no
                     tables (layout or one-cell), no images (of text or not)
    READING ORDER    the file's extracted plain text is the template's own
                     text, word for word, in the template's order - so every
                     CV field is there, in the order the PDF reads
    REAL HEADINGS    every section heading is text in the heading style, kept
                     with what follows
    NATURAL LINES    Auto line spacing only (never Exactly / At least)
    FONTS EMBEDDED   every face a run names is embedded in the file

All 25 ATS templates, English and Arabic, on the demo CV (the builder's
seed) and on the long sample CV (which runs past one page).
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
import zipfile

import pytest
from lxml import etree
from lxml import html as LH

from app import registry
from app.config import DEMO_RESUME_PATHS
from app.exporters.docx import render_docx
from app.rendering import canvas_html
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
KEYS = [k for k in registry.ported_keys() if k.startswith("ats-")]
DEMO = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in DEMO_RESUME_PATHS.items()}
CASES = [("demo-en", DEMO["en"]), ("demo-ar", DEMO["ar"]),
         ("sample-en", ENGLISH), ("sample-ar", ARABIC)]
#: invisible bidi controls (the Arabic PDF isolates phones with LRI/PDI)
_MARKS = re.compile("[⁦-⁩‎‏]")


def _parts(blob: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return {n: z.read(n) for n in z.namelist()}


@pytest.fixture(scope="module")
def files():
    return {(key, cid): _parts(render_docx(data, key)) for key in KEYS for cid, data in CASES}


def _doc(parts):
    return etree.fromstring(parts["word/document.xml"])


def test_every_ats_template_is_covered():
    assert len(KEYS) == 25


@pytest.mark.parametrize("cid", [c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_body_text_only(files, key, cid):
    parts = files[(key, cid)]
    doc = parts["word/document.xml"].decode("utf-8")
    assert "<w:tbl>" not in doc and "<w:tbl " not in doc, "a table holds CV text"
    for marker in ("txbxContent", "v:textbox", "wps:txbx"):
        assert marker not in doc, f"a text box ({marker})"
    root = _doc(parts)
    assert not list(root.iter(f"{WP}anchor")), "a floating shape"
    assert "a:blip" not in doc and "v:imagedata" not in doc, "an image"
    for name, blob in parts.items():
        if re.fullmatch(r"word/(header|footer)\d*\.xml", name):
            text = "".join(t.text or "" for t in etree.fromstring(blob).iter(f"{W}t"))
            assert not text.strip(), f"{name} holds text: {text!r}"


@pytest.mark.parametrize("cid", [c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_natural_line_spacing(files, key, cid):
    for sp in _doc(files[(key, cid)]).iter(f"{W}spacing"):
        assert sp.get(f"{W}lineRule") in (None, "auto")


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", _MARKS.sub("", text))
    return [t for t in text.split() if t != "•"]


_BLOCKS = {"div", "p", "ul", "ol", "li", "br"}


def _html_text(data, key) -> list[str]:
    """The template's text as a browser reads it: inline elements run on,
    block elements (and flex items, which are blocks) are separated."""
    frag = LH.fragment_fromstring(canvas_html(data, key), create_parent="div")
    out: list[str] = []

    def walk(el, flex_item=False):
        sep = el.tag in _BLOCKS or flex_item
        if sep:
            out.append(" ")
        out.append(el.text or "")
        flex = "display:flex" in (el.get("style") or "").replace(" ", "")
        for ch in el:
            if isinstance(ch.tag, str):
                walk(ch, flex)
            out.append(ch.tail or "")
        if sep:
            out.append(" ")
    walk(frag)
    return _tokens("".join(out))


def _word_text(parts) -> list[str]:
    root = _doc(parts)
    paras = []
    for p in root.iter(f"{W}p"):
        bits = []
        for el in p.iter(f"{W}t", f"{W}tab", f"{W}br"):
            bits.append(el.text or "" if el.tag == f"{W}t" else " ")
        paras.append("".join(bits))
    return _tokens(" ".join(paras))


@pytest.mark.parametrize("cid,data", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_plain_text_is_the_templates_text_in_order(files, key, cid, data):
    """What a parser reads from the Word file is what the PDF says, word for
    word and in the same order - every CV field present, none moved."""
    assert _word_text(files[(key, cid)]) == _html_text(data, key)


def _fields(data) -> list[str]:
    from app.schema import normalize
    r = normalize(data)
    c = r["contact"]
    out = [r["name"], r["title"], c["email"], c["phone"], c["address"], c["site"], r["summary"]]
    for a in r["achievements"]:
        out += [a["metric"], a["label"]]
    for j in r["experience"]:
        out += [j["role"], j["company"], j["location"], j["start"], j["end"], *j["bullets"]]
    for s in r["skills"]:
        out += [s["name"], s["level"]]
    for e in r["education"]:
        out += [e["degree"], e["school"], e["end"]]
    for x in r["recognition"]:
        out += [x["title"], x["detail"]]
    out += r["tools"]
    for lang in r["languages"]:
        out += [lang["name"], lang["level"]]
    return [v for v in out if v and v.strip()]


@pytest.mark.parametrize("cid,data", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_every_field_the_pdf_shows_is_in_the_word_text(files, key, cid, data):
    """Belt and braces for the test above: each CV value the template prints
    is found in the Word text (as words, in any case)."""
    word = " ".join(_word_text(files[(key, cid)]))
    html = " ".join(_html_text(data, key))
    for v in _fields(data):
        v = " ".join(_tokens(v))
        if v in html:
            assert v in word, f"{v!r} is in the PDF but not in the Word text"


@pytest.mark.parametrize("cid", [c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_headings_are_real_text_kept_with_next(files, key, cid):
    heads = 0
    for p in _doc(files[(key, cid)]).iter(f"{W}p"):
        styles = {r.get(f"{W}val") for r in p.iter(f"{W}rStyle")}
        if "CVHeading" in styles:
            text = "".join(t.text or "" for t in p.iter(f"{W}t")).strip()
            assert text, "an empty heading"
            assert p.find(f"{W}pPr/{W}keepNext") is not None, f"{text!r} can be orphaned"
            heads += 1
    assert heads >= 4


@pytest.mark.parametrize("cid", [c[0] for c in CASES])
@pytest.mark.parametrize("key", KEYS)
def test_every_named_face_is_embedded(files, key, cid):
    parts = files[(key, cid)]
    named = {f.get(f"{W}ascii") for f in _doc(parts).iter(f"{W}rFonts")} - {"Arial", None}
    table = etree.fromstring(parts["word/fontTable.xml"])
    embedded = {f.get(f"{W}name") for f in table.iter(f"{W}font")
                if f.find(f"{W}embedRegular") is not None or f.find(f"{W}embedBold") is not None}
    assert named and named <= embedded, f"not embedded: {named - embedded}"
