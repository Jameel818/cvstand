"""modern-t9 — Boxed Sections: a white 26px page frame around an inset yellow
rail whose content is vertically centred - a two-line caps name, a tracked
caps title, then 2px-outlined boxes whose caps label row is ruled under
(Contact with labels, Skills, Awards, Tools, Languages). Main column: huge
caps display heads, the summary in a 1px box, a stat band between a 2px and a
1px rule, every job and school in its own 1px box with the dates at the end of
the first line, and a boxed TECHNICAL grid of rounded bars. From modern/t9.j2."""
from __future__ import annotations

from docx.oxml.ns import qn
from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, page_rects, pt, rated, run, skill_pct, tw,
)
from .common import SidebarPage, Stack, block, bullets, date_range, joined

YELLOW, INK, TRACK = "FFDE00", "000000", "E4E4E4"
PAD, SIDE_W = 26, 252


def _all(px):
    return {e: (px, INK) for e in ("top", "bottom", "start", "end")}


@design("modern-t9")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(PAD))
    sec.bottom_margin = Pt(pt(PAD + 26))
    page = SidebarPage(ctx, SIDE_W, side_fill=YELLOW, side_pad=(30, 20, 26, 20),
                       main_pad_x=(30, 12 + PAD), full_height_fill=False, ind_px=PAD)
    page_rects(ctx, [(PAD, SIDE_W, PAD, 1100 - 2 * PAD, YELLOW)])
    side = page.side
    W = SIDE_W - 40
    H = "role" if ctx.rtl else "heading"     # entry titles: bold body face in Arabic

    for k, part in enumerate(r["name"].split(" ", 1)):
        # the PDF's 40px name overruns the rail's padding too: give it the rail
        run(ctx, side.p(align="center", line=0.96, ind_start=-22, ind_end=-22), part, "name",
            size=40, color=INK, caps=True, spacing=-1)
    if r["title"]:
        run(ctx, side.p(align="center", before=8), r["title"], "bold", size=14, color=INK,
            caps=True, spacing=1.6)

    heads = []

    def rail_box(label, write):
        """A 2px-outlined box: the caps label row (4/10px padding) ruled 2px
        under it, then the body (6/10/8px padding)."""
        st = Stack(ctx, side, W)
        b = st.row()
        b.pad_top = 10                       # a spacer paragraph fit_side may shrink
        tbl = b.table([tw(W)], rows=2, borders={**{e: (2, INK) for e in
                                                  ("top", "bottom", "left", "right")},
                                               "insideH": (2, INK)})
        head, body = tbl.rows[0].cells[0], tbl.rows[1].cells[0]
        fmt_cell(ctx, head, pad=(0, 10, 0, 10))
        fmt_cell(ctx, body, pad=(0, 10, 0, 10))
        hb = Box(ctx, head, 0, pad_top=4, pad_bottom=4)
        run(ctx, hb.p(align="center"), label, "heading", size=15, color=INK, caps=True,
            spacing=1.4)
        hb.finish()
        bb = Box(ctx, body, 0, pad_top=6, pad_bottom=8)
        write(bb)
        bb.finish()
        st.done()
        heads.append(next(b.c._tc.iter(qn("w:p"))))

    def lines(items, line=1.5):
        def w(bb):
            for s in items:
                run(ctx, bb.p(align="center", line=line), s, "bold", size=13.9, color=INK)
        return w

    c = r["contact"]
    contact = [(t("Phone"), c["phone"]), (t("Email"), c["email"]), (t("Portfolio"), c["site"]),
               (t("Location"), c["address"])]
    contact += [(s.get("label") or "", s.get("url") or "") for s in c["social"]]
    contact = [x for x in contact if x[1]]
    if contact:
        def w_contact(bb):
            for i, (label, value) in enumerate(contact):
                if label:
                    run(ctx, bb.p(align="center", before=6 if i else 0, line=1.45), label,
                        "bold", size=13.9, color=INK)
                run(ctx, bb.p(align="center", line=1.45), value, "bold", size=13.9, color=INK)
        rail_box(t("Contact"), w_contact)
    if r["skills"]:
        rail_box(t("Skills"), lines([sk["name"] for sk in r["skills"]]))
    if r["recognition"]:
        def w_rec(bb):
            for i, rec in enumerate(r["recognition"]):
                run(ctx, bb.p(align="center", before=7 if i else 0, line=1.4), rec["title"],
                    "bold", size=13.9, color=INK)
                if rec["detail"]:
                    run(ctx, bb.p(align="center", line=1.4), rec["detail"], "bold", size=13.9,
                        color=INK)
        rail_box(t("Awards"), w_rec)
    if r["tools"]:
        rail_box(t("Tools"), lines([" · ".join(r["tools"])]))
    if r["languages"]:
        rail_box(t("Languages"), lines([joined([lg["name"], lg["level"]], " — ")
                                        for lg in r["languages"]]))
    page.center_side()            # justify-content:center in the PDF
    page.fit_side(heads)          # ... and a full rail gives up gaps, never spills

    # ---- main column
    T = page.main_text_px
    gap = [30]

    def row(**kw):
        box = page.main_row(pad_top=gap[0], **kw)
        gap[0] = 16
        return box

    def head(box, label, role="heading"):
        run(ctx, box.p(after=9, line=1.0), label, role, size=34, color=INK, caps=True,
            spacing=-0.8)

    if r["summary"]:
        box = row()
        head(box, t("Summary"))
        eb = block(ctx, box, T, border=_all(1), pad=(11, 14, 11, 14))
        run(ctx, eb.p(line=1.55), r["summary"], size=12.5, color=INK)
        eb.finish()

    if r["achievements"]:
        box = row()
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (2, INK), "bottom": (1, INK)})
        for k, (cell, a) in enumerate(zip(tbl.rows[0].cells, r["achievements"])):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 12 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0, pad_top=10, pad_bottom=10)
            run(ctx, cb.p(line=1.0), a["metric"], "metric", size=23, color=INK)
            run(ctx, cb.p(before=4), a["label"], "bold", size=8.5, color=INK, spacing=0.9,
                caps=True)
            cb.finish()

    inner_w = T - 28
    for j, job in enumerate(r["experience"]):
        box = row() if j == 0 else page.main_row(pad_top=10)
        if j == 0:
            head(box, t("Experience"))
        eb = block(ctx, box, T, border=_all(1), pad=(11, 14, 11, 14))
        p = eb.p(tabs=[(inner_w, "end", None)])
        run(ctx, p, job["company"] or job["role"], H, size=14.5, color=INK, caps=True,
            spacing=0.3)
        dates = date_range(job["start"], job["end"])
        if dates:
            run(ctx, p, "\t", size=11)
            run(ctx, p, dates, "bold", size=11, color=INK)
        sub = joined([job["role"], job["location"]], " · ") if job["company"] else job["location"]
        if sub:
            run(ctx, eb.p(before=1, after=5), sub, "bold", size=13, color=INK)
        bullets(ctx, eb, job["bullets"], size=12, color=INK, line=1.5)
        eb.finish()

    for j, ed in enumerate(r["education"]):
        box = row() if j == 0 else page.main_row(pad_top=9)
        if j == 0:
            head(box, t("Education"))
        eb = block(ctx, box, T, border=_all(1), pad=(9, 14, 9, 14))
        p = eb.p(tabs=[(inner_w, "end", None)])
        run(ctx, p, ed["degree"], H, size=13.5, color=INK)
        dates = date_range(ed["start"], ed["end"])
        if dates:
            run(ctx, p, "\t", size=11)
            run(ctx, p, dates, "bold", size=11, color=INK)
        for v in (ed["school"], f"{t('GPA')} {ed['gpa']}" if ed["gpa"] else ""):
            if v:
                run(ctx, eb.p(), v, size=12, color=INK)
        eb.finish()

    if r["skills"]:
        box = row()
        # "Technical" is not a .cv-section in the PDF (Arabic: the body face)
        head(box, t("Technical"), role=H)
        eb = block(ctx, box, T, border=_all(1), pad=(12, 14, 12, 14))
        col = (inner_w - 22) / 2
        skills = r["skills"]
        tbl = eb.table([tw(col + 22), tw(col)], rows=(len(skills) + 1) // 2)
        for i, sk in enumerate(skills):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 22 if i % 2 == 0 else 0))
            cb = Box(ctx, cell, 0, pad_top=9 if i >= 2 else 0)
            p = cb.p(tabs=[(col, "end", None)])
            run(ctx, p, sk["name"], size=11.5, color=INK)
            if rated(sk):
                pct, label = skill_pct(sk)
                run(ctx, p, "\t", size=10)
                run(ctx, p, label, "bold", size=10, color=INK)
                bar(ctx, cb, pct, col, on=INK, off=TRACK, height=7, before=4)
            cb.finish()
        if len(skills) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()
        eb.finish()
    page.finish()
