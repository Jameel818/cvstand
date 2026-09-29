"""The Word export carries its template's colours and fonts (typography step 5).

Spec §7.6: parse the package and assert the w:rFonts / w:cs / w:bCs values
match the mapping - Word family name and bold flag from build.json, never a
name rebuilt by hand. Plus the user's decisions of 2026-09-27: every accent
that is too light to read becomes a darker TEXT colour, while rules keep the
original accent; modern-t10's DM Sans becomes Poppins.

Where the faces live: the builder gives every themed run a ROLE style
(tools/build_word_masters.py "ROLE STYLES") and app/exporters/docx_theme.py
rewrites those styles, so these tests read styles.xml - and prove that no
themed run carries direct formatting that would override its style.
"""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from lxml import etree

from app import registry
from app.exporters import docx_layout
from app.exporters import docx_theme as T
from app.exporters.docx import render_docx
from app.schema import lang_of
from app.typography import built_faces, face
from tests.samples import ARABIC, ENGLISH

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KEYS = registry.ported_keys()
STYLE_IDS = {"name": "CVName", "heading": "CVHeading", "role": "CVRole",
             "body_bold": "CVBodyBold", "body": "Normal"}


def _parts(blob: bytes):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return (etree.fromstring(z.read("word/document.xml")),
                etree.fromstring(z.read("word/styles.xml")))


def _style(styles, style_id):
    for st in styles.iter(f"{W}style"):
        if st.get(f"{W}styleId") == style_id:
            return st.find(f"{W}rPr")
    raise AssertionError(f"no style {style_id}")


def _font_of(rpr) -> tuple[dict, bool, bool, str | None]:
    fonts = rpr.find(f"{W}rFonts")
    slots = {k: fonts.get(f"{W}{k}") for k in ("ascii", "hAnsi", "eastAsia", "cs")}
    color = rpr.find(f"{W}color")
    return (slots, rpr.find(f"{W}b") is not None, rpr.find(f"{W}bCs") is not None,
            color.get(f"{W}val") if color is not None else None)


def _assert_face(styles, role, family, weight):
    slots, b, bcs, _ = _font_of(_style(styles, STYLE_IDS[role]))
    wname, bold = T.word_font(family, weight)
    built = face(family, weight)  # the spec's rule: the build's names, not ours
    assert (wname, bold) == (built["word_family_name"], bool(built["word_bold"]))
    assert set(slots.values()) == {wname}, (role, slots, wname)
    assert b == bold and bcs == bold, (role, "bold flag", b, bcs, bold)


# ---- the theme data ------------------------------------------------------------

def test_every_template_has_a_theme_in_both_languages():
    themes = T.themes()
    assert sorted(themes) == sorted(KEYS)
    for key in KEYS:
        for lang in ("en", "ar"):
            th = themes[key][lang]
            assert th["accent"] == registry.get(key).accent.upper()
            assert th["name"]["family"] and th["heading"]["family"] and th["body"]


def test_dm_sans_becomes_poppins_in_word():
    """modern-t10 names DM Sans, vendored nowhere (user decision 2026-09-27)."""
    assert T.themes()["modern-t10"]["en"]["body"] == "Poppins"
    assert "DM Sans" not in json.dumps(T.themes())


def test_arabic_themes_follow_the_font_policy():
    for key in KEYS:
        th = T.themes()[key]["ar"]
        assert th["name"] == {"family": "Tajawal", "weight": 800}
        assert th["heading"]["family"] in {"Tajawal", "Cairo"}
        assert th["body"] == "IBM Plex Sans Arabic"


def test_every_face_a_word_file_uses_is_built():
    """Step 6 embeds what a document uses, so all of it must exist as a TTF:
    the dropdown faces AND the template defaults (TEMPLATE_DEFAULT_FACES),
    exactly - a template default nothing reaches would be dead weight."""
    from app.typography.registry import TEMPLATE_DEFAULT_FACES
    used = set()
    for key in KEYS:
        for data in (ENGLISH, ARABIC):
            used |= T.faces_used(T.resolve(data, key))
    assert used <= set(built_faces())
    defaults = {(f, w) for f, ws in TEMPLATE_DEFAULT_FACES.items() for w in ws}
    assert defaults <= used, f"unreached template defaults: {sorted(defaults - used)}"


def test_template_weights_snap_to_built_weights():
    for key in KEYS:
        for data in (ENGLISH, ARABIC):
            for f in T.resolve(data, key)["faces"].values():
                assert (f["family"], f["weight"]) in built_faces(), (key, f)


# ---- colour ----------------------------------------------------------------------

LIGHT = {"modern-t1", "modern-t2", "modern-t3", "modern-t5", "modern-t7", "modern-t9",
         "modern-t23", "modern-t24", "ats-t2", "ats-t4", "ats-t10", "ats-t11", "ats-t21"}


