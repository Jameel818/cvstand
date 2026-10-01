"""modern-t17 — Lavender Rail: a 360px lavender rail headed by a navy block
(caps name, title, summary), navy ribbons running in from the page edge
(Contact, Languages, Tools, Certifications); the main column opens with a
190px photo block across its top, then centred navy stats between rules,
ruled Montserrat heads, entries marked with a navy dot (title, dates at the
line end, school/company, one paragraph), and a 4-up grid of skill RINGS.
From modern/t17.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, fmt_cell, fmt_p, photo_run, pt, rated, ring_anchored, run, skill_pct,
    tiny, tw, vml_oval,
)
from .common import SidebarPage, Stack, block, date_range, joined, single_px

NAVY, LAV, TRACK, INK, RULE = "003366", "E5E8F5", "DCE6F5", "111111", "CCCCCC"
SIDE_PX = 360


@design("modern-t17")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(24))
    page = SidebarPage(ctx, SIDE_PX, side_fill=LAV, side_pad=(0, 0, 24, 0),
                       main_pad_x=(36, 36))
    side = page.side
    W = SIDE_PX - 68

    # the navy head block, full rail width
    hb = block(ctx, side, SIDE_PX, fill=NAVY, pad=(40, 34, 26, 34))
    # Word sets the 900 caps a hair wider: the name may use the block's padding
    run(ctx, hb.p(line=1.0, ind_end=-30), r["name"], "name", size=44, color="FFFFFF", caps=True,
        spacing=2)
    if r["title"]:
        run(ctx, hb.p(before=8), r["title"], size=17, color="CCD6E0")
    if r["summary"]:
        run(ctx, hb.p(before=16, line=1.6), r["summary"], size=12, color="F4F6F9")
    hb.finish()

    first = [True]

    def ribbon_section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, SIDE_PX)
        for i, it in enumerate(items):
            b = st.row()
            if i == 0:
                b.pad_top = 28 if first[0] else 18
                first[0] = False
                # from the page edge to the content's end: 360 - 34 px
                rb = block(ctx, b, SIDE_PX - 34, fill=NAVY, pad=(9, 20, 9, 20))
                run(ctx, rb.p(), label, "heading", size=19, color="FFFFFF")
                rb.finish()
                b.pad_top = 16
            write(b, i, it)
        st.done()

    def line(gap):
        def w(b, i, s):
            run(ctx, b.p(before=gap if i else 0, ind_start=34, ind_end=34), s, size=12.5,
                color=INK)
        return w

    c = r["contact"]
    contact = [x for x in (c["phone"], c["email"], c["address"], c["site"]) if x]
    contact += [s.get("label") for s in c["social"] if s.get("label")]
    ribbon_section(t("CONTACT"), contact, line(9))
    ribbon_section(t("LANGUAGES"), [joined([x["name"], x["level"]], " — ")
                                    for x in r["languages"]], line(6))
    if r["tools"]:
        ribbon_section(t("TOOLS"), [" · ".join(r["tools"])],
                       lambda b, i, s: run(ctx, b.p(line=1.6, ind_start=34, ind_end=34), s,
                                           size=12.5, color=INK))

    def cert(b, i, rec):
        run(ctx, b.p(before=8 if i else 0, ind_start=34, ind_end=34), rec["title"], "bold",
            size=12.5, color=INK)
        if rec["detail"]:
            run(ctx, b.p(ind_start=34, ind_end=34), rec["detail"], size=12.5, color=INK)
    ribbon_section(t("CERTIFICATIONS"), r["recognition"], cert)

    # ---- main column: the photo block across the top
    T = page.main_text_px
    top = page.main_row(pad_x=(0, 0))
    photo_run(ctx, top.p(line=1.0), size_px=850 - SIDE_PX, height_px=190, shape="rect",
              placeholder=LAV)
    H = "role" if ctx.rtl else "body"

    gap = [15]

    def row():
        box = page.main_row(pad_top=gap[0])
        gap[0] = 10
        return box

    if r["achievements"]:
        box = row()
        ach = [a for a in r["achievements"] if a["metric"]]
        n = max(1, len(ach))
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, ach):
            fmt_cell(ctx, cell, pad=(0, 6, 0, 6))
            cb = Box(ctx, cell, 0, pad_top=8, pad_bottom=8)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=25, color=NAVY)
            run(ctx, cb.p(align="center", before=5), a["label"], "bold", size=9,
                color="555555", spacing=1, caps=True)
            cb.finish()

    def bhead(box, label, after):
        run(ctx, box.p(after=8), label, "heading", size=22, color=INK)
        rule = box.p(after=after)
        tiny(rule)
        fmt_p(ctx, rule, after=after, border={"bottom": (1, RULE, 0)})

    node = [0]

    def entry(box, title, dates, sub, text):
        tbl = box.table([tw(28), tw(T - 28)])
        a, b = tbl.rows[0].cells
        node[0] += 1
        ap = a.paragraphs[0]
        vml_oval(ctx, ap, x_pt=0 if not ctx.rtl else pt(28 - 12), y_pt=pt(4), d_pt=pt(12),
                 fill=NAVY, stroke=None, n=300 + node[0])
        Box(ctx, a, 0).finish()
        bb = Box(ctx, b, 0)
        p = bb.p(tabs=[(T - 28, "end", None)])
        run(ctx, p, title, H, size=15, color=INK)
        if dates:
            # the PDF's entry block shrink-wraps: with a text paragraph it is the
            # column's width (dates at the end), without one the dates follow
            # the title 12px on
            run(ctx, p, "\t" if text else "   ", size=12.5)
            run(ctx, p, dates, size=12.5, color="777777")
        if sub:
            run(ctx, bb.p(before=2, after=5), sub, size=12.5, color="555555")
        if text:
            run(ctx, bb.p(line=1.55), text, size=12, color="444444")
        bb.finish()

    for j, ed in enumerate(r["education"]):
        box = row() if j == 0 else page.main_row(pad_top=10)
        if j == 0:
            bhead(box, t("Education"), 10)
        entry(box, ed["degree"], date_range(ed["start"], ed["end"]), ed["school"],
              " ".join(ed["bullets"]))
    for j, job in enumerate(r["experience"]):
        box = row() if j == 0 else page.main_row(pad_top=10)
        if j == 0:
            bhead(box, t("Experience"), 10)
        entry(box, job["role"], date_range(job["start"], job["end"]),
              joined([job["company"], job["location"]], " · "), " ".join(job["bullets"]))

    if r["skills"]:
        skills = r["skills"]
        col = (T - 36) / 4
        for rr in range((len(skills) + 3) // 4):
            box = row() if rr == 0 else page.main_row(pad_top=12)
            if rr == 0:
                bhead(box, t("Skills"), 12)
            tbl = box.table([tw(col + 12)] * 3 + [tw(col)])
            for k in range(4):
                cell = tbl.rows[0].cells[k]
                fmt_cell(ctx, cell, pad=(0, 0, 0, 12 if k < 3 else 0))
                cb = Box(ctx, cell, 0)
                i = rr * 4 + k
                if i < len(skills):
                    sk = skills[i]
                    if rated(sk):
                        pct, _ = skill_pct(sk)
                        line = single_px(ctx, "bold", 11)
                        pad = (54 - line) / 2
                        p = cb.p(align="center", before=pad, after=pad + 7)
                        run(ctx, p, f"{round(pct)}%", "bold", size=11, color=INK)
                        ring_anchored(p, x_pt=pt((col - 54) / 2), y_pt=0, d_px=54,
                                      width_px=7.5, pct=pct, on=NAVY, off=TRACK)
                    run(ctx, cb.p(align="center", ind_start=-6, ind_end=-6), sk["name"],
                        size=12, color="333333")
                    if sk["level"]:
                        run(ctx, cb.p(align="center"), sk["level"], size=10, color="5F6B7A")
                cb.finish()
    page.finish()
