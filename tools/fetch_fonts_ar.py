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


#: Optical-size correction, per Arabic family.
#:
#: An Arabic face at `font-size: 13px` does not paint the same optical size as
#: its Latin partner, and the five faces here do not agree with EACH OTHER
#: either. Measured with canvas actualBoundingBox over five strings the
#: templates actually print, at font-size:100px:
#:
#:     Cairo                  103.6   100.1% of mean
#:     IBM Plex Sans Arabic   103.8   100.3%
#:     Tajawal                 90.6    87.6%   <- 12% smaller
#:     Amiri                  112.8   109.0%   <-  9% larger
#:     Noto Kufi Arabic       106.6   103.0%
#:
#: So the same Arabic résumé rendered at three different optical sizes
#: depending only on which of the 49 templates the user picked — Archivo
#: layouts small, Fraunces/Merriweather layouts large. `size-adjust` scales the
#: glyphs without touching the declared font-size, so no template changes and
#: the Latin side cannot move (unicode-range confines these faces to Arabic).
#:
#: Faces within 5% of the mean are left alone: a correction smaller than the
#: measurement's own spread across different words is noise, not a fix.
SIZE_ADJUST: dict[str, str] = {
    "Tajawal": "114.2%",
    "Amiri": "91.7%",
}


def _alias(block: str, latin_family: str, latin_weight: str, src: str,
           arabic_family: str = "") -> str:
    """One @font-face, renamed to the Latin family and restored to its weight,
    so the rule answers exactly the declaration a template already makes."""
    body = _rewrite(block.strip(), src)
    body = re.sub(r"font-family: '[^']+'", f"font-family: '{latin_family}'", body, count=1)
    body = re.sub(r"font-weight: [^;]+;", f"font-weight: {latin_weight};", body, count=1)
    adjust = SIZE_ADJUST.get(arabic_family)
    if adjust:
        body = f"{body.rstrip().rstrip(';')};\n  size-adjust: {adjust};"
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
                f"{note}\n@font-face {{{_alias(block, lat, weight, f'{WEB_PREFIX}/{name}', ar_fam)}}}")
            if name not in embedded:
                embedded[name] = base64.b64encode((OUT_DIR / name).read_bytes()).decode()
            src = f"data:font/woff2;base64,{embedded[name]}"
            inlined.append(f"{note}\n@font-face {{{_alias(block, lat, weight, src, ar_fam)}}}")

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


#: The shell's Arabic faces, under their REAL names.
#:
#: `fonts_ar.css` declares every Arabic face under a LATIN family name, which
#: is what lets 49 templates stay unedited — but it also means `font-family:
#: Cairo` resolves to nothing, because no such @font-face exists. The app shell
#: needs to name these faces directly to follow the font policy (FONTS.md), so
#: this emits a second, small stylesheet declaring the same files under the
#: names a human would write.
#:
#: Only the weights the shell actually asks for, so the file stays small and no
#: face is downloaded that nothing uses.
SHELL_FACES = {
    ("Tajawal", "800"),                 # hero, CTA — the policy's ExtraBold
    ("Tajawal", "700"),
    ("Cairo", "900"),                   # see VARIABLE_RANGE below
    ("IBM Plex Sans Arabic", "400"),    # body
    ("IBM Plex Sans Arabic", "500"),    # tables
    ("IBM Plex Sans Arabic", "600"),
    ("IBM Plex Sans Arabic", "700"),
}
AR_SHELL_CSS = "fonts_ar_shell.css"

#: Families whose vendored .woff2 is a VARIABLE font, and the range to declare.
#:
#: Google serves one file for Cairo's whole weight range — requesting 700 and
#: requesting 800 return the same URL, which is how this was found. Declaring
#: it `font-weight: 900` pins the variable axis to Black, so `font-weight: 700`
#: in the stylesheet rendered at 900 anyway and the headings came out far
#: heavier than the policy asks for. A RANGE lets the axis respond.
#:
#: Checked with fontTools: cairo has `wght 200-1000`; tajawal does not have an
#: fvar table at all and is correctly declared per static weight.
VARIABLE_RANGE = {
    "Cairo": "200 1000",
}


