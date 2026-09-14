"""Golden gate 2 of 2 — what each template actually LOOKS like.

WHY THIS FILE EXISTS
    `tests/test_golden_html.py` proves the emitted text did not change. It
    cannot prove the appearance did not change, and for the bilingual work that
    is the gap that matters: converting `padding-left` to
    `padding-inline-start` deliberately CHANGES the HTML, so the HTML gate is
    expected to move. In an LTR document those two declarations are the same
    declaration -- so if the pixels move too, the conversion was wrong.

    That makes this the gate that actually guards the promise "English does not
    change". It is the slow one; it is also the one worth waiting for.

WHY IT LIVES HERE AND NOT IN tests/e2e/
    It carries the `e2e` marker, so `tests/conftest.py` skips it in the ~9s
    unit loop and `--e2e` opts in -- the project's existing convention. But it
    is deliberately NOT under tests/e2e/, whose autouse `clean_state` fixture
    boots a live Flask server. This gate renders through `set_content()` and
    needs no server at all; sitting here keeps that dependency out.

WHEN THIS FAILS
    Look at the artifacts before touching the baseline. On a mismatch the test
    writes three files to tests/e2e/artifacts/:
        <key>-golden.png    what it looked like
        <key>-actual.png    what it looks like now
        <key>-diff.png      amplified per-pixel difference
    Regenerate only once you can say what moved and why:
        venv/Scripts/python tools/golden.py --pixels
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import registry
from app.rendering import document_html

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "pixels"
ARTIFACTS = ROOT / "tests" / "e2e" / "artifacts"

SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

# Per-channel delta below which two pixels count as equal. Glyph rasterisation
# is not bit-deterministic across runs; a real layout shift moves whole edges,
# not one channel by a hair. 8/255 separates the two comfortably.
CHANNEL_TOLERANCE = 8
# How many such pixels are allowed before it counts as a change. Zero would
# make the gate flake on antialiasing; this is ~0.005% of an 850x1100 canvas.
MAX_DIFFERING_PIXELS = 50


@pytest.fixture(scope="module")
def browser(_playwright):
    """Chromium from the session-wide Playwright in tests/conftest.py.

    This used to open its own `sync_playwright()`, which works when the
    file runs alone and errors at setup on ALL 50 tests as soon as any
    tests/e2e/ test has run first -- the second entry in one thread
    raises "Playwright Sync API inside the asyncio loop".
    """
    b = _playwright.chromium.launch(args=["--no-sandbox"])
    try:
        yield b
    finally:
        b.close()


def _render(browser, key: str, path: Path) -> None:
    page = browser.new_page(viewport={"width": 850, "height": 1100})
    try:
        # for_pdf=True embeds the fonts; see tools/golden.py for why a linked
        # stylesheet would silently rasterise every glyph in the wrong face.
        page.set_content(document_html(SAMPLE, key, for_pdf=True), wait_until="networkidle")
        page.evaluate("document.fonts && document.fonts.ready")
        page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
        page.locator(".tpl").screenshot(path=str(path))
    finally:
        page.close()


def _compare(golden_path: Path, actual_path: Path, key: str) -> tuple[int, str]:
    """(differing pixel count, explanation). Writes diff artifacts on mismatch."""
    from PIL import Image, ImageChops

    with Image.open(golden_path) as g, Image.open(actual_path) as a:
        golden = g.convert("RGB")
        actual = a.convert("RGB")

        if golden.size != actual.size:
            return 10**9, (
                f"canvas size changed: golden {golden.size} -> actual {actual.size}. "
                f"That is a layout shift, not a rendering wobble."
            )

        diff = ImageChops.difference(golden, actual)
        if diff.getbbox() is None:
            return 0, ""

        # Collapse RGB to the largest single-channel delta per pixel, then count
        # everything past the tolerance.
        mask = diff.convert("L").point(lambda v: 255 if v > CHANNEL_TOLERANCE else 0)
        count = sum(mask.histogram()[255:])
        if count > MAX_DIFFERING_PIXELS:
            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            golden.save(ARTIFACTS / f"{key}-golden.png")
            actual.save(ARTIFACTS / f"{key}-actual.png")
            # Amplified so a subtle shift is actually visible to a human.
            diff.point(lambda v: min(255, v * 12)).save(ARTIFACTS / f"{key}-diff.png")
            bbox = mask.getbbox()
            return count, (
                f"{count} pixels differ by more than {CHANNEL_TOLERANCE}/255, "
                f"bounding box {bbox}. See tests/e2e/artifacts/{key}-diff.png"
            )
        return 0, ""


@pytest.mark.slow
@pytest.mark.parametrize("key", registry.ported_keys())
def test_rendered_canvas_matches_golden(browser, key, tmp_path):
    golden_path = GOLDEN / f"{key}.png"
    if not golden_path.exists():
        pytest.fail(
            f"No pixel golden for {key}. Create it with: "
            f"venv/Scripts/python tools/golden.py --pixels"
        )
    actual_path = tmp_path / f"{key}.png"
    _render(browser, key, actual_path)
    count, why = _compare(golden_path, actual_path, key)
    assert count == 0, f"{key} renders differently: {why}"


def test_every_ported_template_has_a_pixel_golden():
    missing = [k for k in registry.ported_keys() if not (GOLDEN / f"{k}.png").exists()]
    assert not missing, f"templates with no pixel golden: {missing}"
