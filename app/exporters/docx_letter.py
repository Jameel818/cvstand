"""The cover letter in Word: one page, editable, in the template's identity.

The same identity as the PDF letter (app/letter.py: letter_themes.json), drawn
with Word's own editable objects - paragraphs, a shaded table cell for the
band, a header rectangle for the side rail - and the same role styles as the
CV (CVName, CVHeading, Normal), so the fonts follow the template and the font
ribbon exactly as the CV's do (docx_theme.resolve / apply), and are embedded
the same way (docx_font_embed).

Two entry points:
    render(data, key)          the letter alone, a new document
    append(doc, data, key)     the letter as its OWN SECTION after a finished
                               CV document ("CV + cover letter"): a new page
                               with its own (empty) header, so none of the
                               CV's page shapes - a sidebar fill, a band -
                               reach the letter's page.

Arabic: w:bidi on the letter's paragraphs and tables and the section, w:rtl
only on runs holding Arabic letters (docx_design.run), as the CV designs do.
"""
from __future__ import annotations

import io

from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Twips

from .. import letter as letter_mod
from ..schema import lang_of, normalize
from . import docx_design as D
from . import docx_font_embed, docx_theme
from .docx_layout import PPR_ORDER, TBLPR_ORDER, _header_shapes, _put, _w

PAGE_H_PX = 1100
MARGIN_PX = 68
RAIL_PX = 40


#: Word has no auto-fit, and its lines for the Latin body faces run taller
#: than the PDF's (each face's own single line - docx_design.true_lines), so
#: a long ENGLISH letter takes its body a step smaller in Word than in the
#: PDF. Measured in real Word (run 10): at the PDF's sizes the longest letter
#: the form allows spilled 38-151pt onto a second page in all 10 templates
#: checked, while Arabic, whose faces wrap fewer characters per line, ended
#: ~60pt clear. (characters of greeting + paragraphs + closing, body px)
WORD_BODY_SIZES_EN = ((1400, 13.0), (1800, 12.0), (2200, 11.0), (2600, 10.5), (10 ** 9, 10.0))


def word_body_px(letter: dict, lang: str) -> float:
    if lang == "ar":
        return letter_mod.body_px(letter)
    n = len(letter["greeting"]) + len(letter["closing"]) + sum(len(p) for p in letter["paragraphs"])
    return next(px for limit, px in WORD_BODY_SIZES_EN if n <= limit)


def _hex(c: str | None) -> str | None:
    return c.lstrip("#").upper() if c else None


def _section(doc, *, new: bool, rtl: bool, th: dict):
    """The letter's page: Letter size, its margins, an empty header of its
    own (flat, so it takes no room) and the side rail as a page shape."""
    if new:
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        # the paragraph that now ends the CV's section must add nothing. Not
        # D.tiny(): it APPENDS w:rPr, which here would land after w:sectPr -
        # schema-invalid, and Word refuses the whole file (docx gotcha 0).
        ppr = D._ppr(doc.element.body.findall(qn("w:p"))[-1])
        rpr = OxmlElement("w:rPr")
        rpr.append(_w("sz", val=2))
        rpr.append(_w("szCs", val=2))
        _put(ppr, rpr, PPR_ORDER)
        _put(ppr, _w("spacing", before=0, after=0, line=60, lineRule="auto"), PPR_ORDER)
    else:
        sec = doc.sections[0]
    sec.different_first_page_header_footer = False
    sec.page_width, sec.page_height = Twips(12240), Twips(15840)
    rail = th["rail"]
    start = MARGIN_PX + (RAIL_PX if rail and rail["at"] == "start" else 0)
    end = MARGIN_PX + (RAIL_PX if rail and rail["at"] == "end" else 0)
    left, right = (start, end) if not rtl else (end, start)
    sec.left_margin, sec.right_margin = Twips(D.tw(left)), Twips(D.tw(right))
    sec.top_margin = Twips(0 if th["head_bg"] else D.tw(56))
    sec.bottom_margin = Twips(D.tw(40))
    sec.header_distance = sec.footer_distance = 0
    for part in (sec.header, sec.footer):
        part.is_linked_to_previous = False
        for para in part.paragraphs:
            D.tiny(para)
    if rail:
        at_left = (rail["at"] == "start") != rtl
        x = 0 if at_left else D.PAGE_W_PX - RAIL_PX
        _header_shapes(sec, [(D.pt(x), D.pt(RAIL_PX), 0, D.pt(PAGE_H_PX), _hex(rail["bg"]))], [])
    return sec, start, end


