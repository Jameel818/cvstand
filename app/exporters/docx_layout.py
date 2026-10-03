"""The Word LAYOUTS: each Modern template's shape in Word (docs/WORD_LAYOUTS_PLAN.md).

Two masters serve the 24 Modern templates (tools/build_word_masters.py):
`modern_layout` - a 2x2 table, [top side | top main] over [side | main] - and
`modern_gutter` for modern-t19. What differs per template is DATA, measured
from the rendered template into app/word_layouts.json
(tools/build_word_layouts.py): which items sit in which cell and in what
order, the section headings' own words, the zone colours, the side column's
width, the band, the photo.

This module does two things:

  context()  the `lay` variable docxtpl fills the master from: each cell's
             items, keeping only what this résumé has, so no heading is ever
             left without its section.
  apply()    reshapes the FILLED document for its template:
               - drops an empty top row; merges it across both columns for a
                 full-width band or an open layout's header;
               - drops the side column when the template has none;
               - puts the side column on the right (`side: end`); the RTL
                 master mirrors all of it (w:bidiVisual);
               - widths, cell fills, the colours of each cell's role styles;
               - a full-height side column: a shape in the page header, behind
                 the text, so the fill reaches the page edges on every page
                 however long the résumé runs (the cells are filled too, for a
                 reader that ignores header shapes);
               - heading fills (ribbons) and rules, the name and heading
                 sizes, the centred header of modern-t6, the skill bars.

Everything inserted goes in at its schema position; an OOXML property
element appended at the end is well-formed and still makes Word refuse the
file (tests/test_docx_validity.py).
"""
from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path

from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn

from .docx_theme import (
    BAR_OFF, BAR_ON, LAYOUT_CELLS, PS_CONTACT, ST_CONTACT, _face, _set, _style_rpr,
    cell_style, contrast_on_white, head_para_style,
)

LAYOUTS_PATH = Path(__file__).resolve().parent.parent / "word_layouts.json"

#: Archetypes whose templates use the layout masters. The others keep the
#: single-column Modern master until their milestone lands (plan §8).
ARCHETYPES_ON = ("sidebar", "band", "open", "gutter")

PAGE_W = 12240                  # Letter, twips (8.5in); the canvas is 850 x 1100 px
PAGE_H_PT = 792
PAGE_W_PT = 612
TOP_MARGIN_PT = 28.8            # 0.4in: the layout master's top/bottom margin
PAD_SIDE = 432                  # 0.3in either side of a side column's text
PAD_MAIN = 540                  # 0.375in either side of the main column's text
PAD_TOP = 200                   # a cell's text starts 10pt below its top edge
SEAM = 0.75                     # pt of overlap between two neighbouring fills
MIN_SIDE = 0.30                 # of the page: narrower, an email address breaks mid-word


def side_width(L: dict) -> int:
    """The side column's width in twips: the template's, but never under
    MIN_SIDE (modern-t22's is 24.7%, where Word broke the email address in
    two - the PDF's smaller type fits it)."""
    return round(max(L["side_w"], MIN_SIDE) * PAGE_W)


@lru_cache(maxsize=1)
def layouts() -> dict:
    return json.loads(LAYOUTS_PATH.read_text(encoding="utf-8"))["templates"]


def spec_for(template_key: str) -> dict | None:
    """The template's layout, or None when it keeps the single-column master."""
    spec = layouts().get(template_key)
    if spec is None or spec["archetype"] not in ARCHETYPES_ON:
        return None
    return spec


def master_for(template_key: str) -> str | None:
    spec = spec_for(template_key)
    if spec is None:
        return None
    return "modern_gutter.docx" if spec["archetype"] == "gutter" else "modern_layout.docx"


# ---- context ------------------------------------------------------------------

def _present(kind: str, r: dict, photo) -> bool:
    return {
        "name": True, "title": bool(r.get("title")), "photo": bool(photo),
        "contact": bool(r.get("contact_items")), "contact_line": bool(r.get("contact_line")),
    }.get(kind, bool(r.get(kind)))


def _item(entry: dict, lang: str, r: dict | None = None) -> dict:
    it = dict(entry)
    label = it.get("label")
    if label:
        it["text"] = label.upper() if it.get("caps") and lang == "en" else label
    if it["k"] == "experience" and r is not None:
        it["jobs"] = list(r.get("experience") or [])
    return it


