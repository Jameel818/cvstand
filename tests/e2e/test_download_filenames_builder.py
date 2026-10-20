"""The builder saves a download under the person's real name, in any script
(app/filenames.py; static/js/builder.js savedName). Until 2026-10 an Arabic
name saved as "_.pdf" / "_cover_letter.pdf" because the builder kept ASCII
letters only. English names save exactly as before (lower case, "_").
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

#: the builder's demo résumé in each language (data/demo_resume*.json)
STEM = {"en": "wren_ashworth", "ar": "ليلى_خليل"}
SUFFIX = {"cv": "", "letter": "_cover_letter", "both": "_cv_and_cover_letter"}


def _builder(page, server, lang):
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()


def _download(page, part, which):
    page.click("#dl-toggle")
    if part != "cv" or page.locator("#dl-parts").is_visible():
        page.click(f'#dl-parts [data-part="{part}"]')
    with page.expect_download(timeout=120000) as dl:
        page.click(which)
    return dl.value


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_downloads_carry_the_real_name(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    page.check("#cl-toggle")
    expect(page.frame_locator("#letter-frame").locator(".tpl.cv-letter")).to_be_visible()
    for part in ("cv", "letter", "both"):
        for which, ext in (("#dl-pdf", "pdf"), ("#dl-docx", "docx")):
            got = _download(page, part, which).suggested_filename
            assert got == f"{STEM[lang]}{SUFFIX[part]}.{ext}", got


def test_a_name_with_forbidden_characters_saves_cleanly(page, deployed_server):
    _builder(page, deployed_server, "ar")
    page.fill("#f_name", 'ليلى: خليل/"م"')
    page.wait_for_function("document.querySelector('#save-state').className === 'save-state'")
    got = _download(page, "cv", "#dl-docx").suggested_filename
    assert got == "ليلى_خليل_م.docx", got
