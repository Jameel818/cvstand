"""Word: the stacked stat chips' number AND label are centred, as in the PDF
(user, 2026-10-08). The browser half: tests/e2e/test_stat_chips_centred.py.

Read from the .docx itself: the paragraph holding each chip's number and the
one holding its label must carry <w:jc w:val="center"/>.
"""
from __future__ import annotations

import io
import re
import zipfile

import pytest

from app.exporters.docx import render_docx
from tests.samples import ARABIC, ENGLISH

CENTRED = ["modern-t1", "modern-t3", "modern-t4", "modern-t7", "modern-t9", "modern-t11",
           "modern-t13", "modern-t16", "modern-t18", "modern-t19", "modern-t21", "modern-t23"]


def _paragraphs(blob: bytes) -> list[tuple[str, str | None]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        jc = re.search(r'<w:jc w:val="(\w+)"', p)
        out.append((text.strip(), jc.group(1) if jc else None))
    return out


@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
@pytest.mark.parametrize("key", CENTRED)
def test_each_chip_number_and_label_is_centred(key, data):
    paras = _paragraphs(render_docx(data, key))
    for a in data["achievements"][:4]:
        if not a.get("metric"):
            continue
        for want in (a["metric"], a["label"]):
            hits = [jc for text, jc in paras if text == want]
            assert hits, f"{key}: no paragraph is exactly {want!r}"
            assert "center" in hits, f"{key}: {want!r} is aligned {hits}"
