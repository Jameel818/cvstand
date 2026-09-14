"""The Arabic user journey: the same builder, driven the other way round.

WHY A SECOND JOURNEY FILE RATHER THAN A `lang` PARAMETER ON THE FIRST

    `test_journey.py` asserts on English strings — "Your résumé", the template
    label, "Saved". Parametrising it would turn every assertion into a lookup
    and would still not cover what is actually different here, which is not the
    strings but the SHAPE of the page: `dir="rtl"` on the shell, `dir="rtl"`
    inside the preview iframe, a language switcher that has to change one of
    those without changing the other.

    The two languages are independent by design (app/i18n.py): the résumé's
    `lang` is a property of the document, the `ui_lang` cookie a property of
    the reader. Every phase-6 test of that independence is a request-level
    test. This is the only place the two are exercised through a real browser
    at the same time, which is where they would actually be wired together by
    accident — a `document.dir` set from the wrong source, a form re-render
    that reads the shell's language for a level word.

WHAT IS DELIBERATELY NOT HERE

    Nothing re-tests the layout mirroring or the Arabic typography: phases 4-5
    gate those geometrically over all 49 templates, which a journey could only
    duplicate more weakly. This file covers the journey — that an Arabic
    résumé can be opened, edited, previewed, re-templated and exported without
    the interface language and the document language interfering.
"""
from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

from app import registry
from app.i18n import COOKIE
from app.labels import ui_t
from tests import samples

pytestmark = pytest.mark.e2e


@pytest.fixture()
def arabic_resume(seed_resume):
    """An Arabic document, before the browser is pointed at anything.

    Written straight to the data dir rather than through the API for the reason
    the shared `seed_resume` fixture exists: the store re-reads the file per
    request, so there is nothing to invalidate, and going through autosave
    would couple the fixture to the path several of these tests exercise."""
    seed_resume(samples.ARABIC)
    return samples.ARABIC


@pytest.fixture()
def arabic_ui(page, live_server):
    """The interface in Arabic, set the way the switcher sets it."""
    page.context.add_cookies([{
        "name": COOKIE, "value": "ar",
        "url": live_server.url,
    }])
    return page


def _preview(page):
    return page.frame_locator("#preview-frame").locator(".tpl")


def _surname(full: str) -> str:
    """The part of a name that is always ONE element in the render.

    `modern-t1` — the default template — does `r.name.split(" ", 1)` and sets
    the two halves separately, so the full name never appears as one string in
    the DOM. The English journey has always asserted on "Ashworth" for the same
    reason; this just derives it instead of hard-coding it."""
    return full.split(" ", 1)[-1]


#: The surname as it is drawn, and the full name as it is stored.
AR_SURNAME = _surname(samples.ARABIC["name"])


# ------------------------------------------------------ the document is Arabic

def test_an_arabic_resume_opens_right_to_left_in_the_builder(page, live_server,
                                                             arabic_resume):
    """The preview iframe is a whole separate document with its own `dir`.

    Asserted on the iframe's own <html>, not on the builder page: the shell is
    still English here (no cookie), so a test that only looked at the outer
    page would pass while the résumé rendered left-to-right."""
    page.goto(live_server.url + "/builder")
    expect(_preview(page)).to_contain_text(_surname(arabic_resume["name"]))

    frame = page.frame_locator("#preview-frame")
    assert frame.locator("html").get_attribute("dir") == "rtl"
    assert frame.locator("html").get_attribute("lang") == "ar"
    # ... while the interface around it is untouched
    assert page.locator("html").get_attribute("dir") == "ltr"


