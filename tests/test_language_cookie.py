"""The language choice, request by request (user, 2026-10-08): a long-lived
cookie, renewed by every page view, never written by anything but the
switcher's /lang/<code>, and honoured by the error pages too.

tests/e2e/test_language_choice_sticks.py walks the whole site in a browser.
"""
from __future__ import annotations

import pytest

from app import create_app
from app.i18n import COOKIE, COOKIE_MAX_AGE


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _set_cookies(resp):
    return [h for h in resp.headers.getlist("Set-Cookie") if h.startswith(COOKIE + "=")]


def test_the_switcher_stores_a_long_lived_site_wide_cookie(client):
    resp = client.get("/lang/ar?next=/templates")
    (c,) = _set_cookies(resp)
    assert c.startswith(f"{COOKIE}=ar") and f"Max-Age={COOKIE_MAX_AGE}" in c
    assert "Path=/" in c and "SameSite=Lax" in c
    assert COOKIE_MAX_AGE >= 365 * 86400


@pytest.mark.parametrize("path", ["/", "/templates", "/builder", "/account/sign-in", "/no-such-page"])
def test_every_page_view_renews_the_year(client, path):
    client.set_cookie(COOKIE, "ar")
    (c,) = _set_cookies(client.get(path))
    assert c.startswith(f"{COOKIE}=ar") and f"Max-Age={COOKIE_MAX_AGE}" in c


@pytest.mark.parametrize("path", ["/static/css/app.css", "/manifest.webmanifest"])
def test_files_do_not_carry_the_cookie(client, path):
    client.set_cookie(COOKIE, "ar")
    assert not _set_cookies(client.get(path))


def test_no_page_writes_a_choice_nobody_made(client):
    """Without a choice, nothing is stored - not even what the browser said."""
    for path in ("/", "/templates", "/builder", "/no-such-page"):
        resp = client.get(path, headers={"Accept-Language": "ar"})
        assert not _set_cookies(resp), path


@pytest.mark.parametrize("lang,browser", [("ar", "en-US"), ("en", "ar-SA")])
def test_the_choice_beats_the_browser_language_on_every_page(client, lang, browser):
    client.set_cookie(COOKIE, lang)
    for path in ("/", "/templates", "/builder", "/account/sign-up", "/no-such-page"):
        html = client.get(path, headers={"Accept-Language": browser}).get_data(as_text=True)
        assert f'<html lang="{lang}"' in html, path


def test_the_error_page_speaks_the_choice_and_offers_the_switch(client):
    client.set_cookie(COOKIE, "ar")
    resp = client.get("/no-such-page")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 404
    assert "الصفحة غير موجودة" in html and 'dir="rtl"' in html
    assert 'class="lang-switch"' in html


def test_machine_errors_stay_plain(client):
    """The builder reads these as text: no HTML shell around them."""
    resp = client.get("/api/no-such-thing")
    assert resp.status_code == 404 and "lang-switch" not in resp.get_data(as_text=True)


def test_the_switcher_returns_to_the_same_page_and_filter(client):
    client.set_cookie(COOKIE, "en")
    html = client.get("/templates?cat=ats").get_data(as_text=True)
    assert "/lang/ar?next=/templates?cat%3Dats" in html or "/lang/ar?next=%2Ftemplates%3Fcat%3Dats" in html
    resp = client.get("/lang/ar?next=/templates?cat=ats")
    assert resp.headers["Location"].endswith("/templates?cat=ats")
