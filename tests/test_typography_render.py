"""What document_html() emits for the typography keys (spec §6.1, plan step 3).

The load-bearing claim is the first one: a résumé with NO typography keys
emits no trace of this feature at all - no stylesheet link, no rules, no
config, no runtime. The 50 pixel goldens prove the rendered result did not
move; this proves nothing was even added for them to catch.

The browser half (the roles actually resolving, weights mapped, only chosen
faces downloaded) is tests/e2e/test_typography_apply.py.
"""
from __future__ import annotations

import json
import re

import pytest

from app.rendering import RTL_TYPOGRAPHY, autofit_script, document_html
from app.typography import (
    CSS_FAMILY_PREFIX, EMPHASIS_WEIGHT, FONTS, LATIN_EXT_FALLBACK, OFFERED,
    TYPOGRAPHY_KEYS, built_faces, built_weights, nearest_weight,
)
from app.schema import typography_of
from app.typography import face
from app.typography.faces import FONT_DIR
from app.typography.render import effective, family_stack, pdf_faces

EN = json.loads(open("data/sample_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/sample_resume_ar.json", encoding="utf-8").read())
KEY = "ats-t1"

MARKERS = ("typography.css", "cv-typography", "CVTypography", "data-cvt", CSS_FAMILY_PREFIX)


def _doc(base, for_pdf=False, **keys):
    return document_html(dict(base, **keys), KEY, for_pdf=for_pdf)


def _own(doc: str) -> str:
    """The document minus the inlined autofit engine, which ships in every
    document and names its typography hook (and says `display:none` in a
    comment). What is left is what THIS feature added, or did not."""
    af = autofit_script()
    assert doc.count(af) == 1
    return doc.replace(af, "")


def _config(doc: str) -> dict:
    m = re.search(r'<script type="application/json" id="cv-typography-config">(.*?)</script>',
                  doc, re.S)
    assert m, "no config block"
    return json.loads(m.group(1))


# ---- no keys: nothing at all ------------------------------------------------

@pytest.mark.parametrize("base", [EN, AR], ids=["en", "ar"])
def test_no_keys_emit_nothing(base):
    doc = _own(_doc(base))
    for marker in MARKERS:
        assert marker not in doc, marker


@pytest.mark.parametrize("base", [EN, AR], ids=["en", "ar"])
def test_null_keys_are_the_same_document_as_absent_keys(base):
    assert _doc(base, **dict.fromkeys(TYPOGRAPHY_KEYS)) == _doc(base)


@pytest.mark.parametrize("base", [EN, AR], ids=["en", "ar"])
def test_invalid_or_cross_language_keys_emit_nothing(base):
    other = "Cairo" if base is EN else "Montserrat"
    doc = _own(_doc(base, font_heading=other, font_body="Comic Sans",
                    font_heading_weight=800))
    for marker in MARKERS:
        assert marker not in doc, marker


def test_a_css_injection_string_never_reaches_the_document():
    evil = "Inter'; } body { display:none } .x{ font-family:'"
    doc = _own(_doc(EN, font_body=evil, font_heading="Montserrat"))
    assert "display:none" not in doc
    assert "Montserrat" in doc                 # the valid half still applies


# ---- keys present ------------------------------------------------------------

def test_chosen_fonts_link_the_sheet_and_set_the_families():
    doc = _doc(EN, font_heading="Montserrat", font_body="Inter")
    assert '<link rel="stylesheet" href="/static/fonts/typography.css">' in doc
    assert f"font-family: {family_stack('Inter')} !important" in doc
    assert f"font-family: {family_stack('Montserrat')} !important" in doc
    assert "font-synthesis: none !important" in doc


def test_details_rule_cannot_reach_the_headlines():
    """Choosing only a Details font must leave the name and the section titles
    on the template's face; the :not(:where(...)) is what guarantees it."""
    doc = _doc(EN, font_body="Inter")
    rule = re.search(r"html\[data-cvt\] \.tpl,\s*html\[data-cvt\] \.tpl (:not\(.*?\)) \{", doc, re.S)
    assert rule, "details rule missing"
    for hook in (".cv-name", ".cv-name *", ".cv-section", ".cv-section *"):
        assert hook in rule.group(1)
    assert "Montserrat" not in doc


def test_a_size_alone_needs_no_stylesheet():
    """A size with no font is kept by the validator and applies to the
    template's own face: runtime and config, but no faces to load."""
    doc = _doc(EN, font_body_size=11)
    assert "typography.css" not in doc and "cv-typography\"" not in doc
    cfg = _config(doc)
    assert cfg["body"]["family"] is None
    assert cfg["body"]["size_px"] == pytest.approx(11 * 4 / 3)


