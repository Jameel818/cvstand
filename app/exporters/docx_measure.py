"""Estimate how tall Word will draw a piece of a designed document.

Word has no flexbox. Where a template's column is `justify-content:
space-between` (or pushes a block down with `margin-top:auto`), the PDF spreads
the sections down the whole page and Word, stacking from the top, packed them
high (docs/WORD_FIDELITY_AUDIT.md, item 1b). A design can instead measure what
it wrote, work out the slack on the page and hand it out as paragraph spacing
- still ordinary editable spacing, no fixed heights.

The estimate reads the finished XML: paragraph spacing, the face each run
draws (the role style's face from the resolved theme, or a run's own font),
its size, letter spacing and caps, greedy word-wrap on the font's advance
widths, inline pictures, tables (fixed widths, cell margins, "at least" row
heights). Word's single line, measured in Word on this PC for every built face
(2026-10-01): the face's typo line (ascender - descender + line gap) when the
font sets USE_TYPO_METRICS, else its win line (winAscent + winDescent).
It is an estimate: callers keep a reserve so a column never spills a page.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

from docx.oxml.ns import qn
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"

_STYLE_FACE = {"CVName": "name", "CVHeading": "heading", "CVRole": "role",
               "CVBodyBold": "body_bold", "CVMetric": "heading", "CVAccentText": "body"}
_ARIAL = {"line": 1.149, "avg": 0.55, "widths": {}}


@lru_cache(maxsize=None)
def _font(ttf_rel: str):
    from fontTools.ttLib import TTFont

    from ..typography.faces import FONT_DIR
    f = TTFont(FONT_DIR / ttf_rel, lazy=True)
    upm = f["head"].unitsPerEm
    os2, hhea = f["OS/2"], f["hhea"]
    if os2.fsSelection & 128:      # USE_TYPO_METRICS
        line = (os2.sTypoAscender - os2.sTypoDescender + os2.sTypoLineGap) / upm
    else:
        line = (os2.usWinAscent + os2.usWinDescent) / upm
    cmap = f.getBestCmap() or {}
    hmtx = f["hmtx"].metrics
    widths = {cp: hmtx[g][0] / upm for cp, g in cmap.items() if g in hmtx}
    avg = widths.get(ord("n"), 0.5)
    del hhea
    return {"line": line, "widths": widths, "avg": avg}


@lru_cache(maxsize=None)
def _face_file(family: str, weight: int) -> str | None:
    from ..typography import face
    f = face(family, weight)
    return f["ttf"] if f else None


def _lift(rpr) -> float:
    if rpr is None:
        return 0.0
    el = rpr.find(qn("w:position"))
    return int(el.get(qn("w:val"))) / 2 if el is not None else 0.0


def _empty_tiny(p) -> bool:
    if any((t.text or "").strip() for t in p.iter(qn("w:t"))):
        return False
    ppr = p.find(qn("w:pPr"))
    rpr = ppr.find(qn("w:rPr")) if ppr is not None else None
    sz = rpr.find(qn("w:sz")) if rpr is not None else None
    return sz is not None and int(sz.get(qn("w:val"))) <= 4


@lru_cache(maxsize=1)
def _joined_forms() -> dict[int, int]:
    """Arabic letter -> its joined (medial, else final) presentation form:
    joined Arabic is narrower than its isolated letters, so widths are read
    from the forms the text actually shows mid-word."""
    import unicodedata
    out: dict[int, int] = {}
    for cp in range(0xFE70, 0xFEFF):
        name = unicodedata.name(chr(cp), "")
        for form in (" MEDIAL FORM", " FINAL FORM"):
            if name.endswith(form):
                try:
                    base = ord(unicodedata.lookup(name[: -len(form)]))
                except KeyError:
                    continue
                if form == " MEDIAL FORM" or base not in out:
                    out[base] = cp
    return out


def _w(m, ch: str) -> float:
    cp = ord(ch)
    jf = _joined_forms().get(cp)
    if jf is not None and jf in m["widths"]:
        return m["widths"][jf]
    return m["widths"].get(cp, m["avg"])


class Measure:
    """Height estimates (pt) for elements of a document built with `resolved`."""

    def __init__(self, resolved: dict, base_size_pt: float = 10.0):
        self.faces = resolved["faces"]
        self.base = base_size_pt

    # ---- fonts
    def _metrics(self, rpr):
        role = "body"
        if rpr is not None:
            st = rpr.find(qn("w:rStyle"))
            if st is not None:
                role = _STYLE_FACE.get(st.get(qn("w:val")), "body")
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is not None and (fonts.get(qn("w:ascii")) or "").lower() == "arial":
                return _ARIAL
            b = rpr.find(qn("w:b"))
            if role == "body" and b is not None and b.get(qn("w:val"), "1") not in ("0", "false"):
                role = "body_bold"
        f = self.faces[role]
        rel = _face_file(f["family"], f["weight"])
        return _font(rel) if rel else _ARIAL

    def _size(self, rpr) -> float:
        if rpr is not None:
            sz = rpr.find(qn("w:sz"))
            if sz is not None:
                return int(sz.get(qn("w:val"))) / 2
        return self.base

    # ---- paragraphs
    def paragraph(self, p, width_pt: float) -> float:
        ppr = p.find(qn("w:pPr"))
        before = after = 0.0
        mult, exact = 1.0, None
        ind = 0.0
        if ppr is not None:
            sp = ppr.find(qn("w:spacing"))
            if sp is not None:
                before = int(sp.get(qn("w:before"), 0)) / 20
                after = int(sp.get(qn("w:after"), 0)) / 20
                line = sp.get(qn("w:line"))
                rule = sp.get(qn("w:lineRule"), "auto")
                if line is not None:
                    if rule == "auto":
                        mult = int(line) / 240
                    else:
                        exact = (rule, int(line) / 20)
            el = ppr.find(qn("w:ind"))
            if el is not None:
                ind = (int(el.get(qn("w:left"), 0)) + int(el.get(qn("w:right"), 0))) / 20
            bdr = ppr.find(qn("w:pBdr"))
            if bdr is not None:
                for e in ("top", "bottom"):
                    b = bdr.find(qn(f"w:{e}"))
                    if b is not None:
                        before += int(b.get(qn("w:space"), 0)) + int(b.get(qn("w:sz"), 0)) / 8
        avail = max(10.0, width_pt - ind)
        lines = [[0.0, 0.0]]          # per line: [width used, line height]
        pending_space = 0.0
        max_h_para = 0.0

        def line_h(m, size):
            return size * m["line"]

        runs = list(p.iter(qn("w:r")))
        for r in runs:
            rpr = r.find(qn("w:rPr"))
            m = self._metrics(rpr)
            size = self._size(rpr)
            caps = rpr is not None and rpr.find(qn("w:caps")) is not None
            track = 0.0
            if rpr is not None:
                s = rpr.find(qn("w:spacing"))
                if s is not None:
                    track = int(s.get(qn("w:val"))) / 20
            h = line_h(m, size)
            for child in r:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "br":
                    lines.append([0.0, h])
                    pending_space = 0.0
                elif tag == "drawing":
                    ext = child.find(".//" + qn("wp:extent"))
                    if ext is not None:
                        ph = int(ext.get("cy")) / 12700
                        lines[-1][1] = max(lines[-1][1], ph / max(mult, 1e-6))
                        lines[-1][0] += int(ext.get("cx")) / 12700
                elif tag in ("pict", "AlternateContent"):
                    # an INLINE VML shape (a bar) takes its height; an
                    # absolutely positioned one (a node, a page fill) none.
                    # Since run 6 every design shape is DrawingML with this
                    # VML as its mc:Fallback (docx_dml): measured from the
                    # fallback, so the estimate is exactly what it was.
                    if tag == "AlternateContent":
                        child = child.find(f"{{{_MC}}}Fallback/{qn('w:pict')}")
                        if child is None:
                            continue
                    shape = next(iter(child), None)
                    style = shape.get("style", "") if shape is not None else ""
                    if "position:absolute" not in style:
                        hm = re.search(r"height:([\d.]+)pt", style)
                        if hm:
                            ph = float(hm.group(1)) + _lift(rpr)
                            lines[-1][1] = max(lines[-1][1], ph / max(mult, 1e-6))
                elif tag == "tab":
                    lines[-1][0] += 6
                    lines[-1][1] = max(lines[-1][1], h)
                elif tag == "t":
                    text = child.text or ""
                    if caps:
                        text = text.upper()
                    words = text.split(" ")
                    for k, word in enumerate(words):
                        if k > 0:
                            pending_space += (m["widths"].get(32, 0.25) * size) + track
                        if not word:
                            continue
                        w = sum(_w(m, ch) for ch in word) * size \
                            + track * len(word)
                        cur = lines[-1]
                        if cur[0] > 0 and cur[0] + pending_space + w > avail:
                            lines.append([w, h])
                        else:
                            cur[0] += pending_space + w
                            cur[1] = max(cur[1], h)
                        # a single word wider than the line (an e-mail, a URL):
                        # Word breaks it between characters onto more lines
                        while lines[-1][0] > avail:
                            rest = lines[-1][0] - avail
                            lines[-1][0] = avail
                            lines.append([rest, h])
                        pending_space = 0.0
            max_h_para = max(max_h_para, h)
        if not runs:
            rpr = ppr.find(qn("w:rPr")) if ppr is not None else None
            max_h_para = line_h(self._metrics(None), self._size(rpr))
        total = 0.0
        for _, h in lines:
            h = h or max_h_para
            if exact is not None:
                rule, v = exact
                h = v if rule == "exact" else max(v, h)
            else:
                h *= mult
            total += h
        return before + total + after

    # ---- containers
    def block(self, container, width_pt: float) -> float:
        """A cell (w:tc) or the body: its paragraphs and tables, in order."""
        h = 0.0
        kids = [c for c in container if c.tag.rsplit("}", 1)[-1] in ("p", "tbl")]
        for i, child in enumerate(kids):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                if (i == len(kids) - 1 and i > 0 and kids[i - 1].tag == qn("w:tbl")
                        and container.tag == qn("w:tc") and _empty_tiny(child)):
                    # the cell-end paragraph after a nested table: Word draws
                    # it with no height (measured, modern-t2 skill rows)
                    continue
                h += self.paragraph(child, width_pt)
            elif tag == "tbl":
                h += self.table(child)
        return h

    def table(self, tbl) -> float:
        pr = tbl.find(qn("w:tblPr"))
        dl = dr = dt = db = 0.0
        if pr is not None:
            mar = pr.find(qn("w:tblCellMar"))
            if mar is not None:
                dl, dr, dt, db = (self._mar(mar, e) for e in ("left", "right", "top", "bottom"))
        total = 0.0
        # the table's own horizontal rules take room too (t9's 2px boxes)
        rows = tbl.findall(qn("w:tr"))
        if pr is not None:
            bd = pr.find(qn("w:tblBorders"))
            if bd is not None:
                for edge, n in (("top", 1), ("bottom", 1), ("insideH", max(0, len(rows) - 1))):
                    e = bd.find(qn(f"w:{edge}"))
                    if e is not None and e.get(qn("w:val")) not in ("nil", "none"):
                        total += n * int(e.get(qn("w:sz"), 0)) / 8
        # a vertically merged cell (vMerge restart ... continue) spans its
        # rows: its height is shared by them, not added to its first row (a
        # header whose photo spans three rows, modern-t14, read ~170pt tall)
        heights: list[float] = []
        spans: list[tuple[int, int, float]] = []       # (first row, grid col, height)
        for ri, tr in enumerate(rows):
            row_h = 0.0
            trpr = tr.find(qn("w:trPr"))
            at_least = 0.0
            if trpr is not None:
                th = trpr.find(qn("w:trHeight"))
                if th is not None:
                    at_least = int(th.get(qn("w:val"))) / 20
            col = 0
            for tc in tr.findall(qn("w:tc")):
                tcpr = tc.find(qn("w:tcPr"))
                w = 0.0
                l, r_, t, b = dl, dr, dt, db
                gcol = col
                gs = tcpr.find(qn("w:gridSpan")) if tcpr is not None else None
                col += int(gs.get(qn("w:val"))) if gs is not None else 1
                restart = False
                if tcpr is not None:
                    vm = tcpr.find(qn("w:vMerge"))
                    if vm is not None and vm.get(qn("w:val")) != "restart":
                        continue
                    restart = vm is not None
                    tw_ = tcpr.find(qn("w:tcW"))
                    if tw_ is not None:
                        w = int(tw_.get(qn("w:w"))) / 20
                    mar = tcpr.find(qn("w:tcMar"))
                    if mar is not None:
                        l, r_, t, b = (self._mar(mar, e, d) for e, d in
                                       (("left", dl), ("right", dr), ("top", dt), ("bottom", db)))
                ch = t + self.block(tc, max(1.0, w - l - r_)) + b
                if restart:
                    spans.append((ri, gcol, ch))
                    continue
                row_h = max(row_h, ch)
            heights.append(max(row_h, at_least))
        for first, gcol, ch in spans:
            last = first
            while last + 1 < len(rows) and self._continues(rows[last + 1], gcol):
                last += 1
            short = ch - sum(heights[first:last + 1])
            if short > 0:
                heights[last] += short
        return total + sum(heights)

    @staticmethod
    def _continues(tr, gcol: int) -> bool:
        """Is the cell at grid column `gcol` of `tr` a vMerge continuation?"""
        col = 0
        for tc in tr.findall(qn("w:tc")):
            if col == gcol:
                vm = tc.find(qn("w:tcPr") + "/" + qn("w:vMerge"))
                return vm is not None and vm.get(qn("w:val")) != "restart"
            gs = tc.find(qn("w:tcPr") + "/" + qn("w:gridSpan"))
            col += int(gs.get(qn("w:val"))) if gs is not None else 1
        return False

    @staticmethod
    def _mar(mar, edge, default=0.0) -> float:
        el = mar.find(qn(f"w:{edge}"))
        return int(el.get(qn("w:w"))) / 20 if el is not None else default


def bump_before(p, extra_pt: float) -> None:
    """Add `extra_pt` to a paragraph's space-before (the slack a flex column
    hands out between its sections)."""
    from .docx_layout import PPR_ORDER, _put, _w
    ppr = p.find(qn("w:pPr"))
    sp = ppr.find(qn("w:spacing")) if ppr is not None else None
    if sp is None:
        from .docx_design import _ppr
        ppr = _ppr(p)
        sp = _w("spacing", before=0, after=0)
        _put(ppr, sp, PPR_ORDER)
    sp.set(qn("w:before"), str(int(sp.get(qn("w:before"), 0)) + max(0, int(math.floor(extra_pt * 20)))))


def spread(measure: Measure, container, width_pt: float, heads, avail_pt: float,
           reserve_pt: float = 8.0, *, grow: bool = True, shrink: bool = True) -> float:
    """`justify-content: space-between` for a column already written: the
    slack (`avail_pt` - what the column holds - a reserve) is shared equally
    as space before each of `heads` (the first paragraph of every block after
    the first). With `shrink`, a column too tall for the page instead gives
    up the space before those heads (never below 0, never the text), so it
    does not spill one line onto a new page. Returns the change per head."""
    heads = [h for h in heads if h is not None]
    if not heads:
        return 0.0
    slack = avail_pt - reserve_pt - measure.block(container, width_pt)
    if slack > 0 and grow:
        each = slack / len(heads)
        for p in heads:
            bump_before(p, each)
        return each
    if slack < 0 and shrink:
        have = [_before(p) for p in heads]
        total = sum(have)
        if total <= 0:
            return 0.0
        k = max(0.0, 1 - (-slack) / total)
        for p, b in zip(heads, have):
            _set_before(p, b * k)
        return -(-slack) / len(heads)
    return 0.0


def _before(p) -> float:
    ppr = p.find(qn("w:pPr"))
    sp = ppr.find(qn("w:spacing")) if ppr is not None else None
    return int(sp.get(qn("w:before"), 0)) / 20 if sp is not None else 0.0


def _set_before(p, v_pt: float) -> None:
    ppr = p.find(qn("w:pPr"))
    sp = ppr.find(qn("w:spacing")) if ppr is not None else None
    if sp is not None:
        sp.set(qn("w:before"), str(max(0, int(round(v_pt * 20)))))