def test_editing_an_arabic_field_reaches_the_preview_and_the_server(
        page, live_server, arabic_resume):
    """The full round trip in Arabic: keystroke -> 350ms debounce -> /api/render
    -> iframe, and 900ms -> PUT /api/resume -> disk -> reload."""
    page.goto(live_server.url + "/builder")
    canvas = _preview(page)
    expect(canvas).to_contain_text(_surname(arabic_resume["name"]))

    new_name = "ريم القاسمي"
    page.fill("#f_name", new_name)

    expect(canvas).to_contain_text(_surname(new_name))
    expect(canvas).not_to_contain_text(AR_SURNAME)
    expect(page.locator("#save-state")).to_have_text("Saved")

    stored = page.request.get(live_server.url + "/api/resume").json()["resume"]
    assert stored["name"] == new_name
    assert stored["lang"] == "ar", "editing a field must not drop the language"

    page.reload()
    expect(page.locator("#f_name")).to_have_value(new_name)


def test_mixed_content_survives_a_round_trip_through_the_builder(
        page, live_server, seed_resume):
    """An Arabic résumé naming an English employer, typed rather than seeded.

    The bidi gates in tests/test_bidi_mixed.py measure how mixed text is DRAWN.
    This measures whether it survives the trip at all: an `&` through JSON,
    autosave, the schema, Jinja autoescape and back into a form value is four
    encodings deep, and the failure would be a mangled `&amp;amp;` in the
    user's own file rather than anything visible in a render test."""
    seed_resume(samples.ARABIC)
    page.goto(live_server.url + "/builder")
    canvas = _preview(page)
    expect(canvas).to_contain_text(AR_SURNAME)

    page.click('details.sec[data-sid="experience"] > summary')
    company = page.locator('input[name="experience.0.company"]')
    company.scroll_into_view_if_needed()
    company.fill("Halden & Row")

    expect(canvas).to_contain_text("Halden & Row")
    expect(page.locator("#save-state")).to_have_text("Saved")

    stored = page.request.get(live_server.url + "/api/resume").json()["resume"]
    assert stored["experience"][0]["company"] == "Halden & Row", (
        "the ampersand was re-encoded somewhere in the round trip")

    page.reload()
    expect(page.locator('input[name="experience.0.company"]')).to_have_value(
        "Halden & Row")


def test_switching_template_keeps_the_document_arabic(page, live_server,
                                                      arabic_resume):
    """The drawer sets `meta.template_key`, which is not part of the résumé —
    but the re-render goes through the same route, and a template key is the
    one input to `document_html()` besides the data."""
    page.goto(live_server.url + "/builder")
    expect(_preview(page)).to_contain_text(_surname(arabic_resume["name"]))

    page.click("#open-drawer")
    drawer = page.locator("#drawer")
    expect(drawer).to_have_attribute("aria-hidden", "false")
    key = "modern-t5"
    item = drawer.locator(f'.drawer-item[data-key="{key}"]')
    item.scroll_into_view_if_needed()
    item.click()

    expect(page.locator("#tpl-label")).to_have_text(registry.get(key).label)
    frame = page.frame_locator("#preview-frame")
    expect(frame.locator(".tpl")).to_contain_text(_surname(arabic_resume["name"]))
    assert frame.locator("html").get_attribute("dir") == "rtl"


#: Chromium cold-starts inside the server for the PDF; same budget as
#: tests/e2e/test_exports.py, which is where that number was established.
EXPORT_TIMEOUT = 180_000


@pytest.mark.parametrize("item,suffix", [("#dl-pdf", ".pdf"), ("#dl-docx", ".docx")])
def test_both_exports_download_for_an_arabic_resume(page, live_server, tmp_path,
                                                    arabic_resume, item, suffix):
    """Both exporters, driven from the real download menu.

    The DOCX path is the one that can 501 here: phase 7 makes a missing RTL
    master RAISE rather than fall back, deliberately, so that an Arabic résumé
    can never be handed a left-to-right Word file with English headings. That
    choice is only safe if the master is actually present, which is a fact
    about the built artefact rather than about the code — so it is asserted
    through the button a user presses, not through the exporter."""
    page.goto(live_server.url + "/builder")
    expect(_preview(page)).to_contain_text(_surname(arabic_resume["name"]))

    page.click("#dl-toggle")
    expect(page.locator("#dl-menu")).to_have_class(re.compile("is-open"))
    with page.expect_download(timeout=EXPORT_TIMEOUT) as got:
        page.click(item)
    dl = got.value
    assert dl.suggested_filename.endswith(suffix)
    dest = tmp_path / dl.suggested_filename
    dl.save_as(dest)
    assert dest.stat().st_size > 1000


