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
    3. the name carries the TEMPLATE's accent (text-safe variant), not the
       master's built-in navy;
    4. every face those styles draw is embedded in the file.
"""
from __future__ import annotations

import io
import re
import zipfile

import pytest
from playwright.sync_api import expect

from app.exporters.docx_theme import RULE_ACCENT, text_safe, themes

pytestmark = pytest.mark.e2e

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

        page.click('.sec[data-sid="fonts"] > summary')
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

    # 2. the fonts, in the role styles
    for style_id, want in word_names.items():
        assert _family(_style(styles, style_id)) == want, (
            f"{style_id} draws {_family(_style(styles, style_id))!r}, expected {want!r}")

    # 3. the template's accent, not the master's navy
    accent = text_safe(themes()[key][lang]["accent"].lstrip("#")).upper()
    got = _color(_style(styles, "CVName"))
    assert got == accent, f"name colour {got}, template {key} accent is {accent}"
    assert got != RULE_ACCENT.upper()

    # 4. every face those styles draw is embedded
    table = z.read("word/fontTable.xml").decode("utf-8")
    embedded = set(re.findall(
        r'<w:font w:name="([^"]+)">(?:(?!</w:font>).)*?<w:embed', table, re.S))
    assert set(word_names.values()) <= embedded, (
        f"not embedded: {set(word_names.values()) - embedded}")
    assert "embedTrueTypeFonts" in z.read("word/settings.xml").decode("utf-8")
    assert sum(n.endswith(".odttf") for n in z.namelist()) == len(embedded)
