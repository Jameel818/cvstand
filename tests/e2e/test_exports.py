"""Downloads, driven from the builder's own menu.

The builder does not navigate to /export/*: it `fetch`es the route, wraps the
bytes in a blob and clicks a synthetic `<a download>` (builder.js `download()`),
after awaiting `doSave()`. So the thing worth testing is the whole chain —
unsaved edit -> PUT -> export -> a file on disk with the edit in it — which is
what a user actually does and what no unit test covers.
"""
from __future__ import annotations

import re
import zipfile

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

EXPORT_TIMEOUT = 180_000  # Chromium cold-starts inside the server for the PDF


def _pdf_page_count(blob: bytes) -> int:
    """Page objects in a Chromium-produced PDF. `/Type /Page` must not match
    `/Type /Pages`, the tree root — hence the negative lookahead."""
    return len(re.findall(rb"/Type\s*/Page(?!s)", blob))


def _download(page, selector: str, tmp_path):
    page.click("#dl-toggle")
    expect(page.locator("#dl-menu")).to_have_class(re.compile("is-open"))
    with page.expect_download(timeout=EXPORT_TIMEOUT) as info:
        page.click(selector)
    dl = info.value
    dest = tmp_path / dl.suggested_filename
    dl.save_as(dest)
    return dl, dest.read_bytes()


def test_pdf_download_is_one_page_and_carries_the_latest_edit(page, live_server, tmp_path):
    page.goto(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Wren")

    page.fill("#f_name", "Peta Vale")
    expect(page.locator("#save-state")).to_have_text("Saved")

    dl, blob = _download(page, "#dl-pdf", tmp_path)

    assert dl.suggested_filename == "peta_vale.pdf"
    assert blob[:5] == b"%PDF-"
    assert len(blob) > 20_000, "a PDF this small has no embedded fonts"
    assert _pdf_page_count(blob) == 1, (
        "the résumé printed on more than one page — auto-fit did not settle "
        "before page.pdf(), or the layout overflows")


def test_docx_download_opens_as_a_package_containing_the_edit(page, live_server, tmp_path):
    page.goto(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Wren")

    page.fill("#f_name", "Peta Vale")
    expect(page.locator("#save-state")).to_have_text("Saved")

    dl, blob = _download(page, "#dl-docx", tmp_path)

    assert dl.suggested_filename == "peta_vale.docx"
    assert blob[:2] == b"PK", "not a zip — docxtpl returned something else"
    dest = tmp_path / dl.suggested_filename
    with zipfile.ZipFile(dest) as z:
        assert "word/document.xml" in z.namelist()
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Peta Vale" in xml
    assert "{{" not in xml and "{%" not in xml, "an unrendered docxtpl tag shipped"


def test_ats_template_exports_from_the_other_word_master(page, live_server, tmp_path):
    """Two masters serve all 49 layouts; picking an ATS template must switch
    families. The ATS master has no photo slot by design."""
    page.goto(live_server.url + "/templates?cat=ats")
    page.locator('.use-btn[data-key="ats-t3"]').click()
    expect(page).to_have_url(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Wren")

    _dl, blob = _download(page, "#dl-docx", tmp_path)
    assert blob[:2] == b"PK"

    dest = tmp_path / _dl.suggested_filename
    with zipfile.ZipFile(dest) as z:
        assert not [n for n in z.namelist() if n.startswith("word/media/")], (
            "the ATS master must never embed an image — images defeat résumé parsers")


def test_a_failing_export_surfaces_instead_of_silently_doing_nothing(page, live_server):
    """builder.js alerts on a non-OK export. Without this, a 500 looks exactly
    like a successful click."""
    page.route("**/export/pdf*", lambda route: route.fulfill(
        status=500, content_type="text/html", body="<p>boom</p>"))
    page.goto(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Wren")

    messages = []
    page.on("dialog", lambda d: (messages.append(d.message), d.dismiss()))
    page.click("#dl-toggle")
    page.click("#dl-pdf")
    expect(page.locator("#dl-menu")).not_to_have_class(re.compile("is-open"))
    page.wait_for_timeout(1500)
    assert messages and "export failed" in messages[0]