# ------------------------------------------- the interface is independently Arabic

def test_the_language_switcher_flips_the_interface_only(page, live_server,
                                                        arabic_resume):
    """The property phase 6 exists for, through a browser.

    An English résumé read in an Arabic interface is an ordinary case, so the
    switcher must move the shell and leave the document alone. The failure if
    they are wired together is silent and lands in the user's file: a level
    word chosen in an Arabic form would be STORED in an English résumé and
    printed on the page.

    Driven from the GALLERY, not the builder: `builder.html` overrides
    `{% block chrome %}` with an empty block, so the header — and with it the
    switcher — does not exist on the page where a person spends their time.
    The cookie set here still governs the builder, which is what the last leg
    asserts."""
    page.goto(live_server.url + "/templates")
    assert page.locator("html").get_attribute("dir") == "ltr"

    page.click(".lang-switch a[lang='ar']")
    assert page.locator("html").get_attribute("dir") == "rtl"
    assert page.locator("html").get_attribute("lang") == "ar"
    expect(page.locator(".lang-switch a[lang='ar']")).to_have_attribute(
        "aria-current", "true")

    # the document was already Arabic and is still Arabic — untouched
    assert page.request.get(
        live_server.url + "/api/resume").json()["resume"]["lang"] == "ar"

    # the cookie reaches the builder even though the switcher is not drawn there
    page.goto(live_server.url + "/builder")
    assert page.locator("html").get_attribute("dir") == "rtl"
    assert page.locator(".lang-switch").count() == 0, (
        "the builder grew a language switcher; this test drives it from the "
        "gallery only because there was none")

    # and back again: the shell returns to English, the document does not move
    page.goto(live_server.url + "/templates")
    page.click(".lang-switch a[lang='en']")
    assert page.locator("html").get_attribute("dir") == "ltr"
    assert page.request.get(
        live_server.url + "/api/resume").json()["resume"]["lang"] == "ar"


def test_an_english_resume_in_an_arabic_interface(arabic_ui, live_server):
    """The other half of the independence, and the commoner one: a bilingual
    person applying to an English-speaking employer.

    `clean_state` leaves the English sample in place; only the cookie is
    Arabic."""
    page = arabic_ui
    page.goto(live_server.url + "/builder")

    assert page.locator("html").get_attribute("dir") == "rtl"

    frame = page.frame_locator("#preview-frame")
    expect(frame.locator(".tpl")).to_contain_text("Ashworth")
    assert frame.locator("html").get_attribute("dir") == "ltr", (
        "the interface language must not reach the document")
    assert frame.locator("html").get_attribute("lang") == "en"


def test_the_level_dropdown_follows_the_document_not_the_reader(
        arabic_ui, live_server, arabic_resume):
    """The sharpest case in the whole feature.

    A level word is not interface chrome — it is STORED in the résumé and
    printed on the page. So the options offered must be in the document's
    language even when the form around them is not, or an Arabic interface
    would quietly write English level words into an Arabic CV.

    Read here with an Arabic document under an Arabic interface, and asserted
    the other way round below, so a version that simply followed the shell
    would pass one and fail the other."""
    page = arabic_ui
    page.goto(live_server.url + "/builder")
    page.click('details.sec[data-sid="skills"] > summary')
    select = page.locator('select[name="skills.0.level"]')
    select.scroll_into_view_if_needed()
    options = select.locator("option").all_text_contents()
    assert "خبير" in options, f"Arabic document, Arabic levels expected: {options}"
    assert "Expert" not in options


