"""Phone numbers keep their left-to-right digit order inside Arabic CVs (run 4,
item 4). Bidi rule W2 turns digits after Arabic letters into Arabic numbers, so
"الهاتف: 555-0100-22" drew as "22-0100-555" in modern-t4's references. Each
phone is wrapped in an LRI...PDI isolate - right-to-left documents only."""
from __future__ import annotations

import json

from app import registry
from app.rendering import canvas_html

AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
LRI, PDI = "⁦", "⁩"


def _phones(data):
    return [data["contact"]["phone"]] + [r["phone"] for r in data.get("references", []) if r.get("phone")]


def test_every_arabic_phone_is_isolated_in_t4():
    html = canvas_html(AR, "modern-t4")
    for phone in _phones(AR):
        if phone and phone in html:
            assert f"{LRI}{phone}{PDI}" in html, phone


def test_english_output_carries_no_isolates():
    for key in ("modern-t4", "modern-t2", "modern-t20", "ats-t1"):
        assert LRI not in canvas_html(EN, key) and PDI not in canvas_html(EN, key)


def test_an_empty_phone_stays_empty():
    d = json.loads(json.dumps(AR))
    d["contact"]["phone"] = ""
    for r in d.get("references", []):
        r["phone"] = ""
    html = canvas_html(d, "modern-t4")
    assert LRI + PDI not in html and LRI not in html


def test_the_callers_data_is_not_mutated():
    d = json.loads(json.dumps(AR))
    canvas_html(d, "modern-t4")
    assert d == AR


def test_every_template_renders_arabic_phones_isolated():
    for key in registry.ported_keys():
        html = canvas_html(AR, key)
        assert AR["contact"]["phone"] not in html.replace(f"{LRI}{AR['contact']['phone']}{PDI}", ""), key
