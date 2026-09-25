"""The built font files against the spec (docs/CVSTAND_FONT_CONTROLS.md §5, §7.3).

`tools/build_fonts.py` asserts all of this while it builds. These tests assert
it again from the COMMITTED files, reading each one with fontTools, so a hand
edit, a partial rebuild or a lost file fails the suite instead of shipping.
build.json is only trusted for where to look; every measured value is
re-measured here.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from app.typography import CSS_FAMILY_PREFIX, OFFERED, built_faces, offered_weights

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "app" / "static" / "fonts"
CSS = FONT_DIR / "typography.css"
BUILD = json.loads((ROOT / "app" / "typography" / "build.json").read_text(encoding="utf-8"))
FACES = BUILD["faces"]
IDS = [f"{f['family']}-{f['weight']}" for f in FACES]

#: The families whose OFL.txt reserves a name their own name contains. Typed
#: out, so the build's licence parsing is checked against an independent list.
RESERVED = {"Raleway", "Playfair Display", "Lora", "IBM Plex Sans Arabic",
            "Scheherazade New", "Lateef"}

ARABIC_FAMILIES = {f for (lang, _r), fams in OFFERED.items() if lang == "ar" for f in fams}
ASCII_PRINTABLE = set(range(0x20, 0x7F))
ARABIC_LETTERS = set(range(0x0621, 0x063B)) | set(range(0x0641, 0x064B))
#: Accented Latin-1 (José, Müller): every face, Arabic included.
LATIN1_SAMPLE = {0x00E9, 0x00FC}
#: Latin-Ext a name may need (Łukasz, Dvořák, Şahin): every LATIN face.
LATIN_EXT_SAMPLE = {0x0141, 0x0142, 0x0159, 0x015E}
#: Arabic families whose UPSTREAM files stop at Latin-1 - measured, and three
#: of them ship byte-for-byte, so this is the font, not the subset (the build
#: separately asserts subsetting dropped nothing in range). In these, an
#: "Ł" or "ř" in an Arabic CV falls through to the generic fallback, which
#: step 3's font stack has to account for. Pinned so a change is noticed.
ARABIC_WITHOUT_LATIN_EXT = {"Almarai", "Aref Ruqaa", "El Messiri", "IBM Plex Sans Arabic",
                            "Jomhuria", "Lateef", "Scheherazade New", "Tajawal"}
#: Thin/ExtraLight as Google's official static TTFs encode them (Windows GDI).
LEGACY_WEIGHT_CLASS = {100: (250,), 200: (250, 275)}


@lru_cache(maxsize=None)
def _font(rel: str) -> TTFont:
    return TTFont(FONT_DIR / rel, lazy=True)


def _name(font: TTFont, nid: int) -> str | None:
    rec = font["name"].getName(nid, 3, 1, 0x409) or font["name"].getName(nid, 1, 0, 0)
    return rec.toUnicode() if rec else None


def _files(face: dict) -> list[str]:
    return [face["ttf"]] + ([face["woff2"]] if face["woff2"] else [])


# ---- the build covers the registry, exactly ---------------------------------

def test_every_offered_face_is_built_and_nothing_else():
    wanted = {(fam, w) for (lang, role), fams in OFFERED.items() for fam in fams
              for w in offered_weights(lang, role, fam)}
    assert set(built_faces()) == wanted


def test_the_build_is_not_vacuous():
    """106 faces as planned: 69 instanced, 20 official statics subset, 17 unmodified."""
    methods = {}
    for f in FACES:
        methods[f["method"]] = methods.get(f["method"], 0) + 1
    assert len(FACES) == 106
    assert methods == {"instanced": 69, "subset-static": 20, "unmodified": 17}


# ---- per file ---------------------------------------------------------------

@pytest.mark.parametrize("face", FACES, ids=IDS)
def test_files_exist_with_the_right_weight_class(face):
    for rel in _files(face):
        assert (FONT_DIR / rel).is_file(), rel
        got = _font(rel)["OS/2"].usWeightClass
        allowed = (face["weight"],)
        if face["method"] != "instanced":
            allowed += LEGACY_WEIGHT_CLASS.get(face["weight"], ())
        assert got in allowed, f"{rel}: usWeightClass {got}, face is {face['weight']}"


@pytest.mark.parametrize("face", FACES, ids=IDS)
def test_embedding_is_permitted_and_the_licence_survives(face):
    """§5.6: fsType 0 or 8, never 2 or 4. §5.3: nameIDs 0, 13, 14 kept -
    the subsetter's default would have dropped 13 and 14."""
    for rel in _files(face):
        f = _font(rel)
        assert f["OS/2"].fsType in (0, 8), f"{rel}: fsType {f['OS/2'].fsType}"
        assert f["OS/2"].fsType == face["fs_type"]
        for nid in (0, 13, 14):
            assert _name(f, nid), f"{rel}: licence nameID {nid} missing"


