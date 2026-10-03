"""modern-t13 — Navy band: a full-width navy header (caps name, tracked gold
title, the contact lines end-aligned at its foot, a gold stat row under a
translucent rule), then one column: the summary, an experience timeline on a
gold rail with navy nodes, skills in two columns as name + level + dot row,
and Education | Certifications side by side under a hairline.
From modern/t13.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, dots_shape, fmt_cell, fmt_p, pt, run, tiny, tw, vml_oval,
)
from .common import ColumnPage, bullets, date_range, joined

NAVY, GOLD, BAND_TEXT, SOFT, LABEL = "0E2D55", "D8C79A", "E9EEF5", "C7D4E4", "AFC0D4"
INK, BODY, META, DATE, RULE, DOT_OFF = "22293A", "2E3646", "4A5364", "6C7484", "D8DAE0", "C2C6CE"
BAND_RULE = "516885"            # rgba(255,255,255,0.28) over the navy


@design("modern-t13")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(33))
    page = ColumnPage(ctx, pad_x=(48, 48))
    T = page.main_text_px
    H = "role" if ctx.rtl else "bold"

    # ---- the navy header band
    band = page.main_row(fill=NAVY, pad_top=38, pad_bottom=32)
    c = r["contact"]
    bits = [x for x in (c["email"], c["phone"], c["address"], c["site"]) if x]
    right = 200 if bits else 0
    tbl = band.table([tw(T - right), tw(right)] if right else [tw(T)])
    left = tbl.rows[0].cells[0]
    fmt_cell(ctx, left, valign="bottom", pad=(0, 0, 0, 30 if right else 0))
    lb = Box(ctx, left, 0)
    run(ctx, lb.p(line=1.0), r["name"], "name", size=46, color="FFFFFF", caps=True,
        spacing=-1.2)
    # Arabic: Word cannot set the Tajawal name as tight as the PDF's 1.0 (the
    # no-collision floor) - the block came out ~13px taller and pushed the
    # band down (measured, run 6); the gaps under it give that back
    ar = ctx.rtl
    if r["title"]:
        run(ctx, lb.p(before=0 if ar else 9), r["title"], size=14, color=GOLD, caps=True,
            spacing=3.6)
    lb.finish()
    if right:
        rc = tbl.rows[0].cells[1]
        fmt_cell(ctx, rc, valign="bottom")
        rb = Box(ctx, rc, 0)
        for b in bits:
            run(ctx, rb.p(align="end", line=1.8), b, size=11.5, color=SOFT)
        rb.finish()
    if r["achievements"]:
        rule = band.p()
        tiny(rule)
        fmt_p(ctx, rule, before=17 if ar else 22, after=16,
              border={"bottom": (1, BAND_RULE, 0)})
        n = len(r["achievements"])
        st = band.table([tw(T) // n] * n)
        for k, (cell, a) in enumerate(zip(st.rows[0].cells, r["achievements"])):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 16 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0)
            run(ctx, cb.p(line=1.0), a["metric"], "metric", size=25, color=GOLD)
            run(ctx, cb.p(before=5), a["label"], "bold", size=9, color=LABEL, spacing=1.2,
                caps=True)
            cb.finish()

    def head(box, label, after, size=19):
        run(ctx, box.p(after=after), label, "heading", size=size, color=NAVY, caps=True,
            spacing=1.6)

    gap = [30]

    def row(**kw):
        box = page.main_row(pad_top=gap[0], **kw)
        gap[0] = 46
        return box

    if r["summary"]:
        box = row()
        run(ctx, box.p(line=1.7), r["summary"], size=12.5, color=BODY)

    # ---- timeline: a 2px gold rail at the start edge, content 24px in, nodes on it
    node = [0]
    for j, job in enumerate(r["experience"]):
        box = row() if j == 0 else page.main_row(pad_top=20)
        if j == 0:
            head(box, t("Experience"), 16)
        tbl = box.table([tw(T)])
        cell = tbl.rows[0].cells[0]
        fmt_cell(ctx, cell, pad=(0, 24, 0, 0), borders={"start": (2, GOLD)})
        eb = Box(ctx, cell, 0)
        p = eb.p(tabs=[(T - 24, "end", None)])
        node[0] += 1
        x = (T - 24 + 24 - 8) if ctx.rtl else (-24 - 8)
        vml_oval(ctx, p, x_pt=pt(x), y_pt=pt(4), d_pt=pt(14), fill=NAVY, stroke=None,
                 n=400 + node[0])
        run(ctx, p, job["role"], H, size=14.5, color=NAVY)
        dates = date_range(job["start"], job["end"], " — ")
        if dates:
            run(ctx, p, "\t", size=11.5)
            run(ctx, p, dates, size=11.5, color=DATE)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, eb.p(before=2, after=7), meta, size=12.5, color=META)
        bullets(ctx, eb, job["bullets"], size=12.5, color=BODY, line=1.6)
        eb.finish()

    if r["skills"]:
        skills = r["skills"]
        col = (T - 40) / 2
        for rr in range((len(skills) + 1) // 2):
            box = row() if rr == 0 else page.main_row(pad_top=11)
            if rr == 0:
                head(box, t("Skills"), 14)
            tbl = box.table([tw(col + 40), tw(col)])
            for k in range(2):
                cell = tbl.rows[0].cells[k]
                fmt_cell(ctx, cell, pad=(0, 0, 0, 40 if k == 0 else 0))
                cb = Box(ctx, cell, 0)
                i = rr * 2 + k
                if i < len(skills):
                    sk = skills[i]
                    p = cb.p(tabs=[(col, "end", None)])
                    run(ctx, p, sk["name"], "bold", size=12.5, color=INK)
                    if sk["level"]:
                        run(ctx, p, "\t", size=10.5)
                        run(ctx, p, sk["level"], size=10.5, color="5C5C66")
                        dots_shape(ctx, cb.p(before=5), sk["dots"], sk["dot_total"], on=NAVY,
                                   off=DOT_OFF, d=9, gap=5)
                cb.finish()

    if r["education"] or r["recognition"]:
        box = row()
        rule = box.p()
        tiny(rule)
        fmt_p(ctx, rule, after=20, border={"bottom": (1, RULE, 0)})
        col = (T - 40) / 2
        tbl = box.table([tw(col + 40), tw(col)])
        a, b = tbl.rows[0].cells
        fmt_cell(ctx, a, pad=(0, 0, 0, 40))
        ab = Box(ctx, a, 0)
        if r["education"]:
            head(ab, t("Education"), 12)
            for i, ed in enumerate(r["education"]):
                run(ctx, ab.p(before=10 if i else 0, line=1.5), ed["degree"], H, size=12.5,
                    color=NAVY)
                sub = joined([ed["school"], ed["end"]], " · ")
                if sub:
                    run(ctx, ab.p(line=1.5), sub, size=12.5, color="5C6474")
        ab.finish()
        bb = Box(ctx, b, 0)
        if r["recognition"]:
            head(bb, t("Certifications"), 12)
            for i, rec in enumerate(r["recognition"]):
                run(ctx, bb.p(before=8 if i else 0), joined([rec["title"], rec["detail"]],
                                                             " · "), size=12.5, color=BODY)
        bb.finish()
    page.finish()
