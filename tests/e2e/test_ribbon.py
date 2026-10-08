"""The font ribbon above the preview, its Undo and its Default fonts
(2026-10-07, user request).

The Fonts controls moved out of the form into a Word-style ribbon: three
groups (Name, Headings, Details) of Font / Weight / Size, labels beside the
controls unless hidden (icons + tooltips; automatic on a narrow screen),
in Arabic and English, by keyboard. Undo rewinds every builder change -
text, list entries, fonts, Default fonts, template - many steps deep, also
Ctrl+Z, greyed out when there is nothing to rewind; and the exports follow,
because they POST the same state.

tests/e2e/test_fonts_section.py keeps proving the controls themselves (the
lists, weights, resets): moved, they must behave exactly as before.
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

pytestmark = pytest.mark.e2e


def _builder(page, server, lang="en"):
    page.goto(f"{server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()


def _stored(page) -> dict:
    return json.loads(page.evaluate(
        "() => localStorage.getItem('cvstand:resume:' + document.documentElement.lang)") or "{}")


def _settled(page):
    page.wait_for_function("document.querySelector('#save-state').className === 'save-state'")


# ------------------------------------------------------------- the ribbon

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_ribbon_sits_above_the_preview_and_the_form_has_no_fonts_section(page, deployed_server, lang):
    _builder(page, deployed_server, lang)
    expect(page.locator('.sec[data-sid="fonts"]')).to_have_count(0)
    for role in ("name", "heading", "body"):
        _on(page, role)
        for f in ("font", "weight", "size"):
            expect(page.locator(f"#ribbon #ty_{role}_{f}")).to_have_count(1)
    ribbon = page.locator("#ribbon").bounding_box()
    preview = page.locator("#preview-scroll").bounding_box()
    assert ribbon["y"] + ribbon["height"] <= preview["y"] + 1, "the ribbon is not above the preview"
    assert abs(ribbon["x"] - preview["x"]) < 2 and abs(ribbon["width"] - preview["width"]) < 2


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_font_controls_are_one_line(page, deployed_server, lang):
    """2026-10-08 (the user's mockups ribbon-one-line-AR/EN.png): Section ->
    Font -> Weight -> Size in ONE row, with Undo, Default fonts and the labels
    toggle on the same row - so the template preview starts higher."""
    _builder(page, deployed_server, lang)
    ids = ["#undo-btn", "#fonts-default", "#ty_section", "#ty_name_font", "#ty_name_weight",
           "#ty_name_size", "#ribbon-labels"]
    boxes = [page.locator(i).bounding_box() for i in ids]
    mids = [b["y"] + b["height"] / 2 for b in boxes]
    assert max(mids) - min(mids) < 6, f"not one row: {dict(zip(ids, mids))}"
    xs = [page.locator(i).bounding_box()["x"] for i in ("#ty_section", "#ty_name_font",
                                                         "#ty_name_weight", "#ty_name_size")]
    assert xs == (sorted(xs) if lang == "en" else sorted(xs, reverse=True)), \
        "the order is not Section -> Font -> Weight -> Size in the reading direction"
    labels = page.locator("#ribbon .rb-ctl label .rb-lbl").all_inner_texts()
    assert labels == (["Section", "Font", "Weight", "Size"] if lang == "en"
                      else ["القسم", "الخط", "السماكة", "الحجم"])
    assert page.locator("#ribbon").bounding_box()["height"] <= 50


def test_the_section_chooses_which_group_the_controls_edit(page, deployed_server):
    _builder(page, deployed_server)
    expect(page.locator("#ty_section")).to_have_value("name")
    page.select_option("#ty_section", "body")
    expect(page.locator("#ty_body_font")).to_be_visible()
    expect(page.locator("#ty_name_font")).to_have_count(0)
    page.select_option("#ty_body_font", "Inter")
    page.select_option("#ty_section", "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    page.select_option("#ty_section", "body")
    expect(page.locator("#ty_body_font")).to_have_value("Inter")       # kept
    _settled(page)
    s = _stored(page)
    assert (s["font_body"], s["font_heading"]) == ("Inter", "Montserrat")
    # choosing a section is not a change to the résumé: nothing to undo for it
    page.click("#undo-btn")
    expect(page.locator("#ty_body_font")).to_have_value("Inter")
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_value("")


def test_arabic_mirrors_the_ribbon(page, deployed_server):
    """Logical properties only: in Arabic the commands are on the RIGHT and
    the line runs Section -> Size from right to left."""
    _builder(page, deployed_server, "ar")
    cmds = page.locator("#ribbon .rb-cmds").bounding_box()
    section = page.locator("#ty_section").bounding_box()
    size = page.locator("#ty_name_size").bounding_box()
    toggle = page.locator("#ribbon-labels").bounding_box()
    assert cmds["x"] > section["x"] > size["x"] > toggle["x"]


def test_labels_by_default_toggle_to_icons_and_back(page, deployed_server):
    _builder(page, deployed_server)
    rb = page.locator("#ribbon")
    expect(page.locator('label[for="ty_name_font"] .rb-lbl')).to_be_visible()
    expect(page.locator("#ribbon-labels")).to_have_attribute("aria-pressed", "true")

    page.click("#ribbon-labels")
    assert "is-compact" in rb.get_attribute("class")
    expect(page.locator('label[for="ty_name_font"] .rb-ico-t')).to_be_visible()
    expect(page.locator("#ribbon-labels")).to_have_attribute("aria-pressed", "false")
    # icons only: the select still has a tooltip and an accessible label
    _on(page, "body")
    assert page.locator("#ty_body_font").get_attribute("title") == "Details · Font"
    assert page.locator('label[for="ty_body_font"]').inner_text() != ""   # sr text kept

    page.reload()
    assert "is-compact" in page.locator("#ribbon").get_attribute("class"), "not remembered"
    page.click("#ribbon-labels")
    assert "is-compact" not in page.locator("#ribbon").get_attribute("class")


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_a_narrow_screen_is_compact_and_does_not_scroll_sideways(browser, deployed_server, lang):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    try:
        page = ctx.new_page()
        _builder(page, deployed_server, lang)
        assert "is-compact" in page.locator("#ribbon").get_attribute("class")
        expect(page.locator("#ribbon-labels")).to_be_hidden()
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        for sel in ("#ty_section", "#ty_name_font", "#ty_name_weight", "#ty_name_size",
                    "#dl-toggle", ".lang-switch-bar"):
            box = page.locator(sel).bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= 390, sel
    finally:
        ctx.close()


def test_every_ribbon_control_is_reachable_by_keyboard(page, deployed_server):
    _builder(page, deployed_server)
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")     # enables weight + undo
    page.focus("#undo-btn")
    seen = set()
    for _ in range(14):
        page.keyboard.press("Tab")
        seen.add(page.evaluate("document.activeElement.id"))
    assert {"fonts-default", "ty_section", "ty_heading_font", "ty_heading_weight",
            "ty_heading_size", "ribbon-labels"} <= seen


# ------------------------------------------------------------------- undo

def test_undo_is_greyed_out_until_there_is_something_to_undo(page, deployed_server):
    _builder(page, deployed_server)
    expect(page.locator("#undo-btn")).to_be_disabled()
    page.fill("#f_title", "Art Director")
    expect(page.locator("#undo-btn")).to_be_enabled()
    page.click("#undo-btn")
    expect(page.locator("#undo-btn")).to_be_disabled()
    expect(page.locator("#f_title")).not_to_have_value("Art Director")


def test_a_typing_burst_is_one_step(page, deployed_server):
    _builder(page, deployed_server)
    before = page.locator("#f_name").input_value()
    page.locator("#f_name").press_sequentially(" Jr", delay=40)
    _settled(page)
    page.click("#undo-btn")
    expect(page.locator("#f_name")).to_have_value(before)
    _settled(page)
    assert _stored(page)["name"] == before


def test_font_weight_size_and_default_fonts_undo_step_by_step(page, deployed_server):
    _builder(page, deployed_server)
    expect(page.locator("#fonts-default")).to_be_disabled()
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    _on(page, "heading")
    page.select_option("#ty_heading_weight", "900")
    _on(page, "body")
    page.select_option("#ty_body_size", "11")
    page.click("#fonts-default")
    _settled(page)
    s = _stored(page)
    assert all(s.get(k) is None for k in (
        "font_name", "font_name_weight", "font_name_size", "font_heading",
        "font_heading_weight", "font_heading_size", "font_body", "font_body_weight",
        "font_body_size")), "Default fonts left a choice behind"
    expect(page.locator("#fonts-default")).to_be_disabled()

    page.keyboard.press("Control+z")                       # undoes Default fonts
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_value("Montserrat")
    _on(page, "body")
    expect(page.locator("#ty_body_size")).to_have_value("11")
    page.keyboard.press("Control+z")                       # the size
    _on(page, "body")
    expect(page.locator("#ty_body_size")).to_have_value("")
    _on(page, "heading")
    expect(page.locator("#ty_heading_weight")).to_have_value("900")
    page.keyboard.press("Control+z")                       # the weight
    _on(page, "heading")
    expect(page.locator("#ty_heading_weight")).to_have_value("")
    page.keyboard.press("Control+z")                       # the font
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_value("")
    _settled(page)
    assert _stored(page).get("font_heading") is None


def test_default_fonts_returns_the_template_look_in_arabic(page, deployed_server):
    _builder(page, deployed_server, "ar")
    face = page.frame_locator("#preview-frame").locator(".cv-name").first
    original = face.evaluate("e => getComputedStyle(e).fontFamily")
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Beiruti")
    expect(face).to_have_css("font-family", re.compile("CVT Beiruti"))
    page.click("#fonts-default")
    expect(face).to_have_css("font-family", original)


def test_undo_reaches_list_entries_and_works_from_inside_a_text_box(page, deployed_server):
    _builder(page, deployed_server)
    page.click('details.sec[data-sid="tools"] > summary')
    rows = page.locator('[data-list="tools"] .bullet-row')
    n = rows.count()
    rows.first.locator("button").click()
    expect(rows).to_have_count(n - 1)
    page.click("#f_title")
    page.keyboard.press("Control+z")
    expect(rows).to_have_count(n)


def test_a_template_switch_is_undone_with_the_bar_and_drawer(page, deployed_server):
    _builder(page, deployed_server)
    label = page.locator("#tpl-label").inner_text()
    page.click("#open-drawer")
    page.locator('#drawer-body .drawer-item[data-key="modern-t4"]').click()
    expect(page.locator("#tpl-label")).to_have_text("Ribbon Sidebar")
    page.click("#undo-btn")
    expect(page.locator("#tpl-label")).to_have_text(label)
    assert page.evaluate("localStorage.getItem('cvstand:template')") != "modern-t4"


def test_more_than_fifty_steps(page, deployed_server):
    _builder(page, deployed_server)
    for i in range(60):
        _on(page, "body")
        page.select_option("#ty_body_size", ["10", "10.5"][i % 2])
    for _ in range(60):
        page.click("#undo-btn")
    _on(page, "body")
    expect(page.locator("#ty_body_size")).to_have_value("")
    expect(page.locator("#undo-btn")).to_be_disabled()


def test_the_exports_follow_the_undone_state(page, deployed_server):
    _builder(page, deployed_server)
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Raleway")
    page.click("#undo-btn")
    _on(page, "heading")
    expect(page.locator("#ty_heading_font")).to_have_value("Montserrat")
    for kind in ("pdf", "docx"):
        sent = []
        page.route(f"**/export/{kind}", lambda r: (sent.append(r.request.post_data),
                                                    r.fulfill(status=200, body=b"x")))
        page.click("#dl-toggle")
        page.click(f"#dl-{kind}")
        page.wait_for_timeout(300)
        page.unroute(f"**/export/{kind}")
        assert json.loads(sent[-1])["data"]["font_heading"] == "Montserrat", kind
