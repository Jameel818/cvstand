"""The Arabic font POLICY's faces are really loaded (run 4, item 3).

Measured before the fix: with no font chosen, every Arabic CV (preview and
PDF, local and live) drew system fallbacks - Segoe UI / Times New Roman /
Tahoma here, Liberation Sans / FreeSerif on the server - because the policy
named IBM Plex Sans Arabic, Tajawal and Cairo but no document declared them."""
from __future__ import annotations

import json
import re

from app.rendering import POLICY_FACES, document_html

AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())


def test_the_policy_names_the_faces_the_document_declares():
    doc = document_html(AR, "modern-t2")
    for family in ("CVT IBM Plex Sans Arabic", "CVT Tajawal", "CVT Cairo"):
        assert f'"{family}"' in doc, family
    assert "/static/fonts/typography.css" in doc        # the preview fetches them


def test_the_arabic_pdf_inlines_exactly_the_policy_faces():
    doc = document_html(AR, "ats-t1", for_pdf=True)
    block = re.search(r'<style id="cv-policy-faces">(.*?)</style>', doc, re.S).group(1)
    declared = set(re.findall(r"font-family: '([^']+)';\s*font-style: normal;\s*"
                              r"font-weight: (\d+)", block))
    want = {(f"CVT {f}", str(w)) for f, ws in POLICY_FACES for w in ws}
    assert declared == want
    assert "url(data:font/" in block and "/static/fonts/" not in block   # no base URL on the PDF path


def test_an_english_document_carries_none_of_it():
    for pdf in (False, True):
        doc = document_html(EN, "modern-t2", for_pdf=pdf)
        assert "cv-policy-faces" not in doc and "CVT Tajawal" not in doc


def test_a_chosen_font_still_wins_over_the_policy():
    doc = document_html(dict(AR, font_body="Noto Naskh Arabic"), "modern-t2", for_pdf=True)
    assert "CVT Noto Naskh Arabic" in doc


def test_a_chosen_role_drops_only_its_own_policy_faces():
    """typography.js lays the page out once BEFORE data-cvt switches the chosen
    rules on; a declared policy face in a chosen role's stack was fetched by
    that layout and never drawn (R4-8a: every Arabic test_choices_apply case)."""
    from app.rendering import RTL_TYPOGRAPHY, rtl_typography
    from app.schema import typography_of
    css = lambda **k: rtl_typography(typography_of(dict(AR, **k))[0])
    body = '[dir="rtl"] .tpl * {\n    font-family: '
    name = '[dir="rtl"] .tpl .cv-name * {\n    font-family: '
    sec = '[dir="rtl"] .tpl .cv-section * {\n    font-family: '
    assert css() == RTL_TYPOGRAPHY
    only_body = css(font_body="Lateef")
    assert only_body.split(body)[1].startswith('"IBM Plex Sans Arabic"')
    assert only_body.split(name)[1].startswith('"CVT Tajawal"')     # unchosen role keeps it
    # an unset name follows the Headings font, so its policy face goes too ...
    headings = css(font_heading="Cairo")
    assert headings.split(sec)[1].startswith('"Cairo"')
    assert headings.split(name)[1].startswith('"Tajawal"')
    # ... but "template" keeps the name on the policy face
    kept = css(font_heading="Cairo", font_name="template")
    assert kept.split(name)[1].startswith('"CVT Tajawal"')
    assert "CVT " not in css(font_body="Lateef", font_heading="Cairo", font_name="Alexandria")
