"""Regenerate the golden regression baselines.

    venv/Scripts/python tools/golden.py --html       # fast, no browser
    venv/Scripts/python tools/golden.py --pixels     # needs Chromium
    venv/Scripts/python tools/golden.py --all

WHY THIS EXISTS
    The bilingual (AR/RTL) work touches all 49 templates. Nothing in the 506
    existing tests would notice a template that silently changed how it LOOKS —
    they assert structure and contract ("the level word is present", "the chip
    hides when empty"), never appearance. A mirrored padding or a dropped rule
    would sail straight through them.

    So there are two gates, deliberately kept independent, because the phases
    of that work break them at different moments:

      HTML gate   — the exact canvas fragment each template emits.
                    Extracting a hardcoded "EXPERIENCE" to `t('experience')`
                    MUST leave this byte-identical; that is the whole proof the
                    label catalogue changed nothing for English.

      PIXEL gate  — the rendered 850x1100 canvas.
                    Converting `padding-left` to `padding-inline-start` DOES
                    change the HTML (so the HTML gate is expected to move) but
                    in an LTR document the two properties are the same
                    property, so the pixels MUST NOT move.

    Regenerate one without the other. A phase that needs BOTH regenerated is a
    phase that changed English output, which is the thing we said we would not
    do — treat it as a failure to explain, not a baseline to refresh.

The goldens are stored as full text/images rather than hashes so a failure can
show WHAT moved, not merely that something did.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry
from app.rendering import canvas_html, document_html

GOLDEN = ROOT / "tests" / "golden"
HTML_DIR = GOLDEN / "html"
PIXEL_DIR = GOLDEN / "pixels"

SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

# The degrade path: every optional section empty. This is the shape that broke
# `normalize()` before (see the REGRESSION note in app/schema.py) and it is the
# shape most likely to break again when `lang` joins the schema.
SPARSE = {"name": "Wren Ashworth", "title": "Creative Lead"}

def _with_gpa():
    """`sample` with a GPA on every education entry.

    Neither `sample` nor `sparse` sets `education[].gpa`, so the `GPA <value>`
    prefix that 32 templates carry rendered in NEITHER baseline -- the gate was
    byte-identical across a line it never drew. Found while routing that label
    through t() in phase 3; the fix belongs in the gate, not in that phase.
    """
    d = copy.deepcopy(SAMPLE)
    for i, ed in enumerate(d.get("education", [])):
        ed["gpa"] = "3.%d" % (7 + i)
    return d


def _partial_sections():
    """Recognition and tools, but no languages and no education.

    The other blind spot: three ATS templates compose a trailing heading out of
    whichever optional sections exist ("Certifications, Tools & Languages").
    `sample` has all three and `sparse` has none, so the separator and the
    conjunction -- the parts that are language-dependent -- never appeared in a
    baseline. Two items is the case that draws exactly one conjunction.
    """
    d = copy.deepcopy(SAMPLE)
    d["languages"] = []
    d["education"] = []
    return d


SCENARIOS = {
    "sample": SAMPLE,
    "sparse": SPARSE,
    "gpa": _with_gpa(),
    "partial": _partial_sections(),
}


def html_path(scenario: str, key: str) -> Path:
    return HTML_DIR / scenario / f"{key}.html"


def pixel_path(key: str) -> Path:
    return PIXEL_DIR / f"{key}.png"


def write_html() -> int:
    n = 0
    for scenario, data in SCENARIOS.items():
        (HTML_DIR / scenario).mkdir(parents=True, exist_ok=True)
        for key in registry.ported_keys():
            p = html_path(scenario, key)
            p.write_text(canvas_html(data, key), encoding="utf-8")
            n += 1
    return n


def write_pixels() -> int:
    from playwright.sync_api import sync_playwright

    PIXEL_DIR.mkdir(parents=True, exist_ok=True)
    keys = registry.ported_keys()
    n = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            for key in keys:
                page = browser.new_page(viewport={"width": 850, "height": 1100})
                try:
                    # for_pdf=True embeds the font bytes. set_content()'s base
                    # URL is about:blank, so a linked /static/... stylesheet
                    # resolves to nothing and Chromium substitutes a fallback
                    # face WITHOUT error -- every golden would then be captured
                    # in the wrong typeface and the gate would be worthless.
                    page.set_content(document_html(SAMPLE, key, for_pdf=True),
                                     wait_until="networkidle")
                    page.evaluate("document.fonts && document.fonts.ready")
                    # Auto-fit compresses the layout after fonts.ready. Capture
                    # before it settles and the golden is a half-fitted frame,
                    # different on every run -- the classic flaky-baseline trap.
                    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
                    page.locator(".tpl").screenshot(path=str(pixel_path(key)))
                    n += 1
                finally:
                    page.close()
        finally:
            browser.close()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", action="store_true", help="regenerate the HTML fragment goldens")
    ap.add_argument("--pixels", action="store_true", help="regenerate the rendered-canvas goldens")
    ap.add_argument("--all", action="store_true", help="both")
    args = ap.parse_args()

    if not (args.html or args.pixels or args.all):
        ap.error("pick --html, --pixels or --all")

    if args.html or args.all:
        print(f"HTML goldens written:  {write_html()}")
    if args.pixels or args.all:
        print(f"pixel goldens written: {write_pixels()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
