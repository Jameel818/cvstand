"""Horizontal overflow: the other axis, as a gate.

WHAT THIS PROTECTS

    Auto-fit owns the VERTICAL axis and is gated for the whole catalogue
    (`tests/e2e/test_autofit_gate.py`). Nothing had ever looked at the
    horizontal one, and the two fail very differently:

        too tall   auto-fit compresses, reports `fitted: false` if it cannot,
                   and the builder raises a banner the user can act on
        too wide   the text is painted outside the 850px canvas, the PDF page
                   IS the canvas, and it is simply absent from the export

    Nothing throws and nothing warns. The résumé looks right on screen while
    the email address on it has lost its last nine characters.

    Measured 2026-09-09 across all 49 templates in both languages, this found
    one real defect: `modern-t12` set `white-space: nowrap` on the headline, so
    an ordinary 50-character job title ran 39px off the canvas (65px in
    Arabic) and the canvas is `overflow:hidden`. It is fixed, and this is what
    stops it coming back anywhere.

WHAT COUNTS AS LOSING TEXT, AND WHAT DOES NOT

    SILENT loss only. `tools/verify_overflow.py` separates three outcomes and
    this gate asserts on one of them:

      outside     painted beyond the canvas -> absent from the PDF.  FAILS.
      clipped     cut by an ancestor's overflow, no ellipsis.        FAILS.
      ellipsised  cut with a "..." the reader can see.               ALLOWED.

    The third is a design decision, not a defect: `modern-t21`'s contact pill
    ellipsises a long email on purpose, and "fixing" it would mean breaking a
    46px fixed-height pill to fit a 74-character address. A reader who can see
    that text was cut can go and shorten it; the failure this file is named
    after is the one nobody can see.

WHY THE `wide` SAMPLE AND NOT THE `extreme` ONE

    `wide_sample()` is long but entirely ordinary — a university email address,
    a department's full name, a double-barrelled surname. A template that loses
    text on it is broken for a real person, so it is asserted.

    `extreme_sample()` plants a 120-character token with NO break opportunity
    in it, and all 49 templates lose it. That is deliberately NOT asserted, and
    the reason is measured rather than assumed: the obvious global fix
    (`overflow-wrap: break-word` on the canvas) was tried, and it moved
    `modern-t2`'s pixel golden by breaking `Expert` into `Expe`/`rt` in the
    narrow level column — turning invisible spill into visibly broken words on
    a résumé that was fine. Adding `min-width: 0` alongside it recovered 13 more
    templates and moved `modern-t2`'s sidebar by 31k pixels. Both were dropped:
    changing how 49 shipped layouts render is not a fair price for an input
    nobody types. `test_the_scan_can_fail` keeps that case in view instead.
"""
from __future__ import annotations

import pytest

from app import registry
from tools.verify_overflow import extreme_sample, scan, wide_sample, worst

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

KEYS = sorted(registry.ported_keys())


@pytest.fixture(scope="module")
def wide_page(browser):
    """One page for the whole module. 98 renders otherwise pay for 98 contexts."""
    ctx = browser.new_context(viewport={"width": 900, "height": 1200})
    pg = ctx.new_page()
    yield pg
    ctx.close()


def _report(key: str, lang: str, r: dict) -> str:
    lines = [f"{key} ({lang}) loses text horizontally:"]
    for f in sorted(r["outside"], key=lambda x: -x["px"])[:3]:
        lines.append(f"  outside the canvas by {f['px']}px at the {f['side']}: {f['text']!r}")
    for c in sorted(r["clipped"], key=lambda x: -x["px"])[:3]:
        lines.append(f"  clipped by {c['px']}px, no ellipsis: {c['text']!r}")
    lines.append("  reproduce: venv/Scripts/python tools/verify_overflow.py "
                 f"--lang {lang} {key}")
    return "\n".join(lines)


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
def test_no_template_silently_loses_ordinary_text(wide_page, key, lang):
    r = scan(wide_page, wide_sample(lang), key)
    assert worst(r) == 0, _report(key, lang, r)


def test_the_scan_can_fail(wide_page):
    """A gate that cannot fail proves nothing, and this project has shipped one
    before — the pixel gate went 30+ runs without running at all (session 18).

    The `extreme` sample is the natural control because its outcome is a
    measured fact rather than a hypothetical: an unbroken 120-character token
    overflows every template in the catalogue, and deliberately still does (see
    the module docstring). So this asserts the instrument fires, AND pins the
    known-unfixed behaviour in the same breath — if a future change makes
    `modern-t1` absorb an unbreakable token, this test says so out loud instead
    of letting the wide gate above pass for a new reason."""
    r = scan(wide_page, extreme_sample("en"), "modern-t1")
    assert worst(r) > 0, (
        "the overflow scan reports nothing for a 120-character unbroken token — "
        "either the catalogue gained a global wrapping rule (good news; update "
        "this test and the module docstring) or the scan has gone blind")
