"""The Word download follows what the visitor chose in the builder.

WHY THIS FILE EXISTS
    Every earlier Word check (test_docx_theme.py, test_docx_font_embed.py, the
    live check after the 2026-09-28 deploy) POSTed to /export/docx directly.
    None drove the path a visitor takes: the gallery's "Use this", the Fonts
    section, then the real #dl-docx button, in a browser with no saved
    anything. On 2026-09-29 a real Incognito download "looked plain" and there
    was no test able to say whether the template key and the font keys even
    reached the server. (They did: the file was themed; Word has two layouts
    by design, so a Modern template's own layout is not carried. See
    docs/WORD_LAYOUTS_PLAN.md.)

WHAT IT CLAIMS, per language, on a server configured like the public one
(CVSTAND_SERVER_STORE=0, fresh browser context = no cookie, no storage):
    1. the request the button sends carries the chosen template_key and the
       chosen font keys;
    2. the file's name / heading / body styles use those fonts;
    3. the name carries the TEMPLATE's own colour, never the master's
       placeholder navy: on a Word layout the colour measured from the PDF,
       readable on the cell it sits on (docs/WORD_LAYOUTS_PLAN.md §10.4);
       on the single-column master the readable accent;
    4. every face those styles draw is embedded in the file.
"""
from __future__ import annotations

import io
import re
import zipfile

import pytest
from lxml import etree
from playwright.sync_api import expect

from app.exporters import docx_layout
from app.exporters.docx_design import has_design
from app.exporters.docx_theme import RULE_ACCENT, text_safe, themes

pytestmark = pytest.mark.e2e
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

EXPORT_TIMEOUT = 120_000

# (ui language, template, font selects, expected Word family per role style).
# Weight is left at "template": Montserrat snaps to modern-t16's own 800 and
# Cairo to modern-t8's name weight 800, hence the ExtraBold names.
CASES = {
    "en": ("modern-t16",
           {"#ty_heading_font": "Montserrat", "#ty_body_font": "Inter"},
           {"font_heading": "Montserrat", "font_body": "Inter"},
           {"CVName": "Montserrat ExtraBold", "CVHeading": "Montserrat ExtraBold",
            "Normal": "Inter"}),
    "ar": ("modern-t8",
           {"#ty_name_font": "Cairo", "#ty_heading_font": "Markazi Text",
            "#ty_body_font": "Alexandria"},
           {"font_name": "Cairo", "font_heading": "Markazi Text",
            "font_body": "Alexandria"},
           {"CVName": "Cairo ExtraBold", "CVHeading": "Markazi Text",
            "Normal": "Alexandria"}),
}


def _style(styles_xml: str, style_id: str) -> str:
    m = re.search(rf'w:styleId="{style_id}".*?</w:style>', styles_xml, re.S)
    assert m, f"style {style_id} missing from the downloaded file"
    return m.group(0)


def _family(style: str) -> str:
    m = re.search(r'<w:rFonts [^>]*w:ascii="([^"]+)"', style)
    return m.group(1) if m else ""


def _color(style: str) -> str:
    m = re.search(r'<w:color w:val="([0-9A-Fa-f]{6})"', style)
    return m.group(1).upper() if m else ""


