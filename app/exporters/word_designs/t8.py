"""modern-t8 — Interlocking Blocks: pale-blue strips across the top and bottom
of every page, a portrait block, a navy "About me" block with a short rule,
full-width pale-blue section bars, a navy header block (name light + heavy,
tracked title, rule, stats), skills with the level word under the name and the
dots right-aligned, labelled contact rows, entries as "Title (dates)" + one
paragraph, and the "ALSO" block. Measured from modern/t8.j2."""
from __future__ import annotations

from ..docx_design import (
    Box, Ctx, design, dots_shape, fmt_cell, fmt_p, page_rects, photo_run, pt, run, tw,
)
from .common import SidebarPage, Stack, date_range, joined

NAVY, PALE, PHOTO_BG = "003366", "DCE6F2", "DFE3E8"
INK, BODY, MUTED_DOT = "20242E", "3D4653", "8A97A8"
LEFT_PX = 392


def _bar(ctx: Ctx, box: Box, label: str, width_px: float, before: float):
    """The full-width pale-blue section bar (38px, text 20px in)."""
    tbl = box.table([tw(width_px)])
    cell = tbl.rows[0].cells[0]
    fmt_cell(ctx, cell, fill=PALE, pad=(0, 20, 0, 8), valign="center")
    tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
    from ..docx_design import _w
    tr_pr.append(_w("trHeight", val=tw(38), hRule="atLeast"))
    b = Box(ctx, cell, 0)
    run(ctx, b.p(), label, "heading", size=15, color=NAVY, spacing=4)
    b.finish()
    if before:
        # the space above the bar: an empty row would be a blank line, so the
        # bar's table gets a top margin through its cell spacing-free indent row
        _space_above(tbl, before)
    return tbl


def _space_above(tbl, px):
    from ..docx_design import _w
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    # a spacer row above the bar, exactly `px` tall, holding a tiny paragraph
    tr = OxmlElement("w:tr")
    tr_pr = OxmlElement("w:trPr")
    tr_pr.append(_w("cantSplit"))
    tr_pr.append(_w("trHeight", val=tw(px), hRule="atLeast"))
    tr.append(tr_pr)
    tc = OxmlElement("w:tc")
    tc_pr = OxmlElement("w:tcPr")
    first = tbl._tbl.find(qn("w:tr")).find(qn("w:tc")).find(qn("w:tcPr"))
    tc_pr.append(_w("tcW", w=first.find(qn("w:tcW")).get(qn("w:w")), type="dxa"))
    tc.append(tc_pr)
    p = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    ppr.append(_w("spacing", before=0, after=0, line=240, lineRule="auto"))
    rpr = OxmlElement("w:rPr")
    rpr.append(_w("sz", val=2))
    rpr.append(_w("szCs", val=2))
    ppr.append(rpr)
    p.append(ppr)
    tc.append(p)
    tr.append(tc)
    tbl._tbl.find(qn("w:tr")).addprevious(tr)


