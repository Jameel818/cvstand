"""Auto-fit, as a gate rather than a hand-run tool.

`tools/verify_autofit.py` has always been able to prove these two properties;
nothing made them fail a run. This file turns them into tests, and reuses the
tool's `heavy_sample()` so the fixture has exactly one definition.

Two properties, pulling in opposite directions:

  NO-OP on the shared sample. Every ported template already seats it, so
  auto-fit must return density 1 / typeScale 1 and leave the DOM alone. A
  template that comes back compressed here has regressed — as RESUME_HERE.md
  puts it, auto-fit is a safety net for variable user content, not a licence to
  ship an overflowing port.

  RECOVERS a realistic overload. `--heavy` adds a 4th role and two bullets per
  role. 48/49 come back fitted; `modern-t18`'s fixed-height cards cannot, and
  reporting `fitted: false` so the builder warns is the correct outcome
  (`test_autofit_banner.py` asserts the warning actually reaches the user).

Runs the whole catalogue through Chromium (~2 min), so it is marked `slow` as
well as `e2e`:

    venv/Scripts/python -m pytest --e2e -q -m "e2e and not slow"
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import registry
from app.rendering import document_html
from tools.verify_autofit import FLOOR, heavy_sample

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
KEYS = sorted(registry.ported_keys())

# The layouts that cannot absorb a +20% overload. Listed, not skipped: if one
# starts passing, this list is what tells us the layout changed.
#
# MEASURED 2026-08-31: only modern-t18 (1299.9 -> 1120.4). RESUME_HERE.md and
# BUILD.md still say two — modern-t17 as well — and that was true at
# TYPE_FLOOR 0.92. The engine now stops at 0.90, which takes t17 to 1092.5 and
# seats it. See the floors note in tests/test_autofit.py.
KNOWN_OVER = {"modern-t18"}


@pytest.fixture(scope="module")
def fit_page(browser):
    """One page for the whole module. 98 renders otherwise pay for 98 contexts."""
    ctx = browser.new_context(viewport={"width": 900, "height": 1200})
    pg = ctx.new_page()
    yield pg
    ctx.close()


def _fit(page, data: dict, key: str) -> dict:
    # for_pdf=True embeds the fonts: set_content()'s base URL is about:blank, so
    # a linked stylesheet silently falls back and every height below would be
    # measured in the wrong face.
    page.set_content(document_html(data, key, for_pdf=True), wait_until="networkidle")
    result = page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
    assert result is not None, f"{key}: auto-fit engine missing from the document"
    return result


@pytest.mark.parametrize("key", KEYS)
def test_autofit_is_a_strict_noop_on_the_shared_sample(fit_page, key):
    r = _fit(fit_page, SAMPLE, key)
    assert r["fitted"], f"{key} overflows the page on the shared sample ({r['natural']:.1f}px)"
    assert r["density"] == 1 and r["typeScale"] == 1, (
        f"{key} needed compression (d={r['density']} t={r['typeScale']}) to seat the "
        f"standard sample — the port itself no longer fits")


@pytest.mark.parametrize("key", KEYS)
def test_autofit_recovers_a_realistic_overload(fit_page, key):
    r = _fit(fit_page, heavy_sample(), key)
    if key in KNOWN_OVER:
        assert not r["fitted"], (
            f"{key} now recovers the overload — good news; drop it from KNOWN_OVER")
        assert r["density"] == FLOOR, (
            f"{key} gave up at d={r['density']} without reaching the {FLOOR} floor")
        return
    assert r["fitted"], (
        f"{key} could not seat the heavy sample: {r['natural']:.1f} -> {r['height']:.1f} "
        f"at d={r['density']} t={r['typeScale']}")
    # Not every layout needs compressing to take the overload — the multi-column
    # Modern designs (t2, t4, t8, t11, t15, t20, t23) have a column with room in
    # it and come back at d=1 t=1. Fitting is the contract; compressing is not.
    assert r["height"] <= 1100.05, f"{key} reports fitted at {r['height']:.2f}px"
