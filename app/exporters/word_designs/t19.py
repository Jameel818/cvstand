"""modern-t19 — Gutter: a caps name over a 2px rule, the tracked plum title and
the contact line end-aligned on the rule's line, plum stats; then every
section is a row ruled at its top with a 124px plum caps label in the gutter
beside the content - Profile, Experience (dates at the line end), Skills as
stacked rounded bars in two columns, Tooling in three, Education and
Certifications in two, Languages inline with the level in plum.
From modern/t19.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, pt, rated, run, skill_pct, tw,
)
from .common import ColumnPage, bullets, date_range, joined

INK, PLUM, BODY, META, MUTED, RULE, TRACK = ("1B1B22", "6B2A5A", "2E2E38", "3E3E48", "5A5A64",
                                            "D9D7DD", "E4E2E7")
PAD, GUT, GAP = 56, 124, 22


@design("modern-t19")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(52))
    sec.bottom_margin = Pt(pt(44))
    page = ColumnPage(ctx, pad_x=(PAD, PAD))
    T = page.main_text_px
    C = T - GUT - GAP
    H = "role" if ctx.rtl else "heading"

    top = page.main_row()
    run(ctx, top.p(line=1.0), r["name"], "name", size=46, color=INK, caps=True, spacing=-1.6)
    c = r["contact"]
    bits = [x for x in (c["email"], c["phone"], c["address"], c["site"]) if x]
    bits += [s.get("label") for s in c["social"] if s.get("label")]
    top.pad_top = 14
    ht = top.table([tw(T * 0.42), tw(T * 0.58)], borders={"top": (2, INK)})
    a, b = ht.rows[0].cells
    fmt_cell(ctx, a, valign="bottom")
    fmt_cell(ctx, b, valign="bottom")
    ab = Box(ctx, a, 0, pad_top=11)
    if r["title"]:
        run(ctx, ab.p(), r["title"], size=13.5, color=PLUM, caps=True, spacing=3.2)
    ab.finish()
    bb = Box(ctx, b, 0, pad_top=11)
    if bits:
        run(ctx, bb.p(align="end"), " · ".join(bits), size=11.5, color="54545E")
    bb.finish()

    ach = [x for x in r["achievements"] if x["metric"]]
    if ach:
        box = page.main_row(pad_top=22)
        n = len(ach)
        st = box.table([tw(T) // n] * n)
        for k, (cell, x) in enumerate(zip(st.rows[0].cells, ach)):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 20 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0)
            run(ctx, cb.p(line=1.0), x["metric"], "metric", size=28, color=PLUM)
            run(ctx, cb.p(before=6), x["label"], "bold", size=9, color=MUTED, spacing=1.3,
                caps=True)
            cb.finish()

    gap = [22]

    def section_row(label, first=True, pad_top=None):
        """One ruled row: [the gutter label | the content]; returns the content Box."""
        box = page.main_row(pad_top=gap[0] if pad_top is None else pad_top)
        gap[0] = 21
        tbl = box.table([tw(GUT + GAP), tw(C)], borders={"top": (1, RULE)} if first else None)
        g, cc = tbl.rows[0].cells
        fmt_cell(ctx, g, pad=(0, 0, 0, GAP))
        gb = Box(ctx, g, 0, pad_top=15 if first else 0)
        if first:
            run(ctx, gb.p(), label, "heading", size=11.5, color=PLUM, caps=True, spacing=1.4)
        gb.finish()
        return Box(ctx, cc, 0, pad_top=15 if first else 0)

    if r["summary"]:
        cb = section_row(t("Profile"))
        run(ctx, cb.p(line=1.7), r["summary"], size=12.5, color=BODY)
        cb.finish()
    for j, job in enumerate(r["experience"]):
        cb = section_row(t("Experience"), first=j == 0, pad_top=None if j == 0 else 16)
        p = cb.p(tabs=[(C, "end", None)])
        run(ctx, p, job["role"], H, size=15, color=INK)
        dates = date_range(job["start"], job["end"], " — ")
        if dates:
            run(ctx, p, "\t", size=11.5)
            run(ctx, p, dates, size=11.5, color="63636D")
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, cb.p(before=3, after=7), meta, size=12.5, color=META)
        bullets(ctx, cb, job["bullets"], size=12.5, color=BODY, line=1.6)
        cb.finish()
    if r["experience"]:
        gap[0] = 21

    def grid(cb, items, cols, hgap, vgap, write):
        col = (C - hgap * (cols - 1)) / cols
        widths = [tw(col + hgap)] * (cols - 1) + [tw(col)]
        tbl = cb.table(widths, rows=(len(items) + cols - 1) // cols)
        for i, it in enumerate(items):
            cell = tbl.rows[i // cols].cells[i % cols]
            fmt_cell(ctx, cell, pad=(0, 0, 0, hgap if i % cols < cols - 1 else 0))
            ib = Box(ctx, cell, 0, pad_top=vgap if i >= cols else 0)
            write(ib, it, col)
            ib.finish()
        for k in range((cols - len(items) % cols) % cols):
            Box(ctx, tbl.rows[-1].cells[cols - 1 - k], 0).finish()

    if r["skills"]:
        cb = section_row(t("Skills"))

        def skill(ib, sk, col):
            p = ib.p(tabs=[(col, "end", None)])
            run(ctx, p, sk["name"], "bold", size=12.5, color=INK)
            if rated(sk):
                pct, label = skill_pct(sk)
                run(ctx, p, "\t", size=10.5)
                run(ctx, p, label, size=10.5, color=MUTED)
                bar(ctx, ib, pct, col, on=PLUM, off=TRACK, height=8, before=5)
        grid(cb, r["skills"], 2, 34, 11, skill)
        cb.finish()
    if r["tools"]:
        cb = section_row(t("Tooling"))
        grid(cb, r["tools"], 3, 24, 8, lambda ib, s, col: run(ctx, ib.p(), s, size=12.5,
                                                            color=BODY))
        cb.finish()

    def two_lines(ib, pair, col):
        title, sub = pair
        run(ctx, ib.p(line=1.5), title, "bold", size=12.5, color=INK)
        if sub:
            run(ctx, ib.p(line=1.5), sub, size=12.5, color=MUTED)

    if r["education"]:
        cb = section_row(t("Education"))
        grid(cb, [(e["degree"], joined([e["school"], e["end"]], " · ")) for e in r["education"]],
             2, 34, 12, two_lines)
        cb.finish()
    if r["languages"]:
        cb = section_row(t("Languages"))
        p = cb.p(line=1.6)
        for i, lg in enumerate(r["languages"]):
            if i:
                run(ctx, p, "  ·  ", size=12.5, color=BODY)
            run(ctx, p, lg["name"] + " ", size=12.5, color=BODY)
            if lg["level"]:
                run(ctx, p, lg["level"], "bold", size=12.5, color=PLUM)
        cb.finish()
    if r["recognition"]:
        cb = section_row(t("Certifications"))
        grid(cb, [(x["title"], x["detail"]) for x in r["recognition"]], 2, 34, 12, two_lines)
        cb.finish()
    page.finish()
