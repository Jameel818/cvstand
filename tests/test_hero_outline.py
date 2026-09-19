"""The outlined Arabic hero: correct, accessible, and still not a font.

WHAT THIS PROTECTS

    The hero is Thmanyah Serif Display converted to SVG paths at build time,
    because the licence forbids serving the font file and permits the design.
    Three things have to stay true, and none of them is self-evident from
    looking at the page:

    1. NO FONT IS SERVED. The moment someone "simplifies" this into a
       @font-face, the page looks identical and the licence is breached. That
       is the whole failure mode: invisible, and only a lawyer notices.

    2. THE TEXT IS STILL TEXT. Paths are geometry — a screen reader, a search
       engine and a translation tool all see nothing. The partial keeps the
       real string in an .sr-only span, and if that span and the outlines ever
       disagree the page lies to assistive technology while looking right.

    3. ENGLISH IS UNTOUCHED. The whole feature is behind `ui_lang == 'ar'`.

WHY THE STRINGS ARE COMPARED TO THE CATALOGUE

    The outlines are a BUILD ARTEFACT of three specific Arabic strings. Change
    the hero copy in labels.py and the SVG still shows the old words, silently,
    because nothing re-runs the build. So the partial's .sr-only text is
    asserted against what `ui_t` returns today — which is exactly the drift a
    human would never spot in a wall of path data.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.labels import ui_t

ROOT = Path(__file__).resolve().parent.parent
PARTIAL = ROOT / "app" / "templates" / "_hero_ar.html"

#: Every outlined partial and the msgids it was built from. Imported from the
#: generator so the two cannot describe different things — a test with its own
#: copy of the list passes happily after someone adds a fourth partial.
from tools.outline_text import OUTLINED  # noqa: E402

HERO_MSGIDS = tuple(t for t, _ in OUTLINED["_hero_ar.html"])


def _partial(name: str = "_hero_ar.html") -> str:
    return (ROOT / "app" / "templates" / name).read_text(encoding="utf-8")


def _sr_only_text(name: str = "_hero_ar.html") -> str:
    m = re.search(r'<span class="sr-only">(.*?)</span>', _partial(name), re.S)
    assert m, f"{name} has no .sr-only span — the real text is gone"
    return " ".join(m.group(1).split())


@pytest.mark.parametrize("name", sorted(OUTLINED))
def test_the_partial_exists(name):
    assert (ROOT / "app" / "templates" / name).exists(), (
        "run: venv/Scripts/python tools/outline_text.py --build-hero")


@pytest.mark.parametrize("name", sorted(OUTLINED))
def test_no_font_file_is_referenced(name):
    """The licence permits the DESIGN and forbids serving the FONT. An @font-face
    here would look identical on the page and breach it."""
    src = _partial(name)
    # The generator's own Jinja comment names the typeface; strip comments the
    # way Jinja does before rendering, then nothing should remain.
    code = re.sub(r"\{#.*?#\}", " ", src, flags=re.S).lower()
    for bad in ("@font-face", ".woff", ".otf", ".ttf", "thmanyah"):
        assert bad not in code, (
            f"{bad!r} appears in the rendered hero — it must ship geometry "
            "only, never a font reference")


@pytest.mark.parametrize("name", sorted(OUTLINED))
def test_the_real_text_survives_for_assistive_technology(name):
    sr = _sr_only_text(name)
    expected = " ".join(str(ui_t(t, "ar")) for t, _ in OUTLINED[name])
    assert sr == expected, (
        f"{name}'s .sr-only text no longer matches the label catalogue - the "
        "copy changed and the outlines were not rebuilt, so the page SHOWS one "
        "headline and TELLS screen readers another.\n"
        f"  partial:   {sr}\n"
        f"  catalogue: {expected}\n"
        "  fix: venv/Scripts/python tools/outline_text.py --build-hero")


def test_the_outlines_are_hidden_from_assistive_technology():
    """Both halves or neither: visible text that is also announced would make a
    screen reader read the headline twice."""
    src = _partial()
    svgs = re.findall(r"<svg\b[^>]*>", src)
    assert len(svgs) == len(HERO_MSGIDS), (
        f"expected {len(HERO_MSGIDS)} outlined runs, found {len(svgs)}")
    for tag in svgs:
        assert 'aria-hidden="true"' in tag, f"outline not hidden from AT: {tag[:80]}"


def test_the_accent_run_keeps_the_brand_colour():
    """`designed` is the coloured word in the headline. Outlining flattened the
    <span class="accent"> that used to carry it, so the fill has to."""
    assert "var(--brand)" in _partial(), (
        "no run uses var(--brand) — the accent word lost its colour when the "
        "markup was flattened into paths")


def test_english_does_not_include_the_partial():
    landing = (ROOT / "app" / "templates" / "landing.html").read_text(encoding="utf-8")
    assert "_hero_ar.html" in landing, "the partial is never included"
    block = landing[landing.index("_hero_ar.html") - 400:landing.index("_hero_ar.html")]
    assert "ui_lang == 'ar'" in block, (
        "the outlined hero is not behind an Arabic check — English would get it "
        "too, which is explicitly not what was asked for")


@pytest.mark.parametrize("name", sorted(OUTLINED))
def test_every_partial_is_behind_an_arabic_check(name):
    """An outlined partial rendered to an English reader would show Arabic
    headings on an English page — and because they are paths, nothing in the
    label gates would notice."""
    pages = list((ROOT / "app" / "templates").glob("*.html"))
    including = [p for p in pages if name in p.read_text(encoding="utf-8")
                 and not p.name.startswith("_")]
    assert including, f"{name} is generated but never included anywhere"
    for page in including:
        src = page.read_text(encoding="utf-8")
        before = src[max(0, src.index(name) - 500):src.index(name)]
        assert "ui_lang == 'ar'" in before, (
            f"{page.name} includes {name} without an Arabic check — English "
            "readers would get Arabic outlined headings")
