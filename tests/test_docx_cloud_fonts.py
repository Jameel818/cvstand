"""The seven offered faces Word once drew as Calibri (run 4, item 5) are in
every Word file that uses them, so Word never needs Microsoft's copy.

Cause, measured: Lora, Raleway, Work Sans, Playfair Display, Lalezar, Aref
Ruqaa and Bebas Neue are in Microsoft 365's cloud-font catalogue. Word prefers
its own cloud copy to an embedded font; the first time a PC opens a file that
names one, Word shows a stand-in (Calibri) while it downloads the family
(%LOCALAPPDATA%/Microsoft/FontCache/4/CloudFonts - dated the minute of that
first check). Once it is cached the face draws exactly (advance widths equal
our TTFs, real Word, 2026-10-02, ats-t1/modern-t2/modern-t11, EN + AR). Word
without Microsoft 365, and LibreOffice, use the embedded copy checked here."""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest

from app.exporters.docx import render_docx
from app.typography import built_faces

EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
CASES = [  # (data, heading, body) - roles as the dropdowns offer them
    (EN, "Bebas Neue", "Lora"), (EN, "Raleway", "Work Sans"),
    (EN, "Playfair Display", "Lora"), (EN, "Work Sans", "Work Sans"),
    (AR, "Lalezar", None), (AR, "Aref Ruqaa", None),
]


def _font_table(blob: bytes) -> dict[str, set[str]]:
    ft = zipfile.ZipFile(io.BytesIO(blob)).read("word/fontTable.xml").decode("utf-8")
    out = {}
    for name, body in re.findall(r'<w:font w:name="([^"]+)"[^/]*?>(.*?)</w:font>', ft, re.S):
        out[name] = set(re.findall(r"<w:embed(Regular|Bold|Italic|BoldItalic) ", body))
    return out


@pytest.mark.parametrize("key", ["ats-t1", "modern-t2", "modern-t11"])
@pytest.mark.parametrize("data,heading,body", CASES, ids=[f"{h}/{b}" for _, h, b in CASES])
def test_the_chosen_face_is_embedded(key, data, heading, body):
    d = dict(data, font_heading=heading, font_name=heading)
    if body:
        d["font_body"] = body
    table = _font_table(render_docx(d, key))
    for family in filter(None, (heading, body)):
        names = [n for n in table if n == family or n.startswith(family + " ")]
        assert names, f"{family} not in fontTable"
        assert any(table[n] for n in names), f"{family} named but not embedded"


def test_every_face_of_the_seven_is_built():
    built = {f for f, _ in built_faces()}
    for family in ("Lora", "Raleway", "Work Sans", "Playfair Display", "Lalezar",
                   "Aref Ruqaa", "Bebas Neue"):
        assert family in built, family