@pytest.mark.parametrize("lang", sorted(CASES))
def test_the_word_button_sends_and_gets_the_chosen_template_and_fonts(
        browser, deployed_server, lang):
    key, selects, sent_fonts, word_names = CASES[lang]
    ctx = browser.new_context(viewport={"width": 1440, "height": 950},
                              accept_downloads=True)
    try:
        page = ctx.new_page()
        page.set_default_timeout(30_000)
        requests = []
        page.on("request", lambda r: requests.append(r)
                if r.method == "POST" and "/export/docx" in r.url else None)

        page.goto(f"{deployed_server.url}/lang/{lang}?next=/templates")
        page.locator(f'.use-btn[data-key="{key}"]').click()
        page.wait_for_url(re.compile(r"/builder"))
        expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()

        for sel, family in selects.items():
            page.select_option(sel, family)
        # the choice must be live in the preview before we download
        expect(page.frame_locator("#preview-frame").locator("html")).to_have_attribute(
            "data-cvt", re.compile(r".*"))

        page.click("#dl-toggle")
        with page.expect_download(timeout=EXPORT_TIMEOUT) as info:
            page.click("#dl-docx")
        blob = open(info.value.path(), "rb").read()
    finally:
        ctx.close()

    # 1. the request
    assert len(requests) == 1, f"expected one Word request, saw {len(requests)}"
    body = requests[0].post_data_json
    assert body["template_key"] == key
    assert (body["data"].get("lang") or "en") == lang       # English leaves lang unset
    for k, v in sent_fonts.items():
        assert body["data"].get(k) == v, f"{k}: sent {body['data'].get(k)!r}, chose {v!r}"

    assert blob[:2] == b"PK", "the download is not a .docx package"
    z = zipfile.ZipFile(io.BytesIO(blob))
    styles = z.read("word/styles.xml").decode("utf-8")

    # 2. the fonts, in the styles the text really uses. The name's style is
    #    the one its RUN carries: on a Word LAYOUT (docs/WORD_LAYOUTS_PLAN.md)
    #    a name in a band or a side column has that cell's own style.
    doc = etree.fromstring(z.read("word/document.xml"))
    name = body["data"]["name"]
    # the paragraph that spells the name; its first run carries the name's
    # style (a Word DESIGN may set the name in two runs, as its PDF does:
    # modern-t8's light first name + heavy surname)
    name_para = next(p for p in doc.iter(f"{W}p")
                     if "".join(t.text or "" for t in p.iter(f"{W}t")).strip() == name)
    name_run = next(r for r in name_para.iter(f"{W}r")
                    if "".join(t.text or "" for t in r.iter(f"{W}t")).strip())
    name_style = name_run.find(f"{W}rPr/{W}rStyle").get(f"{W}val")
    used = dict(word_names, **{name_style: word_names["CVName"]})
    if name_style != "CVName":
        del used["CVName"]
    for style_id, want in used.items():
        assert _family(_style(styles, style_id)) == want, (
            f"{style_id} draws {_family(_style(styles, style_id))!r}, expected {want!r}")

    # 3. the template's OWN name colour, not the master's placeholder navy: a
    #    layout takes it as measured from the PDF, readable on the cell it sits
    #    on; the single-column master takes the readable accent
    got = _color(_style(styles, name_style))
    if has_design(key):
        # a design colours the run itself, the template's own name colour;
        # it must read on whatever fill the name stands on
        got = name_run.find(f"{W}rPr/{W}color").get(f"{W}val").upper()
        cell = next(a for a in name_run.iterancestors() if a.tag == f"{W}tc")
        shd = cell.find(f"{W}tcPr/{W}shd")
        ground = shd.get(f"{W}fill") if shd is not None else "FFFFFF"
        want = got if docx_layout.contrast(got, ground) >= 3.0 else "readable on " + ground
    elif docx_layout.spec_for(key):
        cell = next(a for a in name_run.iterancestors() if a.tag == f"{W}tc")
        shd = cell.find(f"{W}tcPr/{W}shd")
        ground = shd.get(f"{W}fill") if shd is not None else "FFFFFF"
        want = docx_layout.readable(docx_layout.layouts()[key][lang]["name"]["color"], ground)
    else:
        want = text_safe(themes()[key][lang]["accent"].lstrip("#")).upper()
    assert got == want, f"name colour {got}, template {key} gives {want}"
    assert got != RULE_ACCENT.upper()

    # 4. every face those styles draw is embedded: one font part per embedded
    #    face (a Regular and its Bold share one name, so count the entries)
    table = z.read("word/fontTable.xml").decode("utf-8")
    embedded = set(re.findall(
        r'<w:font w:name="([^"]+)">(?:(?!</w:font>).)*?<w:embed', table, re.S))
    assert set(word_names.values()) <= embedded, (
        f"not embedded: {set(word_names.values()) - embedded}")
    assert "embedTrueTypeFonts" in z.read("word/settings.xml").decode("utf-8")
    entries = len(re.findall(r"<w:embed(?:Regular|Bold|Italic|BoldItalic) ", table))
    assert sum(n.endswith(".odttf") for n in z.namelist()) == entries