@pytest.mark.parametrize("face", FACES, ids=IDS)
def test_word_names_are_what_the_file_says(face):
    """§5.7: the Word mapping reads word_family_name; it must BE nameID 1."""
    f = _font(face["ttf"])
    assert _name(f, 1) == face["word_family_name"]
    assert _name(f, 4) == face["full_name"]
    assert _name(f, 6) == face["postscript_name"]
    assert bool(f["OS/2"].fsSelection & (1 << 5)) == face["word_bold"]


def test_full_and_postscript_names_are_unique():
    for key in ("full_name", "postscript_name"):
        values = [f[key] for f in FACES]
        dupes = sorted({v for v in values if values.count(v) > 1})
        assert not dupes, f"{key} shared between faces: {dupes}"


@pytest.mark.parametrize("face", [f for f in FACES if f["method"] == "instanced"],
                         ids=[i for i, f in zip(IDS, FACES) if f["method"] == "instanced"])
def test_instances_follow_the_ribbi_naming(face):
    """§5.3: 400/700 share the family name (Word's bold toggle reaches 700);
    every other weight is its own family, e.g. 'Montserrat ExtraBold'."""
    fam, w = face["family"], face["weight"]
    names = {200: "ExtraLight", 300: "Light", 800: "ExtraBold", 900: "Black"}
    expected = fam if w in (400, 700) else f"{fam} {names[w]}"
    assert face["word_family_name"] == expected
    assert face["word_bold"] == (w == 700)
    assert "fvar" not in _font(face["ttf"]), "instance is still variable"


# ---- script coverage ----------------------------------------------------------

@pytest.mark.parametrize("face", FACES, ids=IDS)
def test_script_coverage(face):
    """Every face keeps printable ASCII and accented Latin-1. An ARABIC face
    keeps them too, not Arabic alone: English words, emails and URLs in an
    Arabic CV render in the same family (§3.4)."""
    for rel in _files(face):
        have = set(_font(rel).getBestCmap())
        missing = (ASCII_PRINTABLE | LATIN1_SAMPLE) - have
        assert not missing, f"{rel}: Latin missing {[hex(c) for c in sorted(missing)][:6]}"
        if face["family"] in ARABIC_FAMILIES:
            gap = ARABIC_LETTERS - have
            assert not gap, f"{rel}: Arabic letters missing {[hex(c) for c in sorted(gap)][:6]}"
            has_ext = LATIN_EXT_SAMPLE <= have
            assert has_ext == (face["family"] not in ARABIC_WITHOUT_LATIN_EXT), (
                f"{rel}: Latin-Ext coverage changed - update ARABIC_WITHOUT_LATIN_EXT")
        else:
            assert LATIN_EXT_SAMPLE <= have, f"{rel}: Latin-Ext missing"


@pytest.mark.parametrize("face", [f for f in FACES if f["family"] in ARABIC_FAMILIES],
                         ids=[i for i, f in zip(IDS, FACES) if f["family"] in ARABIC_FAMILIES])
def test_arabic_shaping_survived(face):
    """Joining forms live in GSUB. A subset that dropped layout features would
    render every Arabic letter isolated, and no cmap check would notice."""
    gsub = _font(face["ttf"])["GSUB"].table
    scripts = {s.ScriptTag for s in gsub.ScriptList.ScriptRecord}
    features = {r.FeatureTag for r in gsub.FeatureList.FeatureRecord}
    assert "arab" in scripts
    assert {"init", "medi", "fina"} <= features


@pytest.mark.parametrize("face", [f for f in FACES if f["woff2"]],
                         ids=[i for i, f in zip(IDS, FACES) if f["woff2"]])
