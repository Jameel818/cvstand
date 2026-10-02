"""Arabic through the REAL builder (run 4, item 2c): a new visitor who switches
the interface to Arabic gets the Arabic demo CV, right to left, Arabic labels
around it, and Arabic PDF and Word downloads - as on the live site."""
from __future__ import annotations

import io
import re
import zipfile

from playwright.sync_api import expect

from tests.e2e.test_exports import EXPORT_TIMEOUT

AR = re.compile(r"[؀-ۿﭐ-﷿ﹰ-﻿]")
LATIN = re.compile(r"[A-Za-z]")


def _download(page, selector, tmp_path):
    page.click("#dl-toggle")
    expect(page.locator("#dl-menu")).to_have_class(re.compile("is-open"))
    with page.expect_download(timeout=EXPORT_TIMEOUT) as info:
        page.click(selector)
    dest = tmp_path / info.value.suggested_filename
    info.value.save_as(dest)
    return dest.read_bytes()


def test_arabic_builder_is_arabic_end_to_end(page, deployed_server, tmp_path):
    """Against a server configured like the LIVE one (the browser owns the
    document): a single-user local server shows its one stored résumé instead."""
    live_server = deployed_server
    page.goto(f"{live_server.url}/lang/ar?next=/builder")
    tpl = page.frame_locator("#preview-frame").locator(".tpl")
    expect(tpl).to_be_visible()
    # the shell and the document are Arabic and right to left
    assert page.evaluate("document.documentElement.lang") == "ar"
    assert page.evaluate("document.documentElement.dir") == "rtl"
    assert page.frame_locator("#preview-frame").locator("html").get_attribute("dir") == "rtl"
    text = tpl.inner_text()
    assert len(AR.findall(text)) > 5 * len(LATIN.findall(text)), "the preview is not the Arabic demo"
    expect(page.locator("#dl-docx")).to_contain_text("Word")
    assert AR.search(page.locator(".sec summary").first.inner_text()), "builder labels not Arabic"

    pdf = _download(page, "#dl-pdf", tmp_path)
    from pypdf import PdfReader
    pdf_text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    assert len(AR.findall(pdf_text)) > 200, "the PDF is not Arabic"

    docx = _download(page, "#dl-docx", tmp_path)
    xml = zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode("utf-8")
    words = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml))
    assert "<w:bidi/>" in xml, "the Word file is not right to left"
    assert len(AR.findall(words)) > 5 * len(LATIN.findall(words)) / 2, "the Word file is not Arabic"