@pytest.mark.parametrize("key", KEYS)
def test_accent_text_is_readable_and_only_changes_when_it_must(key):
    accent = registry.get(key).accent.lstrip("#").upper()
    text = T.text_safe(accent)
    assert T.contrast_on_white(text) >= 4.5
    assert (text != accent) == (key in LIGHT), (key, accent, text)


@pytest.mark.parametrize("key", ["modern-t3", "modern-t16", "ats-t10", "ats-t1"])
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_text_takes_the_readable_accent_and_rules_keep_the_original(key, data):
    doc, styles = _parts(render_docx(data, key))
    accent = registry.get(key).accent.lstrip("#").upper()
    text = T.text_safe(accent)
    assert _font_of(_style(styles, "CVAccentText"))[3] == text
    rules = {b.get(f"{W}color") for b in doc.iter(f"{W}bottom")}
    assert T.RULE_ACCENT not in rules, "the master's placeholder rule colour survived"
    if docx_layout.spec_for(key):
        # A Word LAYOUT takes the template's OWN colours, measured from its
        # PDF (app/word_layouts.json): here, the main column's headings.
        # tests/test_docx_layouts.py checks every cell's colours in full.
        main = docx_layout.layouts()[key][lang_of(data)]["colours"]["main"]
        assert _font_of(_style(styles, "CVHeading"))[3] == docx_layout.readable(
            main["heading"] or main["text"], "FFFFFF")
        return
    assert _font_of(_style(styles, "CVHeading"))[3] == text
    if key.startswith("modern-"):
        assert accent in rules, "the accent rule lost the template's own colour"
        assert _font_of(_style(styles, "CVName"))[3] == text
    else:
        assert _font_of(_style(styles, "CVName"))[3] == T.INK


# ---- fonts: the template's own, and the user's ---------------------------------

@pytest.mark.parametrize("key", ["modern-t1", "modern-t10", "modern-t16", "ats-t1",
                                 "ats-t9", "ats-t16"])
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_no_choice_draws_the_templates_own_faces(key, data):
    _, styles = _parts(render_docx(data, key))
    faces = T.resolve(data, key)["faces"]
    assert not any(f["chosen"] for f in faces.values())
    for role in STYLE_IDS:
        _assert_face(styles, role, faces[role]["family"], faces[role]["weight"])


#: Three combinations per language, each role explicit where the registry
#: offers a weight. They reach: RIBBI 700 ("Family" + bold), non-RIBBI
#: ("Family Black", not bold), a single-weight display face, and Almarai,
#: whose Bold is its own family name WITH the bold flag.
COMBOS = [
    (ENGLISH, "ats-t1", dict(font_name="Playfair Display", font_name_weight=900,
                             font_heading="Montserrat", font_heading_weight=700,
                             font_body="Inter", font_body_weight=300),
     {"name": ("Playfair Display", 900), "heading": ("Montserrat", 700),
      "body": ("Inter", 300), "body_bold": ("Inter", 700)}),
    (ENGLISH, "modern-t1", dict(font_name="Anton", font_heading="Archivo",
                                font_heading_weight=900, font_body="Lora"),
     {"name": ("Anton", 400), "heading": ("Archivo", 900), "body": ("Lora", 400),
      "body_bold": ("Lora", 700)}),
    (ENGLISH, "modern-t22", dict(font_heading="Raleway", font_heading_weight=800,
                                 font_body="Work Sans", font_body_weight=400),
     {"name": ("Raleway", 800), "heading": ("Raleway", 800),
      "body": ("Work Sans", 400), "body_bold": ("Work Sans", 700)}),
    (ARABIC, "modern-t1", dict(font_name="Tajawal", font_name_weight=800,
                               font_heading="Cairo", font_heading_weight=900,
                               font_body="Amiri"),
     {"name": ("Tajawal", 800), "heading": ("Cairo", 900), "body": ("Amiri", 400),
      "body_bold": ("Amiri", 700)}),
    (ARABIC, "ats-t1", dict(font_name="Almarai", font_name_weight=700,
                            font_heading="Noto Kufi Arabic", font_heading_weight=700,
                            font_body="IBM Plex Sans Arabic", font_body_weight=300),
     {"name": ("Almarai", 700), "heading": ("Noto Kufi Arabic", 700),
      "body": ("IBM Plex Sans Arabic", 300), "body_bold": ("IBM Plex Sans Arabic", 700)}),
    (ARABIC, "modern-t22", dict(font_name="Aref Ruqaa", font_heading="El Messiri",
                                font_body="Scheherazade New"),
     {"name": ("Aref Ruqaa", 700), "heading": ("El Messiri", 700),
      "body": ("Scheherazade New", 400), "body_bold": ("Scheherazade New", 700)}),
]


@pytest.mark.parametrize("base,key,keys,want", COMBOS,
                         ids=[f"{c[1]}-{i}" for i, c in enumerate(COMBOS)])
