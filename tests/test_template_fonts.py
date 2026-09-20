"""Every family the 49 templates name must be vendored, licensed and aliased.

WHAT THIS CATCHES

    `modern/t10.j2` declared `font-family:'DM Sans',sans-serif` on its root.
    DM Sans is not in `app/static/fonts/fonts.css`, not on the FONTS.md
    allowlist, and has no entry in `fetch_fonts_ar.py::PAIRINGS`. The result
    was invisible three times over:

      - in Latin it fell back to the browser's default sans, so the template
        rendered in Arial-or-whatever while its locked spec said otherwise;
      - in Arabic it fell back to the OS, because an alias only exists for
        families that are paired -- this was the one template of 49 the
        Arabic font work never reached;
      - the pixel goldens were captured WITH the fallback in place, so the
        baseline agreed with the bug and would have kept agreeing forever.

    Nothing raised. The page looked like a page. That is the shape of every
    font defect this project has found.

WHY IT READS THE STYLESHEET RATHER THAN A HARDCODED LIST

    A list here would be a second copy of the allowlist, free to drift from
    the one that ships. `fonts.css` is what the browser is actually served, so
    asking it "is this family real?" is asking the only question that matters.

WHY COMMENTS ARE STRIPPED FIRST

    This project has already shipped a gate that fired on the COMMENT
    explaining why a font was banned. A check whose only failure is the note
    saying "we do not do this" teaches people to delete the note. Jinja
    comments are removed the way Jinja removes them, before anything is read.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates" / "resumes"
FONTS_CSS = ROOT / "app" / "static" / "fonts" / "fonts.css"

#: Generic CSS keywords are not families and are always legitimate as the
#: last resort in a stack.
GENERIC = {"sans-serif", "serif", "monospace", "cursive", "fantasy",
           "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "inherit"}

#: Named exemptions: (template stem, family). An entry here is a KNOWN defect
#: that has been looked at and deliberately left, not a family that is fine.
#:
#: modern/t10 declares 'DM Sans', which is vendored nowhere -- so it renders in
#: the browser's default sans in Latin (which differs between Windows and
#: macOS) and in the OS default in Arabic, making it the one template of 49
#: the Arabic font work does not reach. Correcting it moves that template's
#: ENGLISH pixels, and the standing instruction is that the Arabic font policy
#: must not alter English CV templates. There is no Arabic-only fix: the alias
#: generator only emits rules for families present in fonts.css, so a family
#: absent there cannot be given Arabic coverage without also making it render
#: in English.
#:
#: The exemption is a LIST rather than a deleted test on purpose. The other 48
#: templates stay guarded, and this one stays visible -- a gate quietly dropped
#: is a gate nobody remembers was ever there.
EXEMPT: set[tuple[str, str]] = {
    ("t10", "DM Sans"),
}


def _vendored() -> set[str]:
    css = FONTS_CSS.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"font-family:\s*'([^']+)'", css)}


def _template_files() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.j2"))


def _stacks(path: Path) -> list[list[str]]:
    """Every font-family stack in the file, comments stripped, split on commas."""
    src = re.sub(r"\{#.*?#\}", " ", path.read_text(encoding="utf-8"), flags=re.S)
    out = []
    for decl in re.findall(r"font-family\s*:\s*([^;\"']*(?:'[^']*'[^;\"]*)*)", src):
        parts = [x.strip().strip("'\"").strip() for x in decl.split(",")]
        parts = [x for x in parts if x and not x.startswith("{")]
        if parts:
            out.append(parts)
    return out


def _primaries(path: Path) -> set[str]:
    """The family that actually renders: the first one in each stack."""
    return {s[0] for s in _stacks(path) if s[0] not in GENERIC}


def test_there_are_49_templates_to_check():
    """A guard on the guard: if the glob breaks, every test below passes on an
    empty set and reports nothing while checking nothing."""
    keys = [p for p in _template_files() if not p.name.startswith("_")]
    assert len(keys) == 49, f"expected 49 templates, globbed {len(keys)}"


def test_the_extractor_finds_the_families_that_are_there():
    """A guard on the extractor. If the regex stops matching, every test below
    checks an empty set and passes -- which is how a font gate reports "all
    clear" on a template it cannot read."""
    fams = _primaries(TEMPLATES / "modern" / "t2.j2")
    assert "Archivo" in fams, fams
    stacks = _stacks(TEMPLATES / "modern" / "t22.j2")
    assert ["Archivo", "Helvetica", "sans-serif"] in stacks, (
        "the extractor no longer splits a multi-family stack")