def test_config_tables_are_the_registry_nearest_weight():
    doc = _doc(AR, font_heading="Almarai", font_body="Tajawal", font_heading_size=16)
    cfg = _config(doc)
    for role, reg, fam in (("section", "heading", "Almarai"), ("name", "name", "Almarai"),
                           ("body", "body", "Tajawal")):
        assert cfg[role]["family"] == CSS_FAMILY_PREFIX + fam
        assert cfg[role]["nearest"] == {
            str(w): nearest_weight("ar", reg, fam, w) for w in range(100, 1000, 100)}
    assert cfg["body"]["emphasis"] == EMPHASIS_WEIGHT
    # §3.5's example, through the table the builder and runtime both use.
    assert cfg["section"]["nearest"]["900"] == 800


def test_section_size_is_set_directly():
    """Step 3c: no more derivation from the name size."""
    cfg = _config(_doc(EN, font_heading_size=15, font_name_size=40))
    assert cfg["section"]["size_px"] == pytest.approx(15 * 4 / 3)
    assert cfg["name"]["size_px"] == pytest.approx(40 * 4 / 3)


# ---- the Name group (step 3c) ------------------------------------------------------

def test_name_same_as_headings_takes_the_headings_font_and_weight():
    cfg = _config(_doc(EN, font_heading="Montserrat", font_heading_weight=800))
    assert cfg["name"]["family"] == cfg["section"]["family"] == "CVT Montserrat"
    assert cfg["name"]["weight"] == 800


def test_name_own_weight_beats_the_inherited_one():
    cfg = _config(_doc(EN, font_heading="Montserrat", font_heading_weight=800,
                       font_name_weight=900))
    assert (cfg["name"]["weight"], cfg["section"]["weight"]) == (900, 800)


def test_name_template_default_gets_no_rule():
    doc = _doc(EN, font_heading="Montserrat", font_name="template")
    cfg = _config(doc)
    assert cfg["name"]["family"] is None and cfg["section"]["family"] == "CVT Montserrat"
    assert "html[data-cvt] .tpl .cv-name" not in doc
    assert "html[data-cvt] .tpl .cv-section" in doc


def test_name_with_its_own_font():
    doc = _doc(EN, font_heading="Montserrat", font_name="Playfair Display")
    assert _config(doc)["name"]["family"] == "CVT Playfair Display"
    assert f"font-family: {family_stack('Playfair Display')} !important" in doc


def test_name_template_alone_emits_nothing():
    """`font_name: "template"` with nothing else chosen is the template's look."""
    for marker in MARKERS:
        assert marker not in _own(_doc(EN, font_name="template")), marker


@pytest.mark.parametrize("lang, heading, size", [("en", "Montserrat", 32), ("ar", "Cairo", 34)])
def test_a_pre_split_resume_keeps_its_name(lang, heading, size):
    """A résumé saved in step 3 (font_heading + a headline size) renders its
    NAME exactly as step 3 did - same family, same weight, same px - and its
    section titles at the old derived size to the nearest point."""
    base = EN if lang == "en" else AR
    cfg = _config(_doc(base, font_heading=heading, font_heading_weight=800 if lang == "en" else None,
                       font_heading_size=size))
    assert cfg["name"]["family"] == CSS_FAMILY_PREFIX + heading
    assert cfg["name"]["size_px"] == pytest.approx(size * 4 / 3)
    lo, hi = (11, 18) if lang == "en" else (12, 20)
    old_section = min(max(size * 0.42, lo), hi)
    assert abs(cfg["section"]["size_px"] / (4 / 3) - old_section) <= 0.5


def test_typography_comes_after_the_rtl_rules():
    """Equal-looking specificity is decided by source order; ours must win."""
    doc = _doc(AR, font_heading="Cairo", font_name="Tajawal")
    assert doc.index(RTL_TYPOGRAPHY) < doc.index('id="cv-typography"')
    assert doc.index('id="cv-typography-config"') < doc.index("window.ResumeAutofit")


# ---- the PDF (spec step 4) ---------------------------------------------------

def _faces_block(doc: str) -> str:
    m = re.search(r'<style id="cv-typography-faces">(.*?)</style>', doc, re.S)
    assert m, "no inlined faces"
    return m.group(1)


def _inlined(doc: str) -> set[tuple[str, int]]:
    block = _faces_block(doc)
    return {(fam.removeprefix(CSS_FAMILY_PREFIX), int(w)) for fam, w in re.findall(
        r"font-family: '([^']+)'; font-style: normal; font-weight: (\d+);", block)}


@pytest.mark.parametrize("base", [EN, AR], ids=["en", "ar"])
def test_pdf_with_no_keys_emits_nothing(base):
    doc = _own(_doc(base, for_pdf=True))
    for marker in MARKERS:
        assert marker not in doc, marker