def blocks(items: list[dict]) -> list[list[dict]]:
    """The main column as unbreakable blocks (one table row each): a section
    with its heading and whatever unlabelled items follow it; the experience
    split per job, the first job carrying the heading. Items before the first
    section (name, title, chips...) form the first block."""
    out: list[list[dict]] = []
    for it in items:
        if it["k"] == "experience" and len(it.get("jobs") or []) > 1:
            first = dict(it, jobs=it["jobs"][:1])
            out.append([first])
            for job in it["jobs"][1:]:
                out.append([{"k": "experience", "jobs": [job]}])
        elif it.get("label") or not out:
            out.append([it])
        else:
            out[-1].append(it)
    return out


def context(r: dict, template_key: str, lang: str, photo) -> dict:
    """`lay` for docxtpl: each cell's items that this résumé actually has."""
    spec = layouts()[template_key]
    L = spec[lang]
    keep = lambda items: [_item(e, lang, r) for e in items if _present(e["k"], r, photo)]  # noqa: E731
    cells = {name: keep(items) for name, items in L["cells"].items()}
    full = bool(cells["top_full"])
    lay = {
        "top_side": cells["top_full"] if full else cells["top_side"],
        "top_main": [] if full else cells["top_main"],
        "side": cells["side"], "main": cells["main"],
        "blocks": blocks(cells["main"]) or [[]],
        "bars": spec["skills"] == "bars",
    }
    if spec["archetype"] == "gutter":
        everything = [i for n in ("top_full", "top_side", "top_main", "main", "side")
                      for i in cells[n]]
        lay["head"] = [i for i in everything if not i.get("label")]
        # one row per section, and one per job (the first carries the label):
        # a row that cannot split is Word's only reliable keep-together
        lay["rows"] = [b[0] for b in blocks([i for i in everything if i.get("label")])]
    lay["_full_top"] = full
    return lay


def photo_image(tpl, path: Path, template_key: str, lang: str):
    """The photo at the template's size, cut to a circle where the template's
    is round; "" when the template has no photo slot."""
    from docx.shared import Mm
    from docxtpl import InlineImage
    from PIL import Image, ImageDraw, ImageOps

    L = layouts()[template_key][lang]
    if not L.get("photo"):
        return ""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        side = min(im.size)       # the templates' photo boxes are square, object-fit: cover
        im = ImageOps.fit(im, (side, side))
        if L["photo"]["round"]:
            im = im.convert("RGBA")
            mask = Image.new("L", (side, side), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
            im.putalpha(mask)
        else:
            im = im.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "PNG")
    buf.seek(0)
    return InlineImage(tpl, buf, width=Mm(L["photo"]["mm"]))


# ---- colour helpers -------------------------------------------------------------

def _rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(h: str) -> float:
    return 1.05 / contrast_on_white(h) - 0.05


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable(fg: str | None, bg: str, minimum: float = 3.0) -> str:
    """`fg` if it reads on `bg`, else black or white, whichever reads better:
    no text may vanish into its fill (modern-t21's white contact text would
    sit on lime otherwise)."""
    if fg and contrast(fg, bg) >= minimum:
        return fg
    return "000000" if contrast("000000", bg) >= contrast("FFFFFF", bg) else "FFFFFF"


def blend(a: str, b: str, t: float) -> str:
    """t of the way from a to b."""
    return "%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))


# ---- OOXML helpers --------------------------------------------------------------

TCPR_ORDER = ("cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd",
              "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark")
TBLPR_ORDER = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
               "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
               "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")
PPR_ORDER = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
             "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
             "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
             "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
             "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
             "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange")


def _put(parent, el, order: tuple[str, ...]) -> None:
    """Replace `el`'s namesake in `parent`, at its schema position."""
    local = el.tag.rsplit("}", 1)[-1]
    old = parent.find(qn(f"w:{local}"))
    if old is not None:
        parent.remove(old)
    later = order[order.index(local) + 1:]
    for i, child in enumerate(parent):
        if child.tag.rsplit("}", 1)[-1] in later:
            parent.insert(i, el)
            return
    parent.append(el)


def _w(tag: str, **attrs):
    el = OxmlElement(f"w:{tag}")
    for k, v in attrs.items():
        el.set(qn(f"w:{k}"), str(v))
    return el


def _tcpr(tc):
    pr = tc.find(qn("w:tcPr"))
    if pr is None:
        pr = OxmlElement("w:tcPr")
        tc.insert(0, pr)
    return pr


