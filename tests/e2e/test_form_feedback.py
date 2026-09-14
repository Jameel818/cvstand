"""What the builder tells the user when an action does not go through.

The suite already covers the happy paths and the auto-fit bar. What was left
untested is the rest of the feedback surface — the `#form-errors` box, the
`#save-state` indicator, and the download menu's open/close. These are the
parts a user reads when something looks wrong, so a silent failure here is
worse than a loud one: the app appears to be working and simply is not.

`test_a_rejected_render_surfaces_in_the_form` (test_journey.py) covers the
error box for an invalid *field value*. The cases here are different shapes of
the same question: an invalid *file*, an entry that is structurally incomplete,
and a menu that must not stay stuck open.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

# modern-t1 (the default) has no photo slot; modern-t11 does.
PHOTO_KEY = "modern-t11"


def test_a_rejected_photo_says_why_and_frees_the_save_indicator(page, live_server):
    """REGRESSION (2026-09-04). `/api/photo` rejects a non-image with
    `abort(415)`, which answers with an HTML error page — so the handler's
    `res.json()` threw, its `catch` ignored the throw, and the "Saving…" state
    set before the upload was never handed back. The indicator sat on "Saving…"
    for ever and nothing explained the missing photo."""
    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": PHOTO_KEY})
    assert resp.ok, resp.text()
    page.goto(live_server.url + "/builder")
    expect(page.locator("#save-state")).to_have_text("Saved")

    page.locator('input[data-photo="photo_url"]').set_input_files(
        {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"not an image"})

    errors = page.locator("#form-errors")
    expect(errors).to_have_class("form-errors show")
    expect(errors).to_contain_text("not a photo")

    # the indicator must come back to the truth — nothing was pending
    expect(page.locator("#save-state")).to_have_text("Saved")
    assert page.request.get(
        live_server.url + "/api/resume").json()["resume"].get("photo_url", "") == ""


def test_a_good_photo_after_a_rejected_one_clears_the_error(page, live_server):
    """The error box must not outlive the problem it describes — and the file
    input is reset on failure so a retry is possible without a page reload."""
    from PIL import Image
    import io as _io
    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": PHOTO_KEY})
    assert resp.ok, resp.text()
    page.goto(live_server.url + "/builder")

    photo = page.locator('input[data-photo="photo_url"]')
    photo.set_input_files({"name": "notes.txt", "mimeType": "text/plain",
                           "buffer": b"not an image"})
    expect(page.locator("#form-errors")).to_contain_text("not a photo")

    buf = _io.BytesIO()
    Image.new("RGB", (400, 300), (30, 90, 160)).save(buf, format="PNG")
    photo.set_input_files({"name": "portrait.png", "mimeType": "image/png",
                           "buffer": buf.getvalue()})

    expect(page.locator("#form-errors")).not_to_have_class("form-errors show")
    expect(page.locator("#save-state")).to_have_text("Saved")
    url = page.request.get(live_server.url + "/api/resume").json()["resume"]["photo_url"]
    assert url.startswith("/uploads/") and url.endswith(".jpg")


def test_adding_a_role_and_naming_it_works_end_to_end(page, live_server):
    """The whole "+ Add role" journey, which turned out to be broken in two
    places at once (both fixed 2026-09-04).

    `add` pushes a blank `{bullets: []}`, and the schema requires `role`, so the
    résumé is *briefly* invalid by construction — the builder must say so rather
    than silently saving or silently dropping the edit. That half worked.

    Typing the job title then made it schema-valid, and **that** is where it
    broke: `normalize()` had not defaulted `company`/`start`/`end`, the macros
    read `job.start` under `StrictUndefined`, and `/api/render` answered 500 on
    every one of the 49 templates. The builder compounded it by reporting a 500
    as "Could not reach the preview service", pointing at the network instead of
    the server. So: the error box must clear, the preview must actually show the
    new role, and it must reach the server."""
    page.goto(live_server.url + "/builder")
    page.click('details.sec[data-sid="experience"] > summary')
    add = page.locator('[data-act="add"][data-path="experience"]')
    add.scroll_into_view_if_needed()
    add.click()

    expect(page.locator('[data-list="experience"] .entry')).to_have_count(4)
    errors = page.locator("#form-errors")
    expect(errors).to_have_class("form-errors show")
    expect(errors).to_contain_text("experience/3")
    expect(errors).to_contain_text("'role' is a required property")
    expect(page.locator("#save-state")).to_have_text("Unsaved changes")

    # nothing reached the server while it was invalid
    exp = page.request.get(live_server.url + "/api/resume").json()["resume"]["experience"]
    assert len(exp) == 3

    row = page.locator('input[name="experience.3.role"]')
    row.scroll_into_view_if_needed()
    row.fill("Studio Intern")

    # No error of ANY kind — not the 422, and not the 500 that replaced it.
    expect(errors).not_to_have_class("form-errors show")
    expect(errors).to_have_text("")
    expect(page.locator("#save-state")).to_have_text("Saved")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_contain_text("Studio Intern")

    exp = page.request.get(live_server.url + "/api/resume").json()["resume"]["experience"]
    assert [e.get("role") for e in exp][-1] == "Studio Intern"


def test_the_download_menu_opens_and_closes_again(page, live_server):
    """`#dl-toggle` stops propagation so the document-level close handler does
    not eat its own opening click — a one-character regression there would
    leave the menu impossible to open, and no other test touches it."""
    page.goto(live_server.url + "/builder")
    menu = page.locator("#dl-menu")
    expect(menu).not_to_have_class("dl-menu is-open")

    page.click("#dl-toggle")
    expect(menu).to_have_class("dl-menu is-open")
    expect(page.locator("#dl-pdf")).to_be_visible()
    expect(page.locator("#dl-docx")).to_be_visible()

    page.mouse.click(20, 400)               # anywhere outside the menu
    expect(menu).not_to_have_class("dl-menu is-open")

    page.click("#dl-toggle")                # and it can be re-opened
    expect(menu).to_have_class("dl-menu is-open")


def test_a_file_that_only_looks_like_a_photo_says_why_not_error_500(page, live_server):
    """DEFECT 6 (2026-09-06). The test above sends `mimeType: "text/plain"`,
    which is what makes it stop at the mimetype gate — and that is exactly why
    it never caught this. **A real browser sets the part's mimetype from the
    file extension**, so a user who renames a document to `.png`, or picks a
    photo that only half-copied, sends `image/png` and sails straight past the
    gate into Pillow. The handler decoded unguarded, so `UnidentifiedImageError`
    escaped as an unhandled 500 and the builder printed "error 500" — the app
    blaming its own server for the user's file, the same wrong-layer message
    that hid a 500 on all 49 templates for eleven sessions.

    Sent here the way the browser really sends it: an image extension and an
    image mimetype over bytes that are not an image."""
    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": PHOTO_KEY})
    assert resp.ok, resp.text()
    page.goto(live_server.url + "/builder")
    expect(page.locator("#save-state")).to_have_text("Saved")

    page.locator('input[data-photo="photo_url"]').set_input_files(
        {"name": "headshot.png", "mimeType": "image/png",
         "buffer": b"This is my CV in a text file, saved with the wrong name."})

    errors = page.locator("#form-errors")
    expect(errors).to_have_class("form-errors show")
    expect(errors).to_contain_text("not a photo")
    expect(errors).not_to_contain_text("error 500")

    expect(page.locator("#save-state")).to_have_text("Saved")
    assert page.request.get(
        live_server.url + "/api/resume").json()["resume"].get("photo_url", "") == ""


def test_a_damaged_photo_is_told_apart_from_a_wrong_one(page, live_server):
    """A truncated photo has a valid header, so it survives `Image.open()` and
    only fails once the pixels are read. It needs its own advice: "use a PNG"
    is useless when the file already *is* a PNG, just an incomplete one. The
    builder shows the server's reason rather than mapping the status code,
    because only the server has read the bytes."""
    from PIL import Image
    import io as _io

    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": PHOTO_KEY})
    assert resp.ok, resp.text()
    page.goto(live_server.url + "/builder")

    buf = _io.BytesIO()
    Image.new("RGB", (700, 500), (40, 120, 80)).save(buf, format="PNG")
    half = buf.getvalue()[: len(buf.getvalue()) // 2]

    photo = page.locator('input[data-photo="photo_url"]')
    photo.set_input_files({"name": "interrupted.png", "mimeType": "image/png",
                           "buffer": half})

    errors = page.locator("#form-errors")
    expect(errors).to_have_class("form-errors show")
    expect(errors).to_contain_text("damaged")
    expect(errors).not_to_contain_text("error 500")
    expect(page.locator("#save-state")).to_have_text("Saved")

    # and a whole one still goes through afterwards, error box cleared
    photo.set_input_files({"name": "portrait.png", "mimeType": "image/png",
                           "buffer": buf.getvalue()})
    expect(errors).not_to_have_class("form-errors show")
    # The error box clears the moment the upload returns, but the résumé is
    # only PUT after the 900ms debounce — wait for the indicator, or this reads
    # the server before the save has landed.
    expect(page.locator("#save-state")).to_have_text("Saved")
    url = page.request.get(live_server.url + "/api/resume").json()["resume"]["photo_url"]
    assert url.startswith("/uploads/") and url.endswith(".jpg")


# --------------------------------------------------------------- the drawer
# Picking a template is the one builder action that talks to the server with
# NO feedback path of its own: the form has `#form-errors`, exports have their
# alert, saving has the indicator. The drawer had nothing, and the scrim covers
# the form while it is open, so `#form-errors` is not even visible from here.

SWITCH_TO = "modern-t5"


def _fail_switch(page, **fulfil):
    page.route("**/api/template", lambda route: route.fulfill(**fulfil))




def _break_storage(page):
    """Make this browser refuse to store anything, the way a locked-down one does.

    Not hypothetical: `localStorage.setItem` THROWS in a private window with
    site data blocked, rather than returning a falsy value. That is why
    `builder.js::writeStored` wraps every write — an uncaught throw here would
    take the builder down at the moment the user picks a template.
    """
    page.add_init_script(
        "Object.defineProperty(window, 'localStorage', {"
        "  value: { getItem: () => null,"
        "           setItem: () => { throw new Error('denied'); },"
        "           removeItem: () => {} } });"
    )


def _stored_template(page):
    return page.evaluate("() => { try { return localStorage.getItem('cvstand:template'); }"
                         " catch (_) { return null; } }")


def _switch(page, key=SWITCH_TO):
    page.click("#open-drawer")
    item = page.locator(f'#drawer-body .drawer-item[data-key="{key}"]')
    item.scroll_into_view_if_needed()
    item.click()
    return item


def test_a_switch_survives_a_server_that_refuses(page, live_server):
    """REVERSED 2026-09-10, and deliberately.

    DEFECT 7 (2026-09-06) was a switch that failed silently when the server
    said no: `if (!res.ok) return;`, drawer still open, nothing said. The fix
    then was to report it.

    The template choice now lives in localStorage, because the server no longer
    holds one résumé for one user — so a server error CANNOT fail the switch
    any more, and reporting one would be inventing a problem the user does not
    have. The POST that remains is a mirror for the local workflow, and its
    outcome is not the user's business.

    The silent-failure rule that DEFECT 7 established is not repealed; it moved
    to the store that can actually fail. See
    `test_a_browser_that_stores_nothing_says_so`.
    """
    page.goto(live_server.url + "/builder")
    from app import registry
    _fail_switch(page, status=500, content_type="text/html", body="<p>boom</p>")
    _switch(page)

    expect(page.locator("#tpl-label")).to_have_text(registry.get(SWITCH_TO).label)
    expect(page.locator("#drawer")).to_have_attribute("aria-hidden", "true")
    expect(page.locator("#drawer-error")).to_be_hidden()
    assert _stored_template(page) == SWITCH_TO


def test_a_switch_survives_an_unreachable_server(page, live_server):
    """The same, for a dropped connection rather than an error status.

    Worth its own test because the two take different paths in `fetch`: a 500
    resolves, an aborted request rejects. The old code had no `catch` at all
    and turned this into an unhandled rejection in the console.
    """
    page.goto(live_server.url + "/builder")
    from app import registry
    page.route("**/api/template", lambda route: route.abort())
    _switch(page)

    expect(page.locator("#tpl-label")).to_have_text(registry.get(SWITCH_TO).label)
    expect(page.locator("#drawer")).to_have_attribute("aria-hidden", "true")
    expect(page.locator("#drawer-error")).to_be_hidden()


def test_a_browser_that_stores_nothing_says_so(page, live_server):
    """DEFECT 7's rule, at its new address.

    If the switch cannot be recorded, the click must not look like a click on
    the already-current template. The drawer stays open so it can be retried,
    and nothing may claim the switch happened.
    """
    _break_storage(page)
    page.goto(live_server.url + "/builder")
    from app import registry
    start = registry.get(registry.default_key()).label
    expect(page.locator("#tpl-label")).to_have_text(start)

    _switch(page)

    err = page.locator("#drawer-error")
    expect(err).to_be_visible()
    expect(err).to_contain_text("could not")
    expect(page.locator("#drawer")).to_have_attribute("aria-hidden", "false")
    expect(page.locator("#tpl-label")).to_have_text(start)


def test_the_switch_error_clears_once_a_switch_works(page, live_server):
    """The message must not outlive the problem — the same rule the photo error
    box follows. Driven by the storage failure now, since that is the only way
    a switch can fail."""
    page.goto(live_server.url + "/builder")
    from app import registry

    # Refuse the write, click, and expect to be told.
    page.evaluate(
        "() => { window.__realSet = localStorage.setItem.bind(localStorage);"
        "        localStorage.setItem = () => { throw new Error('denied'); }; }"
    )
    _switch(page)
    expect(page.locator("#drawer-error")).to_be_visible()

    # Give storage back and click again.
    page.evaluate("() => { localStorage.setItem = window.__realSet; }")
    page.locator(f'#drawer-body .drawer-item[data-key="{SWITCH_TO}"]').click()

    expect(page.locator("#tpl-label")).to_have_text(registry.get(SWITCH_TO).label)
    expect(page.locator("#drawer")).to_have_attribute("aria-hidden", "true")
    expect(page.locator("#drawer-error")).to_be_hidden()
    assert _stored_template(page) == SWITCH_TO
