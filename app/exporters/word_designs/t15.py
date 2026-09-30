"""modern-t15 — Forest & amber: a deep-green column, an amber band across the
page from 74px down, a big cream circle portrait overlapping both, a caps name
on the band; amber side headings, bars with the percent, inline languages;
green main headings, italic amber dates right, italic company lines, stats
between rules. From modern/t15.j2 (absolutely positioned there)."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, page_rects, photo_run, pt, rated, run, skill_pct, tw,
)
from .common import SidebarPage, Stack, bullets, date_range, joined

GREEN, AMBER, OLIVE, BROWN, TRACK = "1A3F22", "D99201", "58761B", "905A01", "5F7D55"
SIDE_PX = 340


@design("modern-t15")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(30))
    page = SidebarPage(ctx, SIDE_PX, side_fill=GREEN, side_pad=(40, 30, 30, 30),
                       main_pad_x=(38, 40), full_height_fill=False)
    # the green column on every page; the amber band across page 1 (in front)
    page_rects(ctx, [(0, SIDE_PX + 1, 0, 1100, GREEN)], [(0, 850, 74, 186, AMBER)])
    side = page.side
    W = SIDE_PX - 60
    p = side.p(align="start")
    photo_run(ctx, p, size_px=200 if ctx.rtl else 268, placeholder="E8DCC0")

    def section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row(pad_top=(28 if label == first[0] else 13) if i == 0 else 0)
            if i == 0:
                run(ctx, b.p(after=8, line=1.25), label, "heading", size=19, color=AMBER,
                    spacing=1)
            write(b, i, it)
        st.done()

    def contact(b, i, v):
        run(ctx, b.p(before=6 if i else 0), v, size=11.5, color="F2EFE4")

    def education(b, i, ed):
        run(ctx, b.p(before=11 if i else 0, line=1.35), ed["degree"], "bold", size=12.5,
            color="FFFFFF")
        if ed["start"] or ed["end"]:
            run(ctx, b.p(before=3), date_range(ed["start"], ed["end"]), "bold", size=11,
                color=AMBER)
        if ed["school"]:
            run(ctx, b.p(before=2), ed["school"], size=11, color="CFD8C4", italic=True)

    def skill(b, i, sk):
        p = b.p(before=8 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, sk["name"], size=11.5, color="FFFFFF")
        if rated(sk):
            pct, label = skill_pct(sk)
            run(ctx, p, "\t", size=10)
            run(ctx, p, label, "bold", size=10, color=AMBER)
            b.pad_top = 5
            bar(ctx, b, pct, W, on=AMBER, off=TRACK, height=7)

    def languages(b, i, langs):
        p = b.p(line=1.55)
        for k, lg in enumerate(langs):
            run(ctx, p, lg["name"] + " ", size=11.5, color="FFFFFF")
            run(ctx, p, lg["level"], "bold", size=11.5, color=AMBER)
            if k < len(langs) - 1:
                run(ctx, p, " · ", size=11.5, color="FFFFFF")

    def cert(b, i, rec):
        run(ctx, b.p(before=8 if i else 0, line=1.35), rec["title"], "bold", size=12,
            color="FFFFFF")
        if rec["detail"]:
            run(ctx, b.p(before=2), rec["detail"], "bold", size=11, color=AMBER)

    c = r["contact"]
    contact_items = [x for x in (c["email"], c["phone"], c["address"], c["site"]) if x]
    labels = [(t("PERSONAL<br>INFORMATION"), contact_items, contact),
              (t("EDUCATION &amp;<br>QUALIFICATIONS"), r["education"], education),
              (t("SKILLS"), r["skills"], skill),
              (t("LANGUAGES"), [r["languages"]] if r["languages"] else [], languages),
              (t("CERTIFICATIONS"), r["recognition"], cert)]
    present = [x for x in labels if x[1]]
    first = [present[0][0] if present else ""]
    for label, items, write in present:
        section(label, items, write)

    # ---- main column: the name on the band, then the flow from 300px down
    T = page.main_text_px
    top = page.main_row(pad_top=96)
    run(ctx, top.p(line=1.0), r["name"], "name", size=52, color=GREEN, spacing=0.5, caps=True)
    if r["title"]:
        run(ctx, top.p(before=12), r["title"], "bold", size=16, color="3F2C02")
    gap_to_flow = 300 - 112 - (52 * 1.25 * (1 if len(r["name"]) < 16 else 2)) - 34
    box = page.main_row(pad_top=max(24, gap_to_flow))
    if r["summary"]:
        run(ctx, box.p(line=1.55), r["summary"], size=12, color="2B2B2B")
    if r["achievements"]:
        n = len(r["achievements"])
        box.pad_top = 16 if r["summary"] else 0
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, "D8D8D0"),
                                                   "bottom": (1, "D8D8D0")})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(0, 4, 0, 4))
            cb = Box(ctx, cell, 0, pad_top=12, pad_bottom=12)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=23,
                color=OLIVE)
            run(ctx, cb.p(align="center", before=4), a["label"], "bold", size=8.5,
                color="6B6B60", spacing=0.8, caps=True)
            cb.finish()
    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=16 if j == 0 else 13)
        if j == 0:
            run(ctx, box.p(after=12), t("PROFESSIONAL EXPERIENCE"), "heading", size=21,
                color=OLIVE, spacing=0.5)
        p = box.p(tabs=[(T - 2, "end", None)])
        run(ctx, p, job["role"], "role", size=14, color=GREEN)
        dates = date_range(job["start"], job["end"])
        if dates:
            run(ctx, p, "\t", size=11)
            run(ctx, p, dates, "bold", size=11, color=BROWN, italic=True)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, box.p(before=2), meta, size=11.5, color="4A5340", italic=True)
        bullets(ctx, box, job["bullets"], size=11.5, color="2B2B2B", line=1.5, before=7)
    if r["tools"]:
        box = page.main_row(pad_top=16)
        run(ctx, box.p(after=8), t("TOOLS"), "heading", size=21, color=OLIVE, spacing=0.5)
        run(ctx, box.p(line=1.55), " · ".join(r["tools"]), size=11.5, color="2B2B2B")
    page.finish()
