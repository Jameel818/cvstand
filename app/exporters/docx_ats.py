"""ATS templates in Word: each template's OWN markup, written as Word body text.

The 25 ATS templates are single-column HTML with inline styles only (no
classes carry layout). Until 2026-10 their Word downloads shared one generic
master (word_masters/ats_standard*.docx): mixed-case names, a grey rule
under every heading, a four-column stat row, dots on every skill, Word's own
type sizes - nothing like the PDF (user's review of ats-t22, "Accent Bar").

Here a download is built from the template itself. canvas_html() renders it
exactly as the PDF does (Jinja only - no browser), and the inline styles are
read element by element into Word paragraphs:

    font-size, weight, family, colour   -> the run (px of the 850px canvas,
    letter-spacing, text-transform        1px = 0.72pt on the Letter page;
                                          uppercase = w:caps, the text stays
                                          as typed for a parser)
    margin, padding, flex gap            -> space before/after, indents
    line-height                          -> Word's auto multiple, per face
                                            (docx_design.true_lines/half_leading)
    display:flex, space-between          -> a right (end) tab stop
    display:flex, fixed-width children   -> left (start) tab stops: columns
    flex:1 1px rule after a label        -> a raised underscore tab leader
    border-top/bottom/inline-start       -> paragraph borders
    background on a block (a band)       -> paragraph shading, its padding as
                                            borders in the fill colour, out to
                                            the page edge where the PDF bleeds
    <ul><li>                             -> a bullet, a tab, a hanging indent
    dot row / skill bar                  -> one inline drawing beside the
                                            level word (never text: a parser
                                            must not read "●●●○○")

ATS RULES (user, 2026-10-20) - these come before looks:
    every word of the CV is body text, in reading order: no text boxes, no
    floating shapes holding text, nothing in headers or footers, no layout
    tables (not even one cell); headings are real text; fonts embedded;
    Word's Auto line spacing only (never Exactly).
tests/test_ats_word.py checks every rule on all 25 templates, EN + AR.

ARABIC follows the PDF's font policy (rendering.RTL_TYPOGRAPHY): the name in
the name face, section titles in the heading face, everything else in the
body face (bold where the template is >= 600). Phones and e-mails inside an
Arabic line are their own left-to-right runs (docx_design.run, audit X13).

Chosen fonts and sizes (the ribbon) apply as on every other Word file: a
chosen family replaces its role's faces; sizes go through
docx_design.apply_chosen_sizes.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from functools import lru_cache

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from . import docx_design as D
from . import docx_theme
from .docx_layout import PPR_ORDER, _put, _w

CANVAS_W = 850.0
CANVAS_H = 1100.0
BLOCK_TAGS = {"div", "p", "ul", "ol", "li", "section", "header", "footer", "h1", "h2", "h3"}
INHERITED = ("font-family", "font-size", "font-weight", "color", "letter-spacing",
             "text-transform", "line-height", "text-align", "white-space")
#: Word allows at most 31pt between a paragraph border and its text; a band's
#: padding beyond that is made up by the border's own width (max 12pt).
BORDER_SPACE_MAX_PT = 31
BORDER_W_MAX_PT = 12.0
_BIDI_MARKS = re.compile("[⁦-⁩‎‏]")
_WS = re.compile(r"[ \t\r\n\f]+")
#: Separators of a joined line ("a | b · c"); in an Arabic paragraph each item
#: becomes its own run so a phone or an e-mail keeps its order (see module doc)
_JOIN = re.compile(r"( \| | · | — |, )")
NAMED = {"white": "FFFFFF", "black": "000000", "transparent": None}


def handles(template_key: str) -> bool:
    return template_key.startswith("ats-")


# ---- CSS ------------------------------------------------------------------------

def _style(el) -> dict:
    out = {}
    for decl in (el.get("style") or "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _px(v, size: float = 12.0) -> float | None:
    if v is None:
        return None
    v = v.strip()
    m = re.fullmatch(r"(-?[\d.]+)(px|em)?", v)
    if not m:
        return None
    n = float(m.group(1))
    return n * size if m.group(2) == "em" else n


def _colour(v) -> str | None:
    if not v:
        return None
    v = v.strip().lower()
    if v in NAMED:
        return NAMED[v]
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        return (h if len(h) == 6 else "".join(c * 2 for c in h)).upper()
    m = re.fullmatch(r"rgba?\(([^)]*)\)", v)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        return "".join(f"{int(float(p)):02X}" for p in parts[:3])
    return None


def _sides(st: dict, prop: str, rtl: bool, size: float) -> dict:
    """margin/padding as {top, bottom, start, end} px (shorthand + longhands)."""
    out = {"top": 0.0, "bottom": 0.0, "start": 0.0, "end": 0.0}
    if prop in st:
        vals = [(_px(x, size) or 0.0) for x in st[prop].split()]
        if vals:
            t = vals[0]
            r = vals[1] if len(vals) > 1 else t
            b = vals[2] if len(vals) > 2 else t
            left = vals[3] if len(vals) > 3 else r
            out.update(top=t, bottom=b,
                       start=(r if rtl else left), end=(left if rtl else r))
    for side, key in (("top", "top"), ("bottom", "bottom"),
                      ("left", "end" if rtl else "start"),
                      ("right", "start" if rtl else "end"),
                      ("inline-start", "start"), ("inline-end", "end")):
        v = _px(st.get(f"{prop}-{side}"), size)
        if v is not None:
            out[key] = v
    return out


def _border(st: dict, side: str):
    """(width px, colour) of a border side, or None."""
    v = st.get(f"border-{side}") or st.get("border")
    if not v:
        return None
    m = re.match(r"([\d.]+)px\s+\w+\s+(\S+)", v)
    if not m:
        return None
    c = _colour(m.group(2))
    return (float(m.group(1)), c) if c else None


def _family(st: dict) -> str:
    return st.get("font-family", "Archivo").split(",")[0].strip().strip("'\"")


def _weight(st: dict) -> int:
    v = st.get("font-weight", "400")
    return {"normal": 400, "bold": 700}.get(v, int(v) if v.isdigit() else 400)


def _size(st: dict) -> float:
    return _px(st.get("font-size"), 16.0) or 16.0


def _line(st: dict) -> float | None:
    v = st.get("line-height")
    if not v or v == "normal":
        return None
    if v.endswith("px"):
        return float(v[:-2]) / _size(st)
    try:
        return float(v)
    except ValueError:
        return None


# ---- what the walk collects -------------------------------------------------------

@dataclass
class Item:
    kind: str                     # text | tab | dots | bar | br
    text: str = ""
    st: dict = field(default_factory=dict)
    role: str = "body"            # body | name | heading
    extra: dict = field(default_factory=dict)


@dataclass
class Para:
    items: list
    x0: float                     # logical start / end of the text, canvas px
    x1: float
    st: dict
    before: float = 0.0
    after: float = 0.0
    hang: float = 0.0
    tabs: list = field(default_factory=list)      # (x px on the canvas, kind, leader)
    borders: dict = field(default_factory=dict)   # edge -> (px, colour, space px)
    shade: str | None = None
    group: int = 0
    rule: bool = False            # an empty hairline paragraph


class Walk:
    """canvas HTML -> Para list (the page's paragraphs in reading order)."""

    def __init__(self, rtl: bool):
        self.rtl = rtl
        self.paras: list[Para] = []
        self.pending = 0.0
        self.groups = 0

    # -- elements
    def computed(self, el, parent: dict) -> dict:
        st = {k: parent[k] for k in INHERITED if k in parent}
        if el.tag in ("b", "strong"):
            st["font-weight"] = "700"
        own = _style(el)
        st.update({k: v for k, v in own.items()})
        cls = (el.get("class") or "").split()      # tokens: "cv-sections-taj" is not a heading
        if "cv-name" in cls:
            st["_role"] = "name"
        elif "cv-section" in cls:
            st["_role"] = "heading"
        elif "_role" in parent:
            st["_role"] = parent["_role"]
        return st

    def is_block(self, el) -> bool:
        d = _style(el).get("display")
        if d in ("flex", "block", "grid"):
            return el.tag not in ("span", "b", "a", "strong", "em") or d == "block"
        return el.tag in BLOCK_TAGS

    def is_dot(self, el) -> bool:
        s = _style(el)
        return (el.tag == "span" and "50%" in s.get("border-radius", "") and not (el.text or "").strip()
                and len(el) == 0)

    def is_rule(self, el) -> bool:
        s = _style(el)
        return (_px(s.get("height")) is not None and _px(s.get("height")) <= 3
                and _colour(s.get("background")) and not "".join(el.itertext()).strip()
                and len(el) == 0)

    def is_bar(self, el) -> bool:
        s = _style(el)
        return (_px(s.get("height")) is not None and _colour(s.get("background"))
                and len(el) == 1 and "%" in _style(el[0]).get("width", "")
                and not "".join(el.itertext()).strip())

    # -- inline content
    def inline(self, el, st: dict, out: list, *, include_self_text=True) -> None:
        if include_self_text and el.text:
            out.append(Item("text", el.text, st, st.get("_role", "body")))
        for ch in el:
            if not isinstance(ch.tag, str):
                if ch.tail:
                    out.append(Item("text", ch.tail, st, st.get("_role", "body")))
                continue
            cst = self.computed(ch, st)
            if ch.tag == "br":
                out.append(Item("br", st=cst))
            elif self.is_dot(ch):
                pass                                   # dot groups are read by dot_group
            elif _style(ch).get("display") == "flex" and len(ch) and all(self.is_dot(x) for x in ch):
                out.append(self.dot_group(ch, cst))
            else:
                out.append(Item("mark", st=cst, extra={"open": True}))
                self.inline(ch, cst, out)
                out.append(Item("mark", st=cst, extra={"open": False}))
            if ch.tail:
                out.append(Item("text", ch.tail, st, st.get("_role", "body")))

    def dot_group(self, el, st: dict) -> Item:
        dots = list(el)
        on = [x for x in dots if _colour(_style(x).get("background"))]
        d = _px(_style(dots[0]).get("width")) or 9
        gap = _px(_style(el).get("gap")) or 4
        on_c = _colour(_style(on[0]).get("background")) if on else "000000"
        off_b = next((_border(_style(x), "top") for x in dots if x not in on), None)
        return Item("dots", st=st, extra={"filled": len(on), "total": len(dots), "d": d,
                                          "gap": gap, "on": on_c,
                                          "off": off_b[1] if off_b else "BBBBBB",
                                          "stroke": off_b[0] if off_b else 1.0})

    # -- blocks
    def block(self, el, parent: dict, x0: float, x1: float, *, flex_col_gap=None) -> None:
        st = self.computed(el, parent)
        own = _style(el)
        if own.get("display") == "none":
            return
        size = _size(st)
        mar = _sides(own, "margin", self.rtl, size)
        pad = _sides(own, "padding", self.rtl, size)
        bt, bb = _border(own, "top"), _border(own, "bottom")
        bs = _border(own, "inline-start")
        bg = _colour(own.get("background") or own.get("background-color"))
        if bg == "FFFFFF":
            bg = None                                  # the paper, not a band
        if el.tag == "p" and "margin" not in own and "margin-top" not in own:
            mar["top"] = mar["bottom"] = size          # the UA's 1em
        bx0, bx1 = x0 + mar["start"], x1 - mar["end"]  # border box
        ix0 = bx0 + pad["start"] + (bs[0] if bs else 0)
        ix1 = bx1 - pad["end"]
        self.pending += mar["top"]
        if not bt and not bg:
            self.pending += pad["top"]
        mark = len(self.paras)

        if self.is_rule(el):
            self.emit(Para([], x0=bx0, x1=bx1, st=st, rule=True,
                           borders={"bottom": (_px(own["height"]), _colour(own["background"]), 0)}))
        elif self.is_bar(el):
            fill = el[0]
            pct = float(_style(fill)["width"].rstrip("%"))
            self.emit(Para([Item("bar", st=st, extra={
                "pct": pct, "w": bx1 - bx0, "h": _px(own["height"]),
                "on": _colour(_style(fill).get("background")),
                "off": _colour(own.get("background"))})], x0=bx0, x1=bx1, st=st))
        elif own.get("display") == "flex" and own.get("flex-direction", "row") == "row":
            self.flex_row(el, st, own, ix0, ix1)
        elif el.tag in ("ul", "ol"):
            for li in el:
                if isinstance(li.tag, str):
                    self.list_item(li, st, ix0, ix1, bullet_at=ix0 - pad["start"])
        elif not any(isinstance(c.tag, str) and self.is_block(c) for c in el):
            items: list = []
            self.inline(el, st, items)
            if _has_text(items):
                self.emit(Para(items, x0=ix0, x1=ix1, st=st))
        else:
            gap = _px(own.get("gap")) if own.get("display") == "flex" else None
            first = True
            items: list = []
            if el.text and el.text.strip():
                items.append(Item("text", el.text, st, st.get("_role", "body")))
            for ch in el:
                if not isinstance(ch.tag, str):
                    continue
                if self.is_block(ch):
                    if _has_text(items):
                        self.emit(Para(items, x0=ix0, x1=ix1, st=st))
                    items = []
                    if not first and gap:
                        self.pending += gap
                    self.block(ch, st, ix0, ix1)
                    first = False
                else:
                    cst = self.computed(ch, st)
                    self.inline(ch, cst, items)
                if ch.tail and ch.tail.strip():
                    items.append(Item("text", ch.tail, st, st.get("_role", "body")))
            if _has_text(items):
                self.emit(Para(items, x0=ix0, x1=ix1, st=st))

        mine = self.paras[mark:]
        if mine and bt:
            mine[0].borders["top"] = (bt[0], bt[1], pad["top"])
        if mine and bb:
            mine[-1].borders["bottom"] = (bb[0], bb[1], pad["bottom"])
        elif not bg:
            self.pending += pad["bottom"]
        if mine and bs:
            self.groups += 1
            for p in mine:
                p.borders["start"] = (bs[0], bs[1], pad["start"])
                p.group = self.groups
        if mine and bg:
            self.groups += 1
            for p in mine:
                if p.shade:
                    continue                           # an inner band keeps its own
                p.shade = bg
                p.group = self.groups
                # the band's padding: borders in the fill colour, the same on
                # every paragraph of the band (Word draws a group's top border
                # once above it and its bottom border once below it)
                p.borders["top"] = (0, bg, pad["top"])
                p.borders["bottom"] = (0, bg, pad["bottom"])
                p.borders["start"] = (0, bg, ix0 - bx0)
                p.borders["end"] = (0, bg, bx1 - ix1)
        self.pending += mar["bottom"]

    def list_item(self, li, parent: dict, x0: float, x1: float, bullet_at: float) -> None:
        st = self.computed(li, parent)
        items: list = []
        self.inline(li, st, items)
        if _has_text(items):
            self.emit(Para(items, x0=x0, x1=x1, st=st, hang=x0 - bullet_at))

    def flex_row(self, el, st: dict, own: dict, x0: float, x1: float) -> None:
        kids = [c for c in el if isinstance(c.tag, str)]
        gap = _px(own.get("gap")) or 0.0
        items: list = []
        tabs: list = []
        between = own.get("justify-content") == "space-between"
        cursor = x0
        for i, ch in enumerate(kids):
            cst = self.computed(ch, st)
            cs = _style(ch)
            if self.is_rule(ch) or ("flex" in cs and cs.get("flex") == "1" and _colour(cs.get("background"))
                                    and not "".join(ch.itertext()).strip()):
                # "LABEL ————": the rule fills the rest of the line, at mid height
                items.append(Item("tab", st=cst, extra={"rule": _colour(cs.get("background")),
                                                        "gap": gap}))
                tabs.append((x1, "end", "underscore"))
                continue
            if i:
                if between and i == len(kids) - 1:
                    tabs.append((x1, "end", None))
                else:
                    cursor += gap
                    tabs.append((cursor, "start", None))
                items.append(Item("tab", st=cst))
            if _style(ch).get("display") == "flex" and len(ch) and all(self.is_dot(x) for x in ch):
                items.append(self.dot_group(ch, cst))
            else:
                if ch.text:
                    items.append(Item("text", ch.text, cst, cst.get("_role", "body")))
                self.inline(ch, cst, items, include_self_text=False)
            w = _px(cs.get("width"))
            if w is not None:
                cursor += w
            else:
                cursor += _text_px(items_since_tab(items))
        if _has_text(items):
            self.emit(Para(items, x0=x0, x1=x1, st=st, tabs=tabs))

    def emit(self, p: Para) -> None:
        p.before = self.pending
        self.pending = 0.0
        self.paras.append(p)


def items_since_tab(items: list) -> list:
    out = []
    for it in reversed(items):
        if it.kind == "tab":
            break
        out.append(it)
    return out[::-1]


def _text_px(items: list) -> float:
    """A rough width (px) of a run of items, for a column with no width of its
    own (only ever followed by another child in practice)."""
    n = sum(len(it.text) * _size(it.st) * 0.55 for it in items if it.kind == "text")
    return n


def _has_text(items: list) -> bool:
    return any((it.kind == "text" and it.text.strip()) or it.kind in ("dots", "bar")
               for it in items)


# ---- writing Word ---------------------------------------------------------------

class Faces:
    """The (family, weight) each run draws, and the Word name it is written as."""

    def __init__(self, resolved: dict, lang: str):
        self.resolved, self.lang = resolved, lang
        self.used: set[tuple[str, int]] = set()

    def pick(self, st: dict, role: str) -> tuple[str, int]:
        faces = self.resolved["faces"]
        w = _weight(st)
        if role in ("name", "heading"):
            f = faces[role]
            if self.lang == "ar" or f["chosen"]:
                return f["family"], f["weight"]
        elif self.lang == "ar" or faces["body"]["chosen"]:
            f = faces["body_bold"] if w >= 600 else faces["body"]
            return f["family"], f["weight"]
        fam = _family(st)
        fam = docx_theme.WORD_SUBSTITUTES.get(fam, fam)
        try:
            return fam, docx_theme.snap_weight(fam, w)
        except KeyError:
            f = faces["body_bold"] if w >= 600 else faces["body"]
            return f["family"], f["weight"]

    def word(self, st: dict, role: str) -> tuple[str, bool]:
        fam, w = self.pick(st, role)
        name = docx_theme.word_font(fam, w)
        # one face per Word name: Archivo 900 and Archivo Black are both
        # "Archivo Black" to Word, so the file embeds just one of them
        self.used.add(docx_theme._faces_by_word_name().get(name, (fam, w)))
        return name


#: role -> the role style its run carries ("headtext": a heading's other runs,
#: in the heading style but their own face)
ROLE_STYLE = {"name": "name", "heading": "heading", "body": "body", "job": "role",
              "headtext": "heading"}


def _write(ctx: D.Ctx, faces: Faces, p: Para, margin_s: float, margin_e: float,
           jobs: set, keep: bool) -> None:
    para = ctx.doc.add_paragraph()
    ind_s, ind_e = p.x0 - margin_s, margin_e - p.x1
    tabs = [(x - margin_s, kind, leader) for x, kind, leader in p.tabs]
    if p.hang:
        tabs = [(ind_s, "start", None)] + tabs
    align = {"center": "center", "right": "end", "end": "end"}.get(p.st.get("text-align"))
    if ctx.rtl and p.st.get("text-align") == "right":
        align = "start"
    toks = _collapse(p.items)
    D.fmt_p(ctx, para, align=align, before=max(0.0, p.before), after=max(0.0, p.after),
            line=_css_line(faces, p, toks) if not p.rule else None,
            ind_start=ind_s if ind_s else 0, ind_end=ind_e if ind_e else 0,
            hanging=p.hang, shade=p.shade, tabs=tabs or None, keep=keep)
    if p.group % 2:
        # a different indent by 1 twip ends Word's border/shading GROUP, so two
        # sections (or bands) never merge into one box
        ind = para._p.pPr.find(qn("w:ind"))
        if ind is None:
            ind = _w("ind")
            _put(para._p.pPr, ind, PPR_ORDER)
        ind.set(qn("w:right"), str(int(ind.get(qn("w:right"), 0)) + 1))
    if p.borders:
        _borders(ctx, para, p.borders)
    if p.rule:
        D.tiny(para)
        return
    if p.hang:
        it0 = next(it for it in p.items if it.kind == "text")
        _run(ctx, faces, para, "•\t", it0.st, "body")
    heading_para = any(it.kind == "text" and it.role == "heading" for it in toks)
    for it in toks:
        if it.kind == "tab":
            if it.extra.get("rule"):
                _rule_tab(ctx, para, it)
            else:
                r = para.add_run("\t")
                _small_run(r, it.st)
        elif it.kind == "br":
            para.add_run().add_break()
        elif it.kind == "dots":
            e = it.extra
            size = _size(it.st)
            # whole px: the drawing's coordinates must be integers (Word refuses
            # the file over cy="90.0")
            D.dots_shape(ctx, para, e["filled"], e["total"], on=e["on"], off=e["off"],
                         d=int(round(e["d"])), gap=int(round(e["gap"])), stroke=e["stroke"],
                         lift=max(0.0, size * 0.36 - e["d"] / 2))
            # the drawing made the paragraph mark 1pt: give it back its line
            _mark_size(para, size)
        elif it.kind == "bar":
            e = it.extra
            D.bar_shape(ctx, para, e["pct"], e["w"], on=e["on"], off=e["off"], height=e["h"],
                        radius=e["h"] / 2, fill_round=True, lift=0)
        elif it.kind == "text":
            role = it.role
            if role == "body" and heading_para and len(it.text.strip()) <= 4:
                role = "headtext"          # "01" before "Summary" (ats-t14) is heading too
            elif role == "body" and it.text.strip() in jobs:
                role = "job"
            _run(ctx, faces, para, it.text, it.st, role)


@lru_cache(maxsize=None)
def _asc_desc(family: str, weight: int) -> tuple[float, float]:
    """(ascent, descent) per em, as Chromium lays a line out (hhea)."""
    from fontTools.ttLib import TTFont

    from ..typography import face
    from ..typography.faces import FONT_DIR
    f = face(family, weight)
    if not f:
        return 0.9, 0.25
    t = TTFont(FONT_DIR / f["ttf"], lazy=True)
    upm = t["head"].unitsPerEm
    return t["hhea"].ascent / upm, -t["hhea"].descent / upm


def _css_line(faces: "Faces", p: Para, toks: list) -> float | None:
    """The line the PDF REALLY draws, as a multiple of the paragraph's size.
    CSS gives every inline box its own half-leading from its own face, so a
    line mixing faces (a Fraunces "14" in Source Sans text, ats-t16) grows
    past `line-height`: line box = highest (ascent + half-leading) + deepest
    (descent + half-leading), the block's own strut included. Word draws an
    exact multiple of its tallest face, so it is given this height."""
    L = _line(p.st)
    if L is None:
        return None
    boxes = [(p.st, p.items[0].role if p.items else "body")]
    boxes += [(it.st, it.role if it.role != "job" else "body") for it in toks if it.kind == "text"]
    seen = {(faces.pick(st, role), _size(st)) for st, role in boxes}
    if len(seen) < 2:
        return L
    from .docx_measure import _face_file, _font
    top = bottom = 0.0
    tallest, t_size = 0.0, _size(p.st)
    for (fam, w), s in seen:
        a, d = _asc_desc(fam, w)
        # Chromium rounds each face's ascent and descent to whole px first
        a_px, d_px = round(a * s), round(d * s)
        hl = (L * s - (a_px + d_px)) / 2
        top, bottom = max(top, a_px + hl), max(bottom, d_px + hl)
        rel = _face_file(fam, w)
        k = s * (_font(rel)["line"] if rel else 1.2)
        if k > tallest and any(_size(st) == s for st, _ in boxes[1:]):
            tallest, t_size = k, s
    # a multiple of the size of the run Word sets the line by (true_lines
    # divides it by that run's single line): a 14px Anton "14" in 12.5px
    # text (ats-t8) is 12% off when given per the paragraph's size
    return max(L * _size(p.st), top + bottom) / t_size


def _collapse(items: list) -> list:
    """HTML whitespace: runs of spaces collapse to one, none at the start or
    end of the line or around a tab; marks (span edges) vanish."""
    out: list[Item] = []
    for it in items:
        if it.kind == "mark":
            continue
        if it.kind != "text":
            out.append(it)
            continue
        if it.st.get("white-space") in ("pre-line", "pre-wrap") and "\n" in it.text:
            # a letter paragraph's own line breaks (white-space:pre-line)
            for k, line in enumerate(it.text.split("\n")):
                if k:
                    out.append(Item("br", st=it.st))
                out.append(Item("text", _BIDI_MARKS.sub("", _WS.sub(" ", line)), it.st,
                                it.role, it.extra))
            continue
        text = _BIDI_MARKS.sub("", _WS.sub(" ", it.text))
        out.append(Item("text", text, it.st, it.role, it.extra))
    prev_space = True
    for it in out:
        if it.kind != "text":
            prev_space = True
            if out and it.kind == "tab":
                pass
            continue
        if prev_space and it.text.startswith(" "):
            it.text = it.text[1:]
        if it.text:
            prev_space = it.text.endswith(" ")
    # trailing spaces before a tab / the end
    for i, it in enumerate(out):
        if it.kind == "text" and (i + 1 == len(out) or out[i + 1].kind in ("tab", "br")):
            it.text = it.text.rstrip(" ")
    return [it for it in out if it.kind != "text" or it.text]


def _run(ctx, faces: Faces, para, text: str, st: dict, role: str):
    style_role = ROLE_STYLE[role]
    name, bold = faces.word(st, "body" if role in ("job", "headtext") else role)
    kw = dict(size=_size(st), color=_colour(st.get("color")) or "000000",
              caps=st.get("text-transform") == "uppercase",
              spacing=_px(st.get("letter-spacing")) or None, font=name, bold=bold)
    if ctx.rtl and D._ARABIC.search(text) and _JOIN.search(text):
        parts = _JOIN.split(text)
        if any(x and not _JOIN.fullmatch(x) and not D._ARABIC.search(x) for x in parts):
            last = None
            for x in parts:
                if not x:
                    continue
                last = D.run(ctx, para, x, style_role, rtl=bool(_JOIN.fullmatch(x)), **kw)
            return last
    r = D.run(ctx, para, text, style_role, **kw)
    if role == "body" and st.get("background") and _colour(st.get("background")):
        rpr = r._r.get_or_add_rPr()
        D._rpr_put(rpr, "shd", val="clear", color="auto", fill=_colour(st["background"]))
    return r


def _small_run(r, st: dict) -> None:
    rpr = r._r.get_or_add_rPr()
    hp = max(2, int(round(D.pt(_size(st)) * 2)))
    D._rpr_put(rpr, "sz", val=hp)
    D._rpr_put(rpr, "szCs", val=hp)


def _rule_tab(ctx, para, it: Item) -> None:
    """The rule after a label: a gap, then a tab whose underscore leader runs to
    the end of the line, raised to the label's middle (measured in Word)."""
    size = _size(it.st)
    gap = it.extra.get("gap") or 0
    if gap:
        sp = para.add_run(" ")
        rpr = sp._r.get_or_add_rPr()
        hp = max(2, int(round(D.pt(size) * 2)))
        D._rpr_put(rpr, "sz", val=hp)
        D._rpr_put(rpr, "szCs", val=hp)
        D._rpr_put(rpr, "spacing", val=int(round(D.pt(max(0.0, gap - size * 0.28)) * 20)))
    r = para.add_run("\t")
    rpr = r._r.get_or_add_rPr()
    D._rpr_put(rpr, "color", val=it.extra["rule"])
    D._rpr_put(rpr, "position", val=int(round(D.pt(size) * 0.62)))
    D._rpr_put(rpr, "sz", val=8)
    D._rpr_put(rpr, "szCs", val=8)


def _mark_size(para, size_px: float) -> None:
    rpr = para._p.pPr.find(qn("w:rPr"))
    if rpr is not None:
        hp = max(2, int(round(D.pt(size_px) * 2)))
        D._rpr_put(rpr, "sz", val=hp)
        D._rpr_put(rpr, "szCs", val=hp)


def _borders(ctx, para, borders: dict) -> None:
    bdr = OxmlElement("w:pBdr")
    phys = {}
    for logical, (px, colour, space_px) in borders.items():
        phys[ctx.edge(logical)] = (px, colour, space_px)
    for edge in ("top", "left", "bottom", "right"):
        if edge not in phys:
            continue
        px, colour, space_px = phys[edge]
        total = D.pt(space_px)
        line = D.pt(px) if px else 0.0
        # measured in Word (ats-t5, t16): a drawn rule takes no height of its
        # own, so the CSS border width rides in the spacing
        space = min(BORDER_SPACE_MAX_PT, int(round(max(0.0, total + line))))
        if px == 0:
            # a fill-coloured border standing for padding: what the 31pt space
            # cannot hold goes into the border's own width
            line = min(BORDER_W_MAX_PT, max(0.25, total - space))
        sz = max(2, min(96, int(round(line * 8))))
        bdr.append(_w(edge, val="single", sz=sz, space=space, color=colour))
    if "bottom" in phys and phys["bottom"][0]:
        # two neighbours with the same rule are one Word group: draw it between
        # them too, as the PDF draws it under each
        px, colour, _ = phys["bottom"]
        bdr.append(_w("between", val="single", sz=max(2, int(round(D.pt(px) * 8))), space=0,
                      color=colour))
    _put(D._ppr(para._p), bdr, PPR_ORDER)


# ---- the document -----------------------------------------------------------------

_SIG = ("font-family", "font-size", "font-weight", "color", "letter-spacing", "text-transform")


def _mark_unclassed_headings(paras: list) -> None:
    """A heading the template did not mark .cv-section (ats-t4 joins three
    section names into one head) is still a heading in Word - kept with what
    follows, sized as one: a one-run paragraph styled exactly like the marked
    headings."""
    sigs = {tuple(it.st.get(k) for k in _SIG) for p in paras for it in p.items
            if it.kind == "text" and it.role == "heading"}
    for p in paras:
        texts = [it for it in p.items if it.kind == "text" and it.text.strip()]
        if texts and all(it.role == "body" and tuple(it.st.get(k) for k in _SIG) in sigs
                         for it in texts):
            for it in texts:
                it.role = "heading"

def _mode(values: list[float]) -> float:
    from collections import Counter
    return Counter(round(v, 1) for v in values).most_common(1)[0][0]


def build(data: dict, template_key: str, gaps: float = 1.0, type_k: float = 1.0,
          html: str | None = None):
    """(document, resolved theme, faces used, text width pt). `html`: another
    page in this template's identity to write instead of the CV - the cover
    letter (app/letter.py letterhead_canvas)."""
    from lxml import html as LH

    from ..labels import reset_lang, set_lang, t
    from ..rendering import canvas_html
    from ..schema import lang_of, normalize

    r = normalize(data)
    lang = lang_of(data)
    rtl = lang == "ar"
    resolved = docx_theme.resolve(data, template_key)
    doc = D.new_document(rtl)
    docx_theme.apply(doc, resolved)
    frag = LH.fragment_fromstring(html or canvas_html(data, template_key), create_parent="div")
    tpl = next(e for e in frag.iter() if "tpl" in (e.get("class") or "").split())
    walk = Walk(rtl)
    root_st = {"font-size": "16px"}
    tst = walk.computed(tpl, root_st)
    tpad = _sides(_style(tpl), "padding", rtl, _size(tst))
    # the page's own padding is the page margin; everything inside is laid out
    # from it (a full-bleed band reaches back out to the paper's edge)
    walk.block(tpl, root_st, 0.0, CANVAS_W)
    paras = walk.paras
    if not paras:
        raise ValueError(f"{template_key}: nothing to write")
    _mark_unclassed_headings(paras)
    text = [p for p in paras if not p.shade and not p.rule]
    margin_s = _mode([p.x0 for p in text]) if text else tpad["start"]
    margin_e = CANVAS_W - _mode([p.x1 for p in text]) if text else tpad["end"]
    sec = doc.sections[0]
    sec.left_margin = Pt(D.pt(margin_e if rtl else margin_s))
    sec.right_margin = Pt(D.pt(margin_s if rtl else margin_e))
    # the first paragraph's space above becomes the top margin (Word drops space
    # before at the top of a page); a band at the very top keeps margin 0
    first = paras[0]
    top = first.before
    first.before = 0.0
    if first.shade:
        top = max(0.0, top)
    sec.top_margin = Pt(max(0.1, D.pt(top)))
    sec.bottom_margin = Pt(max(0.1, D.pt(tpad["bottom"])))
    sec.header_distance = sec.footer_distance = 0

    token = set_lang(lang)
    try:
        labels = set()
        ctx = D.Ctx(doc=doc, r=r, lang=lang, resolved=resolved, photo=None, t=t)
        ctx.direct_faces = True
        faces = Faces(resolved, lang)
        jobs = {j["role"].strip() for j in r.get("experience", []) if j.get("role")}
        # a job title can only come after the first section heading: above
        # it, "Creative Lead" is the headline, not a job
        in_body = False
        was_job = False
        for p in paras:
            heading = any(it.role == "heading" for it in p.items if it.kind == "text")
            in_body = in_body or heading
            js = jobs if in_body else set()
            is_job = any(it.kind == "text" and it.text.strip() in js and it.role == "body"
                         for it in p.items)
            if heading:
                labels.add("".join(it.text for it in p.items if it.kind == "text").strip())
            # a job title keeps with its next line, and that line with the
            # one after (its first bullet): tests/test_docx_flow.py
            keep = heading or is_job or (was_job and not is_job)
            _write(ctx, faces, p, margin_s, CANVAS_W - margin_e, js, keep)
            was_job = is_job
        ctx.labels = {_WS.sub(" ", x) for x in labels}
        D.chosen_sizes(ctx, data)
        if gaps != 1.0:
            D.scale_gaps(doc, gaps)
        if type_k != 1.0:
            D.scale_type(doc, type_k)
        D.true_lines(ctx)
        D.half_leading(ctx)
    finally:
        reset_lang(token)
    D.flat_headers(doc)
    if rtl:
        D.finish_rtl(doc)
    width_pt = D.pt(CANVAS_W - margin_s - margin_e)
    return doc, resolved, faces.used, width_pt


#: Arabic runs taller in Word than the font-file estimate says (run 2: 20-50pt
#: on a full page; here 30-45pt on ats-t7/t18/t21/t23, measured in Word,
#: 2026-10-20), so an Arabic page is fitted as if it held this much more.
AR_RESERVE_PT = 45.0
#: ...and the ladder's last step is taken while the RAW estimate is at most
#: ~25pt over (in real Word those pages fit: ats-t3/t6/t7/t16 AR, round 7)
AR_FLOOR_EXTRA_PT = 60.0


def overflow_pt(doc, resolved, width_pt: float) -> float:
    from .docx_measure import Measure
    m = Measure(resolved, direct_faces=True)
    sec = doc.sections[0]
    avail = D.PAGE_H_PT - sec.top_margin.pt - sec.bottom_margin.pt
    over = sum(m.paragraph(p, width_pt) for p in doc.element.body.iter(qn("w:p"))) - avail
    return over + (AR_RESERVE_PT if resolved["lang"] == "ar" else 0.0)


def fitted(data: dict, template_key: str, html: str | None = None, base=None):
    """(document, faces used): built, then fitted with the PDF's ladder when it
    runs a little past one page. `base` = a (gaps, type) fit to start from -
    the CV's own, for its cover letter: the letterhead is the CV's header
    exactly as the CV drew it (user, 2026-10-20)."""
    g0, t0 = base or (1.0, 1.0)
    doc, resolved, used, width = build(data, template_key, g0, t0, html=html)
    doc.cvstand_fit = base
    over = overflow_pt(doc, resolved, width)
    if D.TYPE_FIT_TRIGGER_PT < over <= D.TYPE_FIT_PAGE_MAX_PT:
        # the PDF's autofit ladder (gaps, then type), as the Modern designs do;
        # a page the ladder cannot fit flows on at its own sizes (never squeezed)
        # English fits by its gaps only, as its PDF does (measured: the PDF's
        # autofit never scaled type on these 50 pages); Arabic runs taller in
        # Word than in the PDF, so it may also take the type steps
        steps = (D.TYPE_FIT_STEPS if resolved["lang"] == "ar"
                 else tuple(s for s in D.TYPE_FIT_STEPS if s[1] == 1.0))
        if base:
            # only the steps tighter than the one the page starts from
            steps = tuple(s for s in steps if s[0] <= g0 and s[1] <= t0 and s != (g0, t0))
        for gaps, type_k in steps:
            d2, r2, u2, w2 = build(data, template_key, gaps, type_k, html=html)
            o2 = overflow_pt(d2, r2, w2)
            floor = D.TYPE_FIT_FLOOR_OK_PT + (AR_FLOOR_EXTRA_PT if r2["lang"] == "ar" else 0.0)
            if o2 <= D.TYPE_FIT_TARGET_PT or (
                    (gaps, type_k) == steps[-1] and o2 <= floor):
                doc, resolved, used = d2, r2, u2
                doc.cvstand_fit = (gaps, type_k)
                break
    return doc, set(used)


def letter_doc(data: dict, template_key: str):
    """(document, faces used) of the cover letter: the CV's own header
    paragraphs, then the plain body (app/letter.py letterhead_canvas)."""
    from .. import letter as letter_mod
    from ..schema import lang_of
    from .docx_letter import word_body_px
    px = word_body_px(letter_mod.letter_of(data), lang_of(data), template_key)
    # the CV's own fit: an Arabic CV that took a type step to fit its page
    # drew its name 3-11% smaller than an unfitted letter would (user's
    # review, 2026-10-20). The body is sized so that after the same type step
    # it is still the size chosen for it.
    cv, _ = fitted(data, template_key)
    base = cv.cvstand_fit
    if base:
        px = px / base[1]
    return fitted(data, template_key, html=letter_mod.letterhead_canvas(data, template_key,
                                                                         body_px=px),
                  base=base)


def render(data: dict, template_key: str, part: str = "cv") -> bytes:
    """The Word file of an ATS template's CV, its cover letter ("letter"), or
    both, the letter in its own section on its own page ("both")."""
    from . import docx_font_embed
    if part == "letter":
        doc, used = letter_doc(data, template_key)
    else:
        doc, used = fitted(data, template_key)
        if part == "both":
            from . import docx_letter
            ldoc, lused = letter_doc(data, template_key)
            docx_letter.append_document(doc, ldoc)
            used |= lused
    buf = io.BytesIO()
    doc.save(buf)
    return docx_font_embed.embed_fonts(buf.getvalue(), used)
