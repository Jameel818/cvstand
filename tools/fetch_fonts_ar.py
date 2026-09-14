"""Download Arabic glyph coverage and generate the self-hosted Arabic CSS.

    venv/Scripts/python tools/fetch_fonts_ar.py            # fetch + generate
    venv/Scripts/python tools/fetch_fonts_ar.py --check    # verify only, no network

Writes into app/static/fonts/:
    *.woff2              the Arabic font files (arabic subset only)
    fonts_ar.css         @font-face aliases pointing at /static/fonts/<file>.woff2
    fonts_ar_inline.css  the same rules with the fonts embedded as data: URIs

WHY THIS IS A SEPARATE TOOL, NOT A FLAG ON fetch_fonts.py
    Adding the Arabic families to that script's CSS_URL would mean re-running
    fetch(), which rebuilds fonts.css from whatever Google serves TODAY. Those
    Latin files may have been re-hinted or re-subset since they were vendored,
    so the rebuild could silently change how every existing English resume
    renders — the exact failure this project keeps having to hunt down (a wrong
    render that raises nothing). fetch_fonts.py is therefore never re-run to
    add Arabic. These are additional files beside its output, and this module
    only ever READS fonts.css.

THE ALIASING TRICK — why 49 templates need no edit
    Each Arabic @font-face is declared under the LATIN family's name, confined
    by unicode-range to Arabic codepoints:

        @font-face { font-family: 'Archivo';          <- the Latin family name
                     src: url(tajawal-700-...woff2);
                     unicode-range: U+0600-06FF, ...; }   <- Arabic only

    A browser resolves font-family per GLYPH. So `font-family: Archivo`, which
    is already written into all 49 templates, keeps taking Latin glyphs from
    real Archivo and starts taking Arabic glyphs from Tajawal. No template
    changes, and it cannot regress English: the unicode-range excludes every
    Latin codepoint, so no Latin glyph is even eligible to come from these
    files. `--check` asserts that property rather than trusting it.

PAIRING
    Chosen to preserve each template's typographic register, not merely to
    supply glyphs: geometric sans -> geometric Arabic, serif -> naskh serif,
    display -> Kufi display. Weight NUMBERS do not carry across scripts, so the
    override map exists too: Anton is nominally 400 but reads black, and
    pairing it to a 400 Arabic would collapse every Anton masthead in Arabic.
"""
from __future__ import annotations

import base64
import re
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_fonts import (  # noqa: E402  - path set above
    LICENCE_DIR_NAME,
    OUT_DIR,
    WEB_PREFIX,
    _blocks,
    _family,
    _fetch_ofl,
    _filename,
    _get,
    _rewrite,
    _url,
    _write_licences,
)

KEEP_SUBSETS = ("arabic",)
AR_CSS = "fonts_ar.css"
AR_INLINE_CSS = "fonts_ar_inline.css"

# Latin family -> (Arabic family, {latin weight: forced arabic weight})
PAIRINGS: dict[str, tuple[str, dict[str, str]]] = {
    "Poppins":        ("Cairo", {}),                         # geometric sans
    "Montserrat":     ("Cairo", {}),                         # geometric display
    "Archivo":        ("Tajawal", {}),                       # grotesque
    "Archivo Narrow": ("Tajawal", {}),                       # condensed grotesque
    "Anton":          ("Noto Kufi Arabic", {"400": "900"}),  # 400 here reads black
    "Fraunces":       ("Amiri", {}),                         # serif display -> naskh
    "Merriweather":   ("Amiri", {}),                         # serif text -> naskh
    "Inter":          ("IBM Plex Sans Arabic", {}),          # neutral UI sans
    "Open Sans":      ("IBM Plex Sans Arabic", {}),          # humanist sans
    "Source Sans 3":  ("IBM Plex Sans Arabic", {}),          # humanist sans
    # No Arabic monospace has this coverage; the Plex sibling keeps the family
    # relationship, and the mono templates use it for labels, not for columns.
    "IBM Plex Mono":  ("IBM Plex Sans Arabic", {}),
}

