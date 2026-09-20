"""Phase 4: RTL typography.

WHAT THIS PROTECTS

    An English section heading carries three cues - size, weight, and
    small-caps-with-tracking. Arabic has no case, and Chromium applies
    letter-spacing to ZERO gaps inside a joined Arabic run, so the third cue is
    worth nothing. A heading that leant on it flattens into body text, and
    nothing raises: the resume simply stops being scannable.

    Four templates did exactly that (ats-t13/19/21/23: heading size ~= body,
    weight 600, no rule behind it). They carry `sec-head`, and an RTL-only
    stylesheet gives that class size and weight back.

    Two things therefore have to stay true, and neither is covered by the
    golden gates - they render `sample`, which is English:

      * the stylesheet reaches Arabic documents and NO English one, and
      * the four templates' headings actually outrank their body text in a
        rendered Arabic page.

    The English side is already proven: the pixel gate does not move, because
    the class is inert in LTR and the stylesheet is not emitted for LTR at all.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import registry
from app.rendering import RTL_TYPOGRAPHY, canvas_html, document_html

ROOT = Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "app" / "templates" / "resumes"

# The four templates measured to lose every heading cue in Arabic.
RESCUED = ["ats-t13", "ats-t19", "ats-t21", "ats-t23"]

ARABIC_SAMPLE = json.loads(
    (ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))
ENGLISH_SAMPLE = json.loads(
    (ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

MARKER = '[dir="rtl"] .tpl .sec-head'


def test_the_rtl_stylesheet_reaches_arabic_documents_only():
    """Emitted by dir, exactly like the Arabic font sheet. An English document
    never carries the rules at all, which is the belt to the selector's braces.
    """
    assert MARKER in document_html(ARABIC_SAMPLE, "ats-t23")
    assert MARKER not in document_html(ENGLISH_SAMPLE, "ats-t23")
    # and a resume with no `lang` at all is English
    assert MARKER not in document_html({"name": "A", "title": "B"}, "ats-t23")


def test_the_stylesheet_is_scoped_to_rtl():
    """Every selector in it must be dir-scoped. Belt and braces: even if the
    sheet were ever emitted unconditionally, it could not reach English.
    """
    selectors = re.findall(r"([^{}/*]+)\{", RTL_TYPOGRAPHY.split("<style>")[1])
    real = [s.strip() for s in selectors if s.strip() and not s.strip().startswith("@")]
    assert real, "no selectors found - the parse is wrong, not the stylesheet"
    for sel in real:
        assert '[dir="rtl"]' in sel, f"selector not scoped to RTL: {sel!r}"


def test_only_the_measured_templates_carry_sec_head():
    """`sec-head` is a claim that a heading has NO other cue in Arabic. It was
    measured for exactly four templates; a fifth appearing without that
    measurement is a change to review, not to wave through.
    """
    carrying = sorted(
        key for key in registry.ported_keys()
        if "sec-head" in canvas_html(ENGLISH_SAMPLE, key))
    assert carrying == sorted(RESCUED)


def test_each_rescued_template_renders_marked_headings():
    """Cheap smoke check that the class survives into the render at all.

    Deliberately NOT "source occurrences == rendered occurrences": three of the
    four emit their heading from a macro, so the class appears ONCE in the file
    and eight times in the output. Whether every heading is marked is a DOM
    question, and is asserted in the browser test below.
    """
    for key in RESCUED:
        # Count the class TOKEN, not the whole attribute. These headings now
        # also carry `cv-section` (the font policy's role hook), so the
        # attribute reads `class="sec-head cv-section"` and an exact-string
        # count reported 0 marked headings on a template that had eight.
        n = len(re.findall(r'class="[^"]*sec-head[^"]*"',
                           canvas_html(ENGLISH_SAMPLE, key)))
        assert n >= 5, f"{key} rendered only {n} marked headings"


# --- the properties that need a browser -----------------------------------


@pytest.mark.e2e
@pytest.mark.parametrize("key", RESCUED)
def test_rescued_headings_outrank_body_text_in_arabic(_playwright, key):
    """The actual deliverable: in a rendered Arabic page, these headings are
    bigger and heavier than the body text around them.

    Measured on the real page rather than asserted against the CSS, because the
    rule only works if `!important` really does beat the template's inline
    `font-size` - which is the whole mechanism, and the thing that would break
    silently if the selector or the injection ever stopped matching.
    """
    probe = """(labels) => {
      const tpl = document.querySelector('.tpl');
      const px = v => parseFloat(v) || 0;
      const want = new Set(labels);

      // every element whose text is exactly a catalogue label IS a section
      // heading (innermost one, so a wrapper does not count twice)
      const all = [...tpl.querySelectorAll('*')].filter(e => {
        const t = (e.textContent || '').trim();
        if (!want.has(t)) return false;
        return ![...e.children].some(c => (c.textContent || '').trim() === t);
      });
      const unmarked = all.filter(e => !e.classList.contains('sec-head'))
                          .map(e => (e.textContent || '').trim());
      const heads = all.filter(e => e.classList.contains('sec-head')).map(e => {
        const cs = getComputedStyle(e);
        return { size: px(cs.fontSize), weight: parseInt(cs.fontWeight, 10) || 400 };
      });

      const leaves = [...tpl.querySelectorAll('*')].filter(e =>
        e.children.length === 0 && (e.textContent || '').trim().length > 25);
      const sizes = leaves.map(e => px(getComputedStyle(e).fontSize)).sort((a, b) => a - b);
      return { heads, unmarked,
               bodySize: sizes.length ? sizes[Math.floor(sizes.length / 2)] : 0 };
    }"""
    from app.labels import _AR

    browser = _playwright.chromium.launch(args=["--no-sandbox"])
    try:
        page = browser.new_page(viewport={"width": 850, "height": 1100})
        page.set_content(document_html(ARABIC_SAMPLE, key, for_pdf=True),
                         wait_until="networkidle")
        page.evaluate("document.fonts && document.fonts.ready")
        r = page.evaluate(probe, sorted(set(_AR.values())))
    finally:
        browser.close()

    heads, body = r["heads"], r["bodySize"]
    assert heads, f"{key}: no marked Arabic section heading found"
    assert body > 0
    # A section added later without the class would flatten silently, in the one
    # place where nothing else marks a heading.
    assert not r["unmarked"], (
        f"{key}: section headings rendered WITHOUT sec-head, so they stay flat "
        f"in Arabic: {r['unmarked']}")
    smallest = min(h["size"] for h in heads)
    lightest = min(h["weight"] for h in heads)
    assert smallest / body >= 1.10, (
        f"{key}: heading {smallest}px vs body {body}px is not a heading in a "
        f"script with no case and no usable tracking")
    assert lightest >= 700, f"{key}: heading weight {lightest} is not heavier than body"
