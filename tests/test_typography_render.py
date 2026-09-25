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
from app.typography.render import family_stack, section_size_pt

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
    doc = _doc(AR, font_heading="Almarai", font_body="Tajawal", font_heading_size=40)
    cfg = _config(doc)
    for role, fam in (("heading", "Almarai"), ("body", "Tajawal")):
        assert cfg[role]["family"] == CSS_FAMILY_PREFIX + fam
        assert cfg[role]["nearest"] == {
            str(w): nearest_weight("ar", role, fam, w) for w in range(100, 1000, 100)}
    assert cfg["body"]["emphasis"] == EMPHASIS_WEIGHT
    assert cfg["heading"]["section_px"] == pytest.approx(section_size_pt(40, "ar") * 4 / 3)
    # §3.5's example, through the table the builder and runtime both use.
    assert cfg["heading"]["nearest"]["900"] == 800


def test_section_size_is_the_spec_clamp():
    assert section_size_pt(24, "en") == 11          # 10.08 -> floor 11
    assert section_size_pt(44, "en") == 18          # 18.48 -> cap 18
    assert section_size_pt(32, "en") == pytest.approx(13.44)
    assert section_size_pt(26, "ar") == 12
    assert section_size_pt(48, "ar") == 20


def test_typography_comes_after_the_rtl_rules():
    """Equal-looking specificity is decided by source order; ours must win."""
    doc = _doc(AR, font_heading="Cairo")
    assert doc.index(RTL_TYPOGRAPHY) < doc.index('id="cv-typography"')
    assert doc.index('id="cv-typography-config"') < doc.index("window.ResumeAutofit")


def test_pdf_keeps_the_template_look_until_step_4():
    """STEP-4 PIN. The PDF path has no base URL, so /static fonts would fail
    silently; until step 4 inlines the chosen faces, an export renders the
    template's own look rather than a fallback. Step 4 deletes this test."""
    doc = _own(_doc(EN, for_pdf=True, font_heading="Montserrat", font_body="Inter",
                    font_body_size=11))
    for marker in MARKERS:
        assert marker not in doc, marker


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