def test_chosen_fonts_map_to_the_builds_word_names(base, key, keys, want):
    _, styles = _parts(render_docx(dict(base, **keys), key))
    for role, (family, weight) in want.items():
        _assert_face(styles, role, family, weight)


def test_a_non_ribbi_weight_is_its_own_family_and_not_bold():
    """Word only knows Regular/Bold per family: Montserrat 900 is the family
    "Montserrat Black", NOT "Montserrat" + bold, or Word would fake a bold."""
    assert T.word_font("Montserrat", 900) == ("Montserrat Black", False)
    assert T.word_font("Montserrat", 700) == ("Montserrat", True)


def test_almarai_bold_reads_the_builds_own_naming():
    f = face("Almarai", 700)
    assert T.word_font("Almarai", 700) == (f["word_family_name"], bool(f["word_bold"]))


def test_two_faces_never_share_one_word_name():
    """Archivo 900 and the Archivo Black family are both "Archivo Black" in
    the build. The template's Archivo 900 name meets a chosen Archivo Black
    heading here; the chosen face must win for both roles."""
    data = dict(ENGLISH, font_heading="Archivo Black", font_name="template")
    faces = T.resolve(data, "modern-t1")["faces"]  # modern-t1's name is Archivo 900
    assert faces["name"]["family"] == faces["heading"]["family"] == "Archivo Black"
    # Keyed on (name, bold): a family's Regular and Bold share a name by design.
    names = {}
    for f in faces.values():
        names.setdefault(T.word_font(f["family"], f["weight"]), set()).add(
            (f["family"], f["weight"]))
    assert all(len(v) == 1 for v in names.values()), names


# ---- the package stays valid ---------------------------------------------------

@pytest.mark.parametrize("base,key,keys,_", COMBOS, ids=[f"{c[1]}-{i}" for i, c in enumerate(COMBOS)])
def test_themed_styles_follow_schema_order(base, key, keys, _):
    _, styles = _parts(render_docx(dict(base, **keys), key))
    for rpr in styles.iter(f"{W}rPr"):
        seen = [c.tag[len(W):] for c in rpr if c.tag.startswith(W)]
        pos = [T.RPR_ORDER.index(t) for t in seen if t in T.RPR_ORDER]
        assert pos == sorted(pos), seen


@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
@pytest.mark.parametrize("data", [ENGLISH, ARABIC], ids=["en", "ar"])
def test_no_themed_run_overrides_its_style(key, data):
    """Direct formatting beats a style: a styled run with its own face, bold
    or colour would silently ignore the theme."""
    doc, _ = _parts(render_docx(data, key))
    styled = 0
    for r in doc.iter(f"{W}r"):
        rpr = r.find(f"{W}rPr")
        if rpr is None or rpr.find(f"{W}rStyle") is None:
            continue
        styled += 1
        fonts = rpr.find(f"{W}rFonts")
        assert fonts is None or not fonts.get(f"{W}ascii"), "direct face on a styled run"
        assert rpr.find(f"{W}b") is None, "direct bold on a styled run"
        if rpr.find(f"{W}rStyle").get(f"{W}val") != "CVBodyBold":  # title keeps MUTED
            assert rpr.find(f"{W}color") is None, "direct colour on a styled run"
    assert styled >= 5


@pytest.mark.parametrize("master", ["ats_standard.docx", "ats_standard_rtl.docx",
                                    "modern_editorial.docx", "modern_editorial_rtl.docx"])
def test_no_master_asks_for_italic(master):
    """No built face has an italic, so any italic would be slanted by Word
    itself - a faked style. The Modern job title was the one (user,
    2026-09-27)."""
    from pathlib import Path
    masters = Path(__file__).resolve().parents[1] / "word_masters"
    with zipfile.ZipFile(masters / master) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        styles = etree.fromstring(z.read("word/styles.xml"))
    # What the file DRAWS: its runs, Normal and the role styles. python-docx's
    # default styles.xml also defines unused built-ins (Quote, Emphasis...)
    # that are italic; nothing here applies them.
    rprs = list(doc.iter(f"{W}rPr"))
    rprs += [_style(styles, sid) for sid in set(STYLE_IDS.values()) | {"CVAccentText"}]
    for rpr in rprs:
        for tag in ("i", "iCs"):
            el = rpr.find(f"{W}{tag}")
            assert el is None or el.get(f"{W}val") in ("0", "false"), f"{master} asks for italic"


# ---- the download menu -----------------------------------------------------------

@pytest.fixture()
def client():
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize("lang,text", [
    ("en", "Word: editable version · PDF: exact design"),
    ("ar", "Word: نسخة قابلة للتحرير · PDF: التصميم الدقيق"),
])
def test_the_download_menu_says_what_each_export_is(client, lang, text):
    client.set_cookie("ui_lang", lang)
    html = client.get("/builder").get_data(as_text=True)
    assert 'id="dl-note"' in html and text in html
