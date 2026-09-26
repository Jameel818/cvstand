"""Download the template font families and generate self-hosted CSS.

    venv/Scripts/python tools/fetch_fonts.py             # fetch + generate
    venv/Scripts/python tools/fetch_fonts.py --licences  # re-vendor OFL.txt only
    venv/Scripts/python tools/fetch_fonts.py --check     # verify only, no network
    venv/Scripts/python tools/fetch_fonts.py --inline    # rebuild fonts_inline.css only, no network

Writes into app/static/fonts/:
    *.woff2           the font files (latin + latin-ext subsets)
    fonts.css         @font-face rules pointing at /static/fonts/<file>.woff2
    fonts_inline.css  the same rules with the fonts embedded as data: URIs
    LICENSES.md       licence + upstream source for every family

WHY TWO STYLESHEETS
  The on-screen preview is served over HTTP (`/preview`, and an iframe `srcdoc`
  that inherits the page's base URL), so a normal <link> resolves and the
  browser caches the files — cheap on every keystroke.

  PDF export cannot use that. `pdf.py` renders via Playwright's
  `page.set_content()`, whose base URL is `about:blank`; a "/static/..." URL has
  nothing to resolve against and fails SILENTLY — Chromium just substitutes a
  fallback face, no error, no log line. So the PDF document embeds the fonts
  directly (fonts_inline.css). It costs ~4.3 MB per export, but an export is a
  one-off user action, and it cannot fail to find a font because there is
  nothing to find: the bytes are already in the document.

ONE INLINE RULE PER LINKED RULE
  fonts_inline.css is fonts.css with each url() replaced by that file's bytes -
  rule for rule, nothing merged. For a variable family Google emits one rule
  per requested weight, ALL pointing at the same file (Montserrat 400..900 is
  one .woff2 per subset). An earlier version merged the rules sharing a file
  to embed each payload once (1.4 MB): that kept only the FIRST rule's
  `font-weight: 400`, so the PDF drew Inter, Montserrat, Archivo, Archivo
  Narrow, Source Sans 3, Open Sans, Merriweather and Fraunces at weight 400
  everywhere while the preview drew their real weights. A weight RANGE
  (`font-weight: 400 900`) would be smaller but still not the preview: for a
  weight a family does not declare (Open Sans 500/800, Archivo 300, Source
  Sans 3 800 - four templates use one), the preview's discrete rules match
  the NEAREST declared weight and a range draws the exact one. Parity with the
  preview is the contract, so the payload repeats.

SUBSETS
  latin + latin-ext only. The `unicode-range` descriptors are kept exactly as
  Google emits them, so a browser downloads only the subset a given résumé
  needs — latin-ext therefore costs nothing at render time while covering
  accented names (José, Müller, Łukasz).

The @font-face blocks are copied VERBATIM from Google's stylesheet with only
the url() rewritten. Hand-writing them would break the variable-font weight
ranges that Fraunces (opsz,wght), Inter and Archivo depend on.
"""
from __future__ import annotations

import base64
import re
import socket
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "app" / "static" / "fonts"
WEB_PREFIX = "/static/fonts"
KEEP_SUBSETS = ("latin", "latin-ext")

# Chrome UA — Google serves woff2 only to browsers that advertise support.
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")}

CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800"
    "&family=Fraunces:opsz,wght@9..144,500;9..144,700"
    "&family=Montserrat:wght@400;500;600;700;800;900&family=Anton"
    "&family=Archivo+Narrow:wght@400;500;600;700"
    "&family=Archivo:wght@400;600;700;800;900"
    "&family=Source+Sans+3:wght@400;600;700;900"
    "&family=Merriweather:wght@400;700&family=Open+Sans:wght@400;600;700"
    "&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
)

# Every family here is under the SIL Open Font License 1.1, which permits
# redistribution provided the licence travels with the fonts.
LICENCE = "SIL Open Font License 1.1"
UPSTREAM = "https://fonts.google.com/specimen/{}"

# OFL 1.1 clause 2: the licence text must travel WITH the fonts — a link is not
# enough. So the full OFL.txt for each family is vendored next to the .woff2s,
# straight from the family's directory in google/fonts.
LICENCE_DIR_NAME = "licenses"
OFL_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{}/OFL.txt"


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()


def _blocks(css: str):
    """(subset, block-body) for each @font-face, in source order."""
    return re.findall(r"/\* (\S+) \*/\s*@font-face \{(.*?)\}", css, re.S)


