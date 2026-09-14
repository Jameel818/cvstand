"""Every ported template must render an incomplete-but-valid résumé.

`schema.py`'s module docstring promises that "every optional field has a
defined empty-value degrade path ... so a missing field never 500s a render",
and the Jinja environment runs `StrictUndefined`, which turns any gap in that
promise into a hard failure rather than a blank.

It was not true. `normalize()` defaulted only `bullets`, so:

* the builder's "+ Add role" pushes `{bullets: []}`; as soon as the user typed
  the job title the entry became schema-valid (only `role` is required) and
  reached `_macros.j2`'s `{% if job.start or job.end %}` — `/api/render` 500'd
  on all 49 templates;
* a résumé holding nothing but `name` and `title` — the emptiest the schema
  allows — 500'd all 49 on `contact.email`.

Both are ordinary states a real user passes through, so this is a contract test
over the whole catalogue rather than a case for one template. It needs no
browser: `document_html()` is plain Python, so it belongs in the fast loop.

PHASE 8 — BOTH DIRECTIONS. Everything above was only ever run against the
English sample. The degrade paths it pins are the ones this project's real
defects have hidden in, and they now run through Arabic too: the sweeps take
`(lang, sample)` from `tests/samples.BOTH`, so a guard that holds for English
and drops an Arabic entry is a failure rather than a blind spot. The English
half of each pair carries NO `lang` key, which keeps the absent-means-English
promise under test at the same time.
"""
from __future__ import annotations

import json

import pytest

from app import create_app, registry
from app.rendering import document_html
from tests import samples


@pytest.fixture()
def app_ctx():
    """`document_html()` calls `url_for` for the font stylesheet, so it needs an
    application context even though nothing here goes through the test client."""
    with create_app().test_request_context():
        yield

SAMPLE = samples.ENGLISH

# The emptiest résumé the schema permits: `name` and `title` are the only
# required top-level fields. The Arabic one also carries `lang`, which is the
# only key that makes it a different render.
MINIMAL = {"name": "Wren Ashworth", "title": "Creative Lead"}
MINIMAL_AR = {"name": "ورين آشورث", "title": "مديرة إبداعية", "lang": "ar"}
MINIMALS = [("en", MINIMAL), ("ar", MINIMAL_AR)]


def _partial(base: dict = None) -> dict:
    """`base` plus one entry per list carrying ONLY its required field(s) —
    exactly what "+ Add …" leaves behind once the user names it.

    The added entries stay in English whichever résumé they are added to. That
    is deliberate: what is under test is the DEGRADE path, and keeping the
    probe identical means a failure is attributable to the language of the
    document rather than to the language of the probe."""
    data = json.loads(json.dumps(SAMPLE if base is None else base))
    data["experience"].append({"role": "Studio Intern", "bullets": []})
    data["education"].append({"degree": "Foundation Certificate", "bullets": []})
    data["recognition"].append({"title": "Rising Talent"})
    data["skills"].append({"name": "Ceramics", "level": "Foundational"})
    data["languages"].append({"name": "Dutch", "level": "Basic"})
    data["references"].append({"name": "Marek Olander"})
    data["achievements"].append({"metric": "7", "label": "Studios"})
    data["contact"]["social"].append({"label": "Dribbble", "url": "dribbble.example"})
    return data


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_a_half_filled_entry_renders(app_ctx, key, lang, sample):
    assert document_html(_partial(sample), key)


@pytest.mark.parametrize("lang,minimal", MINIMALS)
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_a_name_and_title_alone_render(app_ctx, key, lang, minimal):
    assert document_html(minimal, key)


def test_the_blanks_are_derived_from_the_schema_not_hand_listed(app_ctx):
    """The guard against this regression coming back: every optional property
    the schema declares for a list entry must appear in the defaults, so adding
    a field to the schema cannot silently leave `normalize()` behind."""
    from app.schema import RESUME_SCHEMA, _LIST_BLANKS

    for key, spec in RESUME_SCHEMA["properties"].items():
        if spec.get("type") != "array" or spec.get("items", {}).get("type") != "object":
            continue
        declared = spec["items"]["properties"]
        for name, sub in declared.items():
            if sub.get("type") in ("string", "array", "object"):
                assert name in _LIST_BLANKS[key], f"{key}.{name} has no default"

    # `percent` is deliberately NOT defaulted — the macros read it as
    # `skill.get('percent')` so that "unset" and "0%" stay distinguishable.
    assert "percent" not in _LIST_BLANKS["skills"]


