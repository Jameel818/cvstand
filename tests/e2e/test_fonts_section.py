"""The builder's Fonts section, driven the way a user drives it.

Six selects, their dependencies on each other (a font decides which weights
exist), the §3.5 affordances, the live preview, persistence, and the notice
when a language switch invalidates a stored choice - in both interfaces.
"""
from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect


def _on(page, role):
    """The one-line font bar (2026-10-08) shows ONE section's controls at a
    time: choose it first, as a user would."""
    if page.locator("#ty_section").input_value() != role:
        page.select_option("#ty_section", role)

pytestmark = [pytest.mark.e2e]

#: One stored résumé per language since 2026-10-07 ("cvstand:resume:<lang>").
#: The shell's <html lang> is the document's language, so it names the slot.
STORE_KEY = "'cvstand:resume:' + document.documentElement.lang"
SELECTS = [f"#ty_{role}_{f}" for role in ("name", "heading", "body")
           for f in ("font", "weight", "size")]


def _open_fonts(page, live_server, lang="en"):
    if lang == "ar":
        page.goto(f"{live_server.url}/lang/ar?next=/builder")
    else:
        page.goto(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
    # The controls live in the ribbon above the preview (2026-10-07): always
    # on screen, nothing to open.
    expect(page.locator("#ribbon #ty_section")).to_be_visible()


def _stored(page) -> dict:
    return json.loads(page.evaluate(f"localStorage.getItem({STORE_KEY})") or "{}")


def _preview_name(page):
    return page.frame_locator("#preview-frame").locator(".cv-name").first


def test_nine_selects_template_default_first_and_grouped(page, live_server):
    _open_fonts(page, live_server)
    assert page.locator("#ribbon").get_attribute("aria-label") == "Fonts"
    # one line since 2026-10-08: the Section select names the three groups
    titles = page.locator("#ty_section option").all_inner_texts()
    assert titles == ["Name", "Headings", "Details"]
    for sel in SELECTS:
        _on(page, sel.split("_")[1])
        expect(page.locator(sel)).to_have_count(1)
        # The Name's weight follows the Headings while its font does.
        first = "Same as Headings" if sel == "#ty_name_weight" else "Template default"
        assert page.locator(f"{sel} option").first.inner_text() == first
    _on(page, "heading")
    groups = page.locator("#ty_heading_font optgroup").evaluate_all(
        "els => els.map(e => e.label)")
    assert groups == ["Sans", "Serif", "Display"]
    # No font -> nothing to weigh.
    _on(page, "heading")
    expect(page.locator("#ty_heading_weight")).to_be_disabled()
    _on(page, "heading")
    expect(page.locator("#ty_heading_size")).to_be_enabled()


def test_arabic_interface_names_the_section_and_its_groups(page, live_server):
    _open_fonts(page, live_server, "ar")
    assert page.locator("#ribbon").get_attribute("aria-label") == "الخطوط"
    _on(page, "heading")
    assert page.locator("#ty_heading_font option").first.inner_text() == "افتراضي القالب"
    _on(page, "heading")
    groups = page.locator("#ty_heading_font optgroup").evaluate_all(
        "els => els.map(e => e.label)")
    assert groups[0] == "كوفي / بلا زوائد" and len(groups) == 5


def test_name_offers_template_default_then_same_as_headings(page, live_server):
    _open_fonts(page, live_server)
    _on(page, "name")
    opts = page.locator("#ty_name_font > option").all_inner_texts()
    assert opts[:2] == ["Template default", "Same as Headings"]
    _on(page, "name")
    expect(page.locator("#ty_name_font")).to_have_value("")          # Same as Headings
    # The name follows a Headings font...
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    name = page.frame_locator("#preview-frame").locator(".cv-name").first
    expect(name).to_have_css("font-family", re.compile(r"CVT Montserrat"))
    _on(page, "name")
    expect(page.locator("#ty_name_weight option").first).to_have_text("Same as Headings")
    # ...until it is set back to the template's own face.
    before = page.evaluate("""() => { const f = document.querySelector('#preview-frame');
        return f.contentDocument.querySelector('.cv-section').textContent; }""")
    _on(page, "name")
    page.select_option("#ty_name_font", "template")
    expect(name).not_to_have_css("font-family", re.compile(r"CVT"))
    section = page.frame_locator("#preview-frame").locator(".cv-section").first
    expect(section).to_have_css("font-family", re.compile(r"CVT Montserrat"))
    assert before
    page.wait_for_timeout(1200)
    assert _stored(page)["font_name"] == "template"


def test_arabic_name_labels(page, live_server):
    _open_fonts(page, live_server, "ar")
    titles = page.locator("#ty_section option").all_inner_texts()
    assert titles[1:] == ["عناوين الأقسام", "التفاصيل"]
    _on(page, "name")
    assert page.locator("#ty_name_font > option").nth(1).inner_text() == "مثل عناوين الأقسام"


def test_a_pre_split_resume_opens_migrated(page, live_server):
    """Stored before Name/Headings were split: 32pt headline. It opens with
    Name 32 and Headings 13 selected, silently, and the stored copy follows."""
    page.goto(live_server.url + "/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
    page.evaluate(f"""() => {{
      const d = JSON.parse(localStorage.getItem({STORE_KEY}) || document.querySelector('#resume-data').textContent);
      d.font_heading = 'Montserrat'; d.font_heading_size = 32; delete d.font_name_size;
      localStorage.setItem({STORE_KEY}, JSON.stringify(d)); }}""")
    page.reload()
    _on(page, "name")
    expect(page.locator("#ty_name_size")).to_have_value("32")
    _on(page, "heading")
    expect(page.locator("#ty_heading_size")).to_have_value("13")
    expect(page.locator("#form-notice")).to_be_hidden()
    page.wait_for_timeout(1200)
    stored = _stored(page)
    assert (stored["font_name_size"], stored["font_heading_size"]) == (32, 13)


def test_single_weight_font_shows_its_one_weight_disabled(page, live_server):
    _open_fonts(page, live_server)
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Anton")
    _on(page, "heading")
    weight = page.locator("#ty_heading_weight")
    expect(weight).to_be_disabled()
    expect(weight.locator("option")).to_have_count(1)
    expect(weight.locator("option")).to_have_text("400 — only weight")


def test_font_change_keeps_the_nearest_weight(page, live_server):
    """§3.5's example, in the language where both fonts exist: 900 on Cairo
    becomes 800 on Almarai, which has no 900."""
    _open_fonts(page, live_server, "ar")
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Cairo")
    _on(page, "heading")
    page.select_option("#ty_heading_weight", "900")
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Almarai")
    _on(page, "heading")
    expect(page.locator("#ty_heading_weight")).to_have_value("800")
    page.wait_for_timeout(1200)                      # autosave debounce
    assert _stored(page)["font_heading_weight"] == 800


def test_playful_fonts_carry_the_tag(page, live_server):
    _open_fonts(page, live_server, "ar")
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Lalezar")
    expect(page.locator('[data-ty-role="heading"] .ty-tag')).to_be_visible()
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Cairo")
    expect(page.locator('[data-ty-role="heading"] .ty-tag')).to_have_count(0)


def test_light_weight_small_size_hint(page, live_server):
    _open_fonts(page, live_server)
    _on(page, "body")
    page.select_option("#ty_body_font", "Inter")
    _on(page, "body")
    page.select_option("#ty_body_weight", "200")
    _on(page, "body")
    page.select_option("#ty_body_size", "9.5")
    expect(page.locator('[data-ty-role="body"] .ty-hint')).to_be_visible()
    _on(page, "body")
    page.select_option("#ty_body_size", "10")
    expect(page.locator('[data-ty-role="body"] .ty-hint')).to_have_count(0)


def test_choice_reaches_the_preview_and_survives_a_reload(page, live_server):
    _open_fonts(page, live_server)
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    # The sample is the font select itself, drawn in the chosen face.
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_css("font-family", re.compile(r"CVT Montserrat"))
    expect(_preview_name(page)).to_have_css("font-family", re.compile(r"CVT Montserrat"))
    page.wait_for_timeout(1200)
    assert _stored(page)["font_heading"] == "Montserrat"
    page.reload()
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_value("Montserrat")
    expect(_preview_name(page)).to_have_css("font-family", re.compile(r"CVT Montserrat"))


def test_switching_to_arabic_resets_english_fonts_with_a_notice(page, live_server):
    _open_fonts(page, live_server)
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    _on(page, "heading")
    page.select_option("#ty_heading_weight", "900")
    _on(page, "body")
    page.select_option("#ty_body_size", "11")        # valid in Arabic too: kept
    page.wait_for_timeout(1200)

    page.goto(f"{live_server.url}/lang/ar?next=/builder")
    notice = page.locator("#form-notice")
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("بعض خيارات الخطوط غير متاحة")
    expect(notice).to_contain_text("Montserrat")
    page.wait_for_timeout(1200)
    stored = _stored(page)
    assert stored["font_heading"] is None and stored["font_heading_weight"] is None
    assert stored["font_body_size"] == 11
    page.locator("#form-notice button").click()
    expect(notice).to_be_hidden()


def test_switching_to_english_resets_arabic_fonts_with_a_notice(page, live_server):
    _open_fonts(page, live_server, "ar")
    _on(page, "body")
    page.select_option("#ty_body_font", "Tajawal")
    page.wait_for_timeout(1200)

    page.goto(f"{live_server.url}/lang/en?next=/builder")
    notice = page.locator("#form-notice")
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("Some font choices are not available")
    expect(notice).to_contain_text("Tajawal")
    page.wait_for_timeout(1200)
    assert _stored(page)["font_body"] is None