def _fill(tc, color: str | None) -> None:
    if color:
        _put(_tcpr(tc), _w("shd", val="clear", color="auto", fill=color), TCPR_ORDER)


def _width(tc, twips: int) -> None:
    _put(_tcpr(tc), _w("tcW", w=twips, type="dxa"), TCPR_ORDER)


def _margins(tc, side: int, top: int = PAD_TOP, bottom: int = 120) -> None:
    mar = OxmlElement("w:tcMar")
    for edge, v in (("top", top), ("left", side), ("bottom", bottom), ("right", side)):
        mar.append(_w(edge, w=v, type="dxa"))
    _put(_tcpr(tc), mar, TCPR_ORDER)


def _span(tc, n: int) -> None:
    _put(_tcpr(tc), _w("gridSpan", val=n), TCPR_ORDER)


def _ppr_of_style(document, style_id: str):
    for st in document.styles.element.findall(qn("w:style")):
        if st.get(qn("w:styleId")) == style_id:
            ppr = st.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                rpr = st.find(qn("w:rPr"))
                if rpr is not None:
                    rpr.addprevious(ppr)
                else:
                    st.append(ppr)
            return ppr
    raise KeyError(style_id)


def _size(rpr, pt: float) -> None:
    _set(rpr, "sz", {"w:val": str(int(round(pt * 2)))})
    _set(rpr, "szCs", {"w:val": str(int(round(pt * 2)))})


def _sid(name: str | None) -> str | None:
    return None if name is None else name.replace(" ", "")


# ---- the header shapes (full-height side column, band strip) --------------------

_VML_NS = 'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"'


def _rect(x_pt: float, w_pt: float, y_pt: float, h_pt: float, color: str, n: int) -> str:
    """A page-anchored fill behind the text: DrawingML with the VML as its
    fallback (docx_dml - LibreOffice ignored the VML-only fills)."""
    from .docx_dml import Sp, anchored_run
    z = n - 251658240
    vml = (f'<v:rect id="cvstand_fill_{n}" o:allowincell="f" '
           f'style="position:absolute;margin-left:{x_pt:.2f}pt;margin-top:{y_pt:.2f}pt;'
           f'width:{w_pt:.2f}pt;height:{h_pt:.2f}pt;z-index:{z};'
           f'mso-position-horizontal-relative:page;mso-position-vertical-relative:page" '
           f'fillcolor="#{color}" stroked="f"/>')
    return anchored_run(f"cvstand_fill_{n}", Sp("rect", x_pt, y_pt, w_pt, h_pt, fill=color),
                        vml, rel_h="page", rel_v="page", z=z, in_cell=False)


def _header_shapes(section, rects_all: list, rects_first: list) -> None:
    """Coloured rectangles behind the text, placed on the PAGE: `rects_all` on
    every page, `rects_first` on the first one only (the band's strip above
    the table), drawn later = in front (a full-width band's strip covers the
    side column's fill above the band, modern-t21). Headers repeat on every page, so the side column is full
    height on page 2 too."""
    def fill(header, rects):
        header.is_linked_to_previous = False
        para = header.paragraphs[0]
        para.paragraph_format.space_after = 0
        for i, r in enumerate(rects):
            para._p.append(parse_xml(_rect(*r, n=i + 1)))
    if not rects_all and not rects_first:
        return
    fill(section.header, rects_all)
    if rects_first:
        section.different_first_page_header_footer = True
        fill(section.first_page_header, rects_all + rects_first)


# ---- apply ----------------------------------------------------------------------

def _grid(tbl, widths: list[int]) -> None:
    """Rewrite the table's grid. docxtpl's fix_tables() counts the cells of
    EVERY row under a table - nested rows included - and widens the outer grid
    to match, so a 5-segment skill bar inside a cell gave the 2-column layout
    table 5 grid columns and Word laid its cells out on the wrong grid."""
    grid = tbl.find(qn("w:tblGrid"))
    for col in grid.findall(qn("w:gridCol")):
        grid.remove(col)
    for w in widths:
        grid.append(_w("gridCol", w=w))


def _layout_table(document):
    return document.element.body.find(qn("w:tbl"))


def _rows(tbl):
    return tbl.findall(qn("w:tr"))


def _tcs(tr):
    return tr.findall(qn("w:tc"))


