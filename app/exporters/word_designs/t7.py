"""modern-t7 — Yellow & Navy band: a 300px header band - a yellow panel with a
two-line Anton caps name and a tracked caps title, beside a grey photo block
framed in 5px of white - then a white main column (Career Objective, stats
between rules, Experience, a two-column Training grid) and a navy column at
the END edge (Skills as stacked yellow bars with the value as text,
Education, Tools, Languages, Contact). From modern/t7.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, page_rects, photo_run, pt, rated, row_height, run,
    skill_pct, tw,
)
from .common import SidebarPage, Stack, bullets, date_range, joined

YELLOW, NAVY, INK, GREYBLK = "FFD500", "001D3D", "4A4C4A", "D9D9D9"
SOFT, TRACK, RULE = "DFDEDD", "123A63", "9F9F9E"
SIDE_PX, BAND = 330, 300


@design("modern-t7")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(26))
    page = SidebarPage(ctx, SIDE_PX, side_fill=NAVY, side_pad=(0, 36, 26, 40),
                       main_pad_x=(44, 40), full_height_fill=False, side_end=True)
    # the yellow panel behind the name, page 1 only
    page_rects(ctx, [(850 - SIDE_PX, SIDE_PX + 1, 0, 1100, NAVY)],
               [(0, 850 - SIDE_PX, 0, BAND, YELLOW)])
    side = page.side
    W = SIDE_PX - 76

    # the photo block fills the band's end: 330 x 300, a 5px white frame
    photo_run(ctx, side.p(line=1.0, ind_start=-36, ind_end=-40), size_px=SIDE_PX,
              height_px=BAND, shape="rect", ring_px=5, ring="FFFFFF", placeholder=GREYBLK)

    heads = []

    def head(b, first):
        hp = b.p(before=30 if first else 20, after=12)
        heads.append(hp)
        run(ctx, hp, b._label, "heading", size=21, color="FFFFFF", caps=True, spacing=0.5)

    first = [True]

    def section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row()
            if i == 0:
                b._label = label
                head(b, first[0])
                first[0] = False
            write(b, i, it)
        st.done()

    def skill(b, i, sk):
        p = b.p(before=10 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, sk["name"], "bold", size=12, color="FFFFFF")
        if rated(sk):
            pct, label = skill_pct(sk)
            run(ctx, p, "\t", size=10.5)
            run(ctx, p, label, size=10.5, color=SOFT)
            bar(ctx, b, pct, W, on=YELLOW, off=TRACK, height=8, before=5)

    def education(b, i, ed):
        run(ctx, b.p(before=8 if i else 0), ed["degree"], "bold", size=14, color="FFFFFF")
        if ed["school"]:
            run(ctx, b.p(), ed["school"], size=12, color=SOFT)
        tail = joined([date_range(ed["start"], ed["end"]),
                       f"{t('GPA')} {ed['gpa']}" if ed["gpa"] else ""], " · ")
        if tail:
            run(ctx, b.p(), tail, size=11.5, color=YELLOW)

    def lines(line):
        def w(b, i, s):
            run(ctx, b.p(line=line), s, size=12, color=SOFT)
        return w

    section(t("Skills"), r["skills"], skill)
    section(t("Education"), r["education"], education)
    section(t("Tools"), [" · ".join(r["tools"])] if r["tools"] else [], lines(1.75))
    section(t("Languages"), [joined([x["name"], x["level"]], " — ") for x in r["languages"]],
            lines(1.85))
    c = r["contact"]
    contact = [x for x in (c["email"], c["phone"], c["address"], c["site"]) if x]
    contact += [s.get("label") for s in c["social"] if s.get("label")]
    section(t("Contact"), contact, lines(1.85))
    page.fit_side(heads)       # a full column gives up gaps, never spills

    # ---- main column: the yellow band first (a row at least 300px tall)
    T = page.main_text_px
    top = page.main_row(pad_top=44, fill=YELLOW)
    row_height(page.tbl.rows[0], BAND)
    for part in r["name"].split(" ", 1):
        run(ctx, top.p(line=0.92), part, "name", size=70, color=NAVY, caps=True, spacing=1)
    if r["title"]:
        run(ctx, top.p(before=14), r["title"], "bold", size=17, color=INK, caps=True,
            spacing=2)

    def lhead(box, label):
        run(ctx, box.p(after=10), label, "heading", size=21, color=NAVY, caps=True,
            spacing=0.5)

    gap = [30]

    def row():
        box = page.main_row(pad_top=gap[0])
        gap[0] = 18
        return box

    if r["summary"]:
        box = row()
        lhead(box, t("Career Objective"))
        run(ctx, box.p(line=1.65), r["summary"], size=12.5, color=INK)
    if r["achievements"]:
        box = row()
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for k, (cell, a) in enumerate(zip(tbl.rows[0].cells, r["achievements"])):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 10 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0, pad_top=11, pad_bottom=11)
            # number and label centred in the chip, as in the PDF (user, 2026-10-08)
            run(ctx, cb.p(align="center"), a["metric"], "metric", size=23, color=NAVY)
            run(ctx, cb.p(align="center", before=4), a["label"], "bold", size=9, color=INK, spacing=1,
                caps=True)
            cb.finish()
    H = "role" if ctx.rtl else "bold"
    for j, job in enumerate(r["experience"]):
        box = row() if j == 0 else page.main_row(pad_top=12)
        if j == 0:
            lhead(box, t("Experience"))
        run(ctx, box.p(), job["role"], H, size=14, color=NAVY)
        meta = joined([job["company"], job["location"], date_range(job["start"], job["end"])],
                      " · ")
        if meta:
            run(ctx, box.p(before=2, after=5), meta, size=11.5, color=INK)
        bullets(ctx, box, job["bullets"], size=11.5, color=INK, line=1.55, indent=15)
    if r["recognition"]:
        box = row()
        lhead(box, t("Training"))
        recs = r["recognition"]
        col = (T - 18) / 2
        tbl = box.table([tw(col + 18), tw(col)], rows=(len(recs) + 1) // 2)
        for i, rec in enumerate(recs):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 18 if i % 2 == 0 else 0))
            cb = Box(ctx, cell, 0, pad_top=8 if i >= 2 else 0)
            run(ctx, cb.p(line=1.45), rec["title"], H, size=12, color=NAVY)
            if rec["detail"]:
                run(ctx, cb.p(line=1.45), rec["detail"], size=12, color=INK)
            cb.finish()
        if len(recs) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()
    page.finish()
