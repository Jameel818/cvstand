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
from .docx_dml import Sp, anchored_run, inline_group_run

PX = 0.72                      # pt per template px (850px canvas on a 612pt page)
PAGE_W_PX = 850
PAGE_W = 12240                 # twips
PAGE_H_PT = 792
AR_GAP = 1.0                   # Arabic vertical gaps, of the template's
CSS_LINE_AR = 1.75             # the Arabic faces' natural line
CSS_LINE = 1.2                 # a face's "single" line, as a multiple of its size


def pt(px: float) -> float:
    return px * PX


def tw(px: float) -> int:
    return int(round(px * PX * 20))


_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
RPR_ORDER = docx_theme.RPR_ORDER
_MULT = re.compile(r"([0-9][0-9.,]*)([×+])")   # a stat like "2×"
_RANGE = re.compile(r"(\S+)(\s+[–—]\s+)(\S+)")   # a date range: start – end
_SEP = " · "                                      # a joined list: a · b · c

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
    css_lines: dict = field(init=False)

    def __post_init__(self):
        self.rtl = self.lang == "ar"
        self.css_lines = {}     # paragraph element -> the template's CSS line-height
        self.after_lines = []   # callables run once the true line heights are set
        self.labels = set()     # every catalogue label this design printed (ctx.t)

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
            prev = self.pending._p.getprevious()
            if extra and prev is not None and prev.tag == qn("w:tbl"):
                # measured in Word: an EMPTY paragraph closing a cell after a
                # nested table is not laid out at all - its spacing (this
                # padding) vanished (t8's header lost 26px). A 1pt space makes
                # it a real line again; it shows nothing.
                r = self.pending.add_run(" ")
                rpr = r._r.get_or_add_rPr()
                _rpr_put(rpr, "sz", val=2)
                _rpr_put(rpr, "szCs", val=2)
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
    # a quarter of a 1pt line (~0.3pt): Word must have this paragraph (a cell
    # ends with one, even after a nested table) but it should add nothing;
    # still an AUTO multiple, never Exactly
    _put(ppr, _w("spacing", before=int(round(pt(before_px) * 20)), after=0, line=60,
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
        # provisional; true_lines() rewrites it from the face the runs draw
        mult = max(1.0, line / (CSS_LINE_AR if ctx.rtl else CSS_LINE))
        sp.update(line=int(round(240 * mult)), lineRule="auto")
        ctx.css_lines[p] = line
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
    kw = dict(size=size, color=color, caps=caps, spacing=spacing, italic=italic, bold=bold,
              font=font, position=position, underline=underline)
    m = _RANGE.fullmatch(text or "") if ctx.rtl and not rtl else None
    if m and not _ARABIC.search(text):
        # "2013 – 2015" in an Arabic paragraph: the PDF's bidi draws it right
        # to left (2015 – 2013). Word does the same only when the dash is its
        # own right-to-left run between the two left-to-right numbers.
        run(ctx, para, m.group(1), role, **kw)
        run(ctx, para, m.group(2), role, rtl=True, **kw)
        return run(ctx, para, m.group(3), role, **kw)
    m = _MULT.fullmatch(text or "") if ctx.rtl and not rtl else None
    if m:
        # "2×" in an Arabic paragraph: the PDF's bidi shows "×2"; Word does
        # when the neutral sign is its own right-to-left run
        run(ctx, para, m.group(1), role, **kw)
        return run(ctx, para, m.group(2), role, rtl=True, **kw)
    if (ctx.rtl and not rtl and _SEP in (text or "") and _ARABIC.search(text)
            and any(p and not _ARABIC.search(p) for p in text.split(_SEP))):
        # A joined line ("555-0138-64 · laila@... · دبي") in an Arabic
        # document: one run holding Arabic gets w:rtl, and Word then reorders
        # the phone inside it ("64-0138-555" - found in t11's contact line,
        # run 5). Each item is its own run (w:rtl only where it has Arabic),
        # each separator a right-to-left run, so the items read right to left
        # as the PDF draws them.
        parts = text.split(_SEP)
        for i, part in enumerate(parts):
            if i:
                last = run(ctx, para, _SEP, role, rtl=True, **kw)
            if part:
                last = run(ctx, para, part, role, **kw)
        return last
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
            # measured in real Word (run 4): in a bidiVisual table a cell's
            # w:left / w:right BORDER is its leading / trailing edge - w:right
            # drew the Arabic timeline rail on the far (left) side, away from
            # its nodes - while w:tcMar left / right stay physical (below)
            if logical in ("start", "end"):
                phys["left" if logical == "start" else "right"] = (px, colour)
            else:
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
                 spacing=0, gap=12, rule_px=1, before=0, after=10, caps=False, keep=False):
    """HEADING ——————  : the label, then a hairline to the column's end: a tab
    to the end edge with a leader in the rule colour, lifted to mid-height.
    `keep`: kept on the page of what follows (no heading alone at a page foot)."""
    p = box.p(before=before, after=after, tabs=[(width_px, "end", "underscore")], keep=keep)
    run(ctx, p, label, "heading", size=size, color=color, spacing=spacing, caps=caps)
    run(ctx, p, " " * max(1, round(gap / 4)), "body", size=size)
    # the leader is drawn in the TAB's run: its colour, its size (thickness),
    # raised so the line sits at the label's middle, not under its baseline
    run(ctx, p, "\t", "body", size=max(2, rule_px * 5), color=rule, position=size * 0.33)
    return p


def bar(ctx: Ctx, box: Box, pct: float, width_px: float, *, on: str, off: str, height=7,
        radius=None, before=0.0):
    """A stacked skill bar on its own line: one rounded inline drawing (track +
    fill, both ends round, as the PDF's border-radius:999px bars)."""
    p = box.p(before=before, line=1.0)
    bar_shape(ctx, p, pct, width_px, on=on, off=off, height=height,
              radius=height / 2 if radius is None else radius, fill_round=True, lift=0)
    return p


def inline_bar_cells(ctx: Ctx, fill_cell, track_cell, *, on, off, height=7):
    """The bar of a name | bar | label row: two cells whose one paragraph is
    shaded - a paragraph `height` px tall, centred on the text line."""
    for cell, colour in ((fill_cell, on), (track_cell, off)):
        fmt_cell(ctx, cell, valign="center")
        para = cell.paragraphs[0]
        fmt_p(ctx, para, shade=colour)
        tiny(para, max(2, int(round(pt(height) * 2 / 1.15))))


_SHAPE_N = [0]


def bar_shape(ctx: Ctx, para, pct: float, width_px: float, *, on: str, off: str, height=7,
              radius=4, fill_round=False, lift=None):
    """A skill bar as ONE inline drawing in the text line - a group of rounded
    VML shapes (the track, the fill), so the ends are round as in the PDF and
    the bar stays an editable shape (no picture). The fill starts at the
    START edge (the right in Arabic). `fill_round`: the fill's far end is round
    too (stacked bars); otherwise it is cut square, like the PDF's fill
    clipped by its track. `lift` (px) raises it off the baseline (default:
    centred on a lower-case line)."""
    pct = max(0.0, min(100.0, pct))
    W, H = 1000, max(1, round(1000 * height / width_px))
    # VML arcsize: the corner radius as a fraction of HALF the smaller side
    arc = min(1.0, 2 * radius / max(0.1, height))
    f = round(W * pct / 100)
    x0 = W - f if ctx.rtl else 0
    _SHAPE_N[0] += 1
    n = _SHAPE_N[0]
    parts = [f'<v:roundrect style="position:absolute;left:0;top:0;width:{W};height:{H}" '
             f'arcsize="{arc:.3f}" fillcolor="#{off}" stroked="f"/>']
    sps = [Sp("roundRect", 0, 0, W, H, fill=off, radius=arc)]
    if f > 0:
        parts.append(f'<v:roundrect style="position:absolute;left:{x0};top:0;width:{f};'
                     f'height:{H}" arcsize="{arc:.3f}" '
                     f'fillcolor="#{on}" stroked="f"/>')
        sps.append(Sp("roundRect", x0, 0, f, H, fill=on, radius=arc))
        if not fill_round and f < W:
            # square off the fill's far end
            half = max(1, min(f // 2, H))
            sx = x0 if ctx.rtl else f - half
            parts.append(f'<v:rect style="position:absolute;left:{sx};top:0;width:{half};'
                         f'height:{H}" fillcolor="#{on}" stroked="f"/>')
            sps.append(Sp("rect", sx, 0, half, H, fill=on))
    lift_pt = pt(lift) if lift is not None else max(0.0, pt(height) * 0.15)
    _inline_group(para, f"cvstand_bar_{n}", width_px, height, W, H, parts, lift_pt, sps)


def _inline_group(para, gid: str, width_px: float, height_px: float, cw: int, ch: int,
                  parts: list[str], lift_pt: float, sps: list[Sp]) -> None:
    """Append ONE inline group (an editable drawing in the text line) to
    `para`: DrawingML (wpg) with the VML v:group as its fallback (docx_dml).
    Its run's font is 1pt and so is the paragraph mark, so the line is as tall
    as the drawing, no taller."""
    rpr = (f'<w:rPr><w:position w:val="{int(round(lift_pt * 2))}"/>'
           f'<w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>')
    vml = (f'<v:group id="{gid}" style="width:{pt(width_px):.2f}pt;'
           f'height:{pt(height_px):.2f}pt" coordsize="{cw},{ch}" coordorigin="0,0">'
           + "".join(parts) + '</v:group>')
    para._p.append(parse_xml(inline_group_run(gid, pt(width_px), pt(height_px), cw, ch,
                                              sps, vml, rpr)))
    ppr = _ppr(para._p)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    _rpr_put(rpr, "sz", val=2)
    _rpr_put(rpr, "szCs", val=2)


def dots_shape(ctx: Ctx, para, filled: int, total: int, *, on: str, off: str, d=9, gap=5,
               hollow=True, stroke=1.0, lift=0.0):
    """The PDF's dot row as ONE inline drawing: `total` circles `d` px wide,
    `gap` px apart, the first `filled` solid in `on`, the rest hollow rings in
    `off` (`hollow`) or solid `off`. Filled dots start at the START edge (the
    right in Arabic). Nothing is drawn for an unrated skill (filled == 0)."""
    if not filled:
        return
    total = max(total, filled)
    width = total * d + (total - 1) * gap
    k = 10                                  # coordinate units per px
    parts, sps = [], []
    for i in range(total):
        slot = (total - 1 - i) if ctx.rtl else i
        x = slot * (d + gap) * k
        if i < filled:
            parts.append(f'<v:oval style="position:absolute;left:{x};top:0;width:{d * k};'
                         f'height:{d * k}" fillcolor="#{on}" stroked="f"/>')
            sps.append(Sp("ellipse", x, 0, d * k, d * k, fill=on))
        elif hollow:
            sw = stroke * k
            parts.append(f'<v:oval style="position:absolute;left:{x + sw / 2:.0f};'
                         f'top:{sw / 2:.0f};width:{d * k - sw:.0f};height:{d * k - sw:.0f}" '
                         f'filled="f" strokecolor="#{off}" strokeweight="{pt(stroke):.2f}pt"/>')
            sps.append(Sp("ellipse", round(x + sw / 2), round(sw / 2), round(d * k - sw),
                          round(d * k - sw), line=off, line_w=pt(stroke)))
        else:
            parts.append(f'<v:oval style="position:absolute;left:{x};top:0;width:{d * k};'
                         f'height:{d * k}" fillcolor="#{off}" stroked="f"/>')
            sps.append(Sp("ellipse", x, 0, d * k, d * k, fill=off))
    _SHAPE_N[0] += 1
    _inline_group(para, f"cvstand_dots_{_SHAPE_N[0]}", width, d, round(width * k), d * k,
                  parts, pt(lift), sps)


def slider_shape(ctx: Ctx, para, pct: float, width_px: float, *, on: str, off: str,
                 track=4, knob=18, ring=3, lift=0.0):
    """The PDF's slider as ONE inline drawing: a rounded track, the filled part
    from the START edge, and a white knob with a coloured ring centred on the
    fill's end (kept inside the track). The value stays real text beside it."""
    pct = max(0.0, min(100.0, pct))
    k = 10
    W, H = round(width_px * k), knob * k
    ty, th = (knob - track) / 2 * k, track * k
    f = round(W * pct / 100)
    arc = 1.0
    x0 = W - f if ctx.rtl else 0
    cx = (W - f) if ctx.rtl else f
    kx = min(max(cx - knob * k / 2, 0), W - knob * k)
    rw = ring * k
    parts = [f'<v:roundrect style="position:absolute;left:0;top:{ty:.0f};width:{W};height:{th:.0f}" '
             f'arcsize="{arc}" fillcolor="#{off}" stroked="f"/>']
    sps = [Sp("roundRect", 0, round(ty), W, round(th), fill=off, radius=arc)]
    if f > 0:
        parts.append(f'<v:roundrect style="position:absolute;left:{x0};top:{ty:.0f};width:{f};'
                     f'height:{th:.0f}" arcsize="{arc}" fillcolor="#{on}" stroked="f"/>')
        sps.append(Sp("roundRect", x0, round(ty), f, round(th), fill=on, radius=arc))
    parts.append(f'<v:oval style="position:absolute;left:{kx + rw / 2:.0f};top:{rw / 2:.0f};'
                 f'width:{knob * k - rw:.0f};height:{knob * k - rw:.0f}" fillcolor="#FFFFFF" '
                 f'strokecolor="#{on}" strokeweight="{pt(ring):.2f}pt"/>')
    sps.append(Sp("ellipse", round(kx + rw / 2), round(rw / 2), round(knob * k - rw),
                  round(knob * k - rw), fill="FFFFFF", line=on, line_w=pt(ring)))
    _SHAPE_N[0] += 1
    _inline_group(para, f"cvstand_bar_{_SHAPE_N[0]}", width_px, knob, W, H, parts, pt(lift),
                  sps)


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


def crop_picture_height(r, new_h_pt: float) -> None:
    """Make an inline picture (python-docx run `r`) `new_h_pt` tall by
    cropping its top and bottom equally - the CSS `object-fit:cover` of a
    flex item that shrank - never squashing it."""
    from docx.oxml.ns import nsdecls  # noqa: F401
    el = r._r
    ext = el.find(".//" + qn("wp:extent"))
    old = int(ext.get("cy"))
    new = max(1, int(round(new_h_pt * 12700)))
    if new >= old:
        return
    ext.set("cy", str(new))
    for a_ext in el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}ext"):
        if a_ext.get("cy") == str(old):
            a_ext.set("cy", str(new))
    fill = next(el.iter("{http://schemas.openxmlformats.org/drawingml/2006/picture}blipFill"))
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    src = fill.find(A + "srcRect")
    if src is None:
        src = parse_xml('<a:srcRect xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>')
        blip = fill.find(A + "blip")
        blip.addnext(src)
    cut = int(round((1 - new / old) * 100000 / 2))    # 1/1000 of a percent, each edge
    src.set("t", str(cut))
    src.set("b", str(cut))


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


def page_ovals(ctx: Ctx, ovals: list) -> None:
    """Circles on every page, behind the text: (cx_px, cy_px, d_px, colour),
    cx logical from the start edge. Call after page_rects."""
    para = ctx.doc.sections[0].header.paragraphs[0]
    for n, (cx, cy, d, colour) in enumerate(ovals):
        if ctx.rtl:
            cx = PAGE_W_PX - cx
        z = n - 251650000
        vml = (f'<v:oval id="cvstand_dot_{n}" o:allowincell="f" style="position:absolute;'
               f'margin-left:{pt(cx - d / 2):.2f}pt;margin-top:{pt(cy):.2f}pt;width:{pt(d):.2f}pt;'
               f'height:{pt(d):.2f}pt;z-index:{z};mso-position-horizontal-relative:page;'
               f'mso-position-vertical-relative:page" fillcolor="#{colour}" stroked="f"/>')
        sp = Sp("ellipse", pt(cx - d / 2), pt(cy), pt(d), pt(d), fill=colour)
        para._p.append(parse_xml(anchored_run(f"cvstand_dot_{n}", sp, vml, rel_h="page",
                                              rel_v="page", z=z, in_cell=False)))


def header_picture(ctx: Ctx, path, *, x_pt: float, y_pt: float, w_pt: float, h_pt: float,
                   name: str) -> None:
    """A picture on every page, anchored to the PAGE in the header, behind the
    text and not editable as text - fixed artwork (modern-t22's rail word).
    DrawingML only: every reader that matters draws a header picture."""
    for header in [ctx.doc.sections[0].header] + (
            [ctx.doc.sections[0].first_page_header]
            if ctx.doc.sections[0].different_first_page_header_footer else []):
        header.is_linked_to_previous = False
        para = header.paragraphs[0]
        para.paragraph_format.space_after = 0
        r = para.add_run()
        r.add_picture(str(path), width=Pt(w_pt), height=Pt(h_pt))
        inline = r._r.find(".//" + qn("wp:inline"))
        drawing = inline.getparent()
        from .docx_dml import EMU, _next_id
        anchor = parse_xml(
            '<wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251700000" '
            'behindDoc="1" locked="1" layoutInCell="0" allowOverlap="1">'
            '<wp:simplePos x="0" y="0"/>'
            f'<wp:positionH relativeFrom="page"><wp:posOffset>{int(round(x_pt * EMU))}'
            '</wp:posOffset></wp:positionH>'
            f'<wp:positionV relativeFrom="page"><wp:posOffset>{int(round(y_pt * EMU))}'
            '</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{int(round(w_pt * EMU))}" cy="{int(round(h_pt * EMU))}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{_next_id()}" name="{name}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            '</wp:cNvGraphicFramePr></wp:anchor>')
        anchor.append(inline.find(qn("a:graphic")))
        drawing.remove(inline)
        drawing.append(anchor)


def vml_anchored(para, *, x_pt: float, y_pt: float, w_pt: float, h_pt: float, fill: str,
                 path: str | None = None, coords: str | None = None, z: int = 5,
                 arc: float | None = None, behind: bool = False, stroke: str | None = None,
                 weight_pt: float = 1.0) -> None:
    """A filled shape anchored in `para`, positioned PHYSICALLY from the left
    of its text column (x) and from the paragraph's top INCLUDING its space
    before (y; measured in Word - "relative to line" is not the text line):
    it moves with the text. A rectangle, or a VML `path` in `coords` units (e.g. a fold
    triangle). Behind nothing, in front of the cell fill."""
    _SHAPE_N[0] += 1
    n = _SHAPE_N[0]
    if behind:
        z = -251650000 + n            # behind the text (Word's behindDoc range)
    style = (f'position:absolute;margin-left:{x_pt:.2f}pt;margin-top:{y_pt:.2f}pt;'
             f'width:{w_pt:.2f}pt;height:{h_pt:.2f}pt;z-index:{z};'
             f'mso-position-horizontal-relative:text;mso-position-vertical-relative:line')
    stroke_attr = (f'strokecolor="#{stroke}" strokeweight="{weight_pt:.2f}pt"' if stroke
                   else 'stroked="f"')
    fill_attr = f'fillcolor="#{fill}"' if fill else 'filled="f"'
    geo = dict(fill=fill or None, line=stroke, line_w=weight_pt)
    if path:
        shape = (f'<v:shape id="cvstand_shape_{n}" o:allowincell="t" style="{style}" '
                 f'coordsize="{coords}" path="{path}" {fill_attr} {stroke_attr}/>')
        cw, ch = (float(v) for v in coords.split(","))
        sp = Sp("custom", x_pt, y_pt, w_pt, h_pt, path=path, coords=(cw, ch), **geo)
    elif arc is not None:
        shape = (f'<v:roundrect id="cvstand_shape_{n}" o:allowincell="t" style="{style}" '
                 f'arcsize="{arc:.3f}" {fill_attr} {stroke_attr}/>')
        sp = Sp("roundRect", x_pt, y_pt, w_pt, h_pt, radius=arc, **geo)
    else:
        shape = (f'<v:rect id="cvstand_shape_{n}" o:allowincell="t" style="{style}" '
                 f'{fill_attr} {stroke_attr}/>')
        sp = Sp("rect", x_pt, y_pt, w_pt, h_pt, **geo)
    para._p.append(parse_xml(anchored_run(f"cvstand_shape_{n}", sp, shape, rel_h="text",
                                          rel_v="line", z=z, in_cell=True)))


def ring_anchored(para, *, x_pt: float, y_pt: float, d_px: float, width_px: float, pct: float,
                  on: str, off: str) -> None:
    """A skill RING anchored in `para` (the percent's own paragraph): the
    track circle and the filled arc, STROKES only, in front of the text - the
    hole stays empty, so the percent (real text, centred in that paragraph)
    shows through, and a filled cell behind (a dark rail) does not hide it.
    The arc starts at 12 o'clock and runs clockwise, as CSS conic-gradient
    does in both directions. (x, y) = the ring box's top-left, from the text
    column's left and the paragraph's top."""
    pct = max(0.0, min(100.0, pct))
    sw = pt(width_px)
    inset = sw / 2
    d = pt(d_px) - sw
    _SHAPE_N[0] += 1
    n = _SHAPE_N[0]
    base = (f'position:absolute;margin-left:{x_pt + inset:.2f}pt;margin-top:{y_pt + inset:.2f}pt;'
            f'width:{d:.2f}pt;height:{d:.2f}pt;mso-position-horizontal-relative:text;'
            f'mso-position-vertical-relative:line')
    box = (x_pt + inset, y_pt + inset, d, d)
    shapes = [(f"cvstand_ring_{n}", 30 + n, Sp("ellipse", *box, line=off, line_w=sw),
               f'<v:oval id="cvstand_ring_{n}" o:allowincell="t" style="{base};z-index:{30 + n}" '
               f'filled="f" strokecolor="#{off}" strokeweight="{sw:.2f}pt"/>')]
    if pct > 0:
        end = 359.9 if pct >= 100 else pct * 3.6
        geo = (Sp("ellipse", *box, line=on, line_w=sw) if pct >= 100 else
               Sp("arc", *box, line=on, line_w=sw, start=0, end=end))
        shapes.append((f"cvstand_ringfill_{n}", 31 + n, geo,
                       f'<v:arc id="cvstand_ringfill_{n}" o:allowincell="t" '
                       f'style="{base};z-index:{31 + n}" startangle="0" endangle="{end:.1f}" '
                       f'filled="f" strokecolor="#{on}" strokeweight="{sw:.2f}pt"/>'))
    for name, z, sp, vml in shapes:
        para._p.append(parse_xml(anchored_run(name, sp, vml, rel_h="text", rel_v="line",
                                              z=z, in_cell=True)))


def vml_oval(ctx: Ctx, para, *, x_pt: float, y_pt: float, d_pt: float, fill: str,
             stroke: str | None, weight_pt: float = 1.5, n: int = 1):
    """A small circle anchored in `para`, positioned from the start of its text
    column (a timeline node sitting ON the line)."""
    stroke_attr = (f'strokecolor="#{stroke}" strokeweight="{weight_pt:.2f}pt"' if stroke
                   else 'stroked="f"')
    vml = (f'<v:oval id="cvstand_node_{n}" o:allowincell="t" '
           f'style="position:absolute;margin-left:{x_pt:.2f}pt;margin-top:{y_pt:.2f}pt;'
           f'width:{d_pt:.2f}pt;height:{d_pt:.2f}pt;z-index:{n + 10};'
           f'mso-position-horizontal-relative:text;mso-position-vertical-relative:line" '
           f'fillcolor="#{fill}" {stroke_attr}/>')
    sp = Sp("ellipse", x_pt, y_pt, d_pt, d_pt, fill=fill, line=stroke, line_w=weight_pt)
    para._p.append(parse_xml(anchored_run(f"cvstand_node_{n}", sp, vml, rel_h="text",
                                          rel_v="line", z=n + 10, in_cell=True)))


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
    # only headers that exist: reading `section.header._element` CREATES a
    # header part with a default paragraph (~14pt), which pushed every Arabic
    # page without header shapes down - modern-t13's band sat 23px low
    # (measured in Word, run 6)
    hdrs = [h for s in doc.sections for h in (s.header, s.first_page_header)
            if not h.is_linked_to_previous]
    for part in [doc.element.body] + [h._element for h in hdrs]:
        for p in part.iter(qn("w:p")):
            _put(_ppr(p), _w("bidi"), PPR_ORDER)
        for tbl in part.iter(qn("w:tbl")):
            _put(tbl.find(qn("w:tblPr")), _w("bidiVisual"), TBLPR_ORDER)


def faces_drawn(doc, resolved: dict) -> set[tuple[str, int]]:
    """docx_theme.faces_drawn, with the stat numbers' face as THIS module
    sets it (the role face in Arabic, see render)."""
    faces = docx_theme.faces_drawn(doc, resolved)
    if resolved["lang"] == "ar":
        for r in doc.element.body.iter(qn("w:rStyle")):
            if r.get(qn("w:val")) == "CVMetric":
                f = resolved["faces"]["role"]
                faces.add((f["family"], f["weight"]))
                break
    return faces


def chosen_sizes(ctx: Ctx, data: dict) -> None:
    """The user's chosen SIZES on a per-template design: a section heading is
    a heading-style run whose paragraph is one of the labels it printed."""
    apply_chosen_sizes(ctx.doc, data,
                       lambda ptext, style: style == "CVHeading" and ptext in ctx.labels)


def apply_chosen_sizes(document, data: dict, is_section, base_hp: int = 20) -> None:
    """The user's chosen SIZES (Name, Headings, Details; docs/CVSTAND_FONT_CONTROLS.md),
    applied as the PDF applies them (static/js/typography.js): a FACTOR per
    role - the name: chosen / its largest size; each section heading:
    chosen / its own largest size; details: chosen / the body's dominant size
    (by characters), applied to every other text run (job titles, labels and
    stat numbers are details in the PDF too). A chosen size is CSS pt on the
    850px page (chosen * 4/3 px; 1px = 0.72pt on paper). Graphics (bars, dots,
    rings) keep their size. A run with no size of its own is `base_hp`
    (Normal)."""
    from ..schema import typography_of
    from ..typography.render import effective
    eff = effective(typography_of(data)[0])
    want = {"name": eff["name"]["size"], "section": eff["section"]["size"],
            "body": eff["body"]["size"]}
    if all(v is None for v in want.values()):
        return

    def hp_of(rpr):
        el = rpr.find(qn("w:sz"))
        return int(el.get(qn("w:val"))) if el is not None else base_hp

    groups = {"name": [], "section": {}, "body": []}
    for p in document.element.body.iter(qn("w:p")):
        ptext = "".join(x.text or "" for x in p.iter(qn("w:t"))).strip()
        for r in p.findall(qn("w:r")):
            text = "".join(x.text or "" for x in r.iter(qn("w:t")))
            if not text.strip():
                continue
            rpr = r.get_or_add_rPr() if hasattr(r, "get_or_add_rPr") else r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r.insert(0, rpr)
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is not None and (fonts.get(qn("w:ascii")) or "") == "Arial":
                continue                          # dot glyphs: a graphic
            st = rpr.find(qn("w:rStyle"))
            style = st.get(qn("w:val")) if st is not None else None
            if style == "CVName":
                groups["name"].append(rpr)
            elif is_section(ptext, style):
                groups["section"].setdefault(id(p), []).append(rpr)
            else:
                groups["body"].append((rpr, len(text)))

    def scale(rprs, k):
        for rpr in rprs:
            hp = max(2, int(round(hp_of(rpr) * k)))
            _rpr_put(rpr, "sz", val=hp)
            _rpr_put(rpr, "szCs", val=hp)

    def target_hp(pt_css):
        return pt_css * 4 / 3 * PX * 2

    if want["name"] and groups["name"]:
        scale(groups["name"], target_hp(want["name"]) / max(hp_of(x) for x in groups["name"]))
    if want["section"]:
        for rprs in groups["section"].values():
            scale(rprs, target_hp(want["section"]) / max(hp_of(x) for x in rprs))
    if want["body"] and groups["body"]:
        chars: dict = {}
        for rpr, n in groups["body"]:
            chars[hp_of(rpr)] = chars.get(hp_of(rpr), 0) + n
        dominant = max(chars, key=chars.get)
        scale([x for x, _ in groups["body"]], target_hp(want["body"]) / dominant)


MIN_MULT, MIN_MULT_AR = 0.75, 0.78
#: An ALL-CAPS Latin line has no descenders and no marks: its ink is about
#: the cap height, so its lines may sit as tight as the PDF's (a two-line
#: caps name at CSS 0.82-1.0 in Archivo Black came out ~16px taller per line
#: in Word at 0.75 - measured, run 6)
MIN_MULT_CAPS = 0.6
#: The share of the height a multiple below 1 removes that Word takes from
#: ABOVE the first line (measured in Word, run 6; CSS takes half).
WORD_UP_BELOW_SINGLE = 0.77


def _all_caps(p, text: str) -> bool:
    """Every letter of `p` is drawn as a capital: the text is upper case, or
    every run that holds letters carries w:caps."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    if all(c.isupper() for c in letters):
        return True
    for r in p.iter(qn("w:r")):
        t = "".join(x.text or "" for x in r.iter(qn("w:t")))
        if any(c.isalpha() for c in t):
            rpr = r.find(qn("w:rPr"))
            if rpr is None or rpr.find(qn("w:caps")) is None:
                return False
    return True


def true_lines(ctx: Ctx) -> None:
    """A CSS line-height is a multiple of the font SIZE; Word's "multiple" is a
    multiple of the face's own single line, which differs per face (measured
    in Word, see docx_measure: Archivo 1.088x, Archivo Black 1.347x, IBM Plex
    Sans Arabic 1.5x). So each paragraph's multiple = CSS line / the single of
    the face its largest run draws. Below single only as far as no glyph
    collides (MIN_MULT; Arabic marks need MIN_MULT_AR) - never Exactly."""
    from .docx_measure import Measure
    m = Measure(ctx.resolved)
    for p, css in ctx.css_lines.items():
        best, size = _largest_run(m, p)
        if size == 0:
            continue
        single = m._metrics(best)["line"]
        text = "".join(t.text or "" for t in p.iter(qn("w:t")))
        floor = MIN_MULT_AR if _ARABIC.search(text) else MIN_MULT
        if floor == MIN_MULT and _all_caps(p, text):
            floor = MIN_MULT_CAPS
        mult = max(floor, css / single)
        sp = p.find(qn("w:pPr")).find(qn("w:spacing"))
        sp.set(qn("w:line"), str(int(round(240 * mult))))


def flat_headers(doc) -> None:
    """The page shapes live in the header; its paragraph must take no room.
    Measured in Word: a default header paragraph (~14pt tall at distance 0)
    pushed the body down whenever the template's top margin is smaller
    (modern-t4's name sat 14pt low)."""
    for s in doc.sections:
        s.header_distance = 0
        s.footer_distance = 0
        for hdr in (s.header, s.first_page_header):
            if hdr.is_linked_to_previous:
                continue
            for para in hdr.paragraphs:
                tiny(para)


def half_leading(ctx: Ctx) -> None:
    """CSS puts half of a line's leading ABOVE the text; Word (measured,
    multiples >= 1) keeps the first baseline at the face's ascent and puts all
    the extra space BELOW. So every paragraph with a CSS line-height gets the
    half-leading as space before and loses it from space after (or from the
    next paragraph's space before): same height, the PDF's baselines."""
    from .docx_measure import Measure
    m = Measure(ctx.resolved)
    carry_to = {}
    for p, css in ctx.css_lines.items():
        best, size = _largest_run(m, p)
        if not size:
            continue
        single = m._metrics(best)["line"]
        hl = (css - single) * size / 2           # pt
        sp = p.find(qn("w:pPr")).find(qn("w:spacing"))
        if hl < 0:
            # Below single, CSS moves the glyphs up by HALF the removed height;
            # Word moves them up by ~77% of what its multiple removes (measured,
            # run 6: modern-t7's 70px caps name rode 10-11px high once its
            # lines matched the PDF's). The difference goes down as before.
            mult = int(sp.get(qn("w:line"), 240)) / 240
            word_up = WORD_UP_BELOW_SINGLE * max(0.0, 1 - mult) * single * size
            hl = word_up - (single - css) * size / 2
        if hl <= 0.2:
            continue
        tw_hl = int(round(hl * 20))
        after0 = int(sp.get(qn("w:after"), 0))
        nxt = _next_below(p) if after0 < tw_hl else None
        if after0 < tw_hl and nxt is None:
            tw_hl = after0         # nothing below to take it back from: shift less
        if tw_hl <= 0:
            continue
        sp.set(qn("w:before"), str(int(sp.get(qn("w:before"), 0)) + tw_hl))
        after = after0 - tw_hl
        sp.set(qn("w:after"), str(max(0, after)))
        if after < 0:
            carry_to[nxt] = carry_to.get(nxt, 0) - after
    for p, debt in carry_to.items():
        ppr = p.find(qn("w:pPr"))
        sp = ppr.find(qn("w:spacing")) if ppr is not None else None
        if sp is not None:
            sp.set(qn("w:before"), str(max(0, int(sp.get(qn("w:before"), 0)) - debt)))


def _next_below(p):
    """The paragraph drawn directly BELOW `p`: its next sibling, or - when `p`
    ends a cell of a one-column table (a Stack row) - the first paragraph of
    the next row. None when unknown (a multi-column row, the end of a cell)."""
    nxt = p.getnext()
    if nxt is not None:
        return nxt if nxt.tag == qn("w:p") else None
    tc = p.getparent()
    if tc is None or tc.tag != qn("w:tc"):
        return None
    tr = tc.getparent()
    tbl = tr.getparent()
    if len(tbl.find(qn("w:tblGrid"))) != 1:
        return None
    nrow = tr.getnext()
    while nrow is not None and nrow.tag != qn("w:tr"):
        nrow = nrow.getnext()
    if nrow is None:
        return None
    return next(nrow.iter(qn("w:p")), None)


def _largest_run(m, p):
    best, size = None, 0.0
    for r in p.iter(qn("w:r")):
        if not "".join(t.text or "" for t in r.iter(qn("w:t"))).strip():
            continue
        rpr = r.find(qn("w:rPr"))
        sz = m._size(rpr)
        if sz > size:
            best, size = rpr, sz
    return best, size


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
    faces = resolved["faces"]      # Arabic: "role" is the bold body face (docx_theme.resolve)
    doc = new_document(lang == "ar")
    docx_theme.apply(doc, resolved)
    metric = faces["role"] if lang == "ar" else faces["heading"]
    docx_theme._face(docx_theme._style_rpr(doc, "CVMetric"), metric["family"],
                     metric["weight"], None)
    token = set_lang(lang)
    try:
        labels: set = set()

        def tr(s):
            # a label's <br> is a line break in Word too (python-docx writes
            # "\n" as w:br), as the PDF breaks it
            out = str(t(s)).replace("<br>", "\n").replace("&amp;", "&")
            labels.add(out.strip())
            return out
        ctx = Ctx(doc=doc, r=r, lang=lang, resolved=resolved, photo=photo, t=tr)
        ctx.labels = labels
        DESIGNS[template_key](ctx)
        chosen_sizes(ctx, data)
        true_lines(ctx)
        half_leading(ctx)
        flat_headers(doc)
        for fn in ctx.after_lines:
            fn()
    finally:
        reset_lang(token)
    end_paragraph(doc)
    if lang == "ar":
        finish_rtl(doc)
    return doc, resolved
