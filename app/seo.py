"""Search-engine plumbing: the launch switch, robots.txt, sitemap.xml, and the
canonical / hreflang / social tags every shell page carries.

THE LAUNCH SWITCH is `CVSTAND_SITE_INDEXABLE` (app/config.py), read here and
nowhere else. Until it is 1 the whole site is private to search engines:

  every response      X-Robots-Tag: noindex, nofollow   (PDFs, /preview, fonts)
  every page          <meta name="robots" content="noindex, nofollow">
  /robots.txt         Disallow: /
  /sitemap.xml        404

Launching is setting the variable to 1 on the host. Nothing else changes.
It is read from `app.config` per request, not cached at import, so a test can
flip it on one app without touching the environment.

LANGUAGES. One URL used to serve Arabic or English by cookie, and a crawler
sends no cookie - Google would only ever have seen one language. `?lang=ar`
and `?lang=en` (app/i18n.py) give each language its own address; those are
the canonical and hreflang URLs. Arabic is the market, so x-default is the
Arabic URL (user, 2026-11-16).

ABSOLUTE URLS are built from brand.DOMAIN, never from the request host, so a
preview deployment on a hosting subdomain still points search engines at the
real site.
"""
from __future__ import annotations

from urllib.parse import urlencode

from flask import Response, abort, current_app, has_request_context, request

from . import brand
from .i18n import UI_LANGS, current_lang

ORIGIN = f"https://{brand.DOMAIN}"

#: x-default: where a searcher whose language we do not serve is sent.
X_DEFAULT_LANG = "ar"

#: og:locale per interface language.
OG_LOCALE = {"ar": "ar_AR", "en": "en_US"}

#: Query parameters that make a different PAGE (and so survive into the
#: canonical URL), with the values that are real. Anything else in a query
#: string - a template key, a tracking tag - is the same page.
_PAGE_PARAMS = {"cat": ("modern", "ats")}

#: The pages a search engine should know about once the site launches,
#: as (path, extra query). Account, error, API, export and preview are not.
SITEMAP_PAGES = (
    ("/", {}),
    ("/templates", {}),
    ("/templates", {"cat": "modern"}),
    ("/templates", {"cat": "ats"}),
    ("/builder", {}),
)

#: Paths that are never search results, even after launch: robots.txt
#: disallows them and their responses say noindex, because a disallowed URL
#: can still be indexed from a link if nothing on it says otherwise.
PRIVATE_PREFIXES = ("/api/", "/export/", "/preview", "/account/", "/dev/",
                    "/uploads/", "/lang/")


def indexable() -> bool:
    return bool(current_app.config.get("SITE_INDEXABLE"))


def page_url(lang: str, path: str | None = None, params: dict | None = None) -> str:
    """The absolute, language-pinned URL of a page."""
    if path is None:
        path = request.path
        params = {k: request.args[k] for k, ok in _PAGE_PARAMS.items()
                  if request.args.get(k) in ok}
    query = dict(params or {})
    query["lang"] = lang
    return f"{ORIGIN}{path}?{urlencode(query)}"


def _alternates(path: str | None = None, params: dict | None = None) -> list[tuple[str, str]]:
    out = [(lang, page_url(lang, path, params)) for lang in UI_LANGS]
    out.append(("x-default", page_url(X_DEFAULT_LANG, path, params)))
    return out


def head_context() -> dict:
    """Everything base.html's <head> needs, for the current request."""
    lang = current_lang()
    return {
        "seo_indexable": indexable(),
        "seo_canonical": page_url(lang),
        "seo_alternates": _alternates(),
        "seo_og_locale": OG_LOCALE[lang],
        "seo_og_locale_alt": [OG_LOCALE[x] for x in UI_LANGS if x != lang],
        "seo_origin": ORIGIN,
        "seo_structured_data": structured_data,
    }


def structured_data(description: str) -> dict:
    """JSON-LD for the landing page: what the product is, and who makes it.

    Built here, not in the template: its values are schema.org vocabulary
    ("WebApplication", "Web"), not reader text, and the label gates in
    tests/test_labels.py rightly flag English literals in templates. No
    `sameAs` (there are no social accounts yet) and no SearchAction (there
    is no site search)."""
    url = ORIGIN + "/"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebApplication",
                "name": brand.NAME,
                "url": url,
                "description": description,
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "Web",
                "inLanguage": list(UI_LANGS),
                # building and downloading a PDF are free (account.html)
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            },
            {
                "@type": "Organization",
                "name": brand.NAME,
                "url": url,
                "logo": ORIGIN + "/static/icons/icon-512.png",
                "email": brand.SUPPORT_EMAIL,
            },
        ],
    }


def robots_txt() -> str:
    if not indexable():
        return "User-agent: *\nDisallow: /\n"
    lines = ["User-agent: *", "Allow: /"]
    lines += [f"Disallow: {p}" for p in PRIVATE_PREFIXES]
    lines += ["", f"Sitemap: {ORIGIN}/sitemap.xml", ""]
    return "\n".join(lines)


def sitemap_xml() -> str:
    urls = []
    for path, params in SITEMAP_PAGES:
        links = "".join(
            f'\n    <xhtml:link rel="alternate" hreflang="{hl}" href="{_xml(href)}"/>'
            for hl, href in _alternates(path, params)
        )
        for lang in UI_LANGS:
            urls.append(f"  <url>\n    <loc>{_xml(page_url(lang, path, params))}</loc>"
                        f"{links}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(urls) + "\n</urlset>\n")


def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def register(app) -> None:
    @app.after_request
    def _robots_header(response):
        """Private until launch, on EVERY response - a PDF or a font can be
        indexed as surely as a page. After launch, only the private paths."""
        if not indexable() or request.path.startswith(PRIVATE_PREFIXES):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    @app.context_processor
    def _inject():
        if not has_request_context():   # e.g. a PDF rendered off-request
            return {}
        return head_context()

    @app.get("/robots.txt")
    def robots():
        return Response(robots_txt(), mimetype="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        if not indexable():
            abort(404)
        return Response(sitemap_xml(), mimetype="application/xml")
