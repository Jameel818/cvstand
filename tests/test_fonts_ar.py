"""Arabic font coverage (bilingual AR/EN, phase 2).

WHY THIS FILE EXISTS
    A missing Arabic face raises nothing. Chromium substitutes whatever the
    host machine happens to have, or draws tofu — and the PDF path is worse,
    because `set_content()`'s base URL is about:blank, so a linked stylesheet
    resolves to nothing at all. Every failure in this area is silent, which is
    why it gets asserted rather than eyeballed.

    The central claim these tests defend is the one that lets 49 templates stay
    untouched: the Arabic faces are declared under the LATIN family names, and
    confined by unicode-range to Arabic codepoints. If a single alias reached
    below U+0600 it could outrank the real Latin face and change how English
    renders. `test_no_alias_claims_a_latin_codepoint` is that guarantee.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.rendering import document_html, font_head

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "app" / "static" / "fonts"
AR_CSS = FONTS_DIR / "fonts_ar.css"
AR_INLINE = FONTS_DIR / "fonts_ar_inline.css"
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

# The Arabic block floor. Below this lie Latin, punctuation and the digits.
ARABIC_FLOOR = 0x0600

# The five sources the Latin families are paired to. Pairing preserves register
# (geometric -> geometric, serif -> naskh, display -> Kufi), not just coverage.
ARABIC_SOURCES = {"Cairo", "Tajawal", "Amiri", "Noto Kufi Arabic", "IBM Plex Sans Arabic"}


@pytest.fixture(scope="module")
def ar_css() -> str:
    if not AR_CSS.exists():
        pytest.fail("fonts_ar.css missing — run tools/fetch_fonts_ar.py")
    return AR_CSS.read_text(encoding="utf-8")


# --------------------------------------------------------- the safety property

def test_no_alias_claims_a_latin_codepoint(ar_css):
    """THE guarantee behind "English cannot change".

    Every Arabic @font-face borrows a Latin family's NAME. That is only safe
    while its unicode-range excludes Latin: otherwise `font-family: Archivo`
    could start resolving an English letter out of Tajawal."""
    ranges = re.findall(r"unicode-range: ([^;]+);", ar_css)
    assert ranges, "no unicode-range declared — the aliases would be unbounded"
    for rng in ranges:
        for part in rng.split(","):
            start = part.strip().lstrip("Uu+").split("-")[0]
            assert int(start, 16) >= ARABIC_FLOOR, (
                f"alias range {part.strip()} reaches below U+0600 and could "
                f"claim a Latin glyph")


def test_aliases_use_the_latin_family_names(ar_css):
    """If these declared their own names the templates would need 49 edits."""
    latin = set(re.findall(r"font-family: '([^']+)'",
                           (FONTS_DIR / "fonts.css").read_text(encoding="utf-8")))
    aliased = set(re.findall(r"font-family: '([^']+)'", ar_css))
    assert aliased <= latin, f"alias names that are not Latin families: {aliased - latin}"
    assert aliased == latin, f"Latin families with no Arabic coverage: {latin - aliased}"


# ------------------------------------------------------------------- integrity

def test_every_referenced_arabic_file_is_present(ar_css):
    refs = re.findall(r"url\(/static/fonts/([^)]+)\)", ar_css)
    assert refs, "fonts_ar.css references no files"
    missing = [r for r in refs if not (FONTS_DIR / r).exists()]
    assert not missing, f"fonts_ar.css points at missing files: {missing[:5]}"


def test_both_arabic_stylesheets_declare_the_same_families(ar_css):
    """Drift here means an Arabic PDF renders in a different face than its
    preview — the same trap the Latin pair has."""
    inline = set(re.findall(r"font-family: '([^']+)'", AR_INLINE.read_text(encoding="utf-8")))
    assert set(re.findall(r"font-family: '([^']+)'", ar_css)) == inline


def test_arabic_licences_are_vendored(ar_css):
    """OFL 1.1 clause 2 — the licence travels with the fonts, Arabic included."""
    sources = set(re.findall(r"<- ([A-Za-z0-9 ]+) \d+ \*/", ar_css))
    assert sources == ARABIC_SOURCES, f"unexpected Arabic sources: {sources}"
    for fam in sorted(sources):
        path = FONTS_DIR / "licenses" / f"{fam.replace(' ', '-')}-OFL.txt"
        assert path.exists(), f"no vendored OFL.txt for {fam}"


# ------------------------------------------------------------ language gating

def test_english_documents_carry_no_arabic_payload():
    """Not a safety requirement — the unicode-range already handles that — but
    an English export has no reason to carry ~2.1 MB of Arabic."""
    doc = document_html(SAMPLE, "modern-t1", for_pdf=True)
    assert "fonts_ar" not in doc
    for src in ARABIC_SOURCES:
        assert src not in doc, f"English PDF embeds {src}"


def test_arabic_documents_embed_the_arabic_faces():
    doc = document_html(dict(SAMPLE, lang="ar"), "modern-t1", for_pdf=True)
    assert doc.count("data:font/woff2;base64,") > 0
    assert "Tajawal" in doc or "Cairo" in doc


def test_arabic_preview_links_rather_than_embeds():
    doc = document_html(dict(SAMPLE, lang="ar"), "modern-t1", for_pdf=False)
    assert "/static/fonts/fonts_ar.css" in doc
    assert "data:font/woff2" not in doc, "preview must stay small"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_no_render_path_reaches_google(lang):
    """The offline guarantee (tests/e2e/test_offline.py) must hold in Arabic too."""
    for for_pdf in (False, True):
        html = document_html(dict(SAMPLE, lang=lang), "modern-t1", for_pdf=for_pdf)
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html


def test_font_head_defaults_to_english():
    """Callers that predate bilingual support must keep getting Latin only."""
    assert "fonts_ar" not in font_head()
    assert "fonts_ar" not in font_head(for_pdf=False)
