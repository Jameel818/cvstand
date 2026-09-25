"""Auto-fit wiring tests.

WHY THIS FILE EXISTS
    Auto-fit only works if the engine is actually IN the document on every
    render path, and every way it can go missing is silent:

      - a <script src> instead of an inline <script> works in the preview (an
        iframe srcdoc inherits the page's base URL) and fails in the PDF, whose
        base URL under `set_content()` is about:blank. The PDF would then print
        the unfitted, overflowing layout while the preview showed a clean page —
        with no error anywhere. Exactly the trap the inlined fonts avoid.
      - dropping the `{autofit}` slot from the document template leaves a page
        that renders perfectly and never fits.

    These are fast, browser-free wiring checks. The BEHAVIOUR of the engine —
    that it is a no-op on the shared sample and recovers a realistic overload —
    needs a real layout engine and lives in `tools/verify_autofit.py`, next to
    verify_height.py and fetch_fonts.py, so `pytest -q` stays seconds long.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.rendering import autofit_script, canvas_html, document_html

ROOT = Path(__file__).resolve().parent.parent
AUTOFIT_JS = ROOT / "app" / "static" / "js" / "autofit.js"
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
KEY = "modern-t1"


def test_engine_file_exists():
    assert AUTOFIT_JS.exists(), "app/static/js/autofit.js is the engine; nothing works without it"


def test_autofit_script_is_an_inline_script_tag():
    s = autofit_script()
    assert s.startswith("<script>") and s.rstrip().endswith("</script>")
    assert "src=" not in s, "must be inlined — a src would not resolve under set_content()"
    assert "window.ResumeAutofit" in s


@pytest.mark.parametrize("for_pdf", [False, True])
def test_document_carries_the_engine_on_both_render_paths(for_pdf):
    doc = document_html(SAMPLE, KEY, for_pdf=for_pdf)
    assert "window.ResumeAutofit" in doc
    assert "ResumeAutofit.ready" not in doc.split("<script>")[0]  # inside the script, not before


def test_engine_is_inline_never_linked_in_the_document():
    doc = document_html(SAMPLE, KEY, for_pdf=True)
    assert "<script src" not in doc, (
        "a linked script silently no-ops in the PDF path (base URL about:blank)"
    )


def test_engine_reaches_no_network():
    src = AUTOFIT_JS.read_text(encoding="utf-8")
    assert "http://" not in src and "https://" not in src


def test_engine_runs_after_the_canvas():
    """It queries `.tpl` at parse time, so it must come after the canvas."""
    doc = document_html(SAMPLE, KEY)
    assert (re.search(r'<div class="tpl[ "]', doc).start()
            < doc.index("window.ResumeAutofit"))


def test_canvas_fragment_stays_script_free():
    """`canvas_html()` feeds consumers that are not a browser page. The engine
    belongs to the document wrapper only."""
    frag = canvas_html(SAMPLE, KEY)
    assert "ResumeAutofit" not in frag
    assert "<script" not in frag


def test_floors_match_the_documented_contract():
    """tools/verify_autofit.py and the porting notes quote these numbers. If the
    engine's floors move, the tool's expectations and BUILD.md go stale
    silently — so pin them here.

    2026-08-31: this pin fired. TYPE_FLOOR had been lowered 0.92 -> 0.90 in the
    engine while every other mention — this test, verify_autofit.py, BUILD.md,
    RESUME_HERE.md and autofit.js's own header — still said 0.92. The lower
    floor is what now seats modern-t17's heavy sample (1285.7 -> 1092.5), so
    recovery is 48/49, not the documented 47/49. Pin updated to the engine.

    2026-09-01: CONFIRMED intentional. 0.90 stays, and BUILD.md + this file's
    sibling docs were corrected to it rather than the engine being reverted.
    Stage 2 only runs once stage 1 has bottomed out at 0.85, so it is the last
    thing tried before the builder gives up and shows the amber warning."""
    src = AUTOFIT_JS.read_text(encoding="utf-8")
    assert re.search(r"var FLOOR = 0\.85;", src)
    assert re.search(r"var TYPE_FLOOR = 0\.90;", src)
    assert re.search(r"var MAX_H = 1100;", src)


def test_engine_only_scales_vertical_and_type_properties():
    """The whole safety argument is that no horizontal property is touched —
    that is what keeps full-bleed sidebars at the page edge and the absolutely
    positioned Modern layouts (t7/t8/t11/t14/t15/t18/t21) intact."""
    src = AUTOFIT_JS.read_text(encoding="utf-8")

    # Every property written by name. Anything dynamic goes through `style[k]`,
    # whose keys can only come from PROPS, asserted below. Scanning writes
    # rather than words keeps this immune to the prose in the header, which
    # names `transform` precisely to explain why it is NOT used.
    assert set(re.findall(r"\.style\.(\w+)\s*=", src)) == {"fontSize", "lineHeight"}
    # The typography hook writes the same two properties, !important, when a
    # size was chosen - and nothing else.
    assert set(re.findall(r"\.style\.setProperty\(\s*\"([\w-]+)\"", src)) == {
        "font-size", "line-height"}

    props = re.search(r"var PROPS = \[(.*?)\];", src, re.S).group(1)
    assert set(re.findall(r'"(\w+)"', props)) == {
        "marginTop", "marginBottom", "paddingTop", "paddingBottom", "rowGap"
    }, "PROPS is the whole horizontal-safety guarantee — no width, offset or border"


def test_pdf_exporter_awaits_the_fit():
    """Without the await, page.pdf() races the fit and can print the unfitted
    layout — a PDF that disagrees with the preview the user approved."""
    src = (ROOT / "app" / "exporters" / "pdf.py").read_text(encoding="utf-8")
    await_at = src.index("window.ResumeAutofit")
    print_at = src.index("pdf = page.pdf(")   # the call, not the comment naming it
    assert await_at < print_at, "must be awaited before printing"
