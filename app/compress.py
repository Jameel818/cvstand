"""Page speed (2026-10-08): gzip on the wire, and cache lifetimes for files
that do not change.

MEASURED FIRST (Playwright + DevTools, scratch perf.py): nothing this app
served was compressed - HTML, CSS, JS, the /api/render JSON, and the two
IBM Plex Sans Arabic TTFs (230-240 KB each) that every Arabic preview draws.
Those must ship as unmodified TTF (a Reserved Font Name, FONTS.md), but
Content-Encoding is transport, not a change to the font: the browser gets the
same bytes back. And every static file was `no-cache`, so a repeat visit
asked again for each font.

WHAT THIS DOES NOT TOUCH
  - appearance: the bytes a browser decodes are byte-identical;
  - the PDF and Word exports (binary, already compressed formats);
  - a client that does not say `Accept-Encoding: gzip` (the test client,
    curl without --compressed) gets the plain response, as before;
  - CSS / JS freshness: they stay `no-cache` (and the service worker fetches
    code network-first), so a release is never hidden behind a cache.

Standard library only (gzip): no new runtime dependency for the image.
"""
from __future__ import annotations

import gzip
import mimetypes
from functools import lru_cache

from flask import Flask, request

# The MIME table differs per OS: Windows answers .ttf with
# application/octet-stream, which nothing would compress. Say it once.
mimetypes.add_type("font/ttf", ".ttf")

#: Worth compressing: text, and the TTF fonts (woff2 is compressed already).
COMPRESSIBLE = ("text/", "application/json", "application/javascript",
                "image/svg+xml", "font/ttf", "font/sfnt", "application/font-sfnt",
                "application/x-font-ttf", "application/vnd.ms-opentype")
MIN_BYTES = 1024
#: Fonts, icons and rail artwork are replaced, not edited in place, and only
#: by a deliberate rebuild; a day of caching saves every repeat visit a round
#: trip per face. CSS and JS keep `no-cache` (see above).
LONG_LIVED = ("/static/fonts/", "/static/icons/", "/static/rails/")
LONG_MAX_AGE = 86400


@lru_cache(maxsize=256)
def _gzip_static(key: tuple, data: bytes) -> bytes:
    """Static files are compressed once per (path, size, mtime), not per hit -
    a 240 KB TTF costs ~10 ms to gzip, which would be paid on every request."""
    return gzip.compress(data, compresslevel=6, mtime=0)


def _wants_gzip() -> bool:
    return "gzip" in (request.headers.get("Accept-Encoding") or "").lower()


def register(app: Flask) -> None:
    @app.before_request
    def _plain_etag():
        # A revalidation sends back the gzip variant's tag; the route compares
        # against the plain one, so strip the suffix and the 304 still works.
        tag = request.environ.get("HTTP_IF_NONE_MATCH")
        if tag and "-gz" in tag:
            request.environ["HTTP_IF_NONE_MATCH"] = tag.replace("-gz", "")

    @app.after_request
    def _speed(resp):
        path = request.path
        if path.startswith(LONG_LIVED) and resp.status_code in (200, 304):
            resp.headers["Cache-Control"] = f"public, max-age={LONG_MAX_AGE}"
        if resp.status_code == 304 and _wants_gzip():
            etag, weak = resp.get_etag()
            if etag and not etag.endswith("-gz"):
                resp.set_etag(etag + "-gz", weak=weak)
            resp.vary.add("Accept-Encoding")
        if (resp.status_code != 200 or not _wants_gzip()
                or "Content-Encoding" in resp.headers
                or not (resp.mimetype or "").startswith(COMPRESSIBLE)
                or request.method == "HEAD"):
            return resp
        resp.direct_passthrough = False               # send_file streams by default
        data = resp.get_data()
        if len(data) < MIN_BYTES:
            return resp
        if path.startswith("/static/"):
            body = _gzip_static((path, len(data), resp.headers.get("ETag")), data)
        else:
            body = gzip.compress(data, compresslevel=6, mtime=0)
        resp.set_data(body)
        resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Content-Length"] = str(len(body))
        resp.vary.add("Accept-Encoding")
        # The ETag names the plain bytes; the gzip variant must not share it,
        # or a cache could answer a plain request with gzip (RFC 9110 8.8.3).
        etag, weak = resp.get_etag()
        if etag:
            resp.set_etag(etag + "-gz", weak=weak)
        return resp
