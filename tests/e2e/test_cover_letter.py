"""The cover letter in the builder, driven the way a user drives it
(2026-10-18): the box above the form, the letter's section, the CV / Cover
letter switch, per-language storage, undo, the three downloads in PDF and
Word, the font ribbon reaching the letter, and one page whatever is typed.
"""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from playwright.sync_api import expect

from tests import letter_samples as LS

pytestmark = pytest.mark.e2e


def _builder(page, server, lang="en"):
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()


def _stored(page, lang=None) -> dict:
    key = f"'cvstand:resume:{lang}'" if lang else "'cvstand:resume:' + document.documentElement.lang"
    return json.loads(page.evaluate(f"localStorage.getItem({key})") or "{}")


def _settled(page):
    page.wait_for_function("document.querySelector('#save-state').className === 'save-state'")


def _letter(page):
    return page.frame_locator("#letter-frame").locator(".tpl.cv-letter")


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_off_by_default_nothing_of_the_letter_shows(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    expect(page.locator("#cl-toggle")).not_to_be_checked()
    for sel in ("#letter-stage", "#doc-switch", "#dl-parts", '.sec[data-sid="letter"]'):
        expect(page.locator(sel)).to_be_hidden() if sel != '.sec[data-sid="letter"]' else \
            expect(page.locator(sel)).to_have_count(0)
    # the CV sections keep their numbers
    expect(page.locator('.sec[data-sid="basics"] .num')).to_have_text("1")
    label = "أضف خطاب تقديم" if lang == "ar" else "Add a cover letter"
    expect(page.locator("label.cl-toggle")).to_have_text(label)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_ticking_fills_the_demo_letter_in_the_documents_language(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    page.check("#cl-toggle")
    expect(_letter(page)).to_be_visible()
    expect(page.locator('.sec[data-sid="letter"]')).to_have_attribute("open", "")
    expect(page.locator('.sec[data-sid="basics"] .num')).to_have_text("1")
    subject = LS.demo_letter(lang)["subject"]
    expect(page.locator('[name="cover_letter.subject"]')).to_have_value(subject)
    expect(_letter(page).locator(".cv-section")).to_contain_text(subject)
    expect(page.locator("#doc-switch")).to_be_visible()
    if lang == "ar":
        assert page.frame_locator("#letter-frame").locator("html").get_attribute("dir") == "rtl"
        assert re.search(r"[؀-ۿ]", _letter(page).inner_text())
    _settled(page)
    cl = _stored(page)["cover_letter"]
    assert cl["enabled"] is True and cl["date"]


def test_editing_the_form_reaches_the_letter_and_the_switch_moves_between_pages(page, deployed_server):
    _builder(page, deployed_server)
    page.check("#cl-toggle")
    page.fill('[name="cover_letter.subject"]', "Application for Design Director")
    expect(_letter(page).locator(".cv-section")).to_contain_text("Application for Design Director")
    page.click('#doc-switch [data-doc="cv"]')
    expect(page.locator('#doc-switch [data-doc="cv"]')).to_have_attribute("aria-selected", "true")
    page.click('#doc-switch [data-doc="letter"]')
    expect(page.locator('#doc-switch [data-doc="letter"]')).to_have_attribute("aria-selected", "true")
    # the letter is its own page AFTER the CV
    cv = page.locator("#preview-stage").bounding_box()
    lt = page.locator("#letter-stage").bounding_box()
    assert lt["y"] > cv["y"] + cv["height"] - 1


def test_paragraphs_add_and_remove_and_stop_at_the_cap(page, deployed_server):
    _builder(page, deployed_server)
    page.check("#cl-toggle")
    rows = page.locator('[data-list="cover_letter.paragraphs"] .bullet-row')
    n = rows.count()
    add = page.locator('.sec[data-sid="letter"] button.add')
    while rows.count() < 5:
        add.click()
    expect(add).to_be_disabled()
    rows.nth(0).locator("button").click()
    expect(rows).to_have_count(4)
    assert n >= 1


def test_each_language_keeps_its_own_letter(page, deployed_server):
    _builder(page, deployed_server, "en")
    page.check("#cl-toggle")
    page.fill('[name="cover_letter.subject"]', "English subject kept")
    _settled(page)
    _builder(page, deployed_server, "ar")
    expect(page.locator("#cl-toggle")).not_to_be_checked()   # Arabic has none yet
    page.check("#cl-toggle")
    expect(page.locator('[name="cover_letter.subject"]')).to_have_value(LS.demo_letter("ar")["subject"])
    _settled(page)
    _builder(page, deployed_server, "en")
    expect(page.locator("#cl-toggle")).to_be_checked()
    expect(page.locator('[name="cover_letter.subject"]')).to_have_value("English subject kept")
    assert _stored(page, "ar")["cover_letter"]["subject"] == LS.demo_letter("ar")["subject"]


def test_unticking_hides_it_and_ticking_brings_it_back_as_it_was(page, deployed_server):
    _builder(page, deployed_server)
    page.check("#cl-toggle")
    page.fill('[name="cover_letter.greeting"]', "Hello team,")
    page.uncheck("#cl-toggle")
    expect(page.locator("#letter-stage")).to_be_hidden()
    expect(page.locator('.sec[data-sid="letter"]')).to_have_count(0)
    page.check("#cl-toggle")
    expect(page.locator('[name="cover_letter.greeting"]')).to_have_value("Hello team,")


def test_undo_covers_the_letter(page, deployed_server):
    _builder(page, deployed_server)
    page.check("#cl-toggle")
    page.fill('[name="cover_letter.subject"]', "Changed")
    page.wait_for_timeout(1100)                      # a new undo step
    page.locator("body").click(position={"x": 5, "y": 300})
    page.keyboard.press("Control+z")                 # the typing
    expect(page.locator('[name="cover_letter.subject"]')).to_have_value(LS.demo_letter("en")["subject"])
    page.keyboard.press("Control+z")                 # the tick
    expect(page.locator("#cl-toggle")).not_to_be_checked()
    expect(page.locator("#letter-stage")).to_be_hidden()
    _settled(page)
    assert not _stored(page).get("cover_letter")


def test_the_font_ribbon_reaches_the_letter(page, deployed_server):
    _builder(page, deployed_server)
    page.check("#cl-toggle")
    page.select_option("#ty_section", "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    expect(_letter(page).locator(".cv-section")).to_have_css("font-family", re.compile("CVT Montserrat"))
    expect(_letter(page).locator(".cv-name").first).to_have_css("font-family", re.compile("CVT Montserrat"))


def _download(page, part, which):
    page.click("#dl-toggle")
    page.click(f'#dl-parts [data-part="{part}"]')
    with page.expect_download(timeout=120000) as dl:
        page.click(which)
    return dl.value


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_pdf_and_word_offer_cv_letter_and_both(page, deployed_server, lang):
    from pypdf import PdfReader
    _builder(page, deployed_server, lang)
    page.check("#cl-toggle")
    expect(_letter(page)).to_be_visible()
    expect(page.locator("#dl-parts button")).to_have_count(3)
    pages = {}
    for part in ("cv", "letter", "both"):
        d = _download(page, part, "#dl-pdf")
        pages[part] = len(PdfReader(d.path()).pages)
        w = _download(page, part, "#dl-docx")
        xml = zipfile.ZipFile(w.path()).read("word/document.xml").decode("utf-8")
        assert xml.count("<w:sectPr") == (1 if part != "both" else 2), part
        if part != "cv":
            assert w.suggested_filename.endswith(("_cover_letter.docx", "_cv_and_cover_letter.docx"))
    assert pages == {"cv": 1, "letter": 1, "both": 2}


def test_without_a_letter_the_download_is_the_cv_as_before(page, deployed_server):
    _builder(page, deployed_server)
    page.click("#dl-toggle")
    expect(page.locator("#dl-parts")).to_be_hidden()
    with page.expect_download(timeout=120000) as dl:
        page.click("#dl-pdf")
    assert not dl.value.suggested_filename.endswith("_cover_letter.pdf")


# ---- one page, whatever the form allows ------------------------------------------

@pytest.mark.slow
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_longest_letter_fits_one_page_in_every_template(page, deployed_server, lang):
    from app import registry
    data = LS.with_letter(lang, LS.longest(lang))
    page.goto(deployed_server.url + "/templates")
    not_fitted = []
    for key in registry.ported_keys():
        j = page.evaluate("""async ([d, k]) => (await (await fetch('/api/render', {method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({data: d, template_key: k, doc: 'letter'})})).json())""", [data, key])
        page.set_content(j["doc"])
        r = page.evaluate("window.ResumeAutofit.ready")
        if not r["fitted"]:
            not_fitted.append((key, r["height"]))
    assert not not_fitted


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", ["modern-t4", "modern-t13", "ats-t1", "modern-t3"])
def test_the_longest_letter_prints_on_one_pdf_page(page, deployed_server, lang, key):
    from pypdf import PdfReader
    data = LS.with_letter(lang, LS.longest(lang))
    page.goto(deployed_server.url + "/templates")
    b = page.evaluate("""async ([d, k]) => { const r = await fetch('/export/pdf', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({data: d, template_key: k, part: 'letter'})});
        return Array.from(new Uint8Array(await r.arrayBuffer())); }""", [data, key])
    assert len(PdfReader(io.BytesIO(bytes(b))).pages) == 1
