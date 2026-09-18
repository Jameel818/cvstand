"""Unexplained vertical voids, as a gate over the whole catalogue.

WHAT THIS PROTECTS

    The vertical axis already has two gates and neither can see this defect:

        auto-fit gate     fails when content is too TALL for the frame
        overflow gate     fails when content runs off the side

    A template whose content is too SHORT passes both. Nothing overflows,
    nothing is clipped, nothing is lost — the page simply has a 270px hole in
    the middle of it, and the only thing that notices is a reader.

    That is not hypothetical. `modern-t2`'s main column was
    `justify-content:space-between` on a fixed 1100px frame, which hands all
    leftover height to the gaps: a declared 22px row-gap rendered as 157px,
    twice. It matched the reference image only because the reference's content
    happened to fill the page, and a real résumé does not.

WHY IT RUNS ON THE SHIPPED SAMPLE

    The sample is deliberately shorter than the frame for most layouts — that
    is the normal case, and the case both other gates are blind to. Running
    this on a deliberately overlong fixture would prove nothing, because a
    full frame has no slack to distribute and the defect disappears.
"""
from __future__ import annotations

import pytest

from app import registry
from tests import samples
from tools.verify_voids import SLACK, plant_a_void, report, scan

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

KEYS = sorted(registry.ported_keys())


@pytest.fixture(scope="module")
def void_page(browser):
    """One page for all 49 renders, as the overflow gate does."""
    ctx = browser.new_context(viewport={"width": 900, "height": 1200})
    pg = ctx.new_page()
    yield pg
    ctx.close()


@pytest.mark.parametrize("key", KEYS)
def test_no_template_has_an_unexplained_void(void_page, key):
    hits = scan(void_page, samples.ENGLISH, key)
    assert not hits, report(key, hits)


def test_the_void_scan_can_fail(void_page):
    """A check that cannot fail proves nothing, and this repo has shipped two:
    the pixel gate that went 30+ runs without running (session 18), and the
    pixel BASELINES that were gitignored so a fresh clone had none to compare
    against.

    So the scan is pointed at a void planted on a real template page. If this
    passes while the parametrized tests above are green, their silence means
    the catalogue is clean rather than the instrument being deaf.
    """
    scan(void_page, samples.ENGLISH, "modern-t1")
    planted = plant_a_void(void_page)
    assert planted, (
        "the void scan could not see a 556px void planted on a live template "
        "page - every other assertion in this file is therefore worthless"
    )
    assert planted[0]["excess"] > SLACK
