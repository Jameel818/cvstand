"""Build the font files for the typography controls (spec §5).

    GITHUB_TOKEN=... venv/Scripts/python tools/build_fonts.py   # download + build
    venv/Scripts/python tools/build_fonts.py --check            # verify only, no network

Reads the registry (`app/typography/registry.py`) and produces, for every
(family, weight) any dropdown offers:

    app/static/fonts/ttf/<slug>-<weight>.ttf     every face; Word embeds these (§6.3)
    app/static/fonts/web/<slug>-<weight>.woff2   the browser/PDF copy, EXCEPT the
                                                 Reserved Font Name families
    app/static/fonts/typography.css              one @font-face per face
    app/static/fonts/licenses/<Family>-OFL.txt   per family (OFL clause 2)
    app/typography/build.json                    what was built, from where, and
                                                 what each file measured as

The output is committed; this script is run once and again only when the
registry changes. It is not part of the app and never runs at request time.

THREE WAYS A FACE IS MADE, decided per family from its own OFL.txt
    unmodified       The family declares a Reserved Font Name that its own name
                     contains (Raleway, Playfair Display, Lora, IBM Plex Sans
                     Arabic, Scheherazade New, Lateef). A subset or instance is a
                     Modified Version and may not keep that name, so the
                     official static TTF ships byte-for-byte - to Word AND to
                     the browser, with no woff2 (FONTS.md says why).
    subset-static    Official static TTFs exist upstream: subset them.
    instanced        Only a variable font exists: pin every axis (wght to the
                     face's weight, the rest to their defaults), rename per
                     §5.3, then subset.

SUBSETTING is by script, never by the characters a CV uses: Latin + Latin-Ext
for every family, plus Arabic for Arabic families. An Arabic family keeps its
Latin too - English words, emails and URLs in an Arabic CV render in the same
family (§3.4) - and the build asserts that nothing Latin the source had was
dropped. Layout features are kept whole (Arabic shaping lives in GSUB), and
so are all name records (the subsetter's default keeps only 0-6, which would
delete the licence).

WHY THE CSS FAMILIES ARE 'CVT <Family>'
    fonts.css already declares 'Montserrat', 'Inter', 'Archivo' and others for
    the 49 templates, from different files at different weights. Declaring the
    same name again would add faces to those families and could change what an
    existing template renders. The prefix makes that impossible: nothing a
    template names can resolve to a file this script wrote.

Downloads are pinned to one google/fonts commit, recorded in build.json.
Helpers come from tools/fetch_fonts.py by import; that script is never re-run
(re-running it rebuilds fonts.css from whatever Google serves today).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

from fontTools import subset  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from fontTools.varLib import instancer  # noqa: E402

from fetch_fonts import (  # noqa: E402  - path set above
    LICENCE_DIR_NAME,
    OUT_DIR,
    UA,
    WEB_PREFIX,
    _fetch_ofl,
    _write_licences,
)
from app.typography.registry import (  # noqa: E402
    CSS_FAMILY_PREFIX, FONTS, OFFERED, offered_weights,
)

TTF_DIR = OUT_DIR / "ttf"
WEB_DIR = OUT_DIR / "web"
CSS_OUT = OUT_DIR / "typography.css"
BUILD_JSON = ROOT / "app" / "typography" / "build.json"
CACHE = Path(tempfile.gettempdir()) / "cvstand-font-src"

REPO = "google/fonts"
API = "https://api.github.com/repos/" + REPO
RAW = "https://raw.githubusercontent.com/" + REPO + "/{sha}/{path}"
GF_DOWNLOAD = "https://fonts.google.com/download/list?family={}"

WEIGHT_NAME = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
               500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold",
               900: "Black"}

# fsType values that permit embedding a font in a document (§5.6): 0
# installable, 8 editable. 2 (restricted) and 4 (preview & print) fail.
EMBEDDABLE_FS_TYPE = (0, 8)

# usWeightClass a face of each CSS weight may carry. Exact, except the
# legacy values Google's static TTFs use for Thin/ExtraLight (see
# _statics_by_weight): Poppins/Tajawal ExtraLight say 275, Raleway's older
# build says 250. All sit below Light (300), so no two weights can be confused.
# Instances built here always get the exact weight.
LEGACY_WEIGHT_CLASS = {100: (250,), 200: (250, 275)}


def weight_classes(weight: int) -> tuple[int, ...]:
    return (weight, *LEGACY_WEIGHT_CLASS.get(weight, ()))


# nameIDs that carry the licence; they must survive every step (§5.3).
LICENCE_NAME_IDS = (0, 13, 14)


# ---- Unicode ranges, as Google Fonts defines its subsets ------------------

def _ranges(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.replace("U+", "").split(","):
        lo, _, hi = part.strip().partition("-")
        out.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return out


LATIN = _ranges(
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
    "U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, "
    "U+2212, U+2215, U+FEFF, U+FFFD")
LATIN_EXT = _ranges(
    "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, "
    "U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, "
    "U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF")
# U+25CC is the dotted circle a shaper draws under a stray combining mark.
ARABIC = _ranges(
    "U+0600-06FF, U+0750-077F, U+0870-088E, U+0890-0891, U+0897-08E1, "
    "U+08E3-08FF, U+200C-200E, U+2010-2011, U+204F, U+25CC, U+2E41, "
    "U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC, U+102E0-102FB, U+10E60-10E7E, "
    "U+10EC2-10EC4, U+10EFC-10EFF, U+1EE00-1EEFF")

# What "has Latin" and "has Arabic" mean in the coverage assertion: every
# printable ASCII character (an email address, a URL), and the 36 base
# letters of the Arabic alphabet.
ASCII_PRINTABLE = set(range(0x20, 0x7F))
ARABIC_LETTERS = set(range(0x0621, 0x063B)) | set(range(0x0641, 0x064B))

ARABIC_FAMILIES = {f for (lang, _role), fams in OFFERED.items() if lang == "ar"
                   for f in fams}


def script_ranges(family: str) -> set[int]:
    base = LATIN | LATIN_EXT
    return base | ARABIC if family in ARABIC_FAMILIES else base


def needed_faces() -> dict[str, list[int]]:
    """family -> the weights some dropdown offers, sorted. Nothing else is built."""
    out: dict[str, set[int]] = {}
    for (lang, role), fams in OFFERED.items():
        for fam in fams:
            out.setdefault(fam, set()).update(offered_weights(lang, role, fam))
    return {f: sorted(w) for f, w in sorted(out.items())}


def slug(family: str) -> str:
    return FONTS[family].slug


def licence_path(family: str) -> Path:
    return OUT_DIR / LICENCE_DIR_NAME / f"{family.replace(' ', '-')}-OFL.txt"


# ---- Reserved Font Names --------------------------------------------------

def reserved_names(ofl_text: str) -> list[str]:
    """The names an OFL.txt reserves: the quoted strings in any copyright line
    that says 'Reserved Font Name(s)'. Mada reserves "Source" and Readex Pro
    "RevReading Lexend" - names of the fonts they derive from, not their own."""
    names: list[str] = []
    for line in ofl_text.splitlines():
        if re.search(r"Reserved\s+Font\s+Names?", line, re.I) and "refers to" not in line:
            names += re.findall(r"[\"“”]([^\"“”]+)[\"“”]", line)
    return names


def rfn_applies(family: str, names: list[str]) -> list[str]:
    """The reserved names this family's own name contains ("Plex" in IBM Plex
    Sans Arabic). Those are the ones a modified file could not keep."""
    return [n for n in names if n.lower() in family.lower()]


# ---- Network ---------------------------------------------------------------

def _headers() -> dict[str, str]:
    h = {"User-Agent": UA["User-Agent"], "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _fetch(url: str, api: bool = False) -> bytes:
    req = urllib.request.Request(url, headers=_headers() if api else UA)
    return urllib.request.urlopen(req).read()


def _cached(url: str) -> bytes:
    key = hashlib.sha256(url.encode()).hexdigest()[:24] + "-" + url.rsplit("/", 1)[-1][-60:]
    path = CACHE / re.sub(r"[^\w.\-\[\],]", "_", key)
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fetch(url))
    return path.read_bytes()


def repo_commit() -> str:
    return json.loads(_fetch(f"{API}/commits/main", api=True))["sha"]


def repo_listing(family: str, sha: str) -> tuple[str, list[str]]:
    """(directory, file names) for the family in google/fonts, discovered via
    the API rather than hard-coded (§5.1)."""
    d = family.lower().replace(" ", "")
    for lic in ("ofl", "apache", "ufl"):
        try:
            items = json.loads(_fetch(f"{API}/contents/{lic}/{d}?ref={sha}", api=True))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        return f"{lic}/{d}", [i["name"] for i in items]
    raise SystemExit(f"FAIL {family}: no directory in {REPO}")


def gf_download_statics(family: str) -> dict[str, str]:
    """{file name: url} of the upright static TTFs in Google Fonts' own family
    download - the official statics for families google/fonts ships only as a
    variable font."""
    raw = _fetch(GF_DOWNLOAD.format(family.replace(" ", "+"))).decode("utf-8")
    manifest = json.loads(raw[raw.index("{"):])["manifest"]
    return {r["filename"].rsplit("/", 1)[-1]: r["url"] for r in manifest["fileRefs"]
            if r["filename"].startswith("static/") and r["filename"].endswith(".ttf")
            and "Italic" not in r["filename"]}


def _upright_statics(names: list[str]) -> list[str]:
    return [n for n in names if n.endswith(".ttf") and "[" not in n and "Italic" not in n]


def _upright_variable(names: list[str]) -> str | None:
    var = [n for n in names if n.endswith(".ttf") and "[" in n and "Italic" not in n]
    return var[0] if var else None


# ---- Font surgery ----------------------------------------------------------

def _load(data: bytes) -> TTFont:
    # recalcTimestamp=False: saving must not stamp today's date into head, or
    # every rebuild would rewrite every file with no real change.
    return TTFont(io.BytesIO(data), recalcTimestamp=False)


def _save(font: TTFont, flavor: str | None = None) -> bytes:
    font.flavor = flavor
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def _name(font: TTFont, name_id: int) -> str | None:
    rec = font["name"].getName(name_id, 3, 1, 0x409) or font["name"].getName(name_id, 1, 0, 0)
    return rec.toUnicode() if rec else None


def rename_instance(font: TTFont, family: str, weight: int) -> None:
    """§5.3 naming for a static instance cut from a variable font.

    400 and 700 use RIBBI naming (family / Regular|Bold) so Word pairs them as
    one family with a bold toggle; every other weight is its own family
    ("Montserrat ExtraBold" / Regular), which is how Word reaches it (§6.2)."""
    wn = WEIGHT_NAME[weight]
    ribbi = weight in (400, 700)
    ps = f"{family.replace(' ', '')}-{wn}"
    values = {
        1: family if ribbi else f"{family} {wn}",
        2: "Bold" if weight == 700 else "Regular",
        3: f"{font['head'].fontRevision:.3f};CVStand;{ps}",
        4: f"{family} {wn}",
        6: ps,
        16: family,
        17: wn,
    }
    name = font["name"]
    for nid in (1, 2, 3, 4, 6, 16, 17, 21, 22, 25):
        name.removeNames(nameID=nid)
    for nid, value in values.items():
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)

    os2 = font["OS/2"]
    os2.usWeightClass = weight
    sel = os2.fsSelection & ~((1 << 0) | (1 << 5) | (1 << 6))
    os2.fsSelection = sel | ((1 << 5) if weight == 700 else (1 << 6))
    font["head"].macStyle = (font["head"].macStyle & ~0b11) | (1 if weight == 700 else 0)


def instance(var_data: bytes, family: str, weight: int) -> tuple[TTFont, dict]:
    font = _load(var_data)
    axes = {a.axisTag: a for a in font["fvar"].axes}
    wght = axes["wght"]
    if not wght.minValue <= weight <= wght.maxValue:
        raise SystemExit(f"FAIL {family} {weight}: outside the variable font's "
                         f"wght {wght.minValue:g}-{wght.maxValue:g}")
    loc = {tag: (weight if tag == "wght" else a.defaultValue) for tag, a in axes.items()}
    static = instancer.instantiateVariableFont(font, loc, updateFontNames=False)
    rename_instance(static, family, weight)
    return static, {t: v for t, v in loc.items() if t != "wght"}


def subset_font(font: TTFont, unicodes: set[int]) -> TTFont:
    opts = subset.Options()
    opts.layout_features = ["*"]    # Arabic shaping lives in GSUB
    opts.layout_scripts = ["*"]
    opts.name_IDs = ["*"]           # default 0-6 would drop the licence (13, 14)
    opts.name_legacy = True
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.legacy_kern = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    return font


def cmap(font: TTFont) -> set[int]:
    return set(font.getBestCmap() or {})


# ---- Build -----------------------------------------------------------------

class BuildError(Exception):
    pass


def _check_weights_exist(family: str, *, var: TTFont | None = None,
                         statics: dict[int, str] | None = None) -> None:
    """§3: every weight the registry says the font HAS must really exist in
    the upstream files - not only the ones offered."""
    claimed = FONTS[family].weights
    if var is not None:
        a = next(x for x in var["fvar"].axes if x.axisTag == "wght")
        missing = [w for w in claimed if not a.minValue <= w <= a.maxValue]
        where = f"variable wght {a.minValue:g}-{a.maxValue:g}"
    else:
        missing = [w for w in claimed if w not in (statics or {})]
        where = f"static weights {sorted(statics or {})}"
    if missing:
        raise BuildError(f"{family}: registry claims weights {missing} that the "
                         f"upstream files do not have ({where})")


def _statics_by_weight(files: dict[str, bytes]) -> dict[int, tuple[str, bytes]]:
    """weight -> (file name, bytes), the weight read from the file's STYLE NAME.

    Not from usWeightClass: Google's official statics store Thin as 250 and
    ExtraLight as 275 (a Windows GDI convention - below 250 GDI may smear or
    embolden), so Poppins-ExtraLight.ttf says 275 and means 200. The style
    name is the authority; usWeightClass is then checked against it, allowing
    only that one documented legacy value per weight."""
    by_style = {v.lower(): k for k, v in WEIGHT_NAME.items()}
    out: dict[int, tuple[str, bytes]] = {}
    for fname, data in files.items():
        style = fname.rsplit(".", 1)[0].rsplit("-", 1)[-1].lower()
        if style not in by_style:
            raise BuildError(f"{fname}: unrecognised style name {style!r}")
        w = by_style[style]
        got = _load(data)["OS/2"].usWeightClass
        if got not in weight_classes(w):
            raise BuildError(f"{fname}: style says {w}, usWeightClass says {got}")
        if w in out:
            raise BuildError(f"two upright statics claim weight {w}: {out[w][0]}, {fname}")
        out[w] = (fname, data)
    return out


def build() -> int:
    socket.setdefaulttimeout(60)
    faces = needed_faces()
    missing_ofl = [f for f in faces if not licence_path(f).exists()]
    if missing_ofl:
        print(f"vendoring {len(missing_ofl)} OFL.txt ...")
        if _fetch_ofl(missing_ofl):
            print("FAIL could not fetch every OFL.txt")
            return 1

    sha = repo_commit()
    print(f"google/fonts @ {sha[:12]}")
    TTF_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    report, families_out, faces_out, errors = [], {}, [], []
    for family, weights in faces.items():
        try:
            fam_info, fam_faces = _build_family(family, weights, sha)
        except BuildError as exc:
            errors.append(str(exc))
            continue
        families_out[family] = fam_info
        faces_out += fam_faces
        report.append((family, fam_info))

    print("\nReserved Font Name report (§5.2)")
    print(f"  {'family':22} {'RFN declared':34} {'applies':8} method")
    for family, info in report:
        declared = ", ".join(info["reserved_font_names_declared"]) or "-"
        applies = "YES" if info["reserved_font_names"] else "no"
        print(f"  {family:22} {declared[:34]:34} {applies:8} {info['method']}")

    if errors:
        print(f"\nFAIL - {len(errors)} famil{'y' if len(errors) == 1 else 'ies'} "
              "need a human decision; nothing was written to build.json:")
        for e in errors:
            print("  ", e)
        return 1

    _cross_face_checks(faces_out)
    write_css(faces_out)
    manifest = {
        "generated_by": "tools/build_fonts.py",
        "source": {"repo": REPO, "commit": sha},
        "css": "typography.css",
        "paths_relative_to": "app/static/fonts",
        "families": families_out,
        "faces": faces_out,
    }
    BUILD_JSON.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")

    listed = _licence_families()
    _write_licences(sorted(listed | set(faces)))
    _print_sizes(faces_out)
    return check()


def _build_family(family: str, weights: list[int], sha: str) -> tuple[dict, list[dict]]:
    d, names = repo_listing(family, sha)
    ofl = licence_path(family).read_text(encoding="utf-8", errors="replace")
    declared = reserved_names(ofl)
    rfn = rfn_applies(family, declared)
    statics = _upright_statics(names)
    variable = _upright_variable(names)
    unicodes = script_ranges(family)
    info = {
        "script": "arabic" if family in ARABIC_FAMILIES else "latin",
        "licence": f"{LICENCE_DIR_NAME}/{licence_path(family).name}",
        "reserved_font_names_declared": declared,
        "reserved_font_names": rfn,
    }

    # Which upstream bytes each weight comes from.
    sources: dict[int, tuple[str, bytes]] = {}
    var_font = None
    if statics:
        files = {n: _cached(RAW.format(sha=sha, path=f"{d}/{n}")) for n in statics}
        by_w = _statics_by_weight(files)
        _check_weights_exist(family, statics={w: n for w, (n, _) in by_w.items()})
        sources = {w: (f"{d}/{n}", data) for w, (n, data) in by_w.items()}
        info["method"] = "unmodified" if rfn else "subset-static"
    elif rfn:
        # Variable-only in google/fonts and the name is reserved: an instance
        # would be a Modified Version. Google Fonts' family download carries
        # official statics; use those, unmodified.
        urls = gf_download_statics(family)
        if not urls:
            raise BuildError(f"{family}: Reserved Font Name {rfn} and no official "
                             "static TTF found - needs a human decision")
        files = {n: _cached(u) for n, u in urls.items()}
        by_w = _statics_by_weight(files)
        _check_weights_exist(family, statics={w: n for w, (n, _) in by_w.items()})
        sources = {w: (urls[n], data) for w, (n, data) in by_w.items()}
        info["method"] = "unmodified"
    elif variable:
        var_bytes = _cached(RAW.format(sha=sha, path=f"{d}/{variable}"))
        var_font = _load(var_bytes)
        _check_weights_exist(family, var=var_font)
        info["method"] = "instanced"
        info["variable_source"] = f"{d}/{variable}"
    else:
        raise BuildError(f"{family}: no upright TTF in {d}")
    info["source"] = d if info["method"] != "unmodified" or statics else "fonts.google.com download"

    out = []
    for w in weights:
        stem = f"{slug(family)}-{w}"
        ttf_rel, web_rel = f"ttf/{stem}.ttf", f"web/{stem}.woff2"
        face = {"family": family, "weight": w,
                "css_family": CSS_FAMILY_PREFIX + family,
                "method": info["method"]}
        if info["method"] == "instanced":
            font, pinned = instance(var_bytes, family, w)
            src_path, src_bytes = info["variable_source"], var_bytes
            face["pinned_axes"] = pinned
        else:
            if w not in sources:
                raise BuildError(f"{family} {w}: no upstream static file")
            src_path, src_bytes = sources[w]
            font = _load(src_bytes)
        face["source"] = src_path
        face["source_sha256"] = hashlib.sha256(src_bytes).hexdigest()

        if info["method"] == "unmodified":
            ttf_bytes, web_bytes = src_bytes, None
        else:
            before = cmap(font)
            subset_font(font, unicodes)
            ttf_bytes = _save(font)
            web_bytes = _save(_load(ttf_bytes), "woff2")
            lost = (before & unicodes) - cmap(_load(ttf_bytes))
            if lost:
                raise BuildError(f"{family} {w}: subsetting dropped {len(lost)} "
                                 f"in-range codepoints, e.g. U+{min(lost):04X}")

        (OUT_DIR / ttf_rel).write_bytes(ttf_bytes)
        face["ttf"] = ttf_rel
        face["ttf_bytes"] = len(ttf_bytes)
        face["ttf_sha256"] = hashlib.sha256(ttf_bytes).hexdigest()
        if web_bytes is not None:
            (OUT_DIR / web_rel).write_bytes(web_bytes)
            face["woff2"] = web_rel
            face["woff2_bytes"] = len(web_bytes)
        else:
            face["woff2"] = None
            face["woff2_bytes"] = 0
        face.update(_inspect(family, w, _load(ttf_bytes)))
        out.append(face)
    return info, out


def _inspect(family: str, weight: int, font: TTFont) -> dict:
    """Measure one built TTF and fail on anything §5 forbids."""
    os2 = font["OS/2"]
    if os2.usWeightClass not in weight_classes(weight):
        raise BuildError(f"{family} {weight}: usWeightClass is {os2.usWeightClass}")
    if os2.fsType not in EMBEDDABLE_FS_TYPE:
        raise BuildError(f"{family} {weight}: fsType {os2.fsType} forbids embedding")
    for nid in LICENCE_NAME_IDS:
        if not _name(font, nid):
            raise BuildError(f"{family} {weight}: nameID {nid} (licence) is missing")
    have = cmap(font)
    need = ASCII_PRINTABLE | (ARABIC_LETTERS if family in ARABIC_FAMILIES else set())
    if not need <= have:
        gap = sorted(need - have)
        raise BuildError(f"{family} {weight}: missing {len(gap)} required codepoints, "
                         f"e.g. U+{gap[0]:04X} - an Arabic face must keep its Latin")
    return {
        "us_weight_class": os2.usWeightClass,
        "fs_type": os2.fsType,
        "word_family_name": _name(font, 1),
        "word_bold": bool(os2.fsSelection & (1 << 5)),
        "full_name": _name(font, 4),
        "postscript_name": _name(font, 6),
        "codepoints": len(have),
    }


def _cross_face_checks(faces: list[dict]) -> None:
    for key in ("full_name", "postscript_name"):
        seen: dict[str, str] = {}
        for f in faces:
            v, who = f[key], f"{f['family']} {f['weight']}"
            if v in seen:
                raise SystemExit(f"FAIL {key} {v!r} is shared by {seen[v]} and {who}")
            seen[v] = who


def write_css(faces: list[dict]) -> None:
    rules = []
    for f in faces:
        if f["woff2"]:
            src = f"url({WEB_PREFIX}/{f['woff2']}) format('woff2')"
        else:
            src = f"url({WEB_PREFIX}/{f['ttf']}) format('truetype')"
        rules.append(
            f"@font-face {{ font-family: '{f['css_family']}'; font-style: normal; "
            f"font-weight: {f['weight']}; font-display: block; src: {src}; }}")
    header = ("/* GENERATED by tools/build_fonts.py from app/typography/build.json"
              " - do not edit.\n"
              f"   {len(faces)} static faces for the typography controls. Families are\n"
              f"   prefixed '{CSS_FAMILY_PREFIX.strip()}' so no template's own font can"
              " resolve to them.\n"
              "   Reserved-Font-Name families are served as their unmodified .ttf"
              " (FONTS.md). */\n")
    CSS_OUT.write_text(header + "\n".join(rules) + "\n", encoding="utf-8")


def _licence_families() -> set[str]:
    """The families LICENSES.md already lists, so regenerating it keeps them."""
    text = (OUT_DIR / "LICENSES.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| ([^|]+?) \| SIL", text, re.M))


def _print_sizes(faces: list[dict]) -> None:
    ttf = sum(f["ttf_bytes"] for f in faces)
    web = sum(f["woff2_bytes"] for f in faces)
    by = {}
    for f in faces:
        by[f["method"]] = by.get(f["method"], 0) + 1
    print(f"\n{len(faces)} faces: " + ", ".join(f"{n} {m}" for m, n in sorted(by.items())))
    print(f"  ttf/   {ttf / 1e6:6.2f} MB")
    print(f"  web/   {web / 1e6:6.2f} MB")
    print(f"  total  {(ttf + web) / 1e6:6.2f} MB")


# ---- Check (no network) ----------------------------------------------------

def check() -> int:
    """Everything build.json promises is on disk and in typography.css.
    The deep per-file assertions live in tests/test_typography_build.py."""
    if not BUILD_JSON.exists():
        print("FAIL build.json missing - run without --check")
        return 1
    data = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    built = {(f["family"], f["weight"]) for f in data["faces"]}
    wanted = {(fam, w) for fam, ws in needed_faces().items() for w in ws}
    problems = []
    if built != wanted:
        problems.append(f"registry/build mismatch: missing {sorted(wanted - built)}, "
                        f"extra {sorted(built - wanted)}")
    css = CSS_OUT.read_text(encoding="utf-8") if CSS_OUT.exists() else ""
    for f in data["faces"]:
        for key in ("ttf", "woff2"):
            if f[key] and not (OUT_DIR / f[key]).exists():
                problems.append(f"missing {f[key]}")
        served = f["woff2"] or f["ttf"]
        if f"{WEB_PREFIX}/{served}" not in css:
            problems.append(f"typography.css does not serve {served}")
    for fam in data["families"]:
        if not licence_path(fam).exists():
            problems.append(f"no licence for {fam}")
    if problems:
        print("FAIL\n  " + "\n  ".join(problems[:20]))
        return 1
    print(f"OK  {len(built)} faces over {len(data['families'])} families; every file "
          "exists, is served by typography.css, and has its OFL.txt")
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else build())