def test_an_english_document_keeps_english_levels_in_an_arabic_interface(
        arabic_ui, live_server):
    """The mirror of the test above. `clean_state` leaves the English sample in
    place, and the interface cookie is Arabic."""
    page = arabic_ui
    page.goto(live_server.url + "/builder")
    assert page.locator("html").get_attribute("dir") == "rtl"

    page.click('details.sec[data-sid="skills"] > summary')
    select = page.locator('select[name="skills.0.level"]')
    select.scroll_into_view_if_needed()
    options = select.locator("option").all_text_contents()
    assert "Expert" in options, f"English document, English levels expected: {options}"
    assert "خبير" not in options


def test_the_interface_language_survives_a_reload(arabic_ui, live_server):
    """It is a cookie, not a session — the whole mechanism, in an app whose
    selling point is that it stores nothing server-side."""
    page = arabic_ui
    page.goto(live_server.url + "/templates")
    assert page.locator("html").get_attribute("dir") == "rtl"
    expect(page.locator(".tab.is-active")).to_have_text(ui_t("All", "ar"))

    page.reload()
    assert page.locator("html").get_attribute("dir") == "rtl"

    page.goto(live_server.url + "/")
    assert page.locator("html").get_attribute("dir") == "rtl"


def test_the_gallery_previews_arabic_under_an_arabic_interface(arabic_ui,
                                                               live_server):
    """The 49 gallery thumbnails are live `/preview` renders, not stock images,
    and they render the SHOWCASE sample in the reader's interface language.

    This test used to assert the opposite — that the cards showed the user's
    own résumé — and it was rewritten, not repaired, when that contract was
    deliberately inverted (2026-09-08). The cards are a demonstration of the
    layout, so an Arabic visitor sees Arabic résumés. What survives from the
    old test is the reason it existed: 49 real renders go through one route,
    and a template that 500s shows an empty card and says nothing."""
    page = arabic_ui
    page.goto(live_server.url + "/templates?cat=ats")
    frames = page.locator(".tpl-thumb iframe")
    expect(frames).to_have_count(len(registry.by_category("ats")))
    for i in range(3):
        src = frames.nth(i).get_attribute("src")
        assert "showcase" in src, "a gallery card stopped asking for the showcase"
        resp = page.request.get(live_server.url + src)
        assert resp.status == 200
        body = resp.text()
        assert 'dir="rtl"' in body
        assert _surname(samples.ARABIC["name"]) in body


def test_the_gallery_ignores_the_documents_language(page, live_server,
                                                    arabic_resume):
    """The sharp version: the user's own résumé is ARABIC and the interface is
    ENGLISH, so the cards must be English.

    Kept as its own test because it is the assertion that fails if someone
    "simplifies" the showcase to read `resume["lang"]` — which would look
    right in every other case and is exactly the coupling app/i18n.py exists
    to prevent."""
    page.goto(live_server.url + "/templates?cat=ats")
    src = page.locator(".tpl-thumb iframe").first.get_attribute("src")
    body = page.request.get(live_server.url + src).text()
    assert 'dir="ltr"' in body
    assert "Ashworth" in body
    assert _surname(arabic_resume["name"]) not in body


def test_the_arabic_journey_leaves_the_data_dir_valid(page, live_server,
                                                      arabic_resume):
    """After the round trip the file on disk is still a valid résumé.

    Autosave writes whatever the form serialised. A form that dropped `lang`
    on a structural re-render would leave a file that still validates but has
    silently become English — valid, saved, and wrong."""
    page.goto(live_server.url + "/builder")
    expect(_preview(page)).to_contain_text(_surname(arabic_resume["name"]))
    page.fill("#f_title", "مديرة فنية")
    expect(page.locator("#save-state")).to_have_text("Saved")

    from app.schema import validate

    stored = json.loads(
        (live_server.data_dir / "resume.json").read_text(encoding="utf-8"))
    validate(stored)
    assert stored["lang"] == "ar"
    assert stored["title"] == "مديرة فنية"