QUERY = {
    "Cairo": "Cairo:wght@400;500;600;700;800;900",
    "Tajawal": "Tajawal:wght@400;500;700;800;900",
    "Amiri": "Amiri:wght@400;700",
    "Noto Kufi Arabic": "Noto+Kufi+Arabic:wght@400;500;700;900",
    "IBM Plex Sans Arabic": "IBM+Plex+Sans+Arabic:wght@400;500;600;700",
}

# The Arabic block proper. An alias whose range dipped below this could win over
# a real Latin face; check() enforces the floor.
ARABIC_FLOOR = 0x0600


def _latin_family_weights() -> dict[str, set[str]]:
    """(family -> weights) actually declared in fonts.css.

    Derived from the stylesheet instead of hardcoded, so the Arabic alias set
    cannot drift out of step with the Latin set it shadows."""
    css = (OUT_DIR / "fonts.css").read_text(encoding="utf-8")
    out: dict[str, set[str]] = {}
    for block in re.findall(r"@font-face \{(.*?)\}", css, re.S):
        fam = _family(block)
        w = re.search(r"font-weight: ([^;]+);", block)
        out.setdefault(fam, set()).add(w.group(1).strip() if w else "400")
    return out


def _nearest(weight: str, available: list[str]) -> str:
    """Closest available weight; ties resolve heavier — a heading must not thin."""
    target = int(weight.split()[0])
    return min(available, key=lambda w: (abs(int(w) - target), -int(w)))


def _alias(block: str, latin_family: str, latin_weight: str, src: str) -> str:
    """One @font-face, renamed to the Latin family and restored to its weight,
    so the rule answers exactly the declaration a template already makes."""
    body = _rewrite(block.strip(), src)
    body = re.sub(r"font-family: '[^']+'", f"font-family: '{latin_family}'", body, count=1)
    body = re.sub(r"font-weight: [^;]+;", f"font-weight: {latin_weight};", body, count=1)
    return body


def fetch() -> int:
    if not (OUT_DIR / "fonts.css").exists():
        print("FAIL fonts.css missing — run tools/fetch_fonts.py first")
        return 1

    socket.setdefaulttimeout(30)
    latin = _latin_family_weights()
    needed = sorted({ar for lat, (ar, _o) in PAIRINGS.items() if lat in latin})
    print(f"fetching {len(needed)} Arabic families ...")

    pool: dict[str, dict[str, tuple[str, str]]] = {}
    for fam in needed:
        css = _get(f"https://fonts.googleapis.com/css2?family={QUERY[fam]}&display=swap").decode()
        blocks = [(s, b) for s, b in _blocks(css) if s in KEEP_SUBSETS]
        if not blocks:
            print(f"FAIL no arabic subset returned for {fam}")
            return 1
        entry: dict[str, tuple[str, str]] = {}
        for _subset, block in blocks:
            w = re.search(r"font-weight: ([^;]+);", block)
            entry[(w.group(1).strip() if w else "400")] = (_url(block), block)
        pool[fam] = entry
        print(f"  {fam}: weights {sorted(entry, key=int)}")

    # Download each distinct file once, though several Latin families and
    # weights may alias onto it.
    jobs: dict[str, str] = {}
    for entry in pool.values():
        for remote, block in entry.values():
            jobs[remote] = _filename(block, remote)

    def grab(item):
        remote, name = item
        data = _get(remote)
        (OUT_DIR / name).write_bytes(data)
        return name, len(data)

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(grab, jobs.items()))
    print(f"  {len(results)} files, {sum(n for _, n in results) / 1024:.0f} KB")

    linked: list[str] = []
    inlined: list[str] = []
    embedded: dict[str, str] = {}
    for lat in sorted(PAIRINGS):
        if lat not in latin:
            continue
        ar_fam, overrides = PAIRINGS[lat]
        entry = pool[ar_fam]
        avail = sorted(entry, key=int)
        for weight in sorted(latin[lat], key=lambda w: int(w.split()[0])):
            picked = overrides.get(weight) or _nearest(weight, avail)
            remote, block = entry[picked]
            name = jobs[remote]
            note = f"/* {lat} {weight} <- {ar_fam} {picked} */"
            linked.append(
                f"{note}\n@font-face {{{_alias(block, lat, weight, f'{WEB_PREFIX}/{name}')}}}")
            if name not in embedded:
                embedded[name] = base64.b64encode((OUT_DIR / name).read_bytes()).decode()
            src = f"data:font/woff2;base64,{embedded[name]}"
            inlined.append(f"{note}\n@font-face {{{_alias(block, lat, weight, src)}}}")

    header = (
        "/* GENERATED by tools/fetch_fonts_ar.py — do not edit.\n"
        "   Arabic glyph coverage declared under the LATIN family names, so the\n"
        "   templates need no change. unicode-range confines these faces to\n"
        "   Arabic codepoints, so Latin rendering cannot be affected.\n"
        f"   {len(linked)} alias rules over {len(jobs)} files. */\n")
    (OUT_DIR / AR_CSS).write_text(header + "\n".join(linked) + "\n", encoding="utf-8")
    (OUT_DIR / AR_INLINE_CSS).write_text(header + "\n".join(inlined) + "\n", encoding="utf-8")
    print(f"  wrote {AR_CSS} ({(OUT_DIR / AR_CSS).stat().st_size / 1024:.0f} KB)")
    print(f"  wrote {AR_INLINE_CSS} ({(OUT_DIR / AR_INLINE_CSS).stat().st_size / 1024:.0f} KB)")

    # OFL 1.1 clause 2 — the licence text ships with the fonts, Arabic included.
    latin_fams = sorted(set(re.findall(
        r"font-family: '([^']+)'", (OUT_DIR / "fonts.css").read_text(encoding="utf-8"))))
    failed = _fetch_ofl(needed)
    _write_licences(sorted(set(latin_fams) | set(needed)))
    if failed:
        print(f"FAIL could not vendor OFL.txt for: {', '.join(failed)}")
        return 1
    return check()


