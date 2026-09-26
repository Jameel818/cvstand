"""Self-hosted font tests.

WHY THIS FILE EXISTS
    A font that fails to load raises nothing. Chromium silently substitutes a
    fallback face and the page renders — wrong, but without a single error. So
    "the CSS is present" proves nothing; these tests assert that the bytes are
    reachable by BOTH render paths, and that neither reaches the network.

    The two paths resolve URLs differently:
      preview — served over HTTP, so a <link> to /static/fonts/fonts.css works.
      PDF     — Playwright `set_content()`, base URL about:blank, where that
                same link resolves to nothing. Hence the embedded variant.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import create_app
from app.rendering import document_html, font_head

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "app" / "static" / "fonts"
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

FAMILIES = {"Poppins", "Inter", "Fraunces", "Montserrat", "Anton", "Archivo Narrow",
            "Archivo", "Source Sans 3", "Merriweather", "Open Sans", "IBM Plex Mono"}


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_font_assets_exist():
    assert (FONTS_DIR / "fonts.css").exists(), "run tools/fetch_fonts.py"
    assert (FONTS_DIR / "fonts_inline.css").exists()
    assert (FONTS_DIR / "LICENSES.md").exists(), "OFL requires the licence to ship"
    assert list(FONTS_DIR.glob("*.woff2")), "no font files"


def test_every_family_ships_its_full_ofl_text():
    """OFL 1.1 clause 2: the licence text travels with the fonts. LICENSES.md
    linking upstream is not sufficient for a public copy of this project, so
    each family's OFL.txt is vendored by tools/fetch_fonts.py --licences."""
    css = (FONTS_DIR / "fonts.css").read_text(encoding="utf-8")
    families = sorted(set(re.findall(r"font-family: '([^']+)'", css)))
    assert families, "fonts.css declares no families"
    for fam in families:
        path = FONTS_DIR / "licenses" / f"{fam.replace(' ', '-')}-OFL.txt"
        assert path.exists(), f"no vendored OFL.txt for {fam}"
        text = path.read_text(encoding="utf-8")
        assert "SIL OPEN FONT LICENSE Version 1.1" in text, f"{fam}: not an OFL text"
        assert "PERMISSION & CONDITIONS" in text, f"{fam}: OFL text looks truncated"


def test_every_referenced_font_file_is_present():
    css = (FONTS_DIR / "fonts.css").read_text(encoding="utf-8")
    refs = re.findall(r"url\(/static/fonts/([^)]+)\)", css)
    assert refs, "fonts.css references no files"
    missing = [r for r in refs if not (FONTS_DIR / r).exists()]
    assert not missing, f"fonts.css points at missing files: {missing[:5]}"


def test_both_stylesheets_declare_the_same_families():
    """If these drift, a PDF renders in a different face than its preview."""
    link = set(re.findall(r"font-family: '([^']+)'",
                          (FONTS_DIR / "fonts.css").read_text(encoding="utf-8")))
    inline = set(re.findall(r"font-family: '([^']+)'",
                            (FONTS_DIR / "fonts_inline.css").read_text(encoding="utf-8")))
    assert link == inline == FAMILIES


def _rules(css: str) -> list[tuple[str, str, str, str]]:
    """(family, weight, style, unicode-range) of every @font-face, in order."""
    out = []
    for block in re.findall(r"@font-face\s*\{(.*?)\}", css, re.S):
        def get(prop, default=""):
            m = re.search(rf"{prop}:\s*([^;]+);", block)
            return m.group(1).strip() if m else default
        out.append((get("font-family"), get("font-weight", "400"),
                    get("font-style", "normal"), get("unicode-range")))
    return out


def test_inline_css_has_every_linked_rule():
    """The PDF sheet must declare exactly the preview's rules - every weight.

    It used to merge the rules that share a file, to embed each payload once
    (1.4 MB instead of 4.2). For a variable family Google points EVERY weight
    at one file, so the merge kept only `font-weight: 400`: the PDF, and every
    pixel golden, drew Montserrat 900 / Archivo 900 / Inter 700 ... at 400
    while the preview drew them real. Eight families, 48 of 49 templates."""
    link = _rules((FONTS_DIR / "fonts.css").read_text(encoding="utf-8"))
    inline = _rules((FONTS_DIR / "fonts_inline.css").read_text(encoding="utf-8"))
    assert inline == link


def test_inline_payloads_are_the_linked_files():
    """Rule for rule, each data: URI is the bytes of the file the linked rule
    names - so a re-download that changed a file cannot leave a stale copy."""
    import base64
    css = (FONTS_DIR / "fonts.css").read_text(encoding="utf-8")
    files = re.findall(r"url\(/static/fonts/([^)]+)\)", css)
    inline = (FONTS_DIR / "fonts_inline.css").read_text(encoding="utf-8")
    payloads = re.findall(r"url\(data:font/woff2;base64,([^)]+)\)", inline)
    assert len(payloads) == len(files)
    for name, b64 in zip(files, payloads):
        assert base64.b64decode(b64) == (FONTS_DIR / name).read_bytes(), name


@pytest.mark.parametrize("key", ["modern-t1", "ats-t23"])
def test_no_render_path_reaches_google(key):
    for for_pdf in (False, True):
        html = document_html(SAMPLE, key, for_pdf=for_pdf)
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html


def test_pdf_document_embeds_fonts_and_preview_links_them():
    """The whole point: the PDF path cannot rely on a URL."""
    linked = document_html(SAMPLE, "modern-t1", for_pdf=False)
    assert '/static/fonts/fonts.css' in linked
    assert "data:font/woff2" not in linked, "preview must stay small"

    embedded = document_html(SAMPLE, "modern-t1", for_pdf=True)
    assert "data:font/woff2;base64," in embedded
    assert "/static/fonts/fonts.css" not in embedded, "PDF must not depend on a URL"


def test_font_head_variants_differ():
    assert font_head(for_pdf=False) != font_head(for_pdf=True)
    assert font_head(for_pdf=False).startswith("<link")
    assert font_head(for_pdf=True).startswith("<style")


def test_fonts_are_served_with_the_right_content_type(client):
    css = client.get("/static/fonts/fonts.css")
    assert css.status_code == 200 and css.mimetype == "text/css"
    first = re.search(r"url\(([^)]+)\)", css.data.decode()).group(1)
    woff = client.get(first)
    assert woff.status_code == 200
    assert woff.mimetype == "font/woff2", "Windows has no .woff2 MIME by default"