def _family(block: str) -> str:
    return re.search(r"font-family: '([^']+)'", block).group(1)


def _url(block: str) -> str:
    return re.search(r"url\((\S+?)\)", block).group(1)


def _filename(block: str, remote: str) -> str:
    """Stable local name: family-weight-style-hash.woff2."""
    fam = _family(block).lower().replace(" ", "-")
    weight = re.search(r"font-weight: ([^;]+);", block)
    weight = (weight.group(1).strip().replace(" ", "-") if weight else "400")
    style = re.search(r"font-style: (\w+);", block)
    style = style.group(1) if style else "normal"
    return f"{fam}-{weight}-{style}-{remote.rsplit('/', 1)[-1]}"


def fetch() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    socket.setdefaulttimeout(30)
    print(f"fetching stylesheet ...")
    css = _get(CSS_URL).decode()

    wanted = [(s, b) for s, b in _blocks(css) if s in KEEP_SUBSETS]
    if not wanted:
        print("no @font-face blocks matched — Google may have changed the format")
        return 1

    jobs = {}  # remote url -> local filename
    for _subset, block in wanted:
        jobs[_url(block)] = _filename(block, _url(block))

    print(f"downloading {len(jobs)} .woff2 ({len(wanted)} @font-face blocks) ...")
    def grab(item):
        remote, name = item
        data = _get(remote)
        (OUT_DIR / name).write_bytes(data)
        return name, len(data)

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(grab, jobs.items()))
    total = sum(n for _, n in results)
    print(f"  {len(results)} files, {total / 1024:.0f} KB")

    linked = []
    for subset, block in wanted:
        name = jobs[_url(block)]
        linked.append(
            f"/* {subset} */\n@font-face "
            f"{{{_rewrite(block.strip(), f'{WEB_PREFIX}/{name}')}}}"
        )

    header = (f"/* GENERATED by tools/fetch_fonts.py — do not edit.\n"
              f"   {len(jobs)} files, subsets: {', '.join(KEEP_SUBSETS)}.\n"
              f"   Every family is {LICENCE}; see LICENSES.md. */\n")
    (OUT_DIR / "fonts.css").write_text(header + "\n".join(linked) + "\n", encoding="utf-8")
    print(f"  wrote fonts.css ({(OUT_DIR / 'fonts.css').stat().st_size / 1024:.0f} KB)")
    write_inline()

    families = sorted({_family(b) for _s, b in wanted})
    _fetch_ofl(families)
    _write_licences(families)
    return check()


def inline_css(css: str) -> str:
    """fonts.css with every url(/static/fonts/<file>) replaced by the file's
    bytes as a data: URI. Nothing else changes, so the inline sheet has
    exactly the linked sheet's rules - see ONE INLINE RULE PER LINKED RULE."""
    payloads: dict[str, str] = {}

    def embed(m: re.Match) -> str:
        name = m.group(1)
        if name not in payloads:
            payloads[name] = base64.b64encode((OUT_DIR / name).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{payloads[name]})"

    return re.sub(rf"url\({re.escape(WEB_PREFIX)}/([^)]+)\)", embed, css)


