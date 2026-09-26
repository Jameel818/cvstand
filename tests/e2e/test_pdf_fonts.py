"""Spec §7.5: the PDF embeds exactly the chosen faces, and no fallback.

Through the real route (`POST /export/pdf`, what the builder sends), three
combinations per language. Each sets all three roles with an explicit weight,
so the faces that MUST appear are known exactly; every font in the file must
then be one this document may carry (`pdf_faces()`: the chosen families at
their built weights, the 700 Details emphasis face, the Latin-Ext fallback).
A template face, a system font or a Type3 (how Chromium writes a variable
font) in the file means some text escaped the choices.

The combinations reach the three kinds of file the build ships: instanced
(Montserrat, Inter), unmodified-static TTF for a Reserved-Font-Name family
(IBM Plex Sans Arabic), and Almarai, whose Bold is its own nameID 1.
"""
from __future__ import annotations

import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.exporters.pdf import _LOAD_AND_CHECK
from app.schema import typography_of
from app.typography import face
from app.typography.render import pdf_faces

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
EN = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
AR = json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))

#: (id, base, template, name, heading, body) - each role (family, weight).
COMBOS = [
    ("en-serif-name", EN, "ats-t1",
     ("Playfair Display", 900), ("Montserrat", 800), ("Inter", 300)),
    ("en-display", EN, "modern-t1",
     ("Anton", 400), ("Archivo", 900), ("Lora", 400)),
    ("en-sidebar", EN, "modern-t22",
     ("Bebas Neue", 400), ("Raleway", 700), ("Work Sans", 400)),
    ("ar-kufi-naskh", AR, "modern-t1",
     ("Tajawal", 800), ("Cairo", 900), ("Amiri", 400)),
    ("ar-rfn-ttf", AR, "ats-t1",
     ("Almarai", 800), ("Noto Kufi Arabic", 700), ("IBM Plex Sans Arabic", 300)),
    ("ar-calligraphic", AR, "modern-t22",
     ("Aref Ruqaa", 700), ("El Messiri", 700), ("Scheherazade New", 400)),
]


def _resume(base, name, heading, body):
    return dict(base,
                font_name=name[0], font_name_weight=name[1],
                font_heading=heading[0], font_heading_weight=heading[1],
                font_body=body[0], font_body_weight=body[1])


def _export(live_server, data, key) -> bytes:
    """POST /export/pdf, waiting out the rate limit if other tests in the
    session spent it (the server says how long, in Retry-After)."""
    req = urllib.request.Request(
        live_server.url + "/export/pdf",
        data=json.dumps({"data": data, "template_key": key}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                return res.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(float(exc.headers.get("Retry-After") or 10))
    raise AssertionError("PDF export stayed rate-limited")


#: Template -> the ENGLISH text it draws with -webkit-text-stroke.
STROKED = {"modern-t22": "RESUME"}


def _type3_chars(font) -> str:
    """The characters a Type3 font's ToUnicode map names."""
    tu = font.get("/ToUnicode")
    if tu is None:
        return "?"
    cmap = tu.get_object().get_data().decode("latin-1")
    pairs = re.findall(r"<[0-9A-Fa-f]+>\s*<([0-9A-Fa-f]{4})>", cmap)
    return "".join(chr(int(h, 16)) for h in pairs)


def embedded_fonts(blob: bytes) -> set[str]:
    """Every font the PDF carries, by its name without the subset tag - on
    the pages and inside their form XObjects, where Chromium draws text. A
    Type3 is `<Type3:chars>`, the characters it maps."""
    out: set[str] = set()
    seen: set[int] = set()

    def walk(res):
        if not res:
            return
        res = res.get_object()
        for f in (res.get("/Font") or {}).values():
            f = f.get_object()
            if f.get("/Subtype") == "/Type3":
                out.add(f"<Type3:{_type3_chars(f)}>")
                continue
            base = f["/BaseFont"]
            if "/DescendantFonts" in f:
                base = f["/DescendantFonts"][0].get_object()["/BaseFont"]
            out.add(str(base).lstrip("/").split("+", 1)[-1])
        for x in (res.get("/XObject") or {}).values():
            x = x.get_object()
            if id(x) not in seen:
                seen.add(id(x))
                walk(x.get("/Resources"))

    for page in PdfReader(io.BytesIO(blob)).pages:
        walk(page.get("/Resources"))
    return out


def test_the_instrument_sees_a_default_pdfs_template_fonts(live_server):
    """Calibration: a résumé with no choices embeds the template's own faces
    (ats-t1 is IBM Plex Mono), so an instrument that read nothing, or read
    only the pages and not their XObjects, cannot pass the tests below."""
    fonts = embedded_fonts(_export(live_server, EN, "ats-t1"))
    assert {"IBMPlexMono-Regular", "IBMPlexMono-SemiBold"} <= fonts


@pytest.mark.parametrize("cid,base,key,name,heading,body", COMBOS,
                         ids=[c[0] for c in COMBOS])
def test_pdf_embeds_exactly_the_chosen_faces(live_server, cid, base, key,
                                             name, heading, body):
    data = _resume(base, name, heading, body)
    fonts = embedded_fonts(_export(live_server, data, key))

    required = {face(*f)["postscript_name"] for f in (name, heading, body)}
    allowed = {face(*f)["postscript_name"]
               for f in pdf_faces(typography_of(data)[0], data.get("lang") or "en")}
    for t3 in [f for f in fonts if f.startswith("<Type3:")]:
        assert key in STROKED, f"{key} strokes no text, yet embeds a Type3: {t3}"
        chars = t3[len("<Type3:"):-1]
        if base is EN:
            assert chars and set(chars) <= set(STROKED[key]), (
                f"a Type3 draws {chars!r}, which is not the template's stroked text")
        fonts.discard(t3)
    assert required <= fonts, f"chosen face(s) not embedded: {required - fonts}"
    assert fonts <= allowed, f"fallback / unchosen font(s) embedded: {fonts - allowed}"


def test_load_check_names_a_face_that_did_not_load(page):
    """pdf.py refuses to print when a chosen face is missing. The check it
    runs, on a document where one face loads and one cannot."""
    from app.typography.render import _embed, _face_rules
    good = _embed(_face_rules()[("Inter", 400)])
    page.set_content(
        "<style>" + good + "@font-face { font-family: 'CVT Missing'; "
        "src: url(data:font/woff2;base64,AAAA) format('woff2'); }</style><p>x</p>")
    missing = page.evaluate(_LOAD_AND_CHECK,
                            ['400 16px "CVT Inter"', '400 16px "CVT Missing"'])
    assert missing == ['400 16px "CVT Missing"']
