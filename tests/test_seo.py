"""Search-engine contract: private until launch, then fully described.

THE SWITCH (app/seo.py, CVSTAND_SITE_INDEXABLE) defaults OFF, and while off
nothing on the site may be indexable - pages, PDFs, fonts, the iframe
preview. That is the half that protects the business before launch, so it is
asserted on the DEFAULT app, with no flag touched.

Once on, every public page in both languages must carry its own title and
description, a canonical on the real domain, three hreflang links (x-default
is Arabic), and social tags with absolute images. Account and error pages
stay noindex for good.

`?lang=` is what gives each language its own URL; it must beat the cookie,
or a crawler following an Arabic link could be served English.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from app import create_app
from app.i18n import COOKIE

PUBLIC = ["/", "/templates", "/templates?cat=modern", "/templates?cat=ats", "/builder"]
NEVER_INDEXED = ["/account/sign-in", "/account/sign-up", "/no-such-page"]
ORIGIN = "https://cvstand.com"


def _app(indexable: bool | None = None):
    app = create_app()
    app.config.update(TESTING=True)
    if indexable is not None:
        app.config["SITE_INDEXABLE"] = indexable
    return app


def _get(client, path, lang):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}lang={lang}")


def _head(resp) -> str:
    return resp.get_data(as_text=True).split("</head>", 1)[0]


def _meta(head, attr, name):
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', head)
    return m.group(1) if m else None


# ------------------------------------------------------------ private (default)

def test_the_switch_defaults_off():
    assert _app().config["SITE_INDEXABLE"] is False


@pytest.mark.parametrize("path", PUBLIC + NEVER_INDEXED)
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_private_every_page_says_noindex(path, lang):
    r = _get(_app().test_client(), path, lang)
    assert r.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert _meta(_head(r), "name", "robots") == "noindex, nofollow"


@pytest.mark.parametrize("path", ["/static/icons/og-image.png", "/robots.txt",
                                  "/preview?template_key=t1&showcase=1"])
def test_private_non_pages_carry_the_header_too(path):
    r = _app().test_client().get(path)
    assert r.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_private_robots_disallows_everything_and_no_sitemap():
    c = _app().test_client()
    body = c.get("/robots.txt").get_data(as_text=True)
    assert body.splitlines()[:2] == ["User-agent: *", "Disallow: /"]
    assert "Sitemap" not in body
    assert c.get("/sitemap.xml").status_code == 404


# ------------------------------------------------------------ launched

@pytest.fixture()
def live():
    return _app(indexable=True).test_client()


def test_launched_robots_allows_the_site_and_names_the_sitemap(live):
    body = live.get("/robots.txt").get_data(as_text=True)
    assert "Allow: /" in body and "Disallow: /\n" not in body
    for private in ("/api/", "/export/", "/preview", "/account/"):
        assert f"Disallow: {private}" in body
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in body


def test_launched_sitemap_lists_every_public_page_in_both_languages(live):
    r = live.get("/sitemap.xml")
    assert r.status_code == 200 and r.mimetype == "application/xml"
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9",
          "x": "http://www.w3.org/1999/xhtml"}
    root = ET.fromstring(r.data)
    locs = [u.find("s:loc", ns).text for u in root.findall("s:url", ns)]
    assert len(locs) == len(PUBLIC) * 2 == len(set(locs))
    for u in root.findall("s:url", ns):
        langs = {l.get("hreflang") for l in u.findall("x:link", ns)}
        assert langs == {"ar", "en", "x-default"}


@pytest.mark.parametrize("path", PUBLIC)
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_launched_page_head(live, path, lang):
    r = _get(live, path, lang)
    assert r.status_code == 200 and "X-Robots-Tag" not in r.headers
    head = _head(r)
    assert f'<html lang="{lang}"' in r.get_data(as_text=True)
    assert _meta(head, "name", "robots") == "index, follow"

    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', head).group(1)
    assert canonical.startswith(ORIGIN + path.split("?")[0])
    assert f"lang={lang}" in canonical

    alts = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', head))
    assert set(alts) == {"ar", "en", "x-default"}
    assert alts[lang] == canonical
    assert alts["x-default"] == alts["ar"]          # Arabic-first

    for prop in ("og:title", "og:description", "og:url", "og:image", "og:locale"):
        assert _meta(head, "property", prop), prop
    for name in ("twitter:card", "twitter:title", "twitter:description", "twitter:image"):
        assert _meta(head, "name", name), name
    assert _meta(head, "property", "og:image").startswith(ORIGIN + "/static/")
    assert _meta(head, "name", "twitter:image").startswith(ORIGIN + "/static/")


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_launched_titles_and_descriptions_are_unique_per_page(live, lang):
    titles, descs = set(), set()
    for path in PUBLIC:
        head = _head(_get(live, path, lang))
        titles.add(re.search(r"<title>(.*?)</title>", head, re.S).group(1).strip())
        descs.add(_meta(head, "name", "description"))
    assert len(titles) == len(PUBLIC)
    assert len(descs) == len(PUBLIC)


@pytest.mark.parametrize("path", NEVER_INDEXED)
def test_launched_account_and_error_pages_stay_out(live, path):
    r = _get(live, path, "en")
    assert _meta(_head(r), "name", "robots") == "noindex, nofollow"


def test_landing_structured_data_parses(live):
    html = _get(live, "/", "en").get_data(as_text=True)
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    graph = json.loads(raw)["@graph"]
    assert {n["@type"] for n in graph} == {"WebApplication", "Organization"}
    for node in graph:
        assert node["url"] == ORIGIN + "/"


@pytest.mark.parametrize("path", PUBLIC)
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_exactly_one_h1(live, path, lang):
    html = _get(live, path, lang).get_data(as_text=True)
    assert len(re.findall(r"<h1[\s>]", html)) == 1


# ------------------------------------------------------------ ?lang=

def test_lang_query_beats_the_cookie_and_is_remembered():
    c = _app().test_client()
    c.set_cookie(COOKIE, "en")
    r = c.get("/?lang=ar")
    assert '<html lang="ar"' in r.get_data(as_text=True)
    assert any(h.startswith(f"{COOKIE}=ar") for h in r.headers.getlist("Set-Cookie"))


def test_no_signal_at_all_is_arabic():
    r = _app().test_client().get("/")
    assert '<html lang="ar"' in r.get_data(as_text=True)


def test_an_unserved_browser_language_is_arabic():
    r = _app().test_client().get("/", headers={"Accept-Language": "fr-FR,fr;q=0.9"})
    assert '<html lang="ar"' in r.get_data(as_text=True)


def test_an_english_browser_still_gets_english():
    r = _app().test_client().get("/", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert '<html lang="en"' in r.get_data(as_text=True)


def test_the_switcher_drops_lang_so_the_choice_sticks():
    html = _app().test_client().get("/templates?cat=ats&lang=ar").get_data(as_text=True)
    # the EN switch link must return to /templates?cat=ats, not ...&lang=ar,
    # which would outrank the cookie it just set and flip straight back
    m = re.search(r'href="(/lang/en[^"]*)"', html)
    assert m and "lang%3Dar" not in m.group(1) and "lang=ar" not in m.group(1)
    assert "cat%3Dats" in m.group(1)
