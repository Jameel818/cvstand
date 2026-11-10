"""PDF export — headless Chromium (Playwright) rendering the standalone
document HTML to a pixel-accurate US-Letter PDF.

Why Chromium and not WeasyPrint: the templates use flex/grid two-column
layouts and `conic-gradient` skill rings, neither of which WeasyPrint renders.
Chromium is the same engine the on-screen preview uses, so the PDF matches it.

THE PAGE IS EXACTLY US LETTER, 612 x 792pt - the same page as the Word export
(2026-11-10). The canvas is 850x1100px; Chromium prints a CSS px as 0.75pt, so
an unscaled print is 637.5 x 825pt (measured 637.92 x 824.88), ~4% larger than
Letter. It is printed on Letter at scale 612 / 637.5 = 792 / 825 = 0.96, so a
template px is 0.75 x 0.96 = 0.72pt: exactly docx_design.PX. `margin: 0` - the
template owns its own insets.

Why the @page override (`_LETTER_PAGE`) and not just `format="Letter"`: the
document's own `@page { size: 850px 1100px }` (rendering.py, there for the
preview) decides the paper while `prefer_css_page_size` is on. With it off,
Chromium instead SHRINKS the 850px page to fit the paper by itself - and a
`scale` on top of that scales twice (0.9216: text 4% smaller than Word,
measured). So the paper size and the factor are both stated here, explicitly,
in the headless page only: the preview's HTML is untouched.
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


# The paper, the canvas, and the one factor between them (see the docstring).
LETTER_PT = (612, 792)
CANVAS_PX = (850, 1100)
CSS_PX_PT = 0.75                                   # Chromium prints 1 CSS px as 0.75pt
PDF_SCALE = LETTER_PT[0] / (CANVAS_PX[0] * CSS_PX_PT)   # 0.96
# The same factor down the page, or the print would be distorted.
assert abs(LETTER_PT[1] / (CANVAS_PX[1] * CSS_PX_PT) - PDF_SCALE) < 1e-9
_LETTER_PAGE = "@page { size: 8.5in 11in; margin: 0; }"


class PdfExportError(RuntimeError):
    pass


def chosen_faces(data: dict) -> list[str]:
    """CSS font shorthands for every face the user's choices can request.
    The Latin-Ext fallbacks are not here: they are used only if a glyph falls
    through, so a document may rightly never load them."""
    values = typography_of(data)[0]
    return [f'{w} 16px "{CSS_FAMILY_PREFIX}{fam}"'
            for fam, w in sorted(faces_for(values, lang_of(data)))]


def render_pdf(data: dict, template_id: str, part: str = "cv") -> bytes:
    """The PDF of the CV (`part="cv"`, the default and all an export did
    before the cover letter existed), of the cover letter alone ("letter"),
    or of both, the letter as the last page ("both"). Every document is
    printed by the same Chromium the same way; "both" joins the two files."""
    from .. import letter as letter_mod

    # for_pdf embeds the fonts as data: URIs. set_content()'s base URL is
    # about:blank, so a linked /static/fonts/... URL would resolve to nothing
    # and Chromium would silently fall back to a default face.
    if part not in ("cv", "letter", "both"):
        raise PdfExportError(f"unknown export part {part!r}")
    # (html, or a function of the previous page's auto-fit; print it?)
    docs: list = [(document_html(data, template_id, for_pdf=True), part != "letter")]
    if part != "cv":
        # the letter's letterhead takes the CV's own fit, so it sits exactly
        # where the CV's header does; for "letter" the CV is laid out (to read
        # its fit) but not printed
        docs.append((lambda fit: letter_mod.document_html(data, template_id, for_pdf=True,
                                                          header_fit=fit), True))
    pdfs = _print(docs, chosen_faces(data))
    if len(pdfs) == 1:
        return pdfs[0]
    return _join(pdfs)


def _join(pdfs: list[bytes]) -> bytes:
    import io

    from pypdf import PdfWriter

    out = PdfWriter()
    for blob in pdfs:
        out.append(io.BytesIO(blob))
    buf = io.BytesIO()
    out.write(buf)
    return buf.getvalue()


def _print(docs: list[str], faces: list[str]) -> list[bytes]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise PdfExportError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    out = []
    fit = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            try:
                for item in docs:
                    html, printed = item if isinstance(item, tuple) else (item, True)
                    if callable(html):
                        html = html(fit)
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
                    r = page.evaluate(
                        "window.ResumeAutofit ? window.ResumeAutofit.ready : null"
                    )
                    fit = (r["density"], r["typeScale"]) if isinstance(r, dict) else None
                    if not printed:
                        page.close()
                        continue
                    page.emulate_media(media="print")
                    # Letter paper, declared in THIS page only (the last @page
                    # rule wins), and the canvas scaled onto it: 1px = 0.72pt.
                    page.add_style_tag(content=_LETTER_PAGE)
                    pdf = page.pdf(
                        format="Letter",
                        scale=PDF_SCALE,
                        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                        print_background=True,
                        prefer_css_page_size=True,
                    )
                    out.append(pdf)
                    page.close()
            finally:
                browser.close()
    except PdfExportError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any Playwright failure as ours
        raise PdfExportError(f"Chromium PDF render failed: {exc}") from exc

    return out
