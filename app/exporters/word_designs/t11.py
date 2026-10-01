"""modern-t11 — Dark rail & yellow band: a full-height dark rail at the START
edge headed by a 300px photo block (an italic summary under a short yellow
rule, skills with yellow dot rows and the level word, education, Language
pushed to the foot of the rail), and a 300px yellow band over the main column
(caps name, tracked caps title, a translucent rule, an inline stat row, a
contact line); the main column below holds experience entries ruled in
yellow at their start edge, Recognition and Tools. From modern/t11.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, dots_shape, fmt_cell, fmt_p, page_rects, photo_run, pt, row_height, run,
    tiny, tw,
)
from .common import SidebarPage, Stack, bullets, date_range, joined

RAIL, PHOTO, YELLOW, BAND_INK, INK = "0F1B2B", "2C3846", "FFD700", "08211C", "22262E"
SOFT, MUTED, DOT_OFF, BODY, META = "C3CEDB", "8FA1B4", "46586B", "3A414B", "5E6875"
BAND_RULE = "B09D09"            # rgba(8,33,28,0.32) over the yellow
SIDE_PX, BAND = 300, 300


@design("modern-t11")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(24))
    page = SidebarPage(ctx, SIDE_PX, side_fill=RAIL, side_pad=(0, 32, 24, 28),
                       main_pad_x=(38, 44), full_height_fill=False)
    page_rects(ctx, [(0, SIDE_PX + 1, 0, 1100, RAIL)], [(SIDE_PX, 850 - SIDE_PX, 0, BAND, YELLOW)])
    side = page.side
    W = SIDE_PX - 60
    photo_run(ctx, side.p(line=1.0, ind_start=-32, ind_end=-28), size_px=SIDE_PX,
              height_px=BAND, shape="rect", placeholder=PHOTO)
    side.pad_top = 24

    if r["summary"]:
        run(ctx, side.p(line=1.65), r["summary"], size=11.5, color=SOFT, italic=True)
        rule = side.p()
        tiny(rule)
        fmt_p(ctx, rule, before=13, ind_end=W - 60, border={"bottom": (2, YELLOW, 0)})

    def head(b, label, after=10, before=13):
        hp = b.p(before=before, after=after)
        run(ctx, hp, label, "heading", size=20, color="FFFFFF", caps=True, spacing=1)
        return hp

    if r["skills"]:
        st = Stack(ctx, side, W)
        for i, sk in enumerate(r["skills"]):
            b = st.row()
            if i == 0:
                head(b, t("Skills"))
            p = b.p(before=8 if i else 0, tabs=[(W, "end", None)])
            run(ctx, p, sk["name"], "bold", size=12, color="FFFFFF")
            if sk["level"]:
                run(ctx, p, "\t", size=10.5)
                run(ctx, p, sk["level"], size=10.5, color=MUTED)
                dots_shape(ctx, b.p(before=4), sk["dots"], sk["dot_total"], on=YELLOW,
                           off=DOT_OFF, d=9, gap=5)
        st.done()
    if r["education"]:
        st = Stack(ctx, side, W)
        for i, ed in enumerate(r["education"]):
            b = st.row()
            if i == 0:
                head(b, t("Education"))
            run(ctx, b.p(before=8 if i else 0, line=1.6), ed["degree"], "bold", size=11.5,
                color="FFFFFF")
            sub = joined([ed["school"], ed["end"]], " · ")
            if sub:
                run(ctx, b.p(line=1.6), sub, size=11.5, color=SOFT)
        st.done()
    if r["languages"]:
        st = Stack(ctx, side, W)
        lang_head = None
        for i, lg in enumerate(r["languages"]):
            b = st.row()
            if i == 0:
                lang_head = head(b, t("Language"), after=8)
            run(ctx, b.p(line=1.6), joined([lg["name"], lg["level"]], " — "), size=11.5,
                color=SOFT)
        st.done()
        # margin-top:auto in the PDF: Language closes the rail
        page.spread_side([lang_head])

    # ---- the yellow band over the main column (a row at least 300px tall)
    top = page.main_row(pad_top=38, fill=YELLOW, pad_x=(38, 40))
    row_height(page.tbl.rows[0], BAND)
    TB = 850 - SIDE_PX - 78
    run(ctx, top.p(line=1.0), r["name"], "name", size=48, color=BAND_INK, caps=True,
        spacing=-1.2)
    if r["title"]:
        run(ctx, top.p(before=8), r["title"], size=15, color=BAND_INK, caps=True, spacing=4)
    rule = top.p()
    tiny(rule)
    fmt_p(ctx, rule, before=14, after=12, border={"bottom": (1, BAND_RULE, 0)})
    if r["achievements"]:
        n = len(r["achievements"])
        tbl = top.table([tw(TB) // n] * n)
        for k, (cell, a) in enumerate(zip(tbl.rows[0].cells, r["achievements"])):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 12 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0)
            run(ctx, cb.p(), a["metric"], "metric", size=22, color=BAND_INK)
            run(ctx, cb.p(before=3), a["label"], "bold", size=8.5, color=BAND_INK, spacing=1,
                caps=True)
            cb.finish()
    c = r["contact"]
    bits = [x for x in (c["phone"], c["email"], c["address"], c["site"]) if x]
    bits += [s.get("label") for s in c["social"] if s.get("label")]
    if bits:
        top.pad_top = 12
        run(ctx, top.p(line=1.65), " · ".join(bits), size=11, color=BAND_INK)

    # ---- main column
    T = page.main_text_px
    H = "role" if ctx.rtl else "bold"
    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=28 if j == 0 else 14)
        if j == 0:
            run(ctx, box.p(after=14), t("Experience"), "heading", size=26, color=INK, caps=True,
                spacing=1)
        tbl = box.table([tw(T)])
        cell = tbl.rows[0].cells[0]
        fmt_cell(ctx, cell, pad=(0, 18, 0, 0), borders={"start": (2, YELLOW)})
        eb = Box(ctx, cell, 0)
        run(ctx, eb.p(), job["role"], H, size=14, color=INK, caps=True, spacing=0.4)
        meta = joined([job["company"], job["location"], date_range(job["start"], job["end"])],
                      " · ")
        if meta:
            run(ctx, eb.p(before=3, after=6), meta, size=12, color=META)
        bullets(ctx, eb, job["bullets"], size=12, color=BODY, line=1.55)
        eb.finish()
    if r["recognition"]:
        box = page.main_row(pad_top=15 if r["experience"] else 28)
        run(ctx, box.p(after=10), t("Recognition"), "heading", size=22, color=INK, caps=True,
            spacing=1)
        for i, rec in enumerate(r["recognition"]):
            p = box.p(before=4 if i else 0)
            run(ctx, p, rec["title"], "bold", size=12, color=INK)
            if rec["detail"]:
                run(ctx, p, " — " + rec["detail"], size=12, color=BODY)
    if r["tools"]:
        box = page.main_row(pad_top=15)
        run(ctx, box.p(after=8), t("Tools"), "heading", size=22, color=INK, caps=True,
            spacing=1)
        run(ctx, box.p(line=1.6), " · ".join(r["tools"]), size=12, color=BODY)
    page.finish()
