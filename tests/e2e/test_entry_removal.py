"""Removing entries — the re-index path the rest of the suite never walks.

`test_content_editing.py` already removes a **tool**, but tools are a list of
plain strings: one input, one index, nothing nested. The lists that carry risk
are the object lists with bullets (experience, education). Their inputs are
named by position — `experience.1.bullets.0` — so deleting entry 0 has to
re-bind every input after it. `onChange(true)` handles that by rebuilding the
form from `data` rather than patching the DOM, and nothing proved it: a patch-
in-place regression would keep the visible text correct while writing the next
keystroke into the wrong role, which no screenshot would catch.

Covered here: removing an entry with bullets, removing a single bullet,
emptying a section entirely (its heading must go with it — the same rule the
stat chips follow), and a removal surviving the autosave round trip.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

KILN_BULLET = "Art-directed long-form editorial to a weekly press deadline."
BELLROCK_B0 = "Built the studio's first design-system practice and hired the six people who ran it."
HALDEN_B2 = "Presents creative strategy to the executive group each quarter and defends the roadmap against it."


def _open(page, sid: str):
    """Sections 3+ start collapsed, and a collapsed `<details>` has no layout,
    so its buttons are unclickable until it is opened."""
    page.click(f'details.sec[data-sid="{sid}"] > summary')


def _click(page, selector: str):
    el = page.locator(selector)
    el.scroll_into_view_if_needed()
    el.click()


def _resume(page, live_server) -> dict:
    return page.request.get(live_server.url + "/api/resume").json()["resume"]


def test_removing_a_role_rebinds_the_bullets_of_the_entries_after_it(page, live_server):
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Halden & Row")
    expect(canvas).to_contain_text("Bellrock Studio")

    _open(page, "experience")
    _click(page, '[data-act="rm"][data-path="experience"][data-idx="0"]')

    expect(canvas).not_to_contain_text("Halden & Row")
    expect(canvas).to_contain_text("Bellrock Studio")
    expect(canvas).to_contain_text("Kiln Press")

    # The form itself must have been rebuilt from `data` — one entry fewer, and
    # slot 0 now *holding Bellrock's own values*. Checking only the canvas would
    # miss a patch-in-place regression entirely: the preview renders from `data`
    # either way, so it would look right while the inputs stayed stale.
    entries = page.locator('[data-list="experience"] .entry')
    expect(entries).to_have_count(2)
    expect(entries.first.locator(".entry-head b")).to_have_text("Design Director")
    expect(page.locator('input[name="experience.0.company"]')).to_have_value("Bellrock Studio")
    expect(page.locator('input[name="experience.0.bullets.0"]')).to_have_value(BELLROCK_B0)

    # Bellrock is entry 0 now. Typing into what the form calls
    # `experience.0.bullets.0` must land on Bellrock's first bullet. If the form
    # were patched in place rather than rebuilt, this input would still be bound
    # to the deleted role's slot and the write would go astray.
    sentinel = "Rebuilt the critique ritual around written briefs."
    row = page.locator('input[name="experience.0.bullets.0"]')
    row.scroll_into_view_if_needed()
    row.fill(sentinel)

    expect(canvas).to_contain_text("Rebuilt the critique ritual")
    expect(page.locator("#save-state")).to_have_text("Saved")

    exp = _resume(page, live_server)["experience"]
    assert [e["company"] for e in exp] == ["Bellrock Studio", "Kiln Press"]
    assert exp[0]["bullets"][0] == sentinel
    assert len(exp[0]["bullets"]) == 2, "Bellrock's own second bullet was lost"
    assert exp[1]["bullets"] == [KILN_BULLET], "Kiln Press was touched by a write aimed at Bellrock"


def test_removing_one_bullet_leaves_its_siblings_bound_correctly(page, live_server):
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Replaced four divergent sub-brands")

    _open(page, "experience")
    _click(page, '[data-act="rmbullet"][data-path="experience.0.bullets"][data-idx="1"]')

    expect(canvas).not_to_contain_text("Replaced four divergent sub-brands")
    expect(canvas).to_contain_text("Runs a fourteen-person studio")
    expect(canvas).to_contain_text("Presents creative strategy")

    # The third bullet slid down into slot 1 — in the form, not just in `data`.
    rows = page.locator('input[name^="experience.0.bullets."]')
    expect(rows).to_have_count(2)
    expect(page.locator('input[name="experience.0.bullets.1"]')).to_have_value(HALDEN_B2)

    # Writing into that re-indexed slot must not touch slot 0.
    sentinel = "Chairs the quarterly portfolio review."
    row = page.locator('input[name="experience.0.bullets.1"]')
    row.scroll_into_view_if_needed()
    row.fill(sentinel)

    expect(canvas).to_contain_text("Chairs the quarterly portfolio review")
    expect(page.locator("#save-state")).to_have_text("Saved")

    bullets = _resume(page, live_server)["experience"][0]["bullets"]
    assert len(bullets) == 2
    assert bullets[0].startswith("Runs a fourteen-person studio")
    assert bullets[1] == sentinel


def test_emptying_a_section_takes_its_heading_with_it(page, live_server):
    """A section whose last entry is deleted must disappear, heading and all.

    Same standing rule as the stat chips: no stranded label with nothing under
    it. Every template guards its optional sections with `{% if r.<list> %}`;
    this is the browser-level check that the guard is really reached when the
    list empties through the form."""
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Education")
    expect(canvas).to_contain_text("Harbour School")

    _open(page, "education")
    # Back to front, so the surviving indices never shift under the second click.
    _click(page, '[data-act="rm"][data-path="education"][data-idx="1"]')
    _click(page, '[data-act="rm"][data-path="education"][data-idx="0"]')

    expect(canvas).not_to_contain_text("Harbour School")
    expect(canvas).not_to_contain_text("Northfield University")
    expect(canvas).not_to_contain_text("Education")
    expect(page.locator("#save-state")).to_have_text("Saved")

    assert _resume(page, live_server)["education"] == []


def test_a_structural_removal_survives_a_reload(page, live_server):
    """Autosave carries deletions, not just edits — a removal that reappears on
    reload is the worst kind of data bug, because the preview looked right."""
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Kiln Press")

    _open(page, "experience")
    _click(page, '[data-act="rm"][data-path="experience"][data-idx="2"]')
    expect(page.locator("#save-state")).to_have_text("Saved")

    page.reload()
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Halden & Row")
    expect(canvas).not_to_contain_text("Kiln Press")
    expect(page.locator('[data-list="experience"] .entry')).to_have_count(2)
