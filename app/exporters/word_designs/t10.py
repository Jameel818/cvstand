"""modern-t10 — Rust rail: a round grey portrait, the name and tracked caps
title centred on the rail, labelled contact, Tools as a list, language levels
right in bold; heavy main headings, dates right, stats in blue between rules,
and the skills as a bordered card of three columns of sliders with the percent
as text. From modern/t10.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import Box, Ctx, bar, design, fmt_cell, photo_run, pt, rated, run, skill_pct, tw
from .common import SidebarPage, Stack, bullets, date_range, joined

RUST, INK, BODY, BLUE, SKY, TRACK, RULE = ("A93005", "111111", "333333", "0369A1", "38BDF8",
                                          "D5E8F5", "CFCFCF")
SIDE_PX = 280


def _head(ctx, box, label, after=14):
    run(ctx, box.p(after=after), label, "heading", size=24, color=INK, spacing=-0.3)


@design("modern-t10")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(42))
    page = SidebarPage(ctx, SIDE_PX, side_fill=RUST, side_pad=(42, 32, 42, 32),
                       main_pad_x=(42, 42))
    side = page.side
    W = SIDE_PX - 64
    photo_run(ctx, side.p(align="center"), size_px=148, placeholder="D5D8DD")
    run(ctx, side.p(align="center", before=26, line=1.02), r["name"], "name", size=38,
        color="FFFFFF", spacing=-1)
    if r["title"]:
        run(ctx, side.p(align="center", before=8), r["title"], "bold", size=15, color="FFFFFF",
            spacing=1, caps=True)
    c = r["contact"]
    items = [(t("Phone"), c["phone"]), (t("Email"), c["email"]), (t("Location"), c["address"]),
             (t("Website"), c["site"])]
    items += [(s.get("label") or "", s.get("url") or "") for s in c["social"]]
    for i, (label, value) in enumerate([x for x in items if x[1]]):
        run(ctx, side.p(before=20 if i == 0 else 9, after=1), label, "bold", size=13,
            color="FFFFFF")
        run(ctx, side.p(), value, size=11, color="F1DDD5")

    def section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row(pad_top=18 if i == 0 else 0)
            if i == 0:
                run(ctx, b.p(after=8), label, "heading", size=22, color="FFFFFF")
            write(b, i, it)
        st.done()

    def tool(b, i, s):
        run(ctx, b.p(before=4 if i else 0), s, size=13, color="FFFFFF")

    def language(b, i, lg):
        p = b.p(before=9 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, lg["name"], size=13, color="FFFFFF")
        if lg["level"]:
            run(ctx, p, "\t", size=13)
            run(ctx, p, lg["level"], "bold", size=13, color="FFFFFF")

    def cert(b, i, rec):
        run(ctx, b.p(before=11 if i else 0, line=1.4), rec["title"], size=13, color="FFFFFF")
        if rec["detail"]:
            run(ctx, b.p(line=1.4), rec["detail"], "bold", size=12.5, color="FFFFFF")

    section(t("Tools"), r["tools"], tool)
    section(t("Languages"), r["languages"], language)
    section(t("Certifications"), r["recognition"], cert)

    # ---- main column
    T = page.main_text_px
    first = [46]

    def row(gap):
        box = page.main_row(pad_top=first[0] if first[0] else gap)
        first[0] = 0
        return box

    if r["summary"]:
        box = row(30)
        _head(ctx, box, t("SUMMARY"))
        run(ctx, box.p(line=1.65), r["summary"], size=13, color=BODY)
    if r["achievements"]:
        box = row(30)
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(0, 4, 0, 4))
            cb = Box(ctx, cell, 0, pad_top=14, pad_bottom=14)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=25, color=BLUE)
            run(ctx, cb.p(align="center", before=5), a["label"], "bold", size=9, color="666666",
                spacing=1, caps=True)
            cb.finish()
    for j, job in enumerate(r["experience"]):
        box = row(30) if j == 0 else page.main_row(pad_top=16)
        if j == 0:
            _head(ctx, box, t("EXPERIENCE"))
        p = box.p(tabs=[(T - 2, "end", None)])
        run(ctx, p, job["role"], "role", size=16, color=INK)
        dates = date_range(job["start"], job["end"])
        if dates:
            run(ctx, p, "\t", size=12.5)
            run(ctx, p, dates, size=12.5, color=BODY)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, box.p(before=2, after=6), meta, size=13, color=BODY)
        bullets(ctx, box, job["bullets"], size=12.5, color=BODY, line=1.5, indent=18)
    for j, ed in enumerate(r["education"]):
        box = row(30) if j == 0 else page.main_row(pad_top=12)
        if j == 0:
            _head(ctx, box, t("EDUCATION"))
        p = box.p(tabs=[(T - 2, "end", None)])
        run(ctx, p, ed["degree"], "role", size=15, color=INK)
        dates = date_range(ed["start"], ed["end"], " - ")
        if dates:
            run(ctx, p, "\t", size=12.5)
            run(ctx, p, dates, size=12.5, color=BODY)
        if ed["school"]:
            gpa = f" · {t('GPA')} {ed['gpa']}" if ed["gpa"] else ""
            run(ctx, box.p(), ed["school"] + gpa, size=13, color=BODY)
    if r["skills"]:
        box = row(30)
        _head(ctx, box, t("SKILLS"))
        skills = r["skills"]
        rows = (len(skills) + 2) // 3
        inner = T - 40
        col = (inner - 44) / 3
        widths = [tw(20 + col), tw(22 + col), tw(22 + col + 20)]
        tbl = box.table(widths, rows=rows, borders={"top": (1, RULE), "bottom": (1, RULE),
                                                    "left": (1, RULE), "right": (1, RULE)})
        for i in range(rows * 3):
            cell = tbl.rows[i // 3].cells[i % 3]
            k = i % 3
            fmt_cell(ctx, cell, pad=(0, 20 if k == 0 else 22, 0, 20 if k == 2 else 0))
            cb = Box(ctx, cell, 0, pad_top=18 if i < 3 else 16,
                     pad_bottom=18 if i // 3 == rows - 1 else 0)
            if i < len(skills):
                sk = skills[i]
                p = cb.p(tabs=[(col, "end", None)])
                run(ctx, p, sk["name"], size=11.5, color=INK)
                if rated(sk):
                    pct, label = skill_pct(sk)
                    run(ctx, p, "\t", size=12)
                    run(ctx, p, label, "bold", size=12, color=INK)
                    cb.pad_top = 8
                    bar(ctx, cb, pct, col, on=SKY, off=TRACK, height=6)
            cb.finish()
    page.finish()
