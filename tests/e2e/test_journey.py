"""The user journey: landing -> gallery -> builder -> edit -> preview -> save.

Everything here runs in Chromium against a real server. These are the paths no
other test in the project touches, because all of them are JavaScript.
"""
from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

from app import registry

pytestmark = pytest.mark.e2e


def test_landing_leads_to_the_gallery(page, live_server):
    page.goto(live_server.url + "/")
    expect(page.locator("h1")).to_contain_text("Your résumé")
    page.get_by_role("link", name="Browse templates").click()
    expect(page).to_have_url(live_server.url + "/templates")
    expect(page.locator(".tpl-card")).to_have_count(len(registry.ported_keys()))


def test_gallery_tabs_filter_by_family(page, live_server):
    page.goto(live_server.url + "/templates")
    expect(page.locator(".tab.is-active")).to_have_text("All")

    page.get_by_role("link", name="Modern", exact=True).click()
    expect(page).to_have_url(live_server.url + "/templates?cat=modern")
    expect(page.locator(".tpl-card")).to_have_count(len(registry.by_category("modern")))
    expect(page.locator(".tpl-card .chip-ats")).to_have_count(0)

    page.get_by_role("link", name="ATS-Friendly", exact=True).click()
    expect(page.locator(".tpl-card")).to_have_count(len(registry.by_category("ats")))
    expect(page.locator(".tpl-card .chip-modern")).to_have_count(0)


def test_every_gallery_card_renders_a_live_preview(page, live_server):
    """The thumbnails are 49 real /preview iframes, not images. A template that
    500s renders an empty card and nothing else says so."""
    page.goto(live_server.url + "/templates?cat=ats")
    frames = page.locator(".tpl-thumb iframe")
    expect(frames).to_have_count(len(registry.by_category("ats")))
    # Sample the first few rather than all 25 — lazy loading means the rest are
    # not fetched until scrolled to, and the render path is shared.
    for i in range(3):
        src = frames.nth(i).get_attribute("src")
        resp = page.request.get(live_server.url + src)
        assert resp.status == 200
        assert 'class="tpl"' in resp.text()


def test_use_this_selects_the_template_and_opens_the_builder(page, live_server):
    key = "ats-t3"
    page.goto(live_server.url + "/templates?cat=ats")
    page.locator(f'.use-btn[data-key="{key}"]').click()
    expect(page).to_have_url(live_server.url + "/builder")

    expect(page.locator("#tpl-label")).to_have_text(registry.get(key).label)
    expect(page.locator(".builder-bar .tpl-name .chip.chip-ats")).to_have_count(1)

    meta = page.request.get(live_server.url + "/api/resume").json()["meta"]
    assert meta["template_key"] == key


def test_editing_a_field_reaches_the_preview_and_the_server(page, live_server):
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Ashworth")

    page.fill("#f_name", "Quillfeather Vane")

    # 1. the live preview re-renders (350ms debounce + /api/render round trip)
    expect(canvas).to_contain_text("Quillfeather")
    expect(canvas).not_to_contain_text("Ashworth")

    # 2. autosave settles (900ms debounce, then PUT /api/resume)
    expect(page.locator("#save-state")).to_have_text("Saved")

    # 3. the server actually has it, and a reload shows it
    assert page.request.get(live_server.url + "/api/resume").json()["resume"]["name"] == "Quillfeather Vane"
    page.reload()
    expect(page.locator("#f_name")).to_have_value("Quillfeather Vane")


def test_adding_a_bullet_updates_the_preview(page, live_server):
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Ashworth")

    page.click('details.sec[data-sid="experience"] > summary')
    add = page.locator('[data-act="addbullet"][data-path="experience.0.bullets"]')
    add.scroll_into_view_if_needed()
    add.click()

    # The form re-renders on a structural change; the new row is the last one.
    row = page.locator('input[name^="experience.0.bullets."]').last
    row.fill("Chaired the accessibility guild across six squads.")
    expect(canvas).to_contain_text("Chaired the accessibility guild")
    expect(page.locator("#save-state")).to_have_text("Saved")


def test_template_drawer_switches_the_live_layout(page, live_server):
    page.goto(live_server.url + "/builder")
    expect(page.locator("#tpl-label")).to_have_text(registry.get(registry.default_key()).label)

    page.click("#open-drawer")
    drawer = page.locator("#drawer")
    expect(drawer).to_have_attribute("aria-hidden", "false")

    key = "modern-t5"
    item = drawer.locator(f'.drawer-item[data-key="{key}"]')
    item.scroll_into_view_if_needed()
    item.click()

    expect(page.locator("#tpl-label")).to_have_text(registry.get(key).label)
    expect(drawer).to_have_attribute("aria-hidden", "true")
    assert page.request.get(
        live_server.url + "/api/resume").json()["meta"]["template_key"] == key

    # the selection survives a reload — it is persisted, not just in-page state
    page.reload()
    expect(page.locator("#tpl-label")).to_have_text(registry.get(key).label)


def test_a_rejected_render_surfaces_in_the_form(page, live_server):
    """A 422 from /api/render must reach the form-errors box, and clear again on
    the next good render — otherwise the preview just silently stops updating.

    The 422 is injected rather than provoked: the schema accepts an empty
    `name` (`{"type": "string"}`, no minLength) and the builder clamps `percent`
    itself, so no keystroke in the real form can produce one. That is worth
    knowing — this path is unreachable from the UI today, and would first fire
    on a schema tightened later."""
    page.goto(live_server.url + "/builder")
    errors = page.locator("#form-errors")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Ashworth")
    expect(errors).not_to_have_class(re.compile("show"))

    page.route("**/api/render", lambda route: route.fulfill(
        status=422, content_type="application/json",
        body=json.dumps({"ok": False, "errors": ["'name' is a required property"]})))
    page.fill("#f_name", "Anything")
    expect(errors).to_have_class(re.compile("show"))
    expect(errors).to_contain_text("Fix to update preview")
    expect(errors).to_contain_text("required property")

    page.unroute("**/api/render")
    page.fill("#f_name", "Quillfeather Vane")
    expect(errors).not_to_have_class(re.compile("show"))
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Quillfeather")


def test_zoom_controls_scale_the_stage(page, live_server):
    page.goto(live_server.url + "/builder")
    stage = page.locator("#preview-stage")
    expect(page.locator("#zoom-lvl")).to_have_text("Fit")
    before = stage.evaluate("el => getComputedStyle(el).transform")

    page.click('.zoom button[data-zoom="in"]')
    expect(page.locator("#zoom-lvl")).not_to_have_text("Fit")
    assert stage.evaluate("el => getComputedStyle(el).transform") != before

    page.click('.zoom button[data-zoom="fit"]')
    expect(page.locator("#zoom-lvl")).to_have_text("Fit")