def test_woff2_and_ttf_are_the_same_font(face):
    """The browser gets the woff2 and Word gets the ttf; they must agree."""
    a, b = _font(face["ttf"]), _font(face["woff2"])
    assert a.getBestCmap() == b.getBestCmap()
    assert a["maxp"].numGlyphs == b["maxp"].numGlyphs


# ---- Reserved Font Names ------------------------------------------------------

def _declared_rfn(family: str) -> list[str]:
    text = (FONT_DIR / "licenses" / f"{family.replace(' ', '-')}-OFL.txt").read_text(
        encoding="utf-8", errors="replace")
    out = []
    for line in text.splitlines():
        if re.search(r"Reserved\s+Font\s+Names?", line, re.I) and "refers to" not in line:
            out += re.findall(r"[\"“”]([^\"“”]+)[\"“”]", line)
    return out


def test_reserved_font_name_families_are_exactly_the_six():
    applies = {fam for fam in BUILD["families"]
               if any(n.lower() in fam.lower() for n in _declared_rfn(fam))}
    assert applies == RESERVED


@pytest.mark.parametrize("face", [f for f in FACES if f["family"] in RESERVED],
                         ids=[i for i, f in zip(IDS, FACES) if f["family"] in RESERVED])
def test_reserved_name_faces_ship_byte_for_byte(face):
    """A subset, an instance or a woff2 we produced would be a Modified Version,
    which may not keep a Reserved Font Name (OFL FAQ 2.2.2, 2.6). So: the
    official file, unchanged, and no woff2 at all."""
    assert face["method"] == "unmodified"
    assert face["woff2"] is None
    data = (FONT_DIR / face["ttf"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == face["source_sha256"] == face["ttf_sha256"]
    stem = Path(face["ttf"]).stem
    assert not (FONT_DIR / "web" / f"{stem}.woff2").exists()


def test_no_other_family_is_left_unmodified():
    assert {f["family"] for f in FACES if f["method"] == "unmodified"} == RESERVED


@pytest.mark.parametrize("family", sorted(BUILD["families"]))
def test_every_family_ships_its_licence(family):
    assert (FONT_DIR / BUILD["families"][family]["licence"]).is_file()


# ---- the stylesheet -------------------------------------------------------------

_RULE = re.compile(
    r"@font-face \{ font-family: '([^']+)'; font-style: normal; font-weight: (\d+); "
    r"font-display: block; src: url\(/static/fonts/([^)]+)\) format\('(woff2|truetype)'\); \}")


def _css_rules() -> dict[tuple[str, int], tuple[str, str]]:
    text = CSS.read_text(encoding="utf-8")
    rules = _RULE.findall(text)
    assert len(rules) == text.count("@font-face"), "an @font-face rule has an unexpected shape"
    out = {}
    for fam, w, url, fmt in rules:
        assert (fam, int(w)) not in out, f"duplicate rule for {fam} {w}"
        out[(fam, int(w))] = (url, fmt)
    return out


def test_css_serves_every_face_from_the_right_file():
    rules = _css_rules()
    assert len(rules) == len(FACES)
    for f in FACES:
        url, fmt = rules[(f["css_family"], f["weight"])]
        if f["woff2"]:
            assert (url, fmt) == (f["woff2"], "woff2")
        else:
            assert (url, fmt) == (f["ttf"], "truetype")
        assert (FONT_DIR / url).is_file()


def test_css_families_cannot_collide_with_template_fonts():
    """Every family is 'CVT …', so nothing a template names today can resolve
    to one of these files and change an existing render."""
    ours = {fam for fam, _w in _css_rules()}
    assert all(fam.startswith(CSS_FAMILY_PREFIX) for fam in ours)
    existing = set()
    for sheet in ("fonts.css", "fonts_ar.css", "fonts_ar_shell.css"):
        existing |= set(re.findall(r"font-family: '([^']+)'",
                                   (FONT_DIR / sheet).read_text(encoding="utf-8")))
    assert not ours & existing


def test_css_is_self_hosted():
    """Hard rule 3: nothing is fetched from Google at render time."""
    text = CSS.read_text(encoding="utf-8")
    assert "googleapis" not in text and "gstatic" not in text
