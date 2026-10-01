"""Word applies the user's chosen SIZES (Name, Headings, Details) the way the
PDF does (app/static/js/typography.js): a factor per role - the name's largest
size, each section heading's largest size and the body's dominant size land
exactly on the chosen size (CSS pt on the 850px page = chosen x 4/3 x 0.72pt
on paper). Without a size choice nothing moves."""
from __future__ import annotations

import copy
import io
import re
import zipfile
from collections import Counter

import pytest
from lxml import etree

from app.exporters.docx import render_docx
from app.labels import reset_lang, set_lang, t
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CHOICE = {"font_name_size": 36, "font_heading_size": 15, "font_body_size": 10}


def _hp(pt_css: float) -> int:
    return round(pt_css * 4 / 3 * 0.72 * 2)


def _runs(blob):
    root = etree.fromstring(zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml"))
    for p in root.iter(f"{W}p"):
        ptext = "".join(x.text or "" for x in p.iter(f"{W}t")).strip()
        for r in p.findall(f"{W}r"):
            text = "".join(x.text or "" for x in r.iter(f"{W}t"))
            if not text.strip():
                continue
            st = r.find(f"{W}rPr/{W}rStyle")
            sz = r.find(f"{W}rPr/{W}sz")
            fonts = r.find(f"{W}rPr/{W}rFonts")
            if fonts is not None and fonts.get(f"{W}ascii") == "Arial":
                continue
            yield (st.get(f"{W}val") if st is not None else None,
                   int(sz.get(f"{W}val")) if sz is not None else 20, ptext, text)


@pytest.mark.parametrize("key,label", [("modern-t2", "EXPERIENCE"), ("modern-t11", "Experience"),
                                       ("ats-t1", None)])
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_chosen_sizes_land_exactly(key, label, data):
    d = copy.deepcopy(data)
    d.update(CHOICE)
    runs = list(_runs(render_docx(d, key)))
    names = [hp for st, hp, _, _ in runs if st == "CVName"]
    assert max(names) == _hp(CHOICE["font_name_size"])
    if label:
        token = set_lang("ar" if data is ARABIC else "en")
        try:
            want = str(t(label))
        finally:
            reset_lang(token)
        heads = [hp for st, hp, ptext, _ in runs if st == "CVHeading" and ptext == want]
    else:
        heads = [hp for st, hp, _, _ in runs if st == "CVHeading"]
    assert heads and max(heads) == _hp(CHOICE["font_heading_size"])
    body = Counter()
    for st, hp, ptext, text in runs:
        if st not in ("CVName", "CVHeading"):
            body[hp] += len(text)
    assert body.most_common(1)[0][0] == _hp(CHOICE["font_body_size"])


@pytest.mark.parametrize("key", ["modern-t2", "modern-t19", "ats-t1"])
def test_no_size_choice_moves_nothing(key):
    base = render_docx(ENGLISH, key)
    d = copy.deepcopy(ENGLISH)
    d.update({"font_name_size": None, "font_heading_size": None, "font_body_size": None})
    other = render_docx(d, key)

    def sizes(blob):
        x = zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode()
        return re.findall(r'<w:sz w:val="(\d+)"', x)
    assert sizes(base) == sizes(other)
