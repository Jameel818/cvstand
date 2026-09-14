"""A half-filled social link must leave no dangling separator or empty caption.

The form asks for a Label and a URL. Both keys are schema-required, so a fresh
entry is invalid until the user types in both fields — but clearing one
afterwards leaves `{"label": "", "url": "..."}`, which is perfectly valid and
reaches the renderers. Every other contact field is guarded (`{% if c.phone %}`
…); the social loop was not, in two different ways:

* 29 layouts append the label into a joined list, so an empty one left a
  **dangling separator** — `"… | wrenashworth.example.com | "`, the same shape
  as the `"Ceramics —"` bug in the skill rows;
* 8 layouts render the pair as caption + value, so an empty label left a **bold
  blank caption** floating above the URL — the inverse of the stat-chip rule
  ("never a chip with a caption and no number").

Both are checked as the artefacts they are — an empty element, and a separator
with nothing after it. An earlier cut of this file tried to subtract the
supplied value from the rendered text and compare; that reads well but is
wrong, because a separator legitimately belongs to a value that IS present, so
it flagged 25 correct templates.

PHASE 8 — BOTH DIRECTIONS. The sweeps run against `tests/samples.BOTH`. A
dangling separator is exactly the defect the Arabic side could carry alone:
since phase 3 the fixed labels beside these values come from the catalogue and
`join_labels()` joins them with an Arabic conjunction, so the string either
side of a half-filled social link is not the same string in the two languages.
The link itself stays `Dribbble` / `dribbble.example/wren` in both, so a
failure is attributable to the document rather than to the probe.
"""
from __future__ import annotations

import json
import re

import pytest

from app import create_app, registry
from app.rendering import canvas_html
from tests import samples

SAMPLE = samples.ENGLISH

URL = "dribbble.example/wren"
LABEL = "Dribbble"

EMPTY_EL = re.compile(r"<(div|span|li|p)[^>]*>\s*</\1>")
# A separator with nothing after it before its element closes, or two in a row.
# `<br>` counts: the ~6 layouts that join the contact bits with "<br>" leave a
# trailing line break rather than a stray pipe — the same blank-line artefact in
# different markup. Leaving it out let 6 of them through the mutation check.
DANGLING = re.compile(
    r"[|·•]\s*</|[|·•]\s*[|·•]|<br\s*/?>\s*</|<br\s*/?>\s*<br\s*/?>")


@pytest.fixture()
def app_ctx():
    with create_app().test_request_context():
        yield


def _with(social: dict | None, base: dict = None) -> dict:
    data = json.loads(json.dumps(SAMPLE if base is None else base))
    data["contact"]["social"] = [social] if social else []
    return data


def _artefacts(html: str) -> tuple[int, int]:
    return len(EMPTY_EL.findall(html)), len(DANGLING.findall(html))


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", sorted(registry._PORTED))
@pytest.mark.parametrize("social,what", [
    ({"label": "", "url": URL}, "no label"),
    ({"label": LABEL, "url": ""}, "no URL"),
])
def test_a_half_filled_social_link_leaves_no_artefact(app_ctx, key, social, what,
                                                      lang, sample):
    """Neither half missing may add an empty caption or a dangling separator.

    Measured as a delta against the same résumé with no social link at all, so
    a template that already renders (say) a deliberately empty spacer element
    is not blamed for it."""
    base = _artefacts(canvas_html(_with(None, sample), key))
    now = _artefacts(canvas_html(_with(social, sample), key))
    assert now[0] <= base[0], f"{what}: added {now[0] - base[0]} empty element(s)"
    assert now[1] <= base[1], f"{what}: added {now[1] - base[1]} dangling separator(s)"


def _renders_social(key: str, base: dict = None) -> bool:
    return (canvas_html(_with({"label": LABEL, "url": URL}, base), key)
            != canvas_html(_with(None, base), key))


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_a_complete_social_link_still_renders(app_ctx, key, lang, sample):
    """The guards must not swallow a valid link.

    Nine layouts have no social slot at all — a deliberate design choice where
    there is no room — so the assertion applies only to those that do render
    one, detected rather than hard-coded so the list cannot go stale."""
    if not _renders_social(key, sample):
        pytest.skip("layout has no social slot")
    html = canvas_html(_with({"label": LABEL, "url": URL}, sample), key)
    # which of the two shows is a design choice: most show the label,
    # `ats-t3` shows `s.url or s.label`.
    assert LABEL in html or URL in html