@design("modern-t8")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    from docx.shared import Pt
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(26))
    sec.bottom_margin = Pt(pt(26))
    # the pale-blue strips at the top and bottom of every page
    page_rects(ctx, [(0, 850, 0, 26, PALE), (0, 850, 1100 - 26, 26, PALE)])
    page = SidebarPage(ctx, LEFT_PX, side_fill=None, side_pad=(0, 0, 0, 0),
                       main_pad_x=(0, 0), full_height_fill=False)
    left = page.side
    L = LEFT_PX

    # ---- left column
    p = left.p()
    photo_run(ctx, p, size_px=L, height_px=238, shape="rect", placeholder=PHOTO_BG)
    if r["summary"]:
        tbl = left.table([tw(L)])
        cell = tbl.rows[0].cells[0]
        fmt_cell(ctx, cell, fill=NAVY, pad=(22, 28, 22, 28))
        b = Box(ctx, cell, 0)
        run(ctx, b.p(), t("ABOUT ME"), "heading", size=16, color="FFFFFF", spacing=5)
        rule = b.p(before=10, ind_end=L - 56 - 52, border={"bottom": (2, "FFFFFF", 0)})
        run(ctx, rule, "", size=2)
        from ..docx_design import tiny
        tiny(rule, before_px=10)        # tiny() rewrites the spacing: keep the 10px
        run(ctx, b.p(before=14, line=1.65), r["summary"], size=11, color="E2E8F0")
        b.finish()

    if r["skills"]:
        st = Stack(ctx, left, L)
        for i, sk in enumerate(r["skills"]):
            b = st.row()
            if i == 0:
                _bar(ctx, b, t("PERSONAL SKILLS"), L, 16)
            dots_w = 100
            tbl = b.table([tw(L - 28 - 20 - dots_w), tw(dots_w)])
            c0, c1 = tbl.rows[0].cells
            top = 16 if i == 0 else 11
            fmt_cell(ctx, c0, pad=(top, 28, 0, 0), valign="center")
            fmt_cell(ctx, c1, pad=(top, 0, 0, 20), valign="center")
            nb = Box(ctx, c0, 0)
            run(ctx, nb.p(), sk["name"], "bold", size=12, color=INK, spacing=0.5)
            if sk["level"]:
                run(ctx, nb.p(before=2), sk["level"], "bold", size=9.5, color=NAVY,
                    spacing=1, caps=True)
            nb.finish()
            db = Box(ctx, c1, 0)
            dp = db.p(align="end")
            if sk["level"]:
                dots_shape(ctx, dp, sk["dots"], sk["dot_total"], on=NAVY, off=MUTED_DOT, d=12,
                           gap=7, stroke=1.5)
            db.finish()
        st.done()

    c = r["contact"]
    rows = [(t("EMAIL"), c["email"]), (t("PHONE"), c["phone"]), (t("ADDRESS"), c["address"]),
            (t("WEBSITE"), c["site"])]
    rows += [((s.get("label") or "").upper(), s.get("url") or "") for s in c["social"]]
    rows = [x for x in rows if x[1]]
    if rows:
        st = Stack(ctx, left, L)
        for i, (label, value) in enumerate(rows):
            b = st.row()
            if i == 0:
                _bar(ctx, b, t("CONTACT"), L, 16)
            tbl = b.table([tw(28 + 60 + 12), tw(L - 28 - 60 - 12 - 20)])
            c0, c1 = tbl.rows[0].cells
            top = 14 if i == 0 else 8
            fmt_cell(ctx, c0, pad=(top, 28, 0, 12))
            fmt_cell(ctx, c1, pad=(top, 0, 0, 20))
            run(ctx, Box(ctx, c0, 0).p(), label, "bold", size=9, color=NAVY, spacing=1.2)
            run(ctx, Box(ctx, c1, 0).p(), value, size=11.5, color=INK)
        st.done()

    # ---- right column
    R = page.main_px
    head = page.main_row(fill=NAVY, pad_top=34, pad_bottom=26, pad_x=(36, 36))
    p = head.p(align="center", line=1.1)
    parts = r["name"].split(" ", 1)
    # the template's name face is the LIGHT one (cv-name is on the first
    # word); the surname is Archivo 900 - the heading face
    run(ctx, p, parts[0], "name", size=38, color="FFFFFF", spacing=3)
    if len(parts) > 1:
        run(ctx, p, " ", "name", size=38)
        run(ctx, p, parts[1], "heading", size=38, color="FFFFFF", spacing=3)
    if r["title"]:
        run(ctx, head.p(align="center", before=14), r["title"], "bold", size=12.5,
            color="FFFFFF", spacing=4, caps=True)
    rule = head.p(before=13, border={"bottom": (2, "FFFFFF", 0)})
    from ..docx_design import tiny
    tiny(rule, before_px=13)            # tiny() rewrites the spacing: keep the 13px
    if r["achievements"]:
        n = len(r["achievements"])
        each = tw(R - 72) // n
        tbl = head.table([each] * n, borders={"bottom": (1, PALE)})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(26, 4, 4, 4))
            cb = Box(ctx, cell, 0)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=21,
                color="FFFFFF")
            run(ctx, cb.p(align="center", before=4), a["label"], "bold", size=8.5, color=PALE,
                spacing=0.8, caps=True)
            cb.finish()

    def entry(box, title, dates, text, top):
        p = box.p(before=top, ind_start=20, ind_end=30)
        run(ctx, p, title, "heading", size=13.5, color=NAVY, spacing=0.3)
        if dates:
            run(ctx, p, f" ({dates})", "heading", size=13.5, color=NAVY, spacing=0.3)
        if text:
            run(ctx, box.p(before=4, ind_start=20, ind_end=30, line=1.55), text, size=11,
                color=BODY)

    if r["education"]:
        for i, ed in enumerate(r["education"]):
            box = page.main_row()
            if i == 0:
                _bar(ctx, box, t("EDUCATION"), R, 12)
            gpa = f"{t('GPA')} {ed['gpa']}" if ed["gpa"] else ""
            text = joined([ed["school"], gpa], " · ")
            if ed["bullets"]:
                text = (text + ". " if text else "") + " ".join(ed["bullets"])
            entry(box, ed["degree"], date_range(ed["start"], ed["end"]), text,
                  14 if i == 0 else 12)
    if r["experience"]:
        for i, job in enumerate(r["experience"]):
            box = page.main_row()
            if i == 0:
                _bar(ctx, box, t("WORK EXPERIENCE"), R, 14)
            where = joined([job["company"], job["location"]], ", ")
            text = where
            if job["bullets"]:
                text = (where + ". " if where else "") + " ".join(job["bullets"])
            entry(box, job["role"], date_range(job["start"], job["end"]), text,
                  14 if i == 0 else 12)
    also = []
    if r["recognition"]:
        also.append((t("Recognition"), "; ".join(
            rec["title"] + (f" ({rec['detail']})" if rec["detail"] else "")
            for rec in r["recognition"])))
    if r["tools"]:
        also.append((t("Tools"), " · ".join(r["tools"])))
    if r["languages"]:
        also.append((t("Languages"), ", ".join(
            lg["name"] + (f" ({lg['level']})" if lg["level"] else "") for lg in r["languages"])))
    if also:
        box = page.main_row()
        _bar(ctx, box, t("ALSO"), R, 14)
        for i, (label, text) in enumerate(also):
            p = box.p(before=14 if i == 0 else 6, ind_start=20, ind_end=30, line=1.55)
            run(ctx, p, label, "heading", size=11, color=NAVY)
            run(ctx, p, " — " + text, size=11, color=BODY)
    page.finish()
