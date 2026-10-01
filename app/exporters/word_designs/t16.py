"""modern-t16 — Charcoal Rings: a charcoal 290px rail - a round photo with a
4px brick ring, caps Montserrat heads, contact lines, a 2-up cluster of skill
RINGS (brick arc on a dark track, the percent as text in the hole, name and
level under each), certifications, languages. Main column: a caps name, a
tracked brick title, the summary, a stat band between hairlines, experience
with dates at the line end and brick company lines, education in two columns,
tools in three. From modern/t16.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, fmt_cell, photo_run, pt, rated, ring_anchored, run, skill_pct, tw,
)
from .common import SidebarPage, Stack, bullets, date_range, joined, single_px

RAIL, BRICK, TRACK, RULE = "1C1C20", "A32638", "3C3C44", "DAD8D6"
RAIL_TEXT, RAIL_MUTED, INK, BODY = "DDDDE2", "A7A7B0", "1C1C20", "33333A"
SIDE_PX = 290


@design("modern-t16")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(30))
    page = SidebarPage(ctx, SIDE_PX, side_fill=RAIL, side_pad=(34, 28, 30, 28),
                       main_pad_x=(40, 44))
    side = page.side
    W = SIDE_PX - 56
    photo_run(ctx, side.p(align="center"), size_px=172, ring_px=4, ring=BRICK,
              placeholder="33333A")

    def head(b):
        def h(label):
            run(ctx, b.p(before=30, after=14), label, "heading", size=16, color="FFFFFF",
                caps=True, spacing=1.6)
        return h

    def lines(label, items, line):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, s in enumerate(items):
            b = st.row()
            if i == 0:
                head(b)(label)
            run(ctx, b.p(line=line), s, size=12, color=RAIL_TEXT)
        st.done()

    c = r["contact"]
    contact = [x for x in (c["email"], c["phone"], c["address"], c["site"]) if x]
    contact += [s.get("label") for s in c["social"] if s.get("label")]
    lines(t("Contact"), contact, 1.9)

    if r["skills"]:
        st = Stack(ctx, side, W)
        skills = r["skills"]
        col = (W - 18) / 2
        for rr in range((len(skills) + 1) // 2):
            b = st.row()
            if rr == 0:
                head(b)(t("Skills"))
            tbl = b.table([tw(col + 18), tw(col)])
            for k in range(2):
                cell = tbl.rows[0].cells[k]
                fmt_cell(ctx, cell, pad=(0, 0, 0, 18 if k == 0 else 0))
                cb = Box(ctx, cell, 0, pad_top=16 if rr else 0)
                i = rr * 2 + k
                if i < len(skills):
                    sk = skills[i]
                    if rated(sk):
                        pct, _ = skill_pct(sk)
                        # the 74px ring around the percent's own 74px-tall line
                        line = single_px(ctx, "bold", 13)
                        pad = (74 - line) / 2
                        p = cb.p(align="center", before=pad, after=pad + 7)
                        run(ctx, p, f"{round(pct)}%", "bold", size=13, color="FFFFFF")
                        # y from the paragraph's top INCLUDING the row gap above
                        ring_anchored(p, x_pt=pt((col - 74) / 2), y_pt=pt(16 if rr else 0),
                                      d_px=74, width_px=9, pct=pct, on=BRICK, off=TRACK)
                    # Word's bold sets wider than the PDF's 600: a little room
                    run(ctx, cb.p(align="center", ind_start=-8, ind_end=-8), sk["name"], "bold",
                        size=11.5, color="FFFFFF")
                    if sk["level"]:
                        run(ctx, cb.p(align="center"), sk["level"], size=10.5,
                            color=RAIL_MUTED)
                cb.finish()
        st.done()

    lines(t("Certifications"), [joined([x["title"], x["detail"]], " · ")
                                for x in r["recognition"]], 1.75)
    lines(t("Languages"), [joined([x["name"], x["level"]], " — ") for x in r["languages"]],
          1.85)

    # ---- main column
    T = page.main_text_px
    H = "role" if ctx.rtl else "bold"
    top = page.main_row(pad_top=44)
    run(ctx, top.p(line=1.02), r["name"], "name", size=44, color=INK, caps=True, spacing=-1)
    if r["title"]:
        run(ctx, top.p(before=8), r["title"], size=15, color=BRICK, caps=True, spacing=3.2)
    if r["summary"]:
        run(ctx, top.p(before=12, line=1.7), r["summary"], size=12.5, color="3C3C44")

    if r["achievements"]:
        box = page.main_row(pad_top=34)
        ach = [a for a in r["achievements"] if a["metric"]]
        n = max(1, len(ach))
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for k, (cell, a) in enumerate(zip(tbl.rows[0].cells, ach)):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 14 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0, pad_top=14, pad_bottom=14)
            run(ctx, cb.p(line=1.0), a["metric"], "metric", size=25, color=BRICK)
            run(ctx, cb.p(before=5), a["label"], "bold", size=9, color="66666E", spacing=1.1,
                caps=True)
            cb.finish()

    def bhead(box, label):
        run(ctx, box.p(after=13), label, "heading", size=20, color=INK, caps=True,
            spacing=1.4)

    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=34 if j == 0 else 18)
        if j == 0:
            bhead(box, t("Experience"))
        p = box.p(tabs=[(T, "end", None)])
        run(ctx, p, job["role"], H, size=14.5, color=INK)
        dates = date_range(job["start"], job["end"], " — ")
        if dates:
            run(ctx, p, "\t", size=11.5)
            run(ctx, p, dates, size=11.5, color="70707A")
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, box.p(before=2, after=7), meta, size=12.5, color=BRICK)
        bullets(ctx, box, job["bullets"], size=12.5, color=BODY, line=1.6)

    if r["education"]:
        box = page.main_row(pad_top=34)
        bhead(box, t("Education"))
        eds = r["education"]
        col = (T - 24) / 2
        tbl = box.table([tw(col + 24), tw(col)], rows=(len(eds) + 1) // 2)
        for i, ed in enumerate(eds):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 24 if i % 2 == 0 else 0))
            cb = Box(ctx, cell, 0, pad_top=12 if i >= 2 else 0)
            run(ctx, cb.p(line=1.5), ed["degree"], H, size=12.5, color=INK)
            sub = joined([ed["school"], ed["end"]], " · ")
            if sub:
                run(ctx, cb.p(line=1.5), sub, size=12.5, color="5C5C66")
            cb.finish()
        if len(eds) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()

    if r["tools"]:
        box = page.main_row(pad_top=34)
        bhead(box, t("Tools"))
        tools = r["tools"]
        col = (T - 40) / 3
        tbl = box.table([tw(col + 20), tw(col + 20), tw(col)], rows=(len(tools) + 2) // 3)
        for i, tool in enumerate(tools):
            cell = tbl.rows[i // 3].cells[i % 3]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 20 if i % 3 < 2 else 0))
            cb = Box(ctx, cell, 0, pad_top=8 if i >= 3 else 0)
            run(ctx, cb.p(), tool, size=12.5, color=BODY)
            cb.finish()
        for k in range(len(tools) % 3 and 3 - len(tools) % 3):
            Box(ctx, tbl.rows[-1].cells[2 - k], 0).finish()
    page.finish()
