"""Phase 5: layout mirroring.

WHAT THIS PROTECTS

    `dir="rtl"` mirrors normal inline flow and flex row order for free. It does
    nothing to any property named left/right, so before phase 5 a sidebar
    padded with `padding-left` kept its padding on the left while the text
    beside it flowed the other way, and a timeline dot pinned at `left:-31px`
    stayed on the far left of a column that had moved to the right.

    All 202 such declarations are now logical (`padding-inline-start`,
    `border-inline-start`, `inset-inline-start`, `text-align:end`, and the
    block/inline pair for 4-value `padding`). In an LTR document each logical
    property IS its physical twin - the same used value - which is why the
    pixel gate does not move and is the proof that English was untouched.

    Two things have to stay true, and the golden gates cover neither:

      * no physical directional property comes back. A single `padding-left`
        added later mirrors wrongly and NOTHING raises - the page just renders
        with one panel on the wrong side.
      * every absolutely-positioned decoration actually lands mirrored. That is
        a geometric fact about the rendered page, not about the CSS text, and
        `transform` in particular has no logical form at all.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from app import registry
from app.rendering import document_html

ROOT = Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "app" / "templates" / "resumes"

ARABIC_SAMPLE = json.loads(
    (ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))

# Physical properties that do not mirror. Each has a logical replacement that
# is identical in LTR, so there is never a reason to reintroduce one.
FORBIDDEN = {
    "padding-left": "padding-inline-start",
    "padding-right": "padding-inline-end",
    "margin-left": "margin-inline-start",
    "margin-right": "margin-inline-end",
    "border-left": "border-inline-start",
    "border-right": "border-inline-end",
    "left": "inset-inline-start",
    "right": "inset-inline-end",
}


def _template_files():
    return sorted(TPL_DIR.glob("*/*.j2")) + [TPL_DIR / "_macros.j2"]


def _rel(f: Path) -> str:
    return f"{f.parent.name}/{f.name}" if f.parent.name != "resumes" else f.name


def test_no_physical_directional_property_comes_back():
    """`padding-left` and friends mirror wrongly and raise nothing.

    Matched as a PROPERTY (name followed by a colon), so `text-align:left`
    cannot trip it - there the word is a value, and it is caught separately.
    """
    offenders = []
    for f in _template_files():
        src = f.read_text(encoding="utf-8")
        for prop, logical in FORBIDDEN.items():
            for m in re.finditer(r"(?<![\w-])" + prop + r"\s*:", src):
                line = src.count("\n", 0, m.start()) + 1
                offenders.append(f"{_rel(f)}:{line}  {prop}:  -> use {logical}")
    assert not offenders, (
        "physical directional properties do not mirror under dir=rtl:\n  "
        + "\n  ".join(offenders))


def test_no_physical_text_align():
    """`text-align:left/right` pins text to a side of the page. Every one of
    the 19 sites in this catalogue meant "the far edge" - dates columns, level
    labels, contact lines - which is `end`.
    """
    offenders = []
    for f in _template_files():
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"text-align\s*:\s*(left|right)\b", src):
            line = src.count("\n", 0, m.start()) + 1
            offenders.append(f"{_rel(f)}:{line}  text-align:{m.group(1)}")
    assert not offenders, (
        "use text-align:start / text-align:end so it mirrors:\n  "
        + "\n  ".join(offenders))


def test_no_four_value_padding_shorthand():
    """`padding: t r b l` hides two physical values in a shorthand that no
    linter would flag. There is no 4-value logical shorthand, so these must be
    written as `padding-block` + `padding-inline`.
    """
    offenders = []
    for f in _template_files():
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"(?<![\w-])(padding|margin)\s*:\s*([^;\"']+)", src):
            vals = m.group(2).split()
            if len(vals) == 4 and vals[1] != vals[3]:
                line = src.count("\n", 0, m.start()) + 1
                offenders.append(f"{_rel(f)}:{line}  {m.group(0).strip()[:60]}")
    assert not offenders, (
        "asymmetric 4-value shorthand does not mirror; split it into "
        "`padding-block: t b; padding-inline: l r`:\n  " + "\n  ".join(offenders))


# --- the geometric property, which needs a browser ------------------------

_PROBE = """() => {
  const tpl = document.querySelector('.tpl');
  const base = tpl.getBoundingClientRect();
  const out = [];
  tpl.querySelectorAll('*').forEach(e => {
    const cs = getComputedStyle(e);
    if (cs.position !== 'absolute' && cs.position !== 'fixed') return;
    const r = e.getBoundingClientRect();
    out.push({ x: Math.round((r.left - base.left) * 10) / 10,
               w: Math.round(r.width * 10) / 10,
               text: (e.textContent || '').trim().slice(0, 20) });
  });
  return { width: Math.round(base.width), items: out };
}"""

# Sub-pixel: rounding and glyph metrics move a centre by a fraction, a stranded
# decoration moves by hundreds of px. modern-t2's dots were out by 545px.
TOLERANCE = 2.0


@pytest.mark.e2e
@pytest.mark.slow
def test_every_absolute_decoration_mirrors(_playwright):
    """Render the same resume LTR and RTL; each positioned element's CENTRE
    must land at `canvasWidth - centre_ltr`.

    Centres, not left edges, because one decoration legitimately changes width
    between the two: modern-t22's rail carries six kerned Latin letters at
    214px in English and a single Arabic word at 140px in Arabic, so its
    bounding box is not the same size. Its centre still mirrors exactly, and
    the failure this guards against - an element stranded on the old side -
    moves a centre just as far as it moves an edge.

    Geometric rather than textual because `transform` has no logical form:
    modern-t22's rotated rail has a correctly mirrored BOX and still needed its
    translate negated by hand. Only a rendered comparison sees that.

    Elements are paired by document order, which is identical between the two
    renders because only `lang`/`dir` differ.
    """
    ltr = copy.deepcopy(ARABIC_SAMPLE)
    ltr["lang"] = "en"

    browser = _playwright.chromium.launch(args=["--no-sandbox"])
    failures = []
    try:
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        for key in registry.ported_keys():
            snaps = {}
            for name, data in (("ltr", ltr), ("rtl", ARABIC_SAMPLE)):
                page.set_content(document_html(data, key, for_pdf=True),
                                 wait_until="networkidle")
                page.evaluate("document.fonts && document.fonts.ready")
                page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
                snaps[name] = page.evaluate(_PROBE)
            a, c = snaps["ltr"], snaps["rtl"]
            if len(a["items"]) != len(c["items"]):
                failures.append(f"{key}: element count differs "
                                f"({len(a['items'])} vs {len(c['items'])})")
                continue
            for ea, ec in zip(a["items"], c["items"]):
                centre_ltr = ea["x"] + ea["w"] / 2
                centre_rtl = ec["x"] + ec["w"] / 2
                expected = a["width"] - centre_ltr
                if abs(centre_rtl - expected) > TOLERANCE:
                    failures.append(
                        f"{key}: {ea['text'] or 'decoration'!r} centred at "
                        f"{centre_ltr:.1f} in LTR landed at {centre_rtl:.1f} in RTL, "
                        f"expected {expected:.1f}")
    finally:
        browser.close()

    assert not failures, (
        "absolutely-positioned decorations did not mirror:\n  "
        + "\n  ".join(failures[:20])
        + (f"\n  ... and {len(failures) - 20} more" if len(failures) > 20 else ""))