def shell_faces() -> int:
    """Write `fonts_ar_shell.css` from the already-generated aliases. No network.

    Derived from `fonts_ar.css` rather than refetched, for the same reason
    `--adjust-only` exists: the .woff2 files are already on disk and Google
    Fonts is not always reachable. Each alias rule carries a note recording
    which Arabic family and weight it came from, which is enough to re-declare
    it under its own name with the same src, unicode-range and size-adjust.
    """
    src_css = (OUT_DIR / AR_CSS)
    if not src_css.exists():
        print(f"FAIL {AR_CSS} missing — run without --shell-faces first")
        return 1

    pair = re.compile(
        r"/\* .+? <- (?P<fam>.+?) (?P<w>\d+) \*/\s*@font-face \{(?P<body>[^}]*)\}")
    seen: set[tuple[str, str]] = set()
    rules: list[str] = []
    for m in pair.finditer(src_css.read_text(encoding="utf-8")):
        key = (m.group("fam"), m.group("w"))
        if key not in SHELL_FACES or key in seen:
            continue
        seen.add(key)
        body = m.group("body")
        # Restore the family and weight this face actually IS, rather than the
        # Latin one it was aliased to.
        body = re.sub(r"font-family: '[^']+'", f"font-family: '{key[0]}'", body, count=1)
        weight = VARIABLE_RANGE.get(key[0], key[1])
        body = re.sub(r"font-weight: [^;]+;", f"font-weight: {weight};", body, count=1)
        note = (f"{key[0]} {weight}  (variable)" if key[0] in VARIABLE_RANGE
                else f"{key[0]} {key[1]}")
        rules.append(f"/* {note} */\n@font-face {{{body}}}")

    missing = sorted(SHELL_FACES - seen)
    header = (
        "/* GENERATED by tools/fetch_fonts_ar.py --shell-faces — do not edit.\n"
        "   The same Arabic files as fonts_ar.css, declared under their REAL\n"
        "   family names so the app shell can name them (see FONTS.md).\n"
        "   unicode-range is carried over unchanged, so Latin is untouched and\n"
        "   nothing here downloads for an English page.\n"
        f"   {len(rules)} faces. */\n")
    (OUT_DIR / AR_SHELL_CSS).write_text(header + "\n".join(rules) + "\n",
                                        encoding="utf-8")
    print(f"wrote {AR_SHELL_CSS}: {len(rules)} faces "
          f"({(OUT_DIR / AR_SHELL_CSS).stat().st_size / 1024:.0f} KB)")
    if missing:
        print(f"  NOT FOUND in {AR_CSS} (not aliased by any Latin family): {missing}")
        return 1
    return 0


def adjust_only() -> int:
    """Apply SIZE_ADJUST to the ALREADY-GENERATED css, with no network.

    `fetch()` needs fonts.googleapis.com, which is not always reachable — and
    it does not need to be, because the .woff2 files are already on disk and
    only the optical-size correction is changing. The note comment above each
    rule (`/* Archivo 400 <- Tajawal 400 */`) records which Arabic family it
    came from, so the right rules can be found without refetching anything.

    Idempotent: an existing `size-adjust` is replaced, not appended, so running
    this twice is the same as running it once.
    """
    changed = 0
    for fname in (AR_CSS, AR_INLINE_CSS):
        path = OUT_DIR / fname
        if not path.exists():
            print(f"FAIL {fname} missing — run without --adjust-only first")
            return 1
        css = path.read_text(encoding="utf-8")
        # Match the note TOGETHER WITH the rule it introduces. Splitting on
        # "@font-face {" instead leaves each rule holding the note belonging to
        # the NEXT one, which silently gave Anton/Noto Kufi the Tajawal
        # correction — a wrong number in the right shape.
        pair = re.compile(
            r"(/\* .+? <- (?P<fam>.+?) \d+ \*/\s*@font-face \{)(?P<body>[^}]*)\}")

        def _rewrite_rule(m: "re.Match[str]") -> str:
            nonlocal changed
            body = re.sub(r"\n?\s*size-adjust: [^;]+;", "", m.group("body"))
            adjust = SIZE_ADJUST.get(m.group("fam"))
            if adjust:
                body = f"{body.rstrip().rstrip(';')};\n  size-adjust: {adjust};"
                changed += 1
            return f"{m.group(1)}{body}}}"

        path.write_text(pair.sub(_rewrite_rule, css), encoding="utf-8")
    print(f"size-adjust applied to {changed} rules across 2 files")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        raise SystemExit(check())
    if "--adjust-only" in sys.argv:
        raise SystemExit(adjust_only())
    if "--shell-faces" in sys.argv:
        raise SystemExit(shell_faces())
    raise SystemExit(fetch())
