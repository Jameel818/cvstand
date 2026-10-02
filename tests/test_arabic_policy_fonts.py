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
