"""The CVStand logo files (feature/logo, 2026-11-08).

The brand assets were delivered final in seven files and installed unedited
into app/static/icons/. This gates the three ways that install can silently
regress: a file missing from the image (404 -- the page still renders, with
a broken icon nobody notices), base.html drifting back to the old inline
data: favicon, and the manifest losing an install size.

It also gates the one copy mistake the lockup invites: logo-mark.svg ALREADY
says "CV", so putting it, or the full lockup, next to an HTML "CVStand"
reads "CV CVStand".
"""
from __future__ import annotations

import re

import pytest

from app import create_app

ICONS = {
    "favicon.ico": b"\x00\x00\x01\x00",
    "apple-touch-icon.png": b"\x89PNG\r\n\x1a\n",
    "icon-192.png": b"\x89PNG\r\n\x1a\n",
    "icon-512.png": b"\x89PNG\r\n\x1a\n",
    "logo-mark.svg": b"<svg",
    "cvstand.svg": b"<svg",
    "cvstand-dark.svg": b"<svg",
}
CHROME_PAGES = ["/", "/templates"]


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize("name,magic", ICONS.items())
def test_every_icon_file_is_served(client, name, magic):
    res = client.get(f"/static/icons/{name}")
    assert res.status_code == 200, name
    assert res.data.startswith(magic), f"{name} is not the file type it claims"


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("path", CHROME_PAGES)
def test_base_html_uses_the_new_favicon_and_lockup(client, path, lang):
    client.set_cookie("ui_lang", lang)
    html = client.get(path).get_data(as_text=True)
    assert '<link rel="icon" href="/static/icons/favicon.ico" sizes="any">' in html
    assert 'rel="icon" href="data:' not in html, "the old inline favicon is back"
    assert html.count('src="/static/icons/cvstand.svg"') == 2, "header + footer"
    assert 'href="/static/icons/apple-touch-icon.png"' in html
    assert '<meta name="theme-color" content="#4f46e5">' in html
    # The lockup must never sit beside a text wordmark, nor the old mark.
    assert "logo-mark" not in html
    assert "CV<b>Stand</b>" not in html
    assert not re.search(r"CV\s*CVStand", html)


def _image(client, src):
    from io import BytesIO

    from PIL import Image
    res = client.get(src)
    assert res.status_code == 200, src
    return Image.open(BytesIO(res.data))


def test_every_manifest_icon_is_square_and_its_declared_size(client):
    """The first delivery was 192x183 / 512x489 under a manifest declaring
    192x192 / 512x512; Chrome rejects an install icon whose real size does
    not match `sizes`. Read the PNG itself, not the file name."""
    icons = client.get("/manifest.webmanifest").get_json()["icons"]
    for i in icons:
        w, h = (int(n) for n in i["sizes"].split("x"))
        assert _image(client, i["src"]).size == (w, h), i["src"]
    # Not in the manifest, but iOS expects 180x180.
    assert _image(client, "/static/icons/apple-touch-icon.png").size == (180, 180)


def test_every_favicon_frame_is_square(client):
    ico = _image(client, "/static/icons/favicon.ico")
    sizes = ico.info["sizes"]
    assert {(16, 16), (32, 32)} <= sizes, "a tab needs the 16 and 32 frames"
    for s in sizes:
        ico.size = s
        ico.load()
        assert ico.size[0] == ico.size[1] == s[0], s


def test_the_manifest_lists_both_install_sizes(client):
    icons = client.get("/manifest.webmanifest").get_json()["icons"]
    plain = [i for i in icons if not i.get("purpose")]
    assert {"src": "/static/icons/icon-192.png", "sizes": "192x192",
            "type": "image/png"} in plain
    assert {"src": "/static/icons/icon-512.png", "sizes": "512x512",
            "type": "image/png"} in plain
    for i in icons:
        assert client.get(i["src"]).status_code == 200, i["src"]