def apply(document, template_key: str, lang: str, resolved: dict, lay: dict) -> None:
    spec = layouts()[template_key]
    if spec["archetype"] == "gutter":
        _apply_gutter(document)
        _apply_styles(document, spec, lang, resolved, {"Main": "main"}, {"main": "FFFFFF"})
        if spec["timeline"]:
            _timeline(document, resolved["accent"], lang == "ar")
        return
    L = spec[lang]
    tbl = _layout_table(document)
    rows = _rows(tbl)
    band = L["band"]
    has_side = L["side_w"] is not None
    top_items = bool(lay["top_side"] or lay["top_main"])

    # which zone (colours) each cell shows
    zone = {"top_side": "side", "top_main": "main", "side": "side", "main": "main"}
    if band:
        zone[{"full": "top_side", "main": "top_main", "side": "top_side"}[band["span"]]] = "band"
    if lay["_full_top"] and not band:
        zone["top_side"] = "head"
    bgs = {"side": L["side_bg"] or "FFFFFF", "band": band["bg"] if band else "FFFFFF",
           "main": "FFFFFF", "head": "FFFFFF"}

    # ---- structure. Map each cell BEFORE any swap: top row, then body row.
    cell_of = {}                     # tc -> our cell name
    if not top_items:
        tbl.remove(rows[0])
        rows = rows[1:]
        zone.pop("top_side"), zone.pop("top_main")
    else:
        top = _tcs(rows[0])
        if lay["_full_top"] or not has_side:     # one cell across the page
            rows[0].remove(top[1])
            if has_side:
                _span(top[0], 2)
            cell_of[top[0]] = "top_side"
            zone.pop("top_main")
        else:
            cell_of[top[0]], cell_of[top[1]] = "top_side", "top_main"
    body_rows = rows[1:] if top_items else rows
    for tr in body_rows:
        body = _tcs(tr)
        if has_side:
            cell_of[body[0]], cell_of[body[1]] = "side", "main"
        else:                        # no side column: a one-column grid
            tr.remove(body[0])
            cell_of[body[1]] = "main"
    if not has_side:
        zone.pop("side")
    if spec["side"] == "end":        # the side column on the right (LTR)
        for tr in rows:
            tcs = _tcs(tr)
            if len(tcs) == 2:
                tr.remove(tcs[0])
                tr.append(tcs[0])

    # ---- widths, fills, margins
    side_w = side_width(L) if has_side else 0
    main_w = PAGE_W - side_w
    order = ([side_w, main_w] if spec["side"] != "end" else [main_w, side_w])
    _grid(tbl, [w for w in order if w] if has_side else [PAGE_W])
    tbl_pr = tbl.find(qn("w:tblPr"))
    _put(tbl_pr, _w("tblW", w=PAGE_W, type="dxa"), TBLPR_ORDER)
    _put(tbl_pr, _w("tblInd", w=0, type="dxa"), TBLPR_ORDER)
    _put(tbl_pr, _w("tblLayout", type="fixed"), TBLPR_ORDER)
    first_body, last_body = body_rows[0], body_rows[-1]
    for tc, name in cell_of.items():
        span = tc.find(qn("w:tcPr")) is not None and tc.find(qn("w:tcPr")).find(qn("w:gridSpan")) is not None
        _width(tc, PAGE_W if span else (side_w if name in ("side", "top_side") else main_w))
        z = zone[name]
        tr = tc.getparent()
        # the column's padding at its top and bottom only: blocks stack tight
        body_row = tr in body_rows
        top = PAD_TOP if (not body_row or tr is first_body) else 0
        bottom = 120 if (not body_row or tr is last_body) else 0
        _margins(tc, PAD_SIDE if z == "side" else PAD_MAIN, top, bottom)
        _fill(tc, None if bgs[z] == "FFFFFF" else bgs[z])

    # ---- the rule between the columns, where the PDF draws one (t1, t6)
    if has_side and L.get("split_rule"):
        borders = tbl_pr.find(qn("w:tblBorders"))
        inside = borders.find(qn("w:insideV"))
        for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", L["split_rule"])):
            inside.set(qn(f"w:{k}"), v)

    # ---- the full-height side column and the band's strip, behind the text
    rects_all, rects_first = [], []
    rtl = lang == "ar"
    side_pt = side_w / 20
    def x_of(start: bool, w_pt: float) -> float:
        # logical start = left in English, right in Arabic
        return 0.0 if start != rtl else PAGE_W_PT - w_pt
    if has_side and L["side_bg"]:
        # 0.75pt wider than the column, reaching under its neighbour: two fills
        # that only ABUT leave a light hairline between them on screen
        wide = side_pt + SEAM
        x = x_of(spec["side"] != "end", side_pt)
        rects_all.append((x if x == 0.0 else x - SEAM, wide, 0.0, float(PAGE_H_PT),
                          L["side_bg"]))
    if band and top_items:
        if band["span"] == "full" or not has_side:
            rects_first.append((0.0, float(PAGE_W_PT), 0.0, TOP_MARGIN_PT + 0.5, band["bg"]))
        elif band["span"] == "main":
            main_pt = PAGE_W_PT - side_pt
            rects_first.append((x_of(spec["side"] == "end", main_pt), main_pt, 0.0,
                                TOP_MARGIN_PT + 0.5, band["bg"]))
        else:   # over the side column: the side shape is already its colour below
            rects_first.append((x_of(spec["side"] != "end", side_pt), side_pt, 0.0,
                                TOP_MARGIN_PT + 0.5, band["bg"]))
    _header_shapes(document.sections[0], rects_all, rects_first)

    # ---- centred header (modern-t6)
    if L["name"]["centred"] and lay["_full_top"]:
        for tc, name in cell_of.items():
            if name == "top_side":
                for p in tc.iter(qn("w:p")):
                    _put(_ppr(p), _w("jc", val="center"), PPR_ORDER)

    cell_zone = {{"top_side": "TopSide", "top_main": "TopMain", "side": "Side",
                  "main": "Main"}[n]: zone[n] for n in cell_of.values()}
    _apply_styles(document, spec, lang, resolved, cell_zone, bgs, cell_of=cell_of)
    if spec["timeline"]:
        _timeline(document, resolved["accent"], lang == "ar")