def check() -> int:
    path = OUT_DIR / AR_CSS
    if not path.exists():
        print(f"FAIL {AR_CSS} missing — run tools/fetch_fonts_ar.py")
        return 1
    css = path.read_text(encoding="utf-8")

    refs = re.findall(rf"url\({re.escape(WEB_PREFIX)}/([^)]+)\)", css)
    missing = [r for r in refs if not (OUT_DIR / r).exists()]
    if missing:
        print(f"FAIL {len(missing)} Arabic font file(s) missing: {missing[:5]}")
        return 1

    # THE SAFETY PROPERTY, asserted rather than assumed. If any alias covered a
    # Latin codepoint it could outrank the real Latin face and change English
    # rendering — the one way this design could bite.
    for rng in re.findall(r"unicode-range: ([^;]+);", css):
        for part in rng.split(","):
            start = part.strip().lstrip("Uu+").split("-")[0]
            if int(start, 16) < ARABIC_FLOOR:
                print(f"FAIL an Arabic alias claims a non-Arabic codepoint: {part.strip()}")
                return 1

    inline = OUT_DIR / AR_INLINE_CSS
    if not inline.exists():
        print(f"FAIL {AR_INLINE_CSS} missing")
        return 1
    inline_css = inline.read_text(encoding="utf-8")
    fams_link = set(re.findall(r"font-family: '([^']+)'", css))
    fams_inline = set(re.findall(r"font-family: '([^']+)'", inline_css))
    if fams_link != fams_inline:
        print(f"FAIL Arabic family mismatch between linked and inline: {fams_link ^ fams_inline}")
        return 1
    if inline_css.count("data:font/woff2;base64,") != css.count("@font-face"):
        print("FAIL inline copy does not embed one payload per alias rule")
        return 1

    sources = sorted({m for m in re.findall(r"<- ([A-Za-z0-9 ]+) \d+ \*/", css)})
    missing_ofl = [f for f in sources
                   if not (OUT_DIR / LICENCE_DIR_NAME / f"{f.replace(' ', '-')}-OFL.txt").exists()]
    if missing_ofl:
        print(f"FAIL no vendored OFL.txt for: {', '.join(missing_ofl)}")
        return 1

    print(f"OK  {css.count('@font-face')} Arabic alias rules over {len(set(refs))} files, "
          f"{len(fams_link)} aliased families, {len(sources)} Arabic sources, "
          f"no alias claims a codepoint below U+{ARABIC_FLOOR:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(check() if "--check" in sys.argv else fetch())
