"""The install manifest and the service worker.

The PWA was deferred on 2026-08-30 with a correct reason: while the app was
local-only and server-rendered, an offline shell could not do anything, because
the résumé, the preview and both exports all lived on the server. Deployment
plus the browser-side store changed both halves of that, so it is worth having
now — a cached shell over a bad connection opens the builder and the résumé is
already in localStorage.

Two things here are easy to get wrong and are gated accordingly:

* **Scope.** A worker registered from `/static/js/sw.js` may only control
  `/static/` — it would cache the stylesheet and never see a page. Serving it
  from the root is the whole reason `/sw.js` is a route.
* **Language.** The shell is bilingual and its language comes from a cookie, so
  one URL has two correct manifests. A static manifest file would name the
  installed app in whichever language was written into it.
"""
from __future__ import annotations

import json

import flask
import pytest

from app import create_app, i18n


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_the_manifest_is_served_and_installable(client):
    res = client.get("/manifest.webmanifest")
    assert res.status_code == 200
    m = res.get_json()
    # The four fields a browser needs before it will offer to install.
    assert m["name"] and m["start_url"] and m["display"] == "standalone"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_a_maskable_icon_is_offered(client):
    """Without one, Android crops the square icon into its own shape and slices
    the corners off the artwork."""
    icons = client.get("/manifest.webmanifest").get_json()["icons"]
    assert any("maskable" in (i.get("purpose") or "") for i in icons)


@pytest.mark.parametrize("lang,expected_dir", [("en", "ltr"), ("ar", "rtl")])
def test_the_manifest_follows_the_interface_language(client, lang, expected_dir):
    """An Arabic visitor must not install an app that names itself in English,
    and `dir` has to say which way its name reads."""
    client.set_cookie(i18n.COOKIE, lang)
    m = client.get("/manifest.webmanifest").get_json()
    assert m["lang"] == lang
    assert m["dir"] == expected_dir


def test_the_two_languages_give_different_manifests(client):
    client.set_cookie(i18n.COOKIE, "en")
    en = client.get("/manifest.webmanifest").get_json()
    client.set_cookie(i18n.COOKIE, "ar")
    ar = client.get("/manifest.webmanifest").get_json()
    assert en["description"] != ar["description"], (
        "the manifest description did not translate — a static file would "
        "have passed every other test in this module"
    )


def test_the_worker_is_served_from_the_root(client):
    """Scope is the point. From /static/js/sw.js it could only ever control
    /static/, which is a worker that caches the CSS and no pages."""
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.mimetype
    assert res.headers.get("Service-Worker-Allowed") == "/"


def test_the_worker_is_not_cached_by_intermediaries(client):
    """A stale worker is a stale APP — it decides what every other response is
    allowed to be."""
    cc = client.get("/sw.js").headers.get("Cache-Control", "")
    assert "no-cache" in cc or "no-store" in cc


def test_the_worker_never_caches_a_live_render(client):
    """`/api/*`, `/export/*` and `/preview` all render on demand, and a stale
    answer from any of them is worse than an error. `/export/*` is a POST too,
    which a cache cannot serve at all."""
    src = client.get("/sw.js").get_data(as_text=True)
    assert 'pathname.startsWith("/api/")' in src
    assert 'pathname.startsWith("/export/")' in src
    assert 'pathname === "/preview"' in src
    assert 'req.method !== "GET"' in src


def test_navigations_are_network_first(client):
    """The language hazard. The shell's language comes from a cookie, so one
    URL has two correct responses and a cache keyed by URL cannot tell them
    apart. Online, the server must decide every time — the cache is a fallback
    for being offline and nothing else.

    This is a source assertion rather than a behavioural one on purpose: the
    behaviour it guards only appears in a real browser with a real network
    failure, and the thing that would break it is someone reordering these two
    lines for speed.
    """
    src = client.get("/sw.js").get_data(as_text=True)
    nav = src[src.index('req.mode === "navigate"'):]
    fetch_at = nav.index("fetch(req)")
    cache_at = nav.index("caches.match(req)")
    assert fetch_at < cache_at, "the navigation handler consults the cache first"


def test_every_page_registers_the_worker(client):
    for path in ("/", "/templates", "/builder"):
        html = client.get(path).get_data(as_text=True)
        assert 'navigator.serviceWorker.register("/sw.js")' in html, path
        assert 'rel="manifest"' in html, path


def test_registration_cannot_surface_as_an_unhandled_rejection(client):
    """Registration REJECTS outside a secure context, which is how this app
    runs in development. An uncaught rejection there is the same swallow-shape
    this project has already fixed twice."""
    html = client.get("/").get_data(as_text=True)
    reg = html[html.index("navigator.serviceWorker.register"):]
    assert ".catch(" in reg[:200]


@pytest.mark.parametrize("server_store,expected,forbidden", [
    (True, "stays on this machine", "never stored on our server"),
    (False, "never stored on our server", "single-user tool"),
])
def test_the_footer_says_where_the_resume_actually_lives(server_store, expected, forbidden):
    """Two modes, two true statements — and NEITHER may appear in the other's
    mode. The old line ("Built as a single-user tool. Your résumé stays on this
    machine.") became false the moment the app could be deployed, and the
    replacement would be false on a laptop, where it does also sit in
    data/resume.json.

    Rendered directly with each value rather than through a request: the
    context processor closes over the module constant that `app/config.py`
    reads once at import, so a monkeypatched request would exercise one branch
    twice and look like it had tested both.
    """
    app = create_app()
    # A request context, so `request.path` and the i18n globals the shell uses
    # (`t`, `ui_lang`, `ui_dir`) resolve the way they do on a real page.
    with app.test_request_context("/"):
        # `render_template`, not `jinja_env.get_template(...).render()`: the
        # shell's `t`, `ui_lang` and `ui_dir` come from context processors,
        # which only run on this path. Explicit kwargs beat a processor's
        # value, so the parametrised `server_store` is the one that renders.
        html = flask.render_template("base.html", server_store=server_store)
    assert expected in html
    assert forbidden not in html


def test_the_icons_exist_and_are_real_pngs(client):
    for name in ("icon-192.png", "icon-512.png", "icon-maskable-512.png",
                 "apple-touch-icon.png"):
        res = client.get(f"/static/icons/{name}")
        assert res.status_code == 200, name
        assert res.data[:8] == b"\x89PNG\r\n\x1a\n", name
