"""Per-template Word DESIGNS (docs/WORD_FIDELITY_AUDIT.md).

The generic layout masters (docx_layout.py) give every Modern template its
columns and colours and nothing else. A template listed in DESIGNS here is
instead BUILT IN CODE, element by element, from the same résumé dict the HTML
template reads - its photo frame, heading rules, skill bars, contact grid,
timeline, stats row - with Word's own editable objects only: tables, cell and
paragraph shading, borders, tab stops with leaders, letter spacing, and shapes
in the page header for fills that must reach the paper's edge.

What is shared with the rest of the Word export:
  - the document starts from the layout master (word_masters/modern_layout*.docx):
    its role styles, compatibility mode 15, page size;
  - docx_theme.apply() puts the template's (or the user's chosen) FACES on the
    role styles, and every run here carries one of those styles, so the fonts
    follow the user and docx_theme.faces_drawn() / docx_font_embed embed them;
  - colours and sizes are the template's own, measured from its .j2 source
    (px of the 850px canvas; the page is 612pt wide, so 1px = 0.72pt).

Arabic: the finished document gets w:bidi on the section and every paragraph and
w:bidiVisual on every table (the columns mirror), and w:rtl ONLY on runs that
contain Arabic letters: a phone number, an e-mail or "$3.2M" marked RTL is
reordered by Word ("64-0138-555", "3.2M$" - audit X13).

Every property element is inserted at its schema position (docx_layout._put).
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from docx import Document
from docx.enum.text import WD_BREAK  # noqa: F401  (kept for designs)
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Pt

from . import docx_theme
from .docx_layout import PPR_ORDER, TBLPR_ORDER, TCPR_ORDER, _header_shapes, _put, _w

PX = 0.72                      # pt per template px (850px canvas on a 612pt page)
PAGE_W_PX = 850
PAGE_W = 12240                 # twips
PAGE_H_PT = 792
AR_GAP = 0.8                   # Arabic vertical gaps, of the template's
CSS_LINE_AR = 1.75             # the Arabic faces' natural line
CSS_LINE = 1.2                 # a face's "single" line, as a multiple of its size


def pt(px: float) -> float:
    return px * PX


def tw(px: float) -> int:
    return int(round(px * PX * 20))


_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
RPR_ORDER = docx_theme.RPR_ORDER

ROLE_STYLE = {"body": None, "bold": "CVBodyBold", "name": "CVName", "heading": "CVHeading",
              "role": "CVRole", "metric": "CVMetric", "accent": "CVAccentText"}


# ---- low-level XML ---------------------------------------------------------------

def _rpr_put(rpr, tag: str, **attrs) -> None:
    el = OxmlElement(f"w:{tag}")
    for k, v in attrs.items():
        el.set(qn(f"w:{k}"), str(v))
    old = rpr.find(qn(f"w:{tag}"))
    if old is not None:
        rpr.remove(old)
    later = RPR_ORDER[RPR_ORDER.index(tag) + 1:]
    for i, child in enumerate(rpr):
        if child.tag.rsplit("}", 1)[-1] in later:
            rpr.insert(i, el)
            return
    rpr.append(el)


def _ppr(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        p.insert(0, ppr)
    return ppr


def _tcpr(tc):
    pr = tc.find(qn("w:tcPr"))
    if pr is None:
        pr = OxmlElement("w:tcPr")
        tc.insert(0, pr)
    return pr


# ---- the context -----------------------------------------------------------------

@dataclass
class Ctx:
    doc: object
    r: dict
    lang: str
    resolved: dict
    photo: Path | None
    t: Callable[[str], str]
    rtl: bool = field(init=False)

    def __post_init__(self):
        self.rtl = self.lang == "ar"

    # physical edge of a LOGICAL side, for the properties Word reads physically
    # (paragraph borders; shape positions)
    def edge(self, logical: str) -> str:
        if logical in ("start", "end"):
            left = (logical == "start") != self.rtl
            return "left" if left else "right"
        return logical


class Box:
    """A container (a table cell, or the body) that hands out paragraphs,
    reusing the empty paragraph a new cell starts with and the one python-docx
    leaves after a nested table, so no stray blank line is ever added."""

    def __init__(self, ctx: Ctx, container, width_tw: int, *, pad_top: float = 0,
                 pad_bottom: float = 0):
        """`pad_top`/`pad_bottom` (px) are written as paragraph spacing, never
        as the cell's margins: Word applies the LARGEST top margin in a row to
        every cell of it, so a padded header pushed the merged side column
        down with it (modern-t8's portrait block)."""
        self.ctx, self.c, self.w = ctx, container, width_tw
        self.pad_top, self.pad_bottom = pad_top, pad_bottom
        self.pending = None
        if hasattr(container, "paragraphs") and hasattr(container, "_tc"):
            ps = container.paragraphs
            if len(ps) == 1 and not ps[0].text:
                self.pending = ps[0]

    def p(self, **fmt):
        if self.pending is not None:
            para, self.pending = self.pending, None
        else:
            para = self.c.add_paragraph()
        if self.pad_top:
            fmt["before"] = fmt.get("before", 0) + self.pad_top
            self.pad_top = 0
        return fmt_p(self.ctx, para, **fmt)

    def table(self, widths_tw: list[int], rows: int = 1, **kw):
        unused = self.pending
        if self.pad_top:
            # the padding above a leading table: a tiny spacer paragraph
            spacer = unused if unused is not None else self.c.add_paragraph()
            tiny(spacer, before_px=self.pad_top)
            self.pad_top, unused = 0, None
        tbl = self.c.add_table(rows=rows, cols=len(widths_tw))
        fmt_table(tbl, widths_tw, **kw)
        if unused is not None and unused._p.find(qn("w:r")) is None:
            # an empty paragraph left before the new table would be a blank line
            unused._p.getparent().remove(unused._p)
        self.pending = None
        if hasattr(self.c, "_tc"):
            self.pending = self.c.paragraphs[-1]
        return tbl

    def finish(self):
        """A cell must END with a paragraph; the reused/left-over one is made
        tiny so it adds no visible height (beyond the bottom padding)."""
        extra = self.pad_top + self.pad_bottom
        if self.pending is None and extra:
            self.pending = self.c.add_paragraph()
        if self.pending is not None:
            tiny(self.pending, before_px=extra)
            self.pending = None
        self.pad_top = self.pad_bottom = 0


def tiny(para, half_points: int = 2, before_px: float = 0) -> None:
    fmt = para.paragraph_format
    fmt.space_before = fmt.space_after = Pt(0)
    ppr = _ppr(para._p)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    _rpr_put(rpr, "sz", val=half_points)
    _rpr_put(rpr, "szCs", val=half_points)
    _put(ppr, _w("spacing", before=int(round(pt(before_px) * 20)), after=0, line=240,
                  lineRule="auto"), PPR_ORDER)


# ---- paragraphs and runs -----------------------------------------------------------

def fmt_p(ctx: Ctx, para, *, align=None, before=0.0, after=0.0, line=None, ind_start=0,
          ind_end=0, first=0, hanging=0, shade=None, border=None, tabs=None, keep=False):
    """`before`/`after`/`ind_*` in template px; `line` = the CSS line-height
    (a multiple of the font size), written as Word's AUTO multiple (never
    Exactly: nothing may clip). `border` = {logical edge: (px, colour, space_pt)}.
    `tabs` = [(px from the start edge, "start"|"end"|"center", leader)]."""
    p = para._p
    ppr = _ppr(p)
    if keep:
        _put(ppr, _w("keepNext"), PPR_ORDER)
    if border:
        bdr = OxmlElement("w:pBdr")
        for edge in ("top", "left", "bottom", "right"):
            for logical, (px, colour, space) in border.items():
                if ctx.edge(logical) == edge:
                    bdr.append(_w(edge, val="single", sz=max(2, round(pt(px) * 8)),
                                  space=int(space), color=colour))
        _put(ppr, bdr, PPR_ORDER)
    if shade:
        _put(ppr, _w("shd", val="clear", color="auto", fill=shade), PPR_ORDER)
    if tabs:
        el = OxmlElement("w:tabs")
        for pos, kind, leader in tabs:
            val = {"start": "left", "end": "right", "center": "center"}[kind]
            attrs = {"val": val, "pos": tw(pos)}
            if leader:
                attrs["leader"] = leader
            el.append(_w("tab", **attrs))
        _put(ppr, el, PPR_ORDER)
    # Arabic lines are taller (the faces' own metrics); the GAPS between them
    # shrink so the page keeps the PDF's rhythm - the lines themselves never do
    k = AR_GAP if ctx.rtl else 1.0
    sp = {"before": int(round(pt(before) * 20 * k)), "after": int(round(pt(after) * 20 * k))}
    if line is not None:
        # Word's "single" is the face's own height: ~1.2x the size for the
        # Latin faces, ~1.7x for the Arabic ones - never below single (no clip)
        mult = max(1.0, line / (CSS_LINE_AR if ctx.rtl else CSS_LINE))
        sp.update(line=int(round(240 * mult)), lineRule="auto")
    else:
        sp.update(line=240, lineRule="auto")
    _put(ppr, _w("spacing", **sp), PPR_ORDER)
    if ind_start or ind_end or first or hanging:
        # w:ind start/end are LOGICAL in Word (they follow w:bidi)
        # (seen in real Word: in a bidi paragraph w:left IS the start side)
        attrs = {}
        if ind_start:
            attrs["left"] = tw(ind_start)
        if ind_end:
            attrs["right"] = tw(ind_end)
        if first:
            attrs["firstLine"] = tw(first)
        if hanging:
            attrs["hanging"] = tw(hanging)
        _put(ppr, _w("ind", **attrs), PPR_ORDER)
    if align:
        # in a bidi paragraph Word reads left/right LOGICALLY: "left" = start
        _put(ppr, _w("jc", val={"start": "left", "end": "right", "center": "center",
                                "both": "both"}[align]), PPR_ORDER)
    return para


def run(ctx: Ctx, para, text: str, role: str = "body", *, size=None, color=None,
        caps=False, spacing=None, italic=None, bold=None, font=None, position=None,
        underline=None, rtl=False):
    """One run. `size`/`spacing`/`position` in template px. `role` picks the
    role style (the face); colour and size are the template's, set directly."""
    r = para.add_run(text)
    rpr = r._r.get_or_add_rPr()
    sid = ROLE_STYLE[role]
    if sid:
        _rpr_put(rpr, "rStyle", val=sid)
    if font:
        _rpr_put(rpr, "rFonts", ascii=font, hAnsi=font, eastAsia=font, cs=font)
    if bold is not None:
        _rpr_put(rpr, "b", val="1" if bold else "0")
        _rpr_put(rpr, "bCs", val="1" if bold else "0")
    if italic is not None:
        _rpr_put(rpr, "i", val="1" if italic else "0")
        _rpr_put(rpr, "iCs", val="1" if italic else "0")
    if caps:
        _rpr_put(rpr, "caps")
    if color:
        _rpr_put(rpr, "color", val=color)
    # tracking pulls joined Arabic letters apart (the PDF draws none there)
    if spacing and not _ARABIC.search(text or ""):
        _rpr_put(rpr, "spacing", val=int(round(pt(spacing) * 20)))
    if position:
        _rpr_put(rpr, "position", val=int(round(pt(position) * 2)))
    if size:
        hp = max(2, int(round(pt(size) * 2)))
        _rpr_put(rpr, "sz", val=hp)
        _rpr_put(rpr, "szCs", val=hp)
    if underline:
        _rpr_put(rpr, "u", val=underline)
    if ctx.rtl and (rtl or _ARABIC.search(text or "")):
        _rpr_put(rpr, "rtl")
    return r


# ---- tables ---------------------------------------------------------------------

def fmt_table(tbl, widths_tw: list[int], *, ind=0, borders=None, mar=0, jc=None):
    """Fixed layout, exact widths, borderless unless `borders`
    ({edge: (px, colour)} for top/bottom/insideH/insideV/left/right)."""
    t = tbl._tbl
    pr = t.tblPr
    _put(pr, _w("tblW", w=sum(widths_tw), type="dxa"), TBLPR_ORDER)
    if jc:
        _put(pr, _w("jc", val=jc), TBLPR_ORDER)
    _put(pr, _w("tblInd", w=ind, type="dxa"), TBLPR_ORDER)
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if borders and edge in borders:
            px, colour = borders[edge]
            b.append(_w(edge, val="single", sz=max(2, round(pt(px) * 8)), space=0, color=colour))
        else:
            b.append(_w(edge, val="nil"))
    _put(pr, b, TBLPR_ORDER)
    _put(pr, _w("tblLayout", type="fixed"), TBLPR_ORDER)
    m = OxmlElement("w:tblCellMar")
    for edge in ("top", "left", "bottom", "right"):
        m.append(_w(edge, w=mar, type="dxa"))
    _put(pr, m, TBLPR_ORDER)
    look = pr.find(qn("w:tblStyle"))
    if look is not None:
        pr.remove(look)
    grid = t.find(qn("w:tblGrid"))
    for col in list(grid):
        grid.remove(col)
    for w in widths_tw:
        grid.append(_w("gridCol", w=w))
    for tr in t.findall(qn("w:tr")):
        for tc, w in zip(tr.findall(qn("w:tc")), widths_tw):
            _put(_tcpr(tc), _w("tcW", w=w, type="dxa"), TCPR_ORDER)
    return tbl


def fmt_cell(ctx: Ctx, cell, *, fill=None, pad=None, valign=None, borders=None, span=None,
             width=None):
    """`pad` = (top, start, bottom, end) in px; `borders` = {logical edge: (px, colour)}."""
    tc = cell._tc
    pr = _tcpr(tc)
    if width is not None:
        _put(pr, _w("tcW", w=width, type="dxa"), TCPR_ORDER)
    if span:
        _put(pr, _w("gridSpan", val=span), TCPR_ORDER)
    if borders:
        b = OxmlElement("w:tcBorders")
        phys = {}
        for logical, (px, colour) in borders.items():
            phys[ctx.edge(logical)] = (px, colour)
        for edge in ("top", "left", "bottom", "right"):
            if edge in phys:
                px, colour = phys[edge]
                b.append(_w(edge, val="single", sz=max(2, round(pt(px) * 8)), space=0,
                            color=colour))
        _put(pr, b, TCPR_ORDER)
    if fill:
        _put(pr, _w("shd", val="clear", color="auto", fill=fill), TCPR_ORDER)
    if pad is not None:
        top, start, bottom, end = pad
        left, right = (start, end) if not ctx.rtl else (end, start)
        m = OxmlElement("w:tcMar")
        for edge, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
            m.append(_w(edge, w=tw(v), type="dxa"))
        _put(pr, m, TCPR_ORDER)
    if valign:
        _put(pr, _w("vAlign", val=valign), TCPR_ORDER)
    return cell


def cant_split(row) -> None:
    pr = row._tr.get_or_add_trPr()
    if pr.find(qn("w:cantSplit")) is None:
        pr.append(OxmlElement("w:cantSplit"))


def row_height(row, px: float, rule: str = "atLeast") -> None:
    pr = row._tr.get_or_add_trPr()
    pr.append(_w("trHeight", val=tw(px), hRule=rule))


def vmerge(cell, val: str) -> None:
    _put(_tcpr(cell._tc), _w("vMerge", val=val) if val == "restart" else _w("vMerge"),
         TCPR_ORDER)


# ---- components -----------------------------------------------------------------

def rule_heading(ctx: Ctx, box: Box, label: str, *, width_px: float, size, color, rule,
                 spacing=0, gap=12, rule_px=1, before=0, after=10, caps=False):
    """HEADING ——————  : the label, then a hairline to the column's end: a tab
    to the end edge with a leader in the rule colour, lifted to mid-height."""
    p = box.p(before=before, after=after, tabs=[(width_px, "end", "underscore")])
    run(ctx, p, label, "heading", size=size, color=color, spacing=spacing, caps=caps)
    run(ctx, p, " " * max(1, round(gap / 4)), "body", size=size)
    # the leader is drawn in the TAB's run: its colour, its size (thickness),
    # raised so the line sits at the label's middle, not under its baseline
    run(ctx, p, "\t", "body", size=max(2, rule_px * 5), color=rule, position=size * 0.33)
    return p


def bar(ctx: Ctx, box: Box, pct: float, width_px: float, *, on: str, off: str, height=7):
    """A stacked skill bar: a one-row table, the filled part and the track."""
    pct = max(0.0, min(100.0, pct))
    full = tw(width_px)
    a = int(round(full * pct / 100))
    widths = [w for w in (a, full - a) if w > 0]
    tbl = box.table(widths)
    row = tbl.rows[0]
    row_height(row, height, "atLeast")
    for cell, colour in zip(row.cells, [on, off] if a and full - a else ([on] if a else [off])):
        fmt_cell(ctx, cell, fill=colour)
        tiny(cell.paragraphs[0])
    return tbl


def inline_bar_cells(ctx: Ctx, fill_cell, track_cell, *, on, off, height=7):
    """The bar of a name | bar | label row: two cells whose one paragraph is
    shaded - a paragraph `height` px tall, centred on the text line."""
    for cell, colour in ((fill_cell, on), (track_cell, off)):
        fmt_cell(ctx, cell, valign="center")
        para = cell.paragraphs[0]
        fmt_p(ctx, para, shade=colour)
        tiny(para, max(2, int(round(pt(height) * 2 / 1.15))))


def dots(ctx: Ctx, para, filled: int, total: int, *, on: str, off: str, size=12, gap=5):
    """●●●○○ - the dot row as glyphs (Arial has them; the CV faces may not)."""
    if not filled:
        return
    # the filled dots come first: on the right in Arabic, as in the PDF
    run(ctx, para, "●" * filled, "body", size=size, color=on, font="Arial",
        spacing=gap, rtl=True)
    if total - filled:
        run(ctx, para, "○" * (total - filled), "body", size=size, color=off,
            font="Arial", spacing=gap, rtl=True)


def skill_pct(sk: dict) -> tuple[float, str]:
    """(percent for the graphic, the text shown) - exactly as _macros.skill_bar."""
    pc = sk.get("percent")
    if pc is not None:
        return float(pc), f"{pc}%"
    return round(sk.get("dots", 0) / max(1, sk.get("dot_total", 5)) * 100), sk.get("level", "")


def rated(sk: dict) -> bool:
    return sk.get("percent") is not None or bool(sk.get("level"))


def photo_run(ctx: Ctx, para, *, size_px: float, shape: str = "circle", ring_px: float = 0,
              ring: str | None = None, placeholder: str = "E0E0E0", height_px=None):
    """The photo, cut to the template's frame, the ring drawn in; where there is
    no photo, the PDF's placeholder shape in its colours (no words: text in an
    image is not text - Word users swap it with Change Picture)."""
    from PIL import Image, ImageDraw, ImageOps

    w_px, h_px = size_px, height_px or size_px
    scale = 4
    W, H = int(w_px * scale), int(h_px * scale)
    im = None
    if ctx.photo is not None:
        try:
            with Image.open(ctx.photo) as src:
                src = ImageOps.exif_transpose(src)
                im = ImageOps.fit(src.convert("RGB"), (W, H))
        except Exception:  # noqa: BLE001 - a bad image falls back to the placeholder
            im = None
    if im is None:
        im = Image.new("RGB", (W, H), "#" + placeholder)
    im = im.convert("RGBA")
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    if shape == "circle":
        d.ellipse((0, 0, W - 1, H - 1), fill=255)
    else:
        d.rectangle((0, 0, W - 1, H - 1), fill=255)
    im.putalpha(mask)
    if ring_px and ring:
        dr = ImageDraw.Draw(im)
        rw = int(ring_px * scale)
        if shape == "circle":
            dr.ellipse((rw / 2, rw / 2, W - 1 - rw / 2, H - 1 - rw / 2), outline="#" + ring,
                       width=rw)
        else:
            dr.rectangle((rw / 2, rw / 2, W - 1 - rw / 2, H - 1 - rw / 2), outline="#" + ring,
                         width=rw)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    buf.seek(0)
    r = para.add_run()
    r.add_picture(buf, width=Pt(pt(w_px)))
    return r


def page_rects(ctx: Ctx, rects_all: list, rects_first: list = ()) -> None:
    """Fills behind the text on every page (a full-height column, page strips):
    (x_px, w_px, y_px, h_px, colour) with x in LOGICAL px from the start edge."""
    def phys(r):
        x, w, y, h, colour = r
        if ctx.rtl:
            x = PAGE_W_PX - x - w
        return (pt(x), pt(w), pt(y), pt(h), colour)
    _header_shapes(ctx.doc.sections[0], [phys(r) for r in rects_all],
                   [phys(r) for r in rects_first])


def vml_oval(ctx: Ctx, para, *, x_pt: float, y_pt: float, d_pt: float, fill: str,
             stroke: str | None, weight_pt: float = 1.5, n: int = 1):
    """A small circle anchored in `para`, positioned from the start of its text
    column (a timeline node sitting ON the line)."""
    stroke_attr = (f'strokecolor="#{stroke}" strokeweight="{weight_pt:.2f}pt"' if stroke
                   else 'stroked="f"')
    xml = (f'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           f'xmlns:v="urn:schemas-microsoft-com:vml" '
           f'xmlns:o="urn:schemas-microsoft-com:office:office"><w:pict>'
           f'<v:oval id="cvstand_node_{n}" o:allowincell="t" '
           f'style="position:absolute;margin-left:{x_pt:.2f}pt;margin-top:{y_pt:.2f}pt;'
           f'width:{d_pt:.2f}pt;height:{d_pt:.2f}pt;z-index:{n + 10};'
           f'mso-position-horizontal-relative:text;mso-position-vertical-relative:line" '
           f'fillcolor="#{fill}" {stroke_attr}/></w:pict></w:r>')
    para._p.append(parse_xml(xml))


# ---- the document -----------------------------------------------------------------

def new_document(rtl: bool):
    from ..config import WORD_MASTERS_DIR
    doc = Document(str(WORD_MASTERS_DIR / ("modern_layout_rtl.docx" if rtl else
                                           "modern_layout.docx")))
    body = doc.element.body
    for el in list(body):
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    return doc


def finish_rtl(doc) -> None:
    """Mirror the document: the section, every paragraph, every table. Runs were
    marked RTL one by one (only those holding Arabic letters)."""
    sect = doc.sections[0]._sectPr
    if sect.find(qn("w:bidi")) is None:
        el = OxmlElement("w:bidi")
        later = ("rtlGutter", "docGrid", "printerSettings", "sectPrChange")
        for i, ch in enumerate(sect):
            if ch.tag.rsplit("}", 1)[-1] in later:
                sect.insert(i, el)
                break
        else:
            sect.append(el)
    for part in [doc.element.body] + [s.header._element for s in doc.sections] + \
            [s.first_page_header._element for s in doc.sections]:
        for p in part.iter(qn("w:p")):
            _put(_ppr(p), _w("bidi"), PPR_ORDER)
        for tbl in part.iter(qn("w:tbl")):
            _put(tbl.find(qn("w:tblPr")), _w("bidiVisual"), TBLPR_ORDER)


def end_paragraph(doc) -> None:
    """The body ends with a (tiny) paragraph after the last table."""
    tiny(doc.add_paragraph())


# ---- registry ---------------------------------------------------------------------

DESIGNS: dict[str, Callable[[Ctx], None]] = {}


def design(key: str):
    def deco(fn):
        DESIGNS[key] = fn
        return fn
    return deco


def has_design(template_key: str) -> bool:
    _load()
    return template_key in DESIGNS


def _load() -> None:
    from . import word_designs  # noqa: F401  (registers the designs)


def render(data: dict, template_key: str, photo: Path | None):
    """(document, resolved theme) for a template with a Word design."""
    from ..labels import reset_lang, set_lang, t
    from ..schema import lang_of, normalize

    _load()
    r = normalize(data)
    lang = lang_of(data)
    resolved = docx_theme.resolve(data, template_key)
    doc = new_document(lang == "ar")
    docx_theme.apply(doc, resolved)
    heading = resolved["faces"]["heading"]
    docx_theme._face(docx_theme._style_rpr(doc, "CVMetric"), heading["family"],
                     heading["weight"], None)
    token = set_lang(lang)
    try:
        ctx = Ctx(doc=doc, r=r, lang=lang, resolved=resolved, photo=photo,
                  t=lambda s: str(t(s)).replace("<br>", " "))
        DESIGNS[template_key](ctx)
    finally:
        reset_lang(token)
    end_paragraph(doc)
    if lang == "ar":
        finish_rtl(doc)
    return doc, resolved