def _timeline(document, accent: str, rtl: bool) -> None:
    """The template's experience timeline, as Word can draw it: an accent bar
    down the START edge of each job's title and company/date line. (One
    continuous line through the bullets is not possible: a paragraph border
    sits at the paragraph's own indent, and the list bullets are indented.)
    Word reads a paragraph border's `w:left` as the PHYSICAL left even in a
    right-to-left paragraph (seen in real Word: the Arabic bars sat at the
    end of the line), so Arabic takes `w:right`, the start edge there."""
    edge = "right" if rtl else "left"
    for p in document.element.body.iter(qn("w:p")):
        rs = p.find(qn("w:r") + "/" + qn("w:rPr") + "/" + qn("w:rStyle"))
        if rs is None or rs.get(qn("w:val")) != "CVRole":
            continue
        group = [p]
        nxt = p.getnext()
        if nxt is not None and nxt.tag == qn("w:p"):
            ns = nxt.find(qn("w:r") + "/" + qn("w:rPr") + "/" + qn("w:rStyle"))
            if ns is not None and ns.get(qn("w:val")) == "CVAccentText":
                group.append(nxt)
        for q in group:
            bdr = OxmlElement("w:pBdr")
            bdr.append(_w(edge, val="single", sz=18, space=6, color=accent))
            _put(_ppr(q), bdr, PPR_ORDER)
            _put(_ppr(q), _w("ind", **{edge: 160}), PPR_ORDER)


GUTTER_W = 0.22       # the label column of modern-t19, of the text width
TEXT_W = 12240 - 2 * 720                  # the gutter master keeps 0.5in margins


def _apply_gutter(document) -> None:
    # the LAST table in the body: the header's stat chips (a table too) come
    # before it in modern-t19
    tbl = document.element.body.findall(qn("w:tbl"))[-1]
    label = round(TEXT_W * GUTTER_W)
    _grid(tbl, [label, TEXT_W - label])
    tbl_pr = tbl.find(qn("w:tblPr"))
    _put(tbl_pr, _w("tblW", w=TEXT_W, type="dxa"), TBLPR_ORDER)
    _put(tbl_pr, _w("tblLayout", type="fixed"), TBLPR_ORDER)
    for tr in _rows(tbl):
        tcs = _tcs(tr)
        if len(tcs) == 2:
            _width(tcs[0], label)
            _width(tcs[1], TEXT_W - label)