def test_normalize_leaves_a_supplied_value_alone(app_ctx):
    """Defaulting must never overwrite real data."""
    from app.schema import normalize

    out = normalize({"name": "A", "title": "B",
                     "experience": [{"role": "R", "company": "C"}],
                     "skills": [{"name": "S", "level": "Expert", "percent": 0}]})
    job = out["experience"][0]
    assert job["role"] == "R" and job["company"] == "C"
    assert job["start"] == "" and job["bullets"] == []
    assert out["skills"][0]["percent"] == 0, "an explicit 0% was clobbered"


# --------------------------------------------------------------- DOCX side

def _docx_paragraphs(blob: bytes) -> list[str]:
    import io
    from docx import Document
    return [p.text for p in Document(io.BytesIO(blob)).paragraphs]


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_docx_renders_a_half_filled_entry(app_ctx, key, lang, sample):
    from app.exporters import render_docx
    blob = render_docx(_partial(sample), key)
    assert blob[:2] == b"PK"
    assert "Studio Intern" in _docx_paragraphs(blob)


@pytest.mark.parametrize("lang,minimal", MINIMALS)
@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_docx_renders_a_name_and_title_alone(app_ctx, key, lang, minimal):
    from app.exporters import render_docx
    assert render_docx(minimal, key)[:2] == b"PK"


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_a_role_with_no_dates_leaves_no_blank_line(app_ctx, key, lang, sample):
    """REGRESSION (2026-09-04). The Word masters guarded each *separator* in the
    company/location/dates line but not the line itself, so a role carrying only
    a title rendered an EMPTY PARAGRAPH — a stray blank line in Word where the
    HTML drops the row outright, in a master tuned to fit exactly one page.
    Fixed with a `{%p if %}` around the whole meta paragraph (safe here: it is
    in the document body, not a table cell — cells must keep a paragraph).

    Note the master is GENERATED: fix `tools/build_word_masters.py` and re-run
    it, never edit the .docx."""
    from app.exporters import render_docx
    paras = _docx_paragraphs(render_docx(_partial(sample), key))
    assert not [p for p in paras if not p.strip()], "stray blank paragraph(s)"
    i = paras.index("Studio Intern")
    assert paras[i + 1].strip(), "the role is followed by a blank line"


@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_complete_entries_keep_their_meta_line(app_ctx, key):
    """The guard must not swallow the line it is guarding."""
    from app.exporters import render_docx
    paras = _docx_paragraphs(render_docx(SAMPLE, key))
    # matched by company, not by the "  ·  " separator — the Tools line uses
    # that too, which is what made the first cut of this assertion wrong.
    for company in ("Halden & Row", "Bellrock Studio", "Kiln Press"):
        assert any(p.startswith(company) and "  ·  " in p for p in paras), company
    assert "Halden & Row, Portside  ·  2021 - Present" in paras


# ------------------------------------------------- stale summary_highlight

HIGHLIGHT_TEMPLATES = ["ats-t4", "ats-t10", "modern-t2"]


@pytest.mark.parametrize("lang,sample", samples.BOTH)
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_a_highlight_that_no_longer_appears_in_the_summary(app_ctx, key, lang, sample):
    """The builder's hint says the phrase "must appear word-for-word in the
    summary above", and the user can break that at any time by editing the
    summary afterwards.

    The three templates that draw the marker swipe do
    `r.summary.split(r.summary_highlight, 1)` and read `around[1]` — which
    raises IndexError, i.e. a 500, the moment the phrase is absent. They are
    already guarded with `and r.summary_highlight in r.summary`; this pins that
    guard, because removing it fails loudly only for a user whose summary has
    drifted, which no fixture would otherwise reproduce."""
    data = json.loads(json.dumps(sample))
    data["summary_highlight"] = "a phrase that is nowhere in the summary"
    html = document_html(data, key)
    assert html
    assert "a phrase that is nowhere" not in html, \
        "a stale highlight was rendered as if it were part of the summary"
