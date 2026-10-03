"""A joined line in an Arabic Word design keeps its phone left to right (run 5).

modern-t11's contact line ("555-0138-64 · laila@... · دبي") was ONE run, and
because it held Arabic it carried w:rtl - so Word drew the phone as
"64-0138-555" (seen in Word's own PDF of a real builder download). Each item
is now its own run, w:rtl only where it has Arabic letters."""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from lxml import etree

from app.exporters.docx import render_docx

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
EN = json.loads(open("data/demo_resume.json", encoding="utf-8").read())
AR = json.loads(open("data/demo_resume_ar.json", encoding="utf-8").read())
PHONE = re.compile(r"\d{3}-\d{4}-\d{2}")
ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z0-9]")


def _runs(data, key):
    x = etree.fromstring(zipfile.ZipFile(io.BytesIO(render_docx(data, key)))
                         .read("word/document.xml"))
    for r in x.iter(W + "r"):
        text = "".join(t.text or "" for t in r.iter(W + "t"))
        yield text, r.find(f"{W}rPr/{W}rtl") is not None


@pytest.mark.parametrize("key", ["modern-t6", "modern-t11", "modern-t19"])
def test_no_phone_sits_in_a_right_to_left_run(key):
    runs = list(_runs(AR, key))
    phones = [(t, rtl) for t, rtl in runs if PHONE.search(t)]
    assert phones, "the demo's phone must be in the document"
    assert not [t for t, rtl in phones if rtl], phones
    # and nothing Latin-only rides in a w:rtl run next to it
    # (neutral-only runs - a dash, a "×", a separator - are right to left on purpose)
    assert not [t for t, rtl in runs if rtl and LATIN.search(t) and not ARABIC.search(t)]


def test_the_items_keep_their_text_and_order():
    text = "".join(t for t, _ in _runs(AR, "modern-t11"))
    c = AR["contact"]
    joined = " · ".join(x for x in (c["phone"], c["email"], c["address"], c["site"]) if x)
    assert joined in text


def test_english_is_one_run_as_before():
    runs = [t for t, _ in _runs(EN, "modern-t11")]
    assert any(t.count(" · ") >= 2 and PHONE.search(t) for t in runs)