def _ppr(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        p.insert(0, ppr)
    return ppr


def _apply_styles(document, spec, lang, resolved, cell_zone: dict, bgs: dict, cell_of=None):
    """Fonts, colours and sizes of every cell's styles, heading fills/rules,
    the contact pill, the skill bars."""
    L = spec[lang]
    faces = resolved["faces"]
    colours = L["colours"]
    accent = resolved["accent"]
    items_by_cell = {"TopSide": [], "TopMain": [], "Side": [], "Main": []}
    for name, items in L["cells"].items():
        target = {"top_full": "TopSide", "top_side": "TopSide", "top_main": "TopMain",
                  "side": "Side", "main": "Main"}[name]
        items_by_cell[target] += items
    role_face = {"Name": "name", "Heading": "heading", "Text": "body", "Bold": "body_bold",
                 "Accent": "body", "Metric": "heading"}
    for cell, z in cell_zone.items():
        bg = bgs[z]
        zc = colours.get(z) or colours["main"]
        text = readable(zc.get("text") or "17181A", bg, 4.5)
        heading = readable(zc.get("heading") or zc.get("text"), bg)
        items = items_by_cell[cell]
        filled = next((i for i in items if i.get("fill")), None)
        head_color = readable(filled["hcolor"], filled["fill"]) if filled else heading
        name_color = readable(L["name"]["color"], bg) if any(i["k"] == "name" for i in items) \
            else heading
        acc = accent if contrast(accent, bg) >= 3.0 else readable(resolved["accent_text"], bg)
        colour = {"Name": name_color, "Heading": head_color, "Text": text, "Bold": text,
                  "Accent": acc, "Metric": heading}
        for role in ("Name", "Heading", "Text", "Bold", "Accent", "Metric"):
            sid = _sid(cell_style(cell, role))
            if sid is None:          # the main column's body text is Normal
                rpr = _style_rpr(document, "Normal")
                _set(rpr, "color", {"w:val": text})
                continue
            rpr = _style_rpr(document, sid)
            f = faces[role_face[role]]
            if cell != "Main" or role == "Metric":   # CV Metric: no step-5 theming
                _face(rpr, f["family"], f["weight"], colour[role])
            elif role in ("Name", "Heading"):
                _set(rpr, "color", {"w:val": colour[role]})
            if role == "Name":
                _size(rpr, L["name"]["pt"])
            if role == "Heading":
                _size(rpr, L["heading_pt"])
        if cell == "Main":
            # the job title keeps the role style; only its colour follows the page
            _set(_style_rpr(document, "CVRole"), "color", {"w:val": text})
        # the heading paragraph: a fill (ribbon / pill heading) and a rule
        ppr = _ppr_of_style(document, _sid(head_para_style(cell)))
        if filled:
            _put(ppr, _w("shd", val="clear", color="auto", fill=filled["fill"]), PPR_ORDER)
        elif any(i.get("rule") for i in items if i.get("label")):
            bdr = OxmlElement("w:pBdr")
            bdr.append(_w("bottom", val="single", sz=6, space=2, color=heading))
            _put(ppr, bdr, PPR_ORDER)
        # the contact line: its own pill where the template has one
        contact = next((i for i in items if i["k"] == "contact_line"), None)
        if contact:
            crpr = _style_rpr(document, _sid(ST_CONTACT))
            f = faces["body"]
            pill = contact.get("bg") and contact["bg"] != bg
            cbg = contact["bg"] if pill else bg
            _face(crpr, f["family"], f["weight"], readable(contact.get("color") if pill else text,
                                                           cbg, 4.5))
            if pill:
                _put(_ppr_of_style(document, _sid(PS_CONTACT)),
                     _w("shd", val="clear", color="auto", fill=cbg), PPR_ORDER)
    # skill bars: accent on the track of whatever cell they sit in
    if cell_of:
        for tc, name in cell_of.items():
            cell = {"top_side": "TopSide", "top_main": "TopMain", "side": "Side", "main": "Main"}[name]
            bg = bgs[cell_zone[cell]]
            text = readable((colours.get(cell_zone[cell]) or colours["main"]).get("text"), bg, 4.5)
            on = accent if contrast(accent, bg) >= 1.6 else text
            off = blend(bg, text, 0.22)
            _recolour_bars(tc, on, off)
    else:
        _recolour_bars(document.element.body, accent, "E4E4E4")


def _recolour_bars(root, on: str, off: str) -> None:
    """The skill bars' placeholder colours - fills and their seam borders."""
    for el in root.iter(qn("w:shd"), qn("w:left"), qn("w:right")):
        attr = qn("w:fill") if el.tag == qn("w:shd") else qn("w:color")
        val = (el.get(attr) or "").upper()
        if val == BAR_ON:
            el.set(attr, on)
        elif val == BAR_OFF:
            el.set(attr, off)
