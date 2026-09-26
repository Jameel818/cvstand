"""PDF export — headless Chromium (Playwright) rendering the standalone
document HTML to a pixel-accurate US-Letter PDF.

Why Chromium and not WeasyPrint: the templates use flex/grid two-column
layouts and `conic-gradient` skill rings, neither of which WeasyPrint renders.
Chromium is the same engine the on-screen preview uses, so the PDF matches it.

The page box is exactly 850x1100px (Letter @ 100dpi). We set the PDF `width`
/`height` to match and `margin: 0` — the template owns its own insets.
"""
from __future__ import annotations

import logging

from ..rendering import document_html
from ..schema import lang_of, typography_of
from ..typography import CSS_FAMILY_PREFIX
from ..typography.render import faces_for

log = logging.getLogger(__name__)

# Spec §6.1: load every chosen face explicitly, then check it. fonts.ready
# alone only covers the faces the layout happened to request, and a face that
# failed to load is drawn in a fallback with no error at all. allSettled, not
# all: a face that cannot load REJECTS its load(), and the check must still
# name it rather than abort on the first one.
_LOAD_AND_CHECK = """async (faces) => {
    await Promise.allSettled(faces.map(f => document.fonts.load(f)));
    return faces.filter(f => !document.fonts.check(f));
}"""


class PdfExportError(RuntimeError):
    pass


def chosen_faces(data: dict) -> list[str]:
    """CSS font shorthands for every face the user's choices can request.
    The Latin-Ext fallbacks are not here: they are used only if a glyph falls
    through, so a document may rightly never load them."""
    values = typography_of(data)[0]
    return [f'{w} 16px "{CSS_FAMILY_PREFIX}{fam}"'
            for fam, w in sorted(faces_for(values, lang_of(data)))]


def render_pdf(data: dict, template_id: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise PdfExportError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    # for_pdf embeds the fonts as data: URIs. set_content()'s base URL is
    # about:blank, so a linked /static/fonts/... URL would resolve to nothing
    # and Chromium would silently fall back to a default face.
    html = document_html(data, template_id, for_pdf=True)
    faces = chosen_faces(data)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            try:
                page = browser.new_page()
                page.set_content(html, wait_until="networkidle")
                # Fonts must be loaded before layout is measured for pagination.
                page.evaluate("document.fonts && document.fonts.ready")
                missing = page.evaluate(_LOAD_AND_CHECK, faces) if faces else []
                if missing:
                    log.error("PDF export: chosen font(s) did not load: %s", missing)
                    raise PdfExportError(
                        f"chosen font(s) did not load, refusing to print a fallback: {missing}")
                # Auto-fit compresses vertical rhythm until the résumé seats on
                # one page (app/static/js/autofit.js). It is inlined in every
                # document and self-starts after fonts.ready; awaiting its
                # promise here is what guarantees the PDF is printed from the
                # SAME fitted layout the user approved in the preview. Without
                # this await, page.pdf() can race the fit and print the
                # unfitted, overflowing layout.
                page.evaluate(
                    "window.ResumeAutofit ? window.ResumeAutofit.ready : null"
                )
                page.emulate_media(media="print")
                pdf = page.pdf(
                    width="850px",
                    height="1100px",
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                browser.close()
    except PdfExportError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any Playwright failure as ours
        raise PdfExportError(f"Chromium PDF render failed: {exc}") from exc

    return pdf