def write_inline() -> int:
    """Regenerate fonts_inline.css from fonts.css and the files on disk -
    no network, so the bytes are the ones the preview already serves."""
    css_path = OUT_DIR / "fonts.css"
    if not css_path.exists():
        print("FAIL fonts.css missing - run without a flag to fetch everything")
        return 1
    out = OUT_DIR / "fonts_inline.css"
    out.write_text(inline_css(css_path.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"  wrote fonts_inline.css ({out.stat().st_size / 1024:.0f} KB)")
    return 0


def _rewrite(block: str, new_url: str) -> str:
    return re.sub(r"url\(\S+?\)", f"url({new_url})", block, count=1)


def _ofl_slug(family: str) -> str:
    """google/fonts directory name: lowercase, no spaces (Source Sans 3 ->
    sourcesans3, IBM Plex Mono -> ibmplexmono)."""
    return family.lower().replace(" ", "")


def _fetch_ofl(families: list[str]) -> list[str]:
    """Vendor each family's OFL.txt. Returns the families that could not be
    fetched, so a network hiccup is reported rather than silently shipping an
    incomplete licence set."""
    out = OUT_DIR / LICENCE_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for fam in families:
        dest = out / f"{fam.replace(' ', '-')}-OFL.txt"
        try:
            text = _get(OFL_URL.format(_ofl_slug(fam)))
        except Exception as exc:
            print(f"  FAIL {fam}: {exc}")
            failed.append(fam)
            continue
        dest.write_bytes(text)
    print(f"  wrote {len(families) - len(failed)}/{len(families)} OFL.txt files "
          f"to {LICENCE_DIR_NAME}/")
    return failed


def _write_licences(families: list[str]):
    lines = [
        "# Font licences",
        "",
        "These fonts are redistributed with this project. Every family below is",
        f"licensed under the **{LICENCE}** (OFL), which permits bundling and",
        "redistribution provided this notice travels with the files.",
        "",
        "Generated by `tools/fetch_fonts.py`; subsets: " + ", ".join(KEEP_SUBSETS) + ".",
        "",
        "| Family | Licence | Licence text | Source |",
        "|---|---|---|---|",
    ]
    for fam in families:
        rel = f"{LICENCE_DIR_NAME}/{fam.replace(' ', '-')}-OFL.txt"
        lines.append(
            f"| {fam} | {LICENCE} | [`{rel}`]({rel}) | "
            f"{UPSTREAM.format(fam.replace(' ', '+'))} |")
    lines += [
        "",
        "## Full licence text",
        "",
        f"Each family's complete OFL 1.1 text is vendored in `{LICENCE_DIR_NAME}/`,",
        "fetched from that family's directory in google/fonts. OFL 1.1 clause 2",
        "requires the licence to travel with the font files, so those `.txt`",
        "files must ship with any public copy of this project — a link is not",
        "sufficient. `tools/fetch_fonts.py --check` fails if one is missing.",
    ]
    (OUT_DIR / "LICENSES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote LICENSES.md ({len(families)} families)")


def check() -> int:
    """Every url() in fonts.css must resolve to a file that exists on disk."""
    css_path = OUT_DIR / "fonts.css"
    if not css_path.exists():
        print("FAIL fonts.css missing — run without --check to fetch")
        return 1
    css = css_path.read_text(encoding="utf-8")
    refs = re.findall(rf"url\({re.escape(WEB_PREFIX)}/([^)]+)\)", css)
    missing = [r for r in refs if not (OUT_DIR / r).exists()]
    if missing:
        print(f"FAIL {len(missing)} referenced font file(s) missing: {missing[:5]}")
        return 1
    inline = OUT_DIR / "fonts_inline.css"
    if not inline.exists():
        print("FAIL fonts_inline.css missing")
        return 1
    inline_text = inline.read_text(encoding="utf-8")
    # Rule for rule: the PDF must draw what the preview draws. Comparing with
    # a fresh inline_css() also proves every payload is the file's current
    # bytes, not a stale copy of an older download.
    if inline_text != inline_css(css):
        print("FAIL fonts_inline.css is not fonts.css with the files embedded "
              "rule for rule - run tools/fetch_fonts.py --inline")
        return 1
    n_files = len(set(refs))
    fams_link = set(re.findall(r"font-family: '([^']+)'", css))
    # OFL 1.1 clause 2 — the licence text ships with the fonts.
    missing_ofl = [f for f in sorted(fams_link)
                   if not (OUT_DIR / LICENCE_DIR_NAME / f"{f.replace(' ', '-')}-OFL.txt").exists()]
    if missing_ofl:
        print(f"FAIL no vendored OFL.txt for: {', '.join(missing_ofl)} — "
              f"run tools/fetch_fonts.py --licences")
        return 1
    print(f"OK  {len(refs)} @font-face rules over {n_files} files, "
          f"{len(fams_link)} families, inline copy matches rule for rule, "
          f"{len(fams_link)} OFL.txt vendored")
    return 0


def licences_only() -> int:
    """Vendor the OFL texts for the families already in fonts.css, without
    re-downloading a single .woff2."""
    css = OUT_DIR / "fonts.css"
    if not css.exists():
        print("FAIL fonts.css missing — run without a flag to fetch everything")
        return 1
    families = sorted(set(re.findall(r"font-family: '([^']+)'",
                                     css.read_text(encoding="utf-8"))))
    socket.setdefaulttimeout(30)
    failed = _fetch_ofl(families)
    _write_licences(families)
    return 1 if failed else check()


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if "--inline" in sys.argv:
        sys.exit(write_inline() or check())
    sys.exit(licences_only() if "--licences" in sys.argv else fetch())
