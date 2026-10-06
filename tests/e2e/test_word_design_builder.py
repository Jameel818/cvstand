"""The REAL builder path reaches the per-template Word DESIGN (run 4, item 1d).

Every other Word test calls render_docx() directly; the user found the builder
path unverified. This drives what a person does: pick the template with "Use
this" in the gallery, switch the interface language, choose a font and a size
in the Fonts panel, open the download menu and press "Word". The file must be
the template's own design (docs/WORD_FIDELITY_AUDIT.md) - its graphics as
drawings, its own heading words - and carry the font and the size chosen, and
be right-to-left in Arabic."""
from __future__ import annotations

import io
import re
import zipfile
from collections import Counter

import pytest
from playwright.sync_api import expect

from tests.e2e.test_exports import EXPORT_TIMEOUT

# (template, a heading word it prints in EN / AR, the design drawing it must carry)
CASES = [("modern-t2", "EXPERIENCE", "الخبرة", "cvstand_bar_"),
         ("modern-t11", "Experience", "الخبرة", "cvstand_dots_"),
         ("modern-t22", "WORK EXPERIENCE", "الخبرة العملية", "cvstand_rail")]
FONT = {"en": "Montserrat", "ar": "Cairo"}
BODY_SIZE = "11"


def _download_word(page, tmp_path):
    page.click("#dl-toggle")
    expect(page.locator("#dl-menu")).to_have_class(re.compile("is-open"))
    with page.expect_download(timeout=EXPORT_TIMEOUT) as info:
        page.click("#dl-docx")
    dest = tmp_path / info.value.suggested_filename
    info.value.save_as(dest)
    return dest.read_bytes()


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key,head_en,head_ar,drawing", CASES)
def test_builder_word_download_is_the_template_design(page, live_server, tmp_path, key,
                                                      head_en, head_ar, drawing, lang):
    if lang == "ar":
        page.goto(f"{live_server.url}/lang/ar?next=/templates")
    page.goto(f"{live_server.url}/templates")
    page.locator(f'.use-btn[data-key="{key}"]').first.click()
    expect(page).to_have_url(re.compile(r"/builder"))
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()

    page.click('.sec[data-sid="fonts"] > summary')
    page.select_option("#ty_heading_font", FONT[lang])
    page.select_option("#ty_body_size", BODY_SIZE)
    page.wait_for_timeout(1200)                       # the debounced save

    blob = _download_word(page, tmp_path)
    z = zipfile.ZipFile(io.BytesIO(blob))
    xml = z.read("word/document.xml").decode("utf-8")
    parts = xml + "".join(z.read(n).decode("utf-8", "ignore")
                          for n in z.namelist() if n.startswith("word/header"))
    # the template's own DESIGN, not the generic layout
    assert drawing in parts, f"{key}: the per-template design's drawings are missing"
    texts = [t for t in re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml)]
    assert (head_ar if lang == "ar" else head_en) in texts, f"{key}: not its own headings"
    # the font chosen in the Fonts panel is embedded and drawn
    table = z.read("word/fontTable.xml").decode("utf-8")
    assert FONT[lang] in table, f"{FONT[lang]} not in the file's fonts"
    # the size chosen: the body's dominant size is 11pt CSS (x 4/3 x 0.72 x 2)
    sizes = Counter()
    for run in re.findall(r"<w:r>(.*?)</w:r>", xml, re.S):
        if "CVName" in run or "CVHeading" in run:
            continue
        sz = re.search(r'<w:sz w:val="(\d+)"', run)
        text = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", run))
        if sz and text.strip():
            sizes[int(sz.group(1))] += len(text)
    # the chosen 11pt; a page that would spill takes the PDF's type fit, down
    # to 0.90 of it (docx_design.TYPE_FIT_STEPS, run 7) - t22 does here
    want = round(11 * 4 / 3 * 0.72 * 2)
    assert round(want * 0.90) <= sizes.most_common(1)[0][0] <= want
    if lang == "ar":
        assert "<w:bidi/>" in xml and re.search(r"[؀-ۿ]", xml)
    else:
        assert "<w:bidiVisual/>" not in xml
