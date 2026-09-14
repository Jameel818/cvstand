"""The three states of the builder's `#page-warn` bar.

`tests/e2e/test_autofit_gate.py` proves the *engine* fits (or honestly fails to
fit) all 49 layouts. Nothing proved that the builder then says the right thing
about it, and that reporting is the only part of auto-fit a user ever sees:

    fits unaided          -> the bar stays hidden
    fitted after squeeze  -> a green info note naming the tightening
    still over the floors -> the amber warning

The wiring is browser-only (`builder.js::checkOverflow` reads
`ResumeAutofit.ready` inside the preview iframe, across a document boundary), so
`tests/test_autofit.py` — which is deliberately browser-free — cannot reach it.
It is also the exact path that was silently wrong before session 9: the old code
read `.tpl.scrollHeight`, which under-reports on the seven absolutely-positioned
Modern layouts, so the bar could stay hidden over a résumé that was overflowing.

The keys below are pinned from measurement, the way `KNOWN_OVER` is in the gate.
If one moves, the gate's parametrised run says which and by how much.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tools.verify_autofit import heavy_sample

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
# Read rather than importing it from conftest: `tests/` is not a package, so
# `tests.e2e.conftest` would import a SECOND copy of the fixtures module and
# mint a second temp data dir.
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

# MEASURED 2026-09-01 (`tools/verify_autofit.py modern-t1 modern-t18`) against
# the heavy sample — +1 role and +2 bullets per role:
#   modern-t1  1252.0 -> 1100.0 @ d=0.85     seats after a squeeze -> info note
#   modern-t18 1299.9 -> 1120.4 @ d=0.85 t=0.9   past the floors   -> warning
# modern-t1 is also the builder's default. Its shared-sample natural also reads
# 1100.0, but that is a FLOOR, not a tight fit — see the note in
# test_trimming_the_overflow_takes_the_note_away_again.
COMPRESSES_KEY = "modern-t1"
STILL_OVER_KEY = "modern-t18"

WARN = "#page-warn"


def _load(page, live_server, seed_resume, data: dict, key: str):
    """Seat `data` + `key` server-side, then open the builder on them.

    Seeded through conftest's `seed_resume` rather than the API for the same
    reason `clean_state` writes to disk: the store re-reads the file per
    request, and going through the builder's own autosave would make the fixture
    depend on the behaviour under test. `seed_resume` also carries the retry the
    raw write needs — the server may still hold the file open (see
    `_despite_the_server`)."""
    seed_resume(data)
    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": key})
    assert resp.ok, resp.text()
    page.goto(live_server.url + "/builder")
    # The bar is written by a promise that resolves after the iframe's fonts
    # load, so wait on the document's own signal rather than on the bar.
    page.frame_locator("#preview-frame").locator(".tpl").wait_for()
    page.wait_for_function(
        "() => { const f = document.querySelector('#preview-frame');"
        "  const d = f && f.contentDocument;"
        "  return !!(d && d.documentElement.hasAttribute('data-autofit-fitted')); }")


def test_no_bar_when_the_resume_fits_unaided(page, live_server, seed_resume):
    """The shared sample seats on every ported template — the gate asserts that
    — so the builder must say nothing at all about it."""
    _load(page, live_server, seed_resume, SAMPLE, COMPRESSES_KEY)
    expect(page.locator(WARN)).to_be_hidden()


def test_a_compressed_fit_reports_how_much_was_tightened(page, live_server, seed_resume):
    heavy = heavy_sample()
    _load(page, live_server, seed_resume, heavy, COMPRESSES_KEY)

    bar = page.locator(WARN)
    expect(bar).to_be_visible()
    expect(bar).to_have_class("page-warn is-info")          # green, not amber
    expect(bar).to_contain_text("Auto-fitted to one page")

    # The percentage is real, not a placeholder: it is 1 - density, and stage 2
    # only runs once stage 1 has bottomed out, so a compressed document always
    # has density < 1 and the number can never read 0%.
    pct = re.search(r"tightened (\d+)%", bar.inner_text())
    assert pct, f"no percentage in the note: {bar.inner_text()!r}"
    assert 0 < int(pct.group(1)) <= 15, "outside the 1.00-0.85 rhythm band"


def test_content_past_the_floors_gets_the_warning(page, live_server, seed_resume):
    """`modern-t18`'s fixed-height cards cannot absorb the overload. Reporting
    that is the correct outcome — the defect this covers is silence, which is
    what the old `.tpl.scrollHeight` check gave on exactly this kind of layout."""
    _load(page, live_server, seed_resume, heavy_sample(), STILL_OVER_KEY)

    bar = page.locator(WARN)
    expect(bar).to_be_visible()
    expect(bar).not_to_have_class("page-warn is-info")      # amber, not green
    expect(bar).to_contain_text("still runs past one page")


def test_trimming_the_overflow_takes_the_note_away_again(page, live_server, seed_resume):
    """The bar is re-derived on every render, not just the first paint.

    MEASURED 2026-09-01 on `modern-t1`: the heavy sample is 1252.0px natural and
    seats at d=0.85 (the note); dropping its first role takes it to 1100.0 at
    d=1 (silence). A bar that could only ever appear would pass the first half of
    this and fail the second.

    Note what does NOT work as the trim: removing *bullets*. `.tpl` is a 1100px
    flex column, so `measure()` floors at `.tpl.scrollHeight` = 1100 and the
    experience column has slack the sidebar leaves it — eight extra bullets on
    one role still report natural 1100.0. Only a whole extra entry moves it."""
    _load(page, live_server, seed_resume, heavy_sample(), COMPRESSES_KEY)
    bar = page.locator(WARN)
    expect(bar).to_be_visible()
    expect(bar).to_contain_text("Auto-fitted to one page")

    page.click('details.sec[data-sid="experience"] > summary')
    rm = page.locator('[data-act="rm"][data-path="experience"][data-idx="0"]')
    rm.scroll_into_view_if_needed()
    rm.click()

    expect(page.locator("#save-state")).to_have_text("Saved")
    expect(bar).to_be_hidden()
