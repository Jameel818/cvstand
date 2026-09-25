"""The builder's Fonts section payload, its labels, and resets on render.

The browser half (the six selects behaving) is
tests/e2e/test_fonts_section.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.labels import ui_t
from app.typography import (
    FONTS, LIGHT_WARNING_PT, OFFERED, fonts_for, nearest_weight, offered_weights, size_scale,
)
from app.typography.registry import GROUP_LABEL, GROUP_ORDER
from app.typography.ui import builder_payload, payload_msgids

ROOT = Path(__file__).resolve().parent.parent
BUILDER_JS = ROOT / "app" / "static" / "js" / "builder.js"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_payload_lists_exactly_the_registry_in_group_order(lang):
    p = builder_payload(lang)
    assert p["lang"] == lang
    for role, r in p["roles"].items():
        listed = [f["family"] for g in r["groups"] for f in g["families"]]
        assert sorted(listed) == sorted(OFFERED[(lang, role)])
        order = [GROUP_ORDER[lang].index(next(k for k, v in GROUP_LABEL.items() if v == g["label"]))
                 for g in r["groups"]]
        assert order == sorted(order)
        for g in r["groups"]:
            for f in g["families"]:
                fam = f["family"]
                assert GROUP_LABEL[FONTS[fam].category] == g["label"]
                assert f["weights"] == list(offered_weights(lang, role, fam))
                assert f["single"] == (len(f["weights"]) == 1)
                assert f["playful"] == FONTS[fam].playful
                assert f["nearest"] == {str(w): nearest_weight(lang, role, fam, w)
                                        for w in range(100, 1000, 100)}
        scale = size_scale(lang, role)
        assert r["sizes"] == list(scale.options()) and r["default_size"] == scale.default


def test_payload_follows_the_spec_examples():
    en, ar = builder_payload("en"), builder_payload("ar")
    anton = next(f for g in en["roles"]["heading"]["groups"] for f in g["families"]
                 if f["family"] == "Anton")
    assert anton["single"] and anton["weights"] == [400]
    almarai = next(f for g in ar["roles"]["heading"]["groups"] for f in g["families"]
                   if f["family"] == "Almarai")
    assert almarai["nearest"]["900"] == 800          # §3.5: 900 -> Almarai 800
    assert en["light"] == {"weight": 200, "below_pt": LIGHT_WARNING_PT["en"]}
    assert ar["light"]["below_pt"] == 11
    assert ar["sample"] == "جميل أحمد"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_payload_label_has_arabic(lang):
    missing = [m for m in sorted(payload_msgids(lang))
               if str(ui_t(m, "ar")) == str(ui_t(m, "en"))]
    assert not missing, missing


def test_every_builder_T_literal_has_arabic():
    """Every T("...") in builder.js - the Fonts section's included - resolves
    to Arabic. Strictly wider than the old gate, which only saw text nodes."""
    ids = set(re.findall(r'\bT\("([^"]*)"\)', BUILDER_JS.read_text(encoding="utf-8")))
    assert len(ids) > 80
    missing = [m for m in sorted(ids) if str(ui_t(m, "ar")) == str(ui_t(m, "en"))]
    assert not missing, missing


def test_the_section_is_called_fonts():
    src = BUILDER_JS.read_text(encoding="utf-8")
    assert '{ id: "fonts", title: T("Fonts"), custom: "fonts" }' in src
    assert str(ui_t("Fonts", "ar")) == "الخطوط"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_builder_page_ships_the_payload_for_the_document_language(lang):
    from app import create_app
    client = create_app().test_client()
    client.set_cookie("ui_lang", lang)
    html = client.get("/builder").get_data(as_text=True)
    blob = re.search(r'<script id="typography-data" type="application/json">(.*?)</script>',
                     html, re.S).group(1)
    assert json.loads(blob) == json.loads(json.dumps(builder_payload(lang)))
    assert 'href="/static/fonts/typography.css"' in html
    assert 'id="form-notice"' in html


def test_render_reports_resets_for_a_cross_language_font():
    from app import create_app
    client = create_app().test_client()
    data = json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))
    data.update(font_heading="Montserrat", font_heading_weight=900, font_body="Tajawal")
    j = client.post("/api/render", json={"data": data, "template_key": "ats-t1"}).get_json()
    keys = {r["key"]: r["reason"] for r in j["resets"]}
    assert keys == {"font_heading": "not_offered", "font_heading_weight": "needs_font"}
    assert "CVT Tajawal" in j["doc"] and "CVT Montserrat" not in j["doc"]


def test_render_reports_no_resets_for_a_clean_resume():
    from app import create_app
    client = create_app().test_client()
    data = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
    j = client.post("/api/render", json={"data": data, "template_key": "ats-t1"}).get_json()
    assert j["resets"] == []


def test_fonts_for_matches_offered():
    """Sanity: the payload's source helper and OFFERED agree."""
    for (lang, role), fams in OFFERED.items():
        assert [f.family for f in fonts_for(lang, role)] == list(fams)
