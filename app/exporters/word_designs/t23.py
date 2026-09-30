"""modern-t23 — Grey rail with a black seam: a 2px black line down the
column seam carrying three black dots, a two-line caps name, heavy caps
headings, stacked black bars with the percent, the title in a black pill at
the end of the main column, stats between rules. From modern/t23.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, page_ovals, page_rects, pt, rated, run, skill_pct, tw,
)
from .common import SidebarPage, Stack, block, bullets, joined

GREY, INK, BODY, MUTED, TRACK, RULE = "EFEFEF", "151517", "3C3C40", "6B6B70", "DCDCDC", "DEDEDE"
SIDE_PX = 330


def _head(ctx, box, label, after):
    run(ctx, box.p(after=after), label, "heading", size=22, color=INK, spacing=1, caps=True)


@design("modern-t23")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(34))
    page = SidebarPage(ctx, SIDE_PX, side_fill=GREY, side_pad=(56, 30, 34, 24),
                       main_pad_x=(46, 44), full_height_fill=False)
    # the grey rail, the black seam and its three dots, on every page
    page_rects(ctx, [(0, SIDE_PX + 1, 0, 1100, GREY), (SIDE_PX, 2, 0, 1100, INK)])
    page_ovals(ctx, [(SIDE_PX + 1, y, 24, INK) for y in (220, 520, 820)])
    side = page.side
    W = SIDE_PX - 54
    for part in r["name"].split(" ", 1):
        run(ctx, side.p(line=1.02), part, "name", size=40, color=INK, caps=True, spacing=-0.5)

    def section(label, items, write, after):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row(pad_top=28 if i == 0 else 0)
            if i == 0:
                _head(ctx, b, label, after)
            write(b, i, it)
        st.done()

    def lines(b, i, s):
        run(ctx, b.p(line=1.85), s, size=12, color=BODY)

    def summary(b, i, s):
        run(ctx, b.p(line=1.65), s, size=12, color=BODY)

    def skill(b, i, sk):
        p = b.p(before=10 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, sk["name"], "bold", size=11.5, color=INK)
        if rated(sk):
            pct, label = skill_pct(sk)
            run(ctx, p, "\t", size=10.5)
            run(ctx, p, label, size=10.5, color=MUTED)
            b.pad_top = 5
            bar(ctx, b, pct, W, on=INK, off=TRACK, height=7)

    def education(b, i, ed):
        run(ctx, b.p(before=8 if i else 0, line=1.6), ed["degree"], "bold", size=12, color=INK)
        run(ctx, b.p(line=1.6), joined([ed["school"], ed["end"]], " · "), size=12,
            color=BODY)

    c = r["contact"]
    section(t("Contact"), [x for x in (c["email"], c["site"], c["phone"], c["address"]) if x],
            lines, 10)
    section(t("Summary"), [r["summary"]] if r["summary"] else [], summary, 10)
    section(t("Skills"), r["skills"], skill, 12)
    section(t("Education"), r["education"], education, 8)

    # ---- main column
    T = page.main_text_px
    if r["title"]:
        box = page.main_row(pad_top=46)
        w = min(T, len(r["title"]) * 13.5 + 60 + len(r["title"]) * 1.5)
        tbl = box.table([tw(w)], ind=tw(T - w))
        cell = tbl.rows[0].cells[0]
        fmt_cell(ctx, cell, fill=INK, pad=(0, 30, 0, 30), valign="center")
        cb = Box(ctx, cell, 0, pad_top=11, pad_bottom=11)
        run(ctx, cb.p(align="center"), r["title"], "name", size=18, color="FFFFFF",
            spacing=1.5, caps=True)
        cb.finish()
    if r["achievements"]:
        box = page.main_row(pad_top=24 if r["title"] else 46)
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 12))
            cb = Box(ctx, cell, 0, pad_top=12, pad_bottom=12)
            run(ctx, cb.p(), a["metric"], "metric", size=25, color=INK)
            run(ctx, cb.p(before=4), a["label"], "bold", size=9, color=MUTED, spacing=1,
                caps=True)
            cb.finish()
    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=24 if j == 0 else 18)
        if j == 0:
            _head(ctx, box, t("Work Experience"), 14)
        run(ctx, box.p(), job["role"], "bold", size=14, color=INK)
        dates = joined([job["start"], job["end"]], " – ")
        meta = joined([job["company"], job["location"], dates], " · ")
        if meta:
            run(ctx, box.p(before=2, after=7), meta, size=11.5, color=MUTED)
        bullets(ctx, box, job["bullets"], size=12, color=BODY, line=1.6)
    page.finish()
