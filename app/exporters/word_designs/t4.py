"""modern-t4 — Ribbon Sidebar: deep-navy rail with a white-ringed round photo,
clay ribbon headings, labelled contact, dot rows under the skill names; a
two-line caps name, stats between rules, experience with a date column and a
vertical rule, Recognition + inline Tools, References. From modern/t4.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import Box, Ctx, design, dots, fmt_cell, photo_run, pt, run, tw
from .common import SidebarPage, Stack, block, bullets, date_range, joined

RAIL, CLAY, INK, BODY = "000034", "C4562F", "14343B", "37474C"
RAIL_TEXT, RAIL_MUTED, DOT_OFF, RULE, MUTED = "E3E5EF", "AEB4D2", "565C8A", "D8D2C7", "6E7C80"
SIDE_PX = 300


def _ribbon(ctx, box, label, before=13):
    b = block(ctx, box, SIDE_PX, fill=CLAY, pad=(8, 34, 8, 0))
    run(ctx, b.p(), label, "heading", size=19, color="FFFFFF", spacing=0.5)
    b.finish()


def _head(ctx, box, label, after=16):
    run(ctx, box.p(after=after), label, "heading", size=25, color=INK)


@design("modern-t4")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(22))
    page = SidebarPage(ctx, SIDE_PX, side_fill=RAIL, side_pad=(26, 0, 22, 0),
                       main_pad_x=(40, 44))
    side = page.side
    p = side.p(align="center", after=16)
    photo_run(ctx, p, size_px=158, ring_px=5, ring="FFFFFF", placeholder="DCD6CB")
    W = SIDE_PX - 68

    def section(label, items, write, gap):
        if not items:
            return
        st = Stack(ctx, side, SIDE_PX)
        for i, it in enumerate(items):
            b = st.row(pad_top=11 if i == 0 else 0)
            if i == 0:
                _ribbon(ctx, b, label)
            write(b, i, it, gap)
        st.done()

    def contact(b, i, item, gap):
        label, value = item
        run(ctx, b.p(before=11 if i == 0 else gap, ind_start=34, ind_end=34), label, "bold",
            size=13, color="FFFFFF")
        run(ctx, b.p(line=1.45, ind_start=34, ind_end=34), value, size=12.5, color=RAIL_TEXT)

    def education(b, i, ed, gap):
        run(ctx, b.p(before=11 if i == 0 else gap, ind_start=34, ind_end=34), ed["degree"],
            "bold", size=13.5, color="FFFFFF")
        if ed["school"]:
            run(ctx, b.p(line=1.45, ind_start=34, ind_end=34), ed["school"], size=12.5,
                color=RAIL_TEXT)
        if ed["start"] or ed["end"]:
            run(ctx, b.p(line=1.45, ind_start=34), date_range(ed["start"], ed["end"]),
                size=12.5, color=RAIL_MUTED)
        if ed["gpa"]:
            run(ctx, b.p(line=1.45, ind_start=34), f"{t('GPA')} {ed['gpa']}", size=12.5,
                color=RAIL_MUTED)

    def skill(b, i, sk, gap):
        p = b.p(before=11 if i == 0 else gap, ind_start=34, tabs=[(SIDE_PX - 34, "end", None)])
        run(ctx, p, sk["name"], "bold", size=12.5, color="FFFFFF")
        if sk["level"]:
            run(ctx, p, "\t", size=11)
            run(ctx, p, sk["level"], size=11, color=RAIL_MUTED)
            dp = b.p(before=1, ind_start=34)
            dots(ctx, dp, sk["dots"], sk["dot_total"], on=CLAY, off=DOT_OFF, size=15, gap=1)

    def language(b, i, lg, gap):
        p = b.p(before=11 if i == 0 else gap, ind_start=34, tabs=[(SIDE_PX - 34, "end", None)])
        run(ctx, p, lg["name"], "bold", size=12.5, color="FFFFFF")
        if lg["level"]:
            run(ctx, p, "\t", size=12.5)
            run(ctx, p, lg["level"], size=12.5, color=RAIL_MUTED)

    c = r["contact"]
    items = [(t("Phone"), c["phone"]), (t("Email"), c["email"]), (t("Address"), c["address"]),
             (t("Portfolio"), c["site"])]
    items += [(s.get("label") or "", s.get("url") or "") for s in c["social"]]
    section(t("Contact"), [x for x in items if x[1]], contact, 10)
    section(t("Education"), r["education"], education, 14)
    section(t("Skills"), r["skills"], skill, 9)
    section(t("Language"), r["languages"], language, 8)

    # ---- main column
    T = page.main_text_px
    top = page.main_row(pad_top=52)
    parts = r["name"].split(" ", 1)
    for k, part in enumerate(parts):
        run(ctx, top.p(line=1.0), part, "name", size=54, color=INK, caps=True, spacing=-1.5)
    if r["title"]:
        run(ctx, top.p(before=10), r["title"], size=19, color=BODY)
    if r["achievements"]:
        box = page.main_row(pad_top=20)
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 14))
            cb = Box(ctx, cell, 0, pad_top=12, pad_bottom=12)
            run(ctx, cb.p(line=1.0), a["metric"], "metric", size=24, color=CLAY)
            run(ctx, cb.p(before=5), a["label"], "bold", size=9, color=MUTED, spacing=1,
                caps=True)
            cb.finish()
    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=20 if j == 0 else 18)
        if j == 0:
            _head(ctx, box, t("Professional Experience"))
        tbl = box.table([tw(54 + 18), tw(T - 72)])
        d, body = tbl.rows[0].cells
        fmt_cell(ctx, d, pad=(0, 0, 0, 18))
        fmt_cell(ctx, body, pad=(0, 18, 0, 0), borders={"start": (1, "C9C1B3")})
        db = Box(ctx, d, 0)
        for k, part in enumerate([x for x in (job["start"], "–" if job["start"] and
                                              job["end"] else "", job["end"]) if x]):
            run(ctx, db.p(align="end", line=1.5), part, "role", size=12, color=INK,
                spacing=0.5)
        db.finish()
        bb = Box(ctx, body, 0)
        run(ctx, bb.p(), job["role"], "role", size=16, color=INK)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, bb.p(before=3, after=7), meta, size=13, color=BODY)
        bullets(ctx, bb, job["bullets"], size=12.5, color=BODY, line=1.5)
        bb.finish()
    if r["recognition"] or r["tools"]:
        box = page.main_row(pad_top=20)
        if r["recognition"]:
            _head(ctx, box, t("Recognition"), after=10)
            for i, rec in enumerate(r["recognition"]):
                p = box.p(before=5 if i else 0)
                run(ctx, p, rec["title"], "bold", size=12.5, color=INK)
                if rec["detail"]:
                    run(ctx, p, " — " + rec["detail"], size=12.5, color=BODY)
        if r["tools"]:
            p = box.p(before=10 if r["recognition"] else 0)
            run(ctx, p, t("Tools"), "heading", size=12.5, color=INK)
            run(ctx, p, "  " + " · ".join(r["tools"]), size=12.5, color=BODY)
    if r["references"]:
        box = page.main_row(pad_top=20)
        _head(ctx, box, t("References"), after=14)
        refs = r["references"]
        col = (T - 26) / 2
        tbl = box.table([tw(col + 26), tw(col)], rows=(len(refs) + 1) // 2)
        for i, ref in enumerate(refs):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 26 if i % 2 == 0 else 0))
            cb = Box(ctx, cell, 0, pad_top=26 if i >= 2 else 0)
            run(ctx, cb.p(), ref["name"], "role", size=15, color=INK)
            if ref["title"]:
                run(ctx, cb.p(after=6), ref["title"], size=13, color=BODY)
            if ref["phone"]:
                p = cb.p(line=1.6)
                run(ctx, p, t("Phone:"), "bold", size=11.5, color=INK)
                run(ctx, p, " " + ref["phone"], size=11.5, color=MUTED)
            if ref["email"]:
                p = cb.p(line=1.6)
                run(ctx, p, t("Email:"), "bold", size=11.5, color=INK)
                run(ctx, p, " " + ref["email"], size=11.5, color=MUTED)
            cb.finish()
        if len(refs) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()
    page.finish()
