"""Paper size A4 / US Letter (feature/paper-size, 2026-11-17).

The contract, as the user confirmed it:
  - a CV with NO `paper` field is LETTER (old CVs keep the page they approved);
  - a NEW CV is A4, or Letter when the browser language is en-US / en-CA;
  - the user can switch, and the choice is part of the résumé.
And the engineering rule: Letter output does not move by one byte.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import paper as P
from app import registry
from app.rendering import canvas_html, document_html
from app.schema import ResumeValidationError, normalize, validate

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
KEYS = registry.ported_keys()


def _with(paper):
    d = dict(SAMPLE)
    if paper is not None:
        d["paper"] = paper
    return d


# ---- the model -----------------------------------------------------------------

def test_the_two_papers():
    assert (P.LETTER.w, P.LETTER.h, P.LETTER.pt_per_px) == (850, 1100, 0.72)
    assert (P.A4.w, P.A4.h) == (850, 1202)
    assert P.A4.pt_per_px == pytest.approx(0.70033, abs=1e-5)
    assert P.LETTER.pdf_scale == pytest.approx(0.96)
    # Chromium's A4 sheet is 594.96pt wide (it cannot emit 595.28), and the
    # canvas is scaled to exactly that width
    assert P.A4.pdf_pt == (594.96, 841.92)
    assert P.A4.pdf_scale == pytest.approx(0.93327, abs=1e-5)
    assert P.A4.pdf_scale * 0.75 == pytest.approx(P.A4.pt_per_px, rel=6e-4)
    assert P.A4.h * 0.75 * P.A4.pdf_scale <= P.A4.pdf_pt[1]
    assert P.LETTER.twips == (12240, 15840) and P.A4.twips == (11906, 16838)


def test_a4_canvas_never_overruns_the_sheet():
    """1202px printed at 0.70033pt is 0.09pt short of 841.89 - never over it,
    or Chromium would start a second page."""
    printed = P.A4.h * P.A4.pt_per_px
    assert printed <= P.A4.h_pt
    assert P.A4.h_pt - printed < P.A4.pt_per_px          # less than one px short


@pytest.mark.parametrize("value,expected", [
    (None, "letter"), ("", "letter"), ("letter", "letter"), ("a4", "a4"),
    ("A4", "a4"), (" a4 ", "a4"), ("legal", "letter"), (4, "letter")])
def test_missing_or_unknown_paper_is_letter(value, expected):
    data = {} if value is None else {"paper": value}
    assert P.paper_key(data) == expected


@pytest.mark.parametrize("locale,expected", [
    ("en-US", "letter"), ("en-us", "letter"), ("en_CA", "letter"), ("en-CA", "letter"),
    ("en-GB", "a4"), ("en", "a4"), ("ar", "a4"), ("ar-SA", "a4"), ("fr-CA", "a4"),
    ("", "a4"), (None, "a4")])
def test_new_cv_default_by_browser_language(locale, expected):
    assert P.default_for_locale(locale) == expected


def test_use_binds_and_restores():
    assert P.current() is P.LETTER
    with P.use({"paper": "a4"}) as p:
        assert p is P.A4 and P.current() is P.A4
    assert P.current() is P.LETTER


# ---- the schema ------------------------------------------------------------------

def test_schema_accepts_both_papers_and_nothing_else():
    validate(_with("a4"))
    validate(_with("letter"))
    validate(_with(None))
    with pytest.raises(ResumeValidationError):
        validate(_with("legal"))


def test_normalize_does_not_add_paper():
    """Templates read the page from the `page` render variable; normalize()'s
    output (and its goldens) stay as they were."""
    assert "paper" not in normalize(SAMPLE)


# ---- rendering -------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_letter_canvas_is_byte_identical_to_no_paper(key):
    assert canvas_html(_with("letter"), key) == canvas_html(_with(None), key)


@pytest.mark.parametrize("key", KEYS)
def test_a4_canvas_is_1202_tall_and_nothing_says_1100(key):
    html = canvas_html(_with("a4"), key)
    assert "height:1202px" in html
    assert "1100px" not in html


def test_letter_document_carries_no_paper_attribute():
    doc = document_html(_with(None), "modern-t1")
    html_tag = re.search(r"<html[^>]*>", doc).group(0)
    assert html_tag == '<html lang="en" dir="ltr">'
    assert "@page { size: 850px 1100px; margin: 0; }" in doc
    assert doc == document_html(_with("letter"), "modern-t1")


def test_a4_document_declares_its_page():
    doc = document_html(_with("a4"), "modern-t1")
    assert re.search(r'<html [^>]*data-paper="a4" data-page-h="1202"', doc)
    assert "@page { size: 850px 1202px; margin: 0; }" in doc


def test_autofit_reads_the_page_height_from_the_document():
    js = (ROOT / "app" / "static" / "js" / "autofit.js").read_text(encoding="utf-8")
    assert 'getAttribute("data-page-h")' in js
    assert "var MAX_H = 1100;" not in js


def test_no_template_root_hardcodes_the_letter_height():
    tpl_dir = ROOT / "app" / "templates" / "resumes"
    hits = [str(p.relative_to(tpl_dir)) for p in tpl_dir.rglob("*.j2")
            if "height:1100px" in p.read_text(encoding="utf-8")]
    assert not hits, hits


def test_a4_cover_letter_is_1202_tall():
    from app import letter
    from tests import letter_samples as LS
    d = LS.with_letter("en")
    d["paper"] = "a4"
    assert "height:1202px" in letter.canvas_html(d, "modern-t1")
    d.pop("paper")
    assert "height:1100px" in letter.canvas_html(d, "modern-t1")


# ---- PDF ---------------------------------------------------------------------------

def test_pdf_page_rule_per_paper():
    from app.exporters import pdf
    assert pdf.page_css(P.LETTER) == "@page { size: 8.5in 11in; margin: 0; }"
    assert pdf.page_css(P.A4) == "@page { size: 210mm 297mm; margin: 0; }"
    assert pdf.PDF_SCALE == pytest.approx(0.96)


# ---- the builder switch ----------------------------------------------------------

@pytest.fixture()
def client():
    from app import create_app
    return create_app().test_client()


def test_builder_has_the_paper_switch_in_both_languages(client):
    for lang, label in (("en", "Paper size"), ("ar", "حجم الورق")):
        client.set_cookie("ui_lang", lang)
        html = client.get(f"/builder?lang={lang}").get_data(as_text=True)
        assert 'id="paper-switch"' in html
        assert label in html
        assert 'data-paper="a4"' in html and 'data-paper="letter"' in html


def test_builder_js_new_cv_default_and_storage():
    js = (ROOT / "app" / "static" / "js" / "builder.js").read_text(encoding="utf-8")
    # only a fresh CV (the seed) gets a default; a stored one keeps its own
    assert "if (data === seed && seedIsNew && !data.paper)" in js
    assert 'loc === "en-us" || loc === "en-ca" ? "letter" : "a4"' in js
    # missing paper reads as Letter, like the server
    assert 'data.paper === "a4" ? "a4" : "letter"' in js
    # the preview height follows the paper, never the literal
    assert "(scale - 1) * 1100" not in js


# ---- Word (Run 3) ------------------------------------------------------------------

def _docx_xml(data, key, part="cv", name="word/document.xml"):
    import io
    import zipfile
    from app.exporters.docx import render_docx
    z = zipfile.ZipFile(io.BytesIO(render_docx(data, key, part)))
    return z, z.read(name).decode("utf-8")


@pytest.mark.parametrize("key", ["modern-t1", "modern-t18", "modern-t22", "ats-t1"])
@pytest.mark.parametrize("part", ["cv", "both"])
def test_a4_word_sections_are_a4(key, part):
    _, xml = _docx_xml(_with("a4"), key, part)
    sizes = re.findall(r"<w:pgSz [^>]*/>", xml)
    assert sizes and all('w:w="11906"' in s and 'w:h="16838"' in s for s in sizes), sizes


@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_letter_word_sections_are_still_letter(key):
    _, xml = _docx_xml(_with(None), key)
    sizes = re.findall(r"<w:pgSz [^>]*/>", xml)
    assert sizes and all('w:w="12240"' in s and 'w:h="15840"' in s for s in sizes), sizes


def test_word_page_measures_follow_the_bound_paper():
    from app.exporters import docx_design as D
    assert (D.pt(100), D.page_h_px(), D.page_w_tw(), D.page_h_pt()) == (72.0, 1100, 12240, 792.0)
    with P.use("a4"):
        assert D.pt(850) == pytest.approx(595.28)
        assert (D.page_h_px(), D.page_w_tw(), D.page_h_pt()) == (1202, 11906, 841.9)
    assert D.pt(100) == 72.0                        # restored after the export


def test_a4_full_height_rects_reach_the_a4_page():
    """modern-t18's navy sidebar is a page rect: 1202px tall on A4, so
    1202 x 0.70033 = 841.8pt, not Letter's 792pt (it would stop 50pt short)."""
    z, _ = _docx_xml(_with("a4"), "modern-t18")
    hdr = "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("word/header"))
    emu = 1202 * P.A4.pt_per_px * 12700
    assert re.search(rf'cy="{round(emu)}"|cy="{int(emu)}"|height:841\.\d+pt', hdr), "no A4-high rect"


def test_t22_word_uses_the_a4_rail_picture():
    rails = ROOT / "app" / "static" / "rails"
    for lang in ("en", "ar"):
        assert (rails / f"modern-t22-{lang}-a4.png").exists()
    from PIL import Image
    a4 = Image.open(rails / "modern-t22-en-a4.png").size
    lt = Image.open(rails / "modern-t22-en.png").size
    assert a4 == (lt[0], 1202 * 3) and lt == (645, 3300)
