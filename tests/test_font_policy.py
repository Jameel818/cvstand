"""The font policy, as a gate (`FONTS.md`).

WHAT THIS PROTECTS

    Every typeface shipped here has to be free for commercial use inside a
    product that is SOLD, and its licence text has to travel with the files.
    That is stricter than "free to download", and the gap is where the risk
    lives: `Fonts/Nice fonts/` in the project root holds fourteen commercial
    retail faces with zero licence files between them, and Thmanyah is free for
    commercial use while explicitly prohibiting the one delivery method a web
    app would use.

    Neither of those is caught by reading a font's landing page. Both are
    caught by asking two questions of the files actually on disk: is this
    family on the allowlist, and is its licence here.

WHY A TEST AND NOT A NOTE IN A README

    This session nearly shipped Thmanyah, having read its bundled PDF as
    permissive. A policy that lives only in prose is re-litigated by whoever
    reads it next, under time pressure, from a summary. A policy that fails the
    suite is not.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "app" / "static" / "fonts"
LICENSE_DIR = FONT_DIR / "licenses"

#: Every family that may be served. Adding one means adding its licence text
#: too — see FONTS.md, "Adding a family".
ALLOWED = {
    # Arabic
    "IBM Plex Sans Arabic", "Tajawal", "Cairo", "Amiri", "Noto Kufi Arabic",
    # allowed by the policy as the Amiri alternative; not currently used
    "Noto Naskh Arabic",
    # Latin — the families the 49 templates declare
    "Anton", "Archivo", "Archivo Narrow", "Fraunces", "IBM Plex Mono",
    "Inter", "Merriweather", "Montserrat", "Open Sans", "Poppins",
    "Source Sans 3",
    # Typography controls (app/typography/registry.py) — the families a user
    # may choose, beyond those already above. FONTS.md, "Typography controls".
    "Anton SC", "Archivo Black", "Bebas Neue", "Raleway", "Playfair Display",
    "Source Serif 4", "Work Sans", "Lora",
    "Almarai", "Alexandria", "Mada", "Readex Pro", "Noto Sans Arabic",
    "El Messiri", "Markazi Text", "Scheherazade New", "Lateef", "Aref Ruqaa",
    "Lalezar", "Jomhuria", "Rakkas", "Marhey", "Baloo Bhaijaan 2", "Lemonada",
}

#: Named so a grep finds them. All are licensed per-seat or per-domain and are
#: exactly the ones commonly recommended for Arabic work.
PAID = ("29LT Bukra", "29LT Zarid", "GE SS", "DIN Next LT Arabic", "FF Shamel")

#: Free for commercial use, and still unshippable: the licence forbids serving
#: the font file itself. See FONTS.md for the quoted terms.
LICENCE_BLOCKED = ("thmanyah", "Thmanyah")


#: Every font file format that can be served or embedded.
FONT_SUFFIXES = (".woff2", ".woff", ".ttf", ".otf")


def _families_on_disk() -> set[str]:
    """Families inferred from every font file under app/static/fonts/,
    subfolders included.

    `tools/fetch_fonts.py` names them `<family-slug>-<weight>-normal-<hash>`
    and `tools/build_fonts.py` `ttf/<family-slug>-<weight>.ttf` and
    `web/<family-slug>-<weight>.woff2`, so the slug is everything before the
    weight. Read from the FILES rather than from LICENSES.md, which is
    generated from the same fetch and would agree with a wrong answer.

    A font file that matches neither pattern is returned under its own name,
    so it fails the allowlist instead of escaping the check.
    """
    out: set[str] = set()
    for f in FONT_DIR.rglob("*"):
        if f.suffix.lower() not in FONT_SUFFIXES:
            continue
        m = re.match(r"^(.*?)-\d{3}(?:-|\.)", f.name)
        out.add(m.group(1) if m else f.name)
    return out


def _slug(family: str) -> str:
    return family.lower().replace(" ", "-")


def test_every_shipped_family_is_on_the_allowlist():
    allowed_slugs = {_slug(f) for f in ALLOWED}
    stray = sorted(f for f in _families_on_disk() if f not in allowed_slugs)
    assert not stray, (
        "font files are served for families the policy does not allow - "
        "add them to FONTS.md with a licence, or delete them:\n  "
        + "\n  ".join(stray)
    )


def test_every_shipped_family_ships_its_licence():
    """OFL permits redistribution *provided the notice travels with the files*.
    A family bundled without its licence text is a licence breach even though
    the family itself is free."""
    licences = {p.stem.replace("-OFL", "").lower()
                for p in LICENSE_DIR.glob("*.txt")}
    missing = sorted(
        fam for fam in _families_on_disk()
        if fam.replace("-", "") not in {l.replace("-", "") for l in licences}
    )
    assert not missing, (
        "families are shipped with no licence file in "
        f"app/static/fonts/licenses/:\n  " + "\n  ".join(missing)
    )


def _sources() -> list[Path]:
    return [
        *ROOT.joinpath("app").rglob("*.py"),
        *ROOT.joinpath("app", "templates").rglob("*.j2"),
        *ROOT.joinpath("app", "templates").rglob("*.html"),
        *ROOT.joinpath("app", "static", "css").rglob("*.css"),
        *ROOT.joinpath("app", "static", "js").rglob("*.js"),
    ]


#: Comment syntaxes across the file types scanned. Stripped before searching,
#: because a gate that cannot tell a USE from an EXPLANATION fires on the
#: comment documenting why a font is banned — which it did, on the FONTS.md
#: rationale written into app.css. A check whose only failure is the note
#: saying "we do not do this" teaches people to delete the note.
_COMMENTS = re.compile(
    r"/\*.*?\*/"        # css, js block
    r"|//[^\n]*"        # js line
    r"|\{#.*?#\}"       # jinja
    r"|<!--.*?-->"      # html
    r"|\"\"\".*?\"\"\"" # python docstring
    r"|#[^\n]*",        # python line
    re.S,
)


def _code(path: Path) -> str:
    """File contents with comments removed, lowercased for searching."""
    return _COMMENTS.sub(" ", path.read_text(encoding="utf-8", errors="replace")).lower()


@pytest.mark.parametrize("family", PAID)
def test_no_paid_family_is_referenced(family):
    hits = [p.relative_to(ROOT).as_posix() for p in _sources()
            if family.lower() in _code(p)]
    assert not hits, (
        f"{family!r} is licensed per-seat or per-domain and must not be "
        f"referenced: {hits}")


def test_thmanyah_is_not_served():
    """Free for commercial use, and still not shippable.

    Its licence permits embedding "only as part of a compiled, packaged, or
    obfuscated product" and prohibits making the font available in any manner
    allowing end users to extract or download it "independently as font files,
    including through web embedding". A @font-face serving a .woff2 is that
    case, and it applies to the app shell exactly as much as to the résumé
    templates: the prohibition is about the FILE being fetchable, not about
    what text it renders.

    If a single-domain grant is obtained (see
    outreach/thmanyah-webfont-licence.md), delete this test and add the family
    to ALLOWED with a pointer to the written grant.
    """
    served = [p.name for p in FONT_DIR.rglob("*")
              if p.is_file() and any(b in p.name for b in LICENCE_BLOCKED)]
    assert not served, (
        "Thmanyah font files are being served from app/static/fonts - the "
        f"licence forbids exactly this: {served}")

    refs = [p.relative_to(ROOT).as_posix() for p in _sources()
            if "thmanyah" in _code(p)]
    assert not refs, (
        f"Thmanyah is referenced in code that renders to the browser: {refs}")


def test_the_allowlist_is_not_vacuous():
    """A guard on the guards. If the filename pattern ever changes,
    `_families_on_disk()` returns an empty set and every test above passes by
    having nothing to check - the exact shape of failure this repo has shipped
    twice (a pixel gate that never ran, and its baselines gitignored)."""
    found = _families_on_disk()
    assert len(found) >= 35, (
        f"only {len(found)} families detected on disk ({sorted(found)}) - the "
        "filename pattern in _families_on_disk() has probably drifted, and "
        "every other assertion in this file is passing vacuously")
