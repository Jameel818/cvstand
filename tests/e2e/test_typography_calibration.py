"""The step 7 calibration page (spec §7.4) drawn by Chromium: every offered
face loads, and the page is saved to tests/e2e/artifacts/ for a person to
judge (the gitignored artifacts folder the other e2e tests use)."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from tests.e2e.conftest import ARTIFACTS

ORIGIN = "http://cal.local"
STATIC = Path("app/static").resolve()


def test_calibration_page_draws_every_face(page):
    from app import create_app
    app = create_app()
    app.debug = True
    html = app.test_client().get("/dev/typography").get_data(as_text=True)

    def serve(route):
        path = route.request.url.split(ORIGIN, 1)[1].split("?", 1)[0]
        if path == "/":
            return route.fulfill(body=html, content_type="text/html")
        f = (STATIC / path.removeprefix("/static/")).resolve()
        if STATIC not in f.parents or not f.is_file():
            return route.fulfill(status=404, body="")
        route.fulfill(body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or "font/woff2")

    page.route(f"{ORIGIN}/**", serve)
    page.goto(f"{ORIGIN}/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    missing = page.evaluate("""() => [...document.querySelectorAll('tr[data-family]')]
        .filter(r => !document.fonts.check(
            `${r.dataset.weight} 16px "CVT ${r.dataset.family}"`, r.cells[2].textContent))
        .map(r => r.dataset.family + ' ' + r.dataset.weight)""")
    assert not missing, missing
    assert page.locator("tr[data-family]").count() > 60
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(ARTIFACTS / "typography_calibration.png"), full_page=True)