def _build(doc, data: dict, key: str, resolved: dict, *, new_section: bool) -> None:
    from ..labels import reset_lang, set_lang, t

    lang = lang_of(data)
    rtl = lang == "ar"
    th = letter_mod.theme(key, lang)
    L = letter_mod.letter_of(data)
    r = normalize(data)
    body = doc.element.body
    existing = set(body)            # held, so lxml keeps the same proxies
    band = []
    _, start, end = _section(doc, new=new_section, rtl=rtl, th=th)
    token = set_lang(lang)
    try:
        ctx = D.Ctx(doc=doc, r=r, lang=lang, resolved=resolved, photo=None, t=t)
        page = D.Box(ctx, doc, D.tw(D.PAGE_W_PX - start - end))
        align = "center" if th["centred"] else "start"
        head_bg = _hex(th["head_bg"])

        def head(box: D.Box) -> None:
            p = box.p(align=align, line=1.1)
            D.run(ctx, p, r["name"], "name", size=36, color=_hex(th["name"]),
                  caps=th["name_caps"], spacing=th["name_tracking"] or None)
            if r["title"]:
                caps = th["heading_caps"]
                p = box.p(align=align, before=9, line=1.3)
                D.run(ctx, p, r["title"], "body", size=12.5 if caps else 15, bold=True,
                      color=_hex(th["title"]), caps=caps, spacing=1.6 if caps else None)
            items = letter_mod.contact_items(r)
            if items:
                p = box.p(align=align, before=14, line=1.45)
                D.run(ctx, p, D._SEP.join(items), "body", size=11.5, color=_hex(th["contact"]))

        if head_bg:
            band_w = D.PAGE_W_PX - (RAIL_PX if th["rail"] else 0)
            tbl = page.table([D.tw(band_w)], rows=2, ind=-D.tw(MARGIN_PX))
            band.append(tbl._tbl)
            cell = D.fmt_cell(ctx, tbl.rows[0].cells[0], fill=head_bg,
                              pad=(0, MARGIN_PX, 0, MARGIN_PX))
            box = D.Box(ctx, cell, D.tw(band_w - 2 * MARGIN_PX), pad_top=46, pad_bottom=34)
            head(box)
            box.finish()
            stripe = D.fmt_cell(ctx, tbl.rows[1].cells[0], fill=_hex(th["stripe"]))
            D.row_height(tbl.rows[1], 5, "exact")
            D.tiny(stripe.paragraphs[0])
        else:
            head(page)
            rule = page.table([D.tw(56)], rows=1, jc="center" if th["centred"] else None)
            cell = D.fmt_cell(ctx, rule.rows[0].cells[0], fill=_hex(th["accent"]))
            D.row_height(rule.rows[0], 3, "exact")
            D.tiny(cell.paragraphs[0])
            # the rule sits under the header with the PDF's 26px above it
            prev = rule._tbl.getprevious()
            if prev is not None and prev.tag == qn("w:p"):
                sp = prev.find(qn("w:pPr")).find(qn("w:spacing"))
                sp.set(qn("w:after"), str(int(round(D.pt(26) * 20))))

        size = word_body_px(L, lang)
        text = _hex(th["text"])
        gap = 34
        if L["date"]:
            D.run(ctx, page.p(align="end", before=gap, line=1.62), L["date"], "body",
                  size=size, color=text)
            gap = 18
        for i, line in enumerate(letter_mod.recipient_lines(L)):
            D.run(ctx, page.p(before=gap if i == 0 else 0, line=1.62), line, "body", size=size,
                  color=text, bold=True if i == 0 else None)
            gap = 26
        if L["subject"]:
            p = page.p(before=gap, line=1.35, keep=True)
            D.run(ctx, p, "■ ", "body", size=11, color=_hex(th["accent"]))
            D.run(ctx, p, L["subject"], "heading", size=14, color=_hex(th["heading"]),
                  caps=th["heading_caps"], spacing=1.2 if th["heading_caps"] else None)
            gap = 22
        if L["greeting"]:
            D.run(ctx, page.p(before=gap, line=1.62), L["greeting"], "body", size=size,
                  color=text)
            gap = 12
        for para in L["paragraphs"]:
            D.run(ctx, page.p(before=gap, line=1.62), para, "body", size=size, color=text)
            gap = 12
        if L["closing"]:
            D.run(ctx, page.p(before=24, line=1.62, keep=True), L["closing"], "body",
                  size=size, color=text)
        if L["signature"]:
            D.run(ctx, page.p(before=8 if L["closing"] else 24, line=1.2), L["signature"],
                  "name", size=21, color=_hex(th["heading"]))
        D.true_lines(ctx)
    finally:
        reset_lang(token)
    D.end_paragraph(doc)
    if rtl:
        # Only what the letter added - the CV before it is already finished.
        # Told apart by IDENTITY, not position: new content goes in BEFORE the
        # body's closing sectPr, so "everything after the old length" skipped
        # the letter's first element (its band, or its name line), which then
        # kept left-to-right properties (found in real Word, run 10).
        for el in [e for e in body if e not in existing]:
            for p in el.iter(qn("w:p")):
                _put(D._ppr(p), _w("bidi"), PPR_ORDER)
            for tbl in el.iter(qn("w:tbl")):
                if tbl in band:
                    # One cell, nothing to mirror - and Word applies the band's
                    # negative indent from the wrong side in a bidiVisual
                    # table: the band slid 49pt off the right edge, cutting
                    # the name (measured in Word, run 10).
                    continue
                _put(tbl.find(qn("w:tblPr")), _w("bidiVisual"), TBLPR_ORDER)
        _section_bidi(doc.sections[-1]._sectPr)


def _section_bidi(sect) -> None:
    """w:bidi on a section, at its schema position (as docx_design.finish_rtl)."""
    if sect.find(qn("w:bidi")) is not None:
        return
    el = OxmlElement("w:bidi")
    later = ("rtlGutter", "docGrid", "printerSettings", "sectPrChange")
    for i, ch in enumerate(sect):
        if ch.tag.rsplit("}", 1)[-1] in later:
            sect.insert(i, el)
            return
    sect.append(el)


def render(data: dict, template_key: str) -> bytes:
    """The cover letter alone: a one-page, editable Word document."""
    rtl = lang_of(data) == "ar"
    doc = D.new_document(rtl)
    resolved = docx_theme.resolve(data, template_key)
    docx_theme.apply(doc, resolved)
    _build(doc, data, template_key, resolved, new_section=False)
    faces = docx_theme.faces_drawn(doc, resolved)
    buf = io.BytesIO()
    doc.save(buf)
    return docx_font_embed.embed_fonts(buf.getvalue(), faces)


def append(doc, data: dict, template_key: str) -> set:
    """Add the letter after a finished CV document; returns the faces it draws
    (the caller embeds them with the CV's)."""
    resolved = docx_theme.resolve(data, template_key)
    _build(doc, data, template_key, resolved, new_section=True)
    return docx_theme.faces_drawn(doc, resolved)
