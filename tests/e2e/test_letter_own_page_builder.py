"""The cover letter is always its OWN page, never on the same page as the CV
(run 11): in the builder's preview, in the "Cover letter" download and in
"CV + cover letter", where it starts on a new page after the CV's last one -
also when the CV itself runs to more than one page.
"""
from __future__ import annotations

import copy
import io
import re
import unicodedata

import pytest
from playwright.sync_api import expect

from tests import letter_samples as LS

pytestmark = pytest.mark.e2e

KEYS = ["modern-t4", "modern-t13", "modern-t3", "ats-t1"]


def _flat(s: str) -> str:
    """PDF text and source text made comparable: Arabic presentation forms
    folded (NFKC), case folded (caps templates print the subject uppercase),
    all whitespace dropped."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s)).casefold()


def _pdf_pages(page, data, key, part) -> list[str]:
    from pypdf import PdfReader
    b = page.evaluate("""async ([d, k, p]) => { const r = await fetch('/export/pdf', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({data: d, template_key: k, part: p})});
        if (!r.ok) throw new Error('export ' + r.status);
        return Array.from(new Uint8Array(await r.arrayBuffer())); }""", [data, key, part])
    return [_flat(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(bytes(b))).pages]


def _long_cv(lang: str) -> dict:
    """The demo CV with its experience repeated, so a flowing (ATS) template
    runs past one page and the letter has to follow page 2, not page 1."""
    d = LS.with_letter(lang)
    d["experience"] = [copy.deepcopy(e) for e in d["experience"] * 4]
    return d


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("cv", ["demo", "long"])
def test_pdf_letter_starts_on_a_new_page_after_the_cv(page, deployed_server, lang, key, cv):
    data = LS.with_letter(lang) if cv == "demo" else _long_cv(lang)
    subject = _flat(data["cover_letter"]["subject"])
    bullet = _flat(data["experience"][0]["bullets"][0])
    page.goto(deployed_server.url + "/templates")
    cv_pages = _pdf_pages(page, data, key, "cv")
    letter_pages = _pdf_pages(page, data, key, "letter")
    both = _pdf_pages(page, data, key, "both")

    assert len(letter_pages) == 1
    assert subject in letter_pages[0] and bullet not in letter_pages[0]
    # the CV's pages, unchanged, then exactly one more page: the letter's
    assert len(both) == len(cv_pages) + 1
    assert both[:-1] == cv_pages
    assert all(subject not in p for p in both[:-1])
    assert subject in both[-1] and bullet not in both[-1]


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_preview_shows_the_letter_as_a_separate_page_below_the_cv(page, deployed_server, lang):
    page.goto(f"{deployed_server.url}/lang/{lang}?next=/builder")
    cv = page.frame_locator("#preview-frame")
    expect(cv.locator(".tpl")).to_be_visible()
    page.check("#cl-toggle")
    letter = page.frame_locator("#letter-frame")
    expect(letter.locator(".tpl.cv-letter")).to_be_visible()
    subject = page.input_value('[name="cover_letter.subject"]') if page.locator(
        '[name="cover_letter.subject"]').count() else None

    # two documents: the CV page holds no letter, the letter frame one page and no CV
    expect(cv.locator(".cv-letter")).to_have_count(0)
    expect(letter.locator(".tpl")).to_have_count(1)
    if subject:
        assert subject not in cv.locator("body").inner_text()
    # stacked, never overlapping: the letter's page begins below the CV's.
    # Both boxes in ONE read - the builder scrolls the letter into view, and
    # two separate reads straddle that scroll.
    cv_bottom, letter_top = page.evaluate("""() => [
        document.getElementById('preview-stage').getBoundingClientRect().bottom,
        document.getElementById('letter-stage').getBoundingClientRect().top]""")
    assert letter_top >= cv_bottom + 16