PDF_CASES = [
    (EN, dict(font_heading="Montserrat", font_body="Inter", font_body_size=11)),
    (EN, dict(font_name="Playfair Display", font_heading="Raleway", font_body="Lora")),
    (AR, dict(font_heading="Cairo", font_body="IBM Plex Sans Arabic", font_name="Tajawal")),
    (AR, dict(font_heading="Almarai", font_body="Scheherazade New")),
]


@pytest.mark.parametrize("base,keys", PDF_CASES, ids=[str(i) for i in range(len(PDF_CASES))])
def test_pdf_inlines_exactly_the_faces_it_can_request(base, keys):
    """No <link> (it would resolve to nothing on about:blank); instead every
    face pdf_faces() names, as data: - and nothing else."""
    doc = _doc(base, for_pdf=True, **keys)
    assert "typography.css" not in doc
    assert "/static/fonts/" not in _faces_block(doc)
    values, _ = typography_of(dict(base, **keys))
    assert _inlined(doc) == pdf_faces(values, base.get("lang") or "en")


@pytest.mark.parametrize("base,keys", PDF_CASES, ids=[str(i) for i in range(len(PDF_CASES))])
def test_pdf_carries_the_previews_rules_config_and_runtime(base, keys):
    """Only how the faces arrive may differ: the family rules, the config and
    the runtime are byte-identical, so the PDF resolves roles as the preview."""
    pdf, preview = _doc(base, for_pdf=True, **keys), _doc(base, **keys)
    for pattern in (r'<style id="cv-typography">.*?</style>',
                    r'<script type="application/json" id="cv-typography-config">.*?</script>'):
        a, b = re.search(pattern, pdf, re.S), re.search(pattern, preview, re.S)
        assert a and b and a.group(0) == b.group(0)
    assert "window.CVTypography" in _own(pdf)


def test_pdf_adds_the_latin_ext_fallback_only_where_the_stack_names_it():
    with_fb = _inlined(_doc(AR, for_pdf=True, font_body="Tajawal"))
    assert {f for f, _w in with_fb} == {"Tajawal", "Work Sans"}
    without = _inlined(_doc(AR, for_pdf=True, font_body="Cairo"))
    assert {f for f, _w in without} == {"Cairo"}


def test_pdf_embeds_rfn_families_as_their_unmodified_ttf():
    """The Reserved-Font-Name families ship no woff2 (FONTS.md); the PDF
    embeds the same TTF bytes the preview links."""
    import base64
    block = _faces_block(_doc(AR, for_pdf=True, font_body="IBM Plex Sans Arabic"))
    payloads = re.findall(r"url\(data:font/ttf;base64,([^)]+)\) format\('truetype'\)", block)
    assert payloads
    ttf = {(FONT_DIR / face("IBM Plex Sans Arabic", w)["ttf"]).read_bytes()
           for w in built_weights("ar", "body", "IBM Plex Sans Arabic")}
    assert {base64.b64decode(p) for p in payloads} == ttf


# ---- Latin-Ext fallback --------------------------------------------------------

ARABIC = sorted({f for (lang, _r), fams in OFFERED.items() if lang == "ar" for f in fams})
NO_LATIN_EXT = {"Almarai", "Aref Ruqaa", "El Messiri", "IBM Plex Sans Arabic",
                "Jomhuria", "Lateef", "Scheherazade New", "Tajawal"}


@pytest.mark.parametrize("family", ARABIC)
def test_fallback_only_where_latin_ext_is_missing(family):
    stack = family_stack(family)
    fallback = LATIN_EXT_FALLBACK[FONTS[family].generic]
    assert stack.startswith(f"'{CSS_FAMILY_PREFIX}{family}'")
    assert (f"'{CSS_FAMILY_PREFIX}{fallback}'" in stack) == (family in NO_LATIN_EXT)
    assert stack.endswith(FONTS[family].generic)


@pytest.mark.parametrize("family", sorted(NO_LATIN_EXT))
def test_fallback_is_built_at_every_weight_it_can_be_asked_for(family):
    """The fallback renders at whatever weight the Arabic face was asked for;
    with font-synthesis none, a missing weight would silently substitute."""
    fallback = LATIN_EXT_FALLBACK[FONTS[family].generic]
    needed = {w for (lang, role), fams in OFFERED.items() if lang == "ar" and family in fams
              for w in built_weights(lang, role, family)}
    have = {w for (f, w) in built_faces() if f == fallback}
    assert needed <= have, f"{fallback} lacks {sorted(needed - have)}"


@pytest.mark.parametrize("family", sorted({f for fams in OFFERED.values() for f in fams}))
def test_no_latin_family_gets_a_fallback(family):
    if family in NO_LATIN_EXT:
        return
    assert family_stack(family).count(CSS_FAMILY_PREFIX) == 1
