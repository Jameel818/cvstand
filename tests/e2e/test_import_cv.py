"""Import my CV in the builder (2026-10-18): the button, the review screen,
Replace vs Add, Undo, Cancel, errors - EN + AR.

The test server has NO API key (none is ever set by this suite), so the
button is disabled and says "Coming soon" - that is asserted first, as it
is. The rest of the journey then enables the button in the page and answers
/api/import with a MOCKED reply (page.route), so the browser side is driven
end to end with no network and no cost. The server side of the same
contract - real files, the guard, limits - is tests/test_import_cv.py.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

IMPORTED = {
    "en": {
        "name": "Sam Rivera", "title": "Product Designer",
        "summary": "Designer of booking flows for regional airlines.",
        "contact": {"email": "sam.rivera@example.org", "phone": "555-0101-22", "address": "Lisbon",
                    "site": "", "social": [{"label": "LinkedIn", "url": "linkedin.com/in/samrivera"}]},
        "experience": [{"role": "Senior Product Designer", "company": "Northwind Air", "location": "Lisbon",
                        "start": "2020", "end": "Present", "bullets": ["Redesigned check-in for 2M users."]}],
        "education": [{"degree": "BA Interaction Design", "school": "Lisbon School of Design",
                       "start": "2012", "end": "2015", "gpa": "", "bullets": []}],
        "skills": [{"name": "Prototyping", "level": "Expert"}, {"name": "Research", "level": ""}],
        "tools": ["Figma"], "languages": [{"name": "Portuguese", "level": "Native"}],
        "recognition": [{"title": "Google UX Certificate", "detail": "2021"}], "references": [],
    },
    "ar": {
        "name": "سامي رياض", "title": "مصمم منتجات",
        "summary": "مصمم مسارات حجز لشركات طيران إقليمية.",
        "contact": {"email": "sami.riad@example.org", "phone": "555-0101-22", "address": "عمّان",
                    "site": "", "social": []},
        "experience": [{"role": "مصمم منتجات أول", "company": "طيران الشمال", "location": "عمّان",
                        "start": "2020", "end": "حتى الآن", "bullets": ["أعدتُ تصميم تسجيل الوصول لمليوني مستخدم."]}],
        "education": [], "skills": [{"name": "النماذج الأولية", "level": "خبير"}], "tools": [],
        "languages": [{"name": "العربية", "level": "اللغة الأم"}], "recognition": [], "references": [],
    },
}


def _builder(page, server, lang="en"):
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()


def _mock(page, body, status=200):
    page.route("**/api/import", lambda route: route.fulfill(
        status=status, content_type="application/json", body=json.dumps(body, ensure_ascii=False)))


def _enable(page):
    """What a key on the server does to the page - nothing else changes."""
    page.evaluate("""() => { const b = document.querySelector('#import-btn');
        b.disabled = false; b.removeAttribute('aria-disabled');
        b.querySelector('.soon') && b.querySelector('.soon').remove(); }""")


def _stored(page) -> dict:
    return json.loads(page.evaluate(
        "localStorage.getItem('cvstand:resume:' + document.documentElement.lang)") or "{}")


def _settled(page):
    page.wait_for_function("document.querySelector('#save-state').className === 'save-state'")


def _read(page, lang, dropped=0, as_lang=None):
    _mock(page, {"ok": True, "resume": IMPORTED[as_lang or lang], "lang": as_lang or lang,
                 "dropped": dropped, "left_today": 9})
    _enable(page)
    page.click("#import-btn")
    page.fill("#import-text", "pasted CV text " * 10)
    page.click("#import-read")
    expect(page.locator("#import-review")).to_be_visible()


@pytest.mark.parametrize("lang,soon", [("en", "Coming soon"), ("ar", "قريباً")])
def test_without_a_key_the_button_says_coming_soon(page, deployed_server, lang, soon):
    _builder(page, deployed_server, lang)
    btn = page.locator("#import-btn")
    expect(btn).to_be_disabled()
    expect(btn).to_contain_text(soon)
    expect(btn).to_contain_text("استيراد سيرتي الذاتية" if lang == "ar" else "Import my CV")


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_review_shows_every_field_before_anything_changes(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    before = page.input_value('[name="name"]')
    _read(page, lang, dropped=2)
    fields = page.locator("#import-fields")
    R = IMPORTED[lang]
    for text in (R["name"], R["title"], R["contact"]["email"], R["experience"][0]["role"],
                 R["experience"][0]["bullets"][0], R["skills"][0]["name"], R["languages"][0]["name"]):
        expect(fields).to_contain_text(text)
    expect(page.locator("#import-summary")).to_contain_text("2")      # what was left out
    page.click('#import-review [data-import="cancel"]')
    expect(page.locator("#import-dlg")).not_to_be_visible()
    assert page.input_value('[name="name"]') == before                 # cancel = nothing changed


def test_the_privacy_note_is_on_the_import_screen(page, deployed_server):
    _builder(page, deployed_server)
    _enable(page)
    page.click("#import-btn")
    expect(page.locator(".import-privacy")).to_have_text(
        "Your CV text is sent to Anthropic to read it; files are not stored.")


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_replace_then_undo(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    old_name = page.input_value('[name="name"]')
    old_n = page.locator('[data-list="experience"] .entry').count()
    _read(page, lang)
    page.click("#import-replace")
    R = IMPORTED[lang]
    expect(page.locator('[name="name"]')).to_have_value(R["name"])
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text(R["experience"][0]["company"])
    expect(page.locator('[data-list="experience"] .entry')).to_have_count(1)
    _settled(page)
    st = _stored(page)
    assert st["name"] == R["name"] and st["achievements"] == []
    page.click("#resume-form .form-intro")
    page.keyboard.press("Control+z")
    expect(page.locator('[name="name"]')).to_have_value(old_name)
    expect(page.locator('[data-list="experience"] .entry')).to_have_count(old_n)


def test_add_fills_what_is_empty_and_appends_lists_then_undo(page, deployed_server):
    _builder(page, deployed_server)
    old_name = page.input_value('[name="name"]')
    n_exp = page.locator('[data-list="experience"] .entry').count()
    _read(page, "en")
    page.click("#import-add")
    expect(page.locator('[name="name"]')).to_have_value(old_name)         # not overwritten
    expect(page.locator('[data-list="experience"] .entry')).to_have_count(n_exp + 1)
    expect(page.locator(f'[name="experience.{n_exp}.role"]')).to_have_value("Senior Product Designer")
    expect(page.locator("#form-notice")).to_be_visible()
    page.click("#resume-form .form-intro")
    page.keyboard.press("Control+z")
    expect(page.locator('[data-list="experience"] .entry')).to_have_count(n_exp)


def test_a_cv_in_the_other_language_is_not_imported_into_this_one(page, deployed_server):
    _builder(page, deployed_server, "en")
    _read(page, "en", as_lang="ar")
    expect(page.locator("#import-summary")).to_contain_text("Arabic")
    expect(page.locator("#import-replace")).to_be_disabled()
    expect(page.locator("#import-add")).to_be_disabled()


@pytest.mark.parametrize("lang,text", [
    ("en", "This PDF has no readable text"),
    ("ar", "لا يحتوي ملف PDF هذا على نص قابل للقراءة"),
])
def test_a_scanned_pdf_gets_a_friendly_message(page, deployed_server, lang, text):
    _builder(page, deployed_server, lang)
    _mock(page, {"ok": False, "error": "This PDF has no readable text", "reason": "scanned"}, 422)
    _enable(page)
    page.click("#import-btn")
    page.set_input_files("#import-file", files=[{"name": "scan.pdf", "mimeType": "application/pdf",
                                                  "buffer": b"%PDF-1.7 scan"}])
    page.click("#import-read")
    expect(page.locator("#import-error")).to_contain_text(text)
    expect(page.locator("#import-review")).to_be_hidden()


def test_a_file_over_5_mb_is_stopped_in_the_browser(page, deployed_server):
    _builder(page, deployed_server)
    _enable(page)
    page.click("#import-btn")
    page.set_input_files("#import-file", files=[{"name": "big.txt", "mimeType": "text/plain",
                                                  "buffer": b"a" * (5 * 1024 * 1024 + 1)}])
    page.click("#import-read")
    expect(page.locator("#import-error")).to_contain_text("larger than 5 MB")


def test_ctrl_z_in_the_paste_box_does_not_undo_the_cv(page, deployed_server):
    _builder(page, deployed_server)
    page.fill('[name="title"]', "Changed title")
    page.wait_for_timeout(1100)
    _enable(page)
    page.click("#import-btn")
    page.locator("#import-text").type("abc")
    page.keyboard.press("Control+z")
    page.keyboard.press("Escape")
    expect(page.locator('[name="title"]')).to_have_value("Changed title")
