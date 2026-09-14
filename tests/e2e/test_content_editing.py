"""Content editing that changes the *shape* of the résumé, not just a value.

Adding and removing entries re-renders the whole form (`onChange(true)`), and
two of the project's standing rules live on this path: a stat chip with no
metric must vanish entirely, and a photo must reach both the canvas and the
export. The unit tests cover `normalize()` and `POST /api/photo` in isolation;
what is untested is the same rules surviving the round trip through the form.
"""
from __future__ import annotations

import io

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

# modern-t1 (the default) has no photo slot — 16 of the 24 Modern layouts do.
PHOTO_KEY = "modern-t11"


def _select(page, live_server, key: str):
    resp = page.request.post(live_server.url + "/api/template",
                             data={"template_key": key})
    assert resp.ok, resp.text()


@pytest.fixture()
def photo_file(tmp_path):
    """A deliberately non-square PNG, so the server's centre-crop is visible in
    the result rather than a no-op."""
    from PIL import Image
    path = tmp_path / "portrait.png"
    img = Image.new("RGB", (900, 600), (200, 60, 40))
    img.paste(Image.new("RGB", (120, 120), (10, 10, 200)), (390, 240))  # centre mark
    img.save(path)
    return path


def test_adding_and_removing_a_tool_reaches_the_preview(page, live_server):
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Figma")

    page.click('details.sec[data-sid="tools"] > summary')
    add = page.locator('[data-act="add"][data-path="tools"]')
    add.scroll_into_view_if_needed()
    add.click()
    page.locator('input[name^="tools."]').last.fill("Blender")
    expect(canvas).to_contain_text("Blender")

    # remove the first tool (Figma) — the rows re-index, so this also proves the
    # form is rebuilt from data rather than patched in place
    page.locator('[data-act="rm"][data-path="tools"][data-idx="0"]').click()
    expect(canvas).not_to_contain_text("Figma")
    expect(canvas).to_contain_text("InDesign")
    expect(page.locator("#save-state")).to_have_text("Saved")

    tools = page.request.get(live_server.url + "/api/resume").json()["resume"]["tools"]
    assert "Figma" not in tools and tools[-1] == "Blender"


def test_a_stat_chip_with_no_metric_disappears_entirely(page, live_server):
    """A standing rule for every template: never a bordered chip with a floating
    caption and no number. `normalize()` drops it; this checks the rule holds
    from the form, where a user clears the metric but leaves the caption."""
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Designers led")

    page.click('details.sec[data-sid="achievements"] > summary')
    metric = page.locator('input[name="achievements.0.metric"]')
    metric.scroll_into_view_if_needed()
    metric.fill("")

    expect(canvas).not_to_contain_text("Designers led")   # caption goes with it
    expect(canvas).to_contain_text("Production budget")   # the others stay


def test_photo_upload_round_trips_to_canvas_and_pdf(page, live_server, photo_file, tmp_path):
    _select(page, live_server, PHOTO_KEY)
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Ashworth")
    expect(canvas.locator("img")).to_have_count(0)

    page.set_input_files("#f_photo_url", str(photo_file))

    # the form grows a thumbnail + Remove control once the upload returns a URL
    thumb = page.locator('#resume-form img[src^="/uploads/"]')
    expect(thumb).to_be_visible()
    expect(page.locator("[data-clear-photo]")).to_be_visible()
    expect(page.locator("#save-state")).to_have_text("Saved")

    url = page.request.get(live_server.url + "/api/resume").json()["resume"]["photo_url"]
    assert url.startswith("/uploads/")

    served = page.request.get(live_server.url + url)
    assert served.ok and served.headers["content-type"] == "image/jpeg"
    from PIL import Image
    got = Image.open(io.BytesIO(served.body()))
    assert got.width == got.height, f"server did not square-crop: {got.size}"
    assert max(got.size) <= 512, f"server did not downscale: {got.size}"

    # and it reaches the résumé itself, not just the form
    expect(canvas.locator(f'img[src="{url}"]')).to_have_count(1)

    # a photo must survive the export too — the Modern Word master has a 22mm
    # slot, and a PDF that drops it is the failure session 8 fixed
    page.click("#dl-toggle")
    with page.expect_download(timeout=180_000) as info:
        page.click("#dl-pdf")
    blob = info.value
    dest = tmp_path / blob.suggested_filename
    blob.save_as(dest)
    assert b"/Image" in dest.read_bytes(), "the PDF embeds no image at all"


def test_removing_a_photo_clears_it_everywhere(page, live_server, photo_file):
    _select(page, live_server, PHOTO_KEY)
    page.goto(live_server.url + "/builder")
    canvas = page.frame_locator("#preview-frame").locator(".tpl")
    expect(canvas).to_contain_text("Ashworth")

    page.set_input_files("#f_photo_url", str(photo_file))
    expect(page.locator('#resume-form img[src^="/uploads/"]')).to_be_visible()
    expect(canvas.locator('img[src^="/uploads/"]')).to_have_count(1)

    page.click("[data-clear-photo]")

    expect(page.locator('#resume-form img[src^="/uploads/"]')).to_have_count(0)
    expect(canvas.locator('img[src^="/uploads/"]')).to_have_count(0)
    expect(page.locator("#save-state")).to_have_text("Saved")
    assert page.request.get(
        live_server.url + "/api/resume").json()["resume"]["photo_url"] == ""
