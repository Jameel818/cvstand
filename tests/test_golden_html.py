"""Golden gate 1 of 2 — the exact HTML each template emits.

WHY THIS FILE EXISTS
    The other 506 tests assert CONTRACT ("the skill level is selectable text",
    "an empty metric hides its chip"). None of them would notice a template
    that quietly changed what it renders, as long as the contract survived.
    That is the exact blind spot the bilingual work walks into: it edits all 49
    templates, and a wrong edit stays green.

    This gate closes it for text. `tests/e2e/test_golden_pixels.py` closes it
    for appearance. They are independent on purpose -- see tools/golden.py for
    which phase is allowed to move which baseline.

WHEN THIS FAILS
    Read the diff before regenerating. For any change that is supposed to be
    invisible to English -- extracting a label to `t()`, adding `lang` to the
    schema -- a diff here is the bug, not a stale baseline.

    Regenerate deliberately, never reflexively:
        venv/Scripts/python tools/golden.py --html
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

import pytest

from app import registry
from app.rendering import canvas_html

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "html"

# Imported rather than redeclared: the scenario list used to exist here AND in
# tools/golden.py, so a scenario added to the generator would silently never be
# asserted (and one added here would have no baseline). Same reason
# test_autofit_gate.py reuses verify_autofit.heavy_sample().
sys.path.insert(0, str(ROOT))
from tools.golden import SCENARIOS  # noqa: E402

CASES = [(s, k) for s in SCENARIOS for k in registry.ported_keys()]


def _ids(case):
    return f"{case[0]}-{case[1]}"


@pytest.mark.parametrize("scenario,key", CASES, ids=[_ids(c) for c in CASES])
def test_canvas_html_matches_golden(scenario: str, key: str):
    path = GOLDEN / scenario / f"{key}.html"
    if not path.exists():
        pytest.fail(
            f"No golden for {scenario}/{key}. If this template is new, create the "
            f"baseline with: venv/Scripts/python tools/golden.py --html"
        )
    expected = path.read_text(encoding="utf-8")
    actual = canvas_html(SCENARIOS[scenario], key)
    if actual == expected:
        return

    diff = "\n".join(difflib.unified_diff(
        expected.splitlines(), actual.splitlines(),
        fromfile=f"golden/{scenario}/{key}.html", tofile=f"rendered/{scenario}/{key}.html",
        lineterm="", n=2,
    ))
    # Long templates produce long diffs; the first divergences are the ones
    # that explain the rest.
    lines = diff.splitlines()
    if len(lines) > 60:
        diff = "\n".join(lines[:60]) + f"\n... ({len(lines) - 60} more diff lines)"
    pytest.fail(f"{scenario}/{key} HTML changed:\n{diff}")


def test_every_ported_template_has_a_golden():
    """A template added without a baseline is a template with no gate."""
    missing = [
        f"{scenario}/{key}"
        for scenario in SCENARIOS
        for key in registry.ported_keys()
        if not (GOLDEN / scenario / f"{key}.html").exists()
    ]
    assert not missing, f"templates with no HTML golden: {missing}"