@pytest.mark.parametrize("path", _template_files(), ids=lambda p: p.stem)
def test_every_primary_family_is_vendored(path):
    """The FIRST family in a stack is the one that renders. Later entries are
    fallbacks for a machine that lacks it, and naming a system font there is
    fine -- `Archivo, Helvetica, sans-serif` renders Archivo everywhere this
    app serves it."""
    vendored = _vendored()
    for fam in sorted(_primaries(path)):
        if (path.stem, fam) in EXEMPT:
            continue
        assert fam in vendored, (
            f"{path.relative_to(ROOT)} leads a font stack with {fam!r}, which "
            f"is not in fonts.css. It will silently fall back to a system font "
            f"in Latin and to the OS default in Arabic, and the golden "
            f"baseline will record the fallback as correct.")


@pytest.mark.parametrize("path", _template_files(), ids=lambda p: p.stem)
def test_every_primary_family_has_an_arabic_alias(path):
    """A family with no pairing has no Arabic coverage.

    The aliases in fonts_ar.css are what give the 49 templates Arabic at all:
    each Arabic face is declared under a LATIN family name, confined by
    unicode-range. A family that is not paired therefore renders Arabic in
    whatever the reader's OS supplies -- the exact failure the Arabic font
    work was meant to end, surviving in one template because nobody had
    checked the list against the templates."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from fetch_fonts_ar import PAIRINGS

    for fam in sorted(_primaries(path)):
        if (path.stem, fam) in EXEMPT:
            continue
        assert fam in PAIRINGS, (
            f"{path.relative_to(ROOT)} leads a font stack with {fam!r}, which "
            f"has no entry in fetch_fonts_ar.py::PAIRINGS, so Arabic text in "
            f"this template falls back to the operating system.")


#: Naming a system font as a FALLBACK is not redistributing it and engages no
#: licence -- FONTS.md makes the same argument for the Word masters. The list
#: is closed so that an unvendored webfont cannot arrive disguised as one.
SYSTEM_FALLBACKS = {"Helvetica", "Arial", "Georgia", "Times New Roman",
                    "Courier", "Courier New", "Segoe UI", "Roboto",
                    "-apple-system", "BlinkMacSystemFont"}


@pytest.mark.parametrize("path", _template_files(), ids=lambda p: p.stem)
def test_fallbacks_are_generic_or_system_families(path):
    for stack in _stacks(path):
        for fam in stack[1:]:
            assert fam in GENERIC or fam in SYSTEM_FALLBACKS or fam in _vendored(), (
                f"{path.relative_to(ROOT)} falls back to {fam!r}, which is "
                f"neither vendored, generic, nor a system family. If it is "
                f"meant to render it must be vendored and licensed; if it is "
                f"not, it is dead weight in the stack.")


def test_every_exemption_is_still_real():
    """An exemption that no longer applies is a lie the next reader inherits.

    If someone fixes t10, this fails and the entry has to go -- which is the
    only way a stale carve-out gets noticed. It is the same reason the
    exemption is a list and not a deleted assertion."""
    vendored = _vendored()
    for stem, fam in sorted(EXEMPT):
        matches = [p for p in _template_files() if p.stem == stem
                   and fam in _primaries(p)]
        assert matches, (
            f"EXEMPT lists ({stem}, {fam}) but no template declares it any "
            f"more - the defect was fixed and the exemption should be removed.")
        assert fam not in vendored, (
            f"EXEMPT lists ({stem}, {fam}) but {fam} IS vendored now - the "
            f"exemption is stale and the guard should apply.")
