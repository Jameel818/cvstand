"""The Arabic families added on 2026-10-07 draw ARABIC in the PDF.

Through the real route (`POST /export/pdf`). For each family, an Arabic
résumé that chooses it - Name + Headings for Beiruti, Changa, Zain; Details
for Parastoo, Alyamama, Cascadia Code, Cascadia Mono, Vazirmatn, Estedad,
Zain - must come back with that face embedded under its own PostScript name
(not a Type3, not a fallback) AND with Arabic letters in that font's
ToUnicode map: the font did not merely load, it drew the Arabic text.
"Embedded" alone would pass for a face that only drew the Latin digits.

The Word half is tests/test_new_arabic_fonts_word.py.
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

from app.typography import face
from app.typography.registry import offered_weights

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
AR = json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))

HEADINGS = ("Beiruti", "Changa", "Zain")
DETAILS = ("Parastoo", "Alyamama", "Cascadia Code", "Cascadia Mono", "Vazirmatn",
           "Estedad", "Zain")
CASES = [(f, "heading") for f in HEADINGS] + [(f, "body") for f in DETAILS]
#: Arabic letters, isolated and presentation forms: what a ToUnicode map of
#: shaped Arabic text names.
ARABIC = re.compile(r"[ء-يﭐ-﷿ﹰ-ﻼ]")


def _export(server, data, key) -> bytes:
    req = urllib.request.Request(
        server.url + "/export/pdf",
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


def _fonts(blob: bytes) -> dict[str, str]:
    """{PostScript name without subset tag: the text its ToUnicode map names},
    over the pages and their form XObjects (where Chromium draws text)."""
    out: dict[str, str] = {}
    seen: set[int] = set()

    def walk(res):
        if not res:
            return
        res = res.get_object()
        for f in (res.get("/Font") or {}).values():
            f = f.get_object()
            base = f.get("/BaseFont")
            if "/DescendantFonts" in f:
                base = f["/DescendantFonts"][0].get_object()["/BaseFont"]
            name = str(base or "<Type3>").lstrip("/").split("+", 1)[-1]
            text = ""
            if f.get("/ToUnicode") is not None:
                cmap = f["/ToUnicode"].get_object().get_data().decode("latin-1")
                for hexes in re.findall(r"<[0-9A-Fa-f]+>\s*<([0-9A-Fa-f]{4,})>", cmap):
                    text += "".join(chr(int(hexes[i:i + 4], 16)) for i in range(0, len(hexes), 4))
            out[name] = out.get(name, "") + text
        for x in (res.get("/XObject") or {}).values():
            x = x.get_object()
            if id(x) not in seen:
                seen.add(id(x))
                walk(x.get("/Resources"))

    for page in PdfReader(io.BytesIO(blob)).pages:
        walk(page.get("/Resources"))
    return out


@pytest.mark.parametrize("family,role", CASES, ids=[f"{f}-{r}" for f, r in CASES])
def test_the_new_family_draws_arabic_in_the_pdf(deployed_server, family, role):
    w = max(offered_weights("ar", role, family))
    if role == "heading":
        data = dict(AR, font_heading=family, font_heading_weight=w)
    else:
        data = dict(AR, font_body=family, font_body_weight=w)
    fonts = _fonts(_export(deployed_server, data, "modern-t1"))
    ps = face(family, w)["postscript_name"]
    assert ps in fonts, f"{ps} is not embedded; the PDF carries {sorted(fonts)}"
    assert ARABIC.search(fonts[ps]), (
        f"{ps} is embedded but draws no Arabic: {fonts[ps][:40]!r}")
