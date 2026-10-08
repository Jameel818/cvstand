"""modern-t3 — Yellow Photo Rail: a yellow 290px rail, everything centred - a
black-framed square photo, a two-line caps name, a tracked caps title, caps
section heads ruled underneath over bold lines (contact, competencies,
software, languages). Main column: huge display caps heads, a stat band
between a 2px and a 1px black rule, caps job titles with a caps meta line,
a black-bordered TECHNICAL SKILLS box of rounded bars in two columns,
education and recognition in caps. From modern/t3.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, bar, design, fmt_cell, photo_run, pt, rated, run, skill_pct, tw,
)
from .common import SidebarPage, Stack, block, bullets, date_range, joined

YELLOW, INK, TRACK = "FFDE00", "000000", "E4E4E4"
SIDE_PX = 290


@design("modern-t3")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(30))
    page = SidebarPage(ctx, SIDE_PX, side_fill=YELLOW, side_pad=(34, 26, 30, 26),
                       main_pad_x=(34, 38))
    side = page.side
    W = SIDE_PX - 52

    # ---- rail: photo, name, title, then the ruled sections - all centred
    photo_run(ctx, side.p(align="center"), size_px=210, shape="rect", ring_px=2, ring=INK,
              placeholder="FFFFFF")
    parts = r["name"].split(" ", 1)
    for k, part in enumerate(parts):
        # Word sets the 900 caps a hair wider than Chromium: the centred name may
        # use the rail's 26px padding rather than break "ASHWORT/H"
        run(ctx, side.p(align="center", before=20 if k == 0 else 0, line=0.98,
                        ind_start=-24, ind_end=-24), part, "name",
            size=38, color=INK, caps=True, spacing=-0.8)
    if r["title"]:
        run(ctx, side.p(align="center", before=8), r["title"], "bold", size=13, color=INK,
            caps=True, spacing=1.4)

    def section(label, lines, *, heading_role="heading"):
        if not lines:
            return
        st = Stack(ctx, side, W)
        for i, line in enumerate(lines):
            b = st.row()
            if i == 0:
                # 900/17px caps, a 2px black rule 7px under it, 12px to the lines
                hp = b.p(align="center", before=20, after=12,
                         border={"bottom": (2, INK, pt(7))})
                run(ctx, hp, label, heading_role, size=17, color=INK, caps=True, spacing=1.2)
            run(ctx, b.p(align="center", line=1.6), line, "bold", size=13.9, color=INK)
        st.done()

    c = r["contact"]
    contact = [x for x in (c["phone"], c["email"], c["site"], c["address"]) if x]
    contact += [s.get("label") for s in c["social"] if s.get("label")]
    section(t("Contact"), contact)
    section(t("Core Competencies"), [sk["name"] for sk in r["skills"]])
    # "Software" is not a .cv-section in the PDF: in Arabic it takes the body face
    section(t("Software"), r["tools"], heading_role="role" if ctx.rtl else "heading")
    section(t("Languages"), [joined([lg["name"], lg["level"]], " — ") for lg in r["languages"]])

    # ---- main column
    T = page.main_text_px
    # job titles, degrees, award titles: Archivo 900 in English; in Arabic the
    # PDF's policy draws them in the bold body face (docx_theme: the role face)
    H = "role" if ctx.rtl else "heading"

    def big(box, label, after, size=33):
        run(ctx, box.p(after=after, line=1.0), label, "heading", size=size, color=INK,
            caps=True, spacing=-0.8 if size == 33 else -0.6)

    gap = [34]                                  # the column's top padding, then 22

    def row(**kw):
        box = page.main_row(pad_top=gap[0], **kw)
        # English rows ran ~1px per 100px long in Word (measured, run 6)
        gap[0] = 22 if ctx.rtl else 20
        return box

    if r["summary"]:
        box = row()
        big(box, t("Professional Summary"), 10)
        run(ctx, box.p(line=1.55), r["summary"], size=13, color=INK)

    if r["achievements"]:
        box = row()
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (2, INK), "bottom": (1, INK)})
        for k, (cell, a) in enumerate(zip(tbl.rows[0].cells, r["achievements"])):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 12 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0, pad_top=11, pad_bottom=11)
            # number and label centred in the chip, as in the PDF (user, 2026-10-08)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=24, color=INK)
            run(ctx, cb.p(align="center", before=4), a["label"], "bold", size=8.5, color=INK, spacing=0.9,
                caps=True)
            cb.finish()

    for j, job in enumerate(r["experience"]):
        box = row() if j == 0 else page.main_row(pad_top=14)
        if j == 0:
            big(box, t("Experience"), 12)
        run(ctx, box.p(), job["role"], H, size=16, color=INK, caps=True, spacing=0.2)
        meta = joined([job["company"], job["location"], date_range(job["start"], job["end"])],
                      " · ")
        if meta:
            run(ctx, box.p(before=2, after=5), meta, "bold", size=11.5, color=INK, caps=True,
                spacing=0.4)
        bullets(ctx, box, job["bullets"], size=12.5, color=INK, line=1.5)

    if r["skills"]:
        box = row()
        # a 1px black box, 14/16/16 padding, the skills in two columns
        inner = block(ctx, box, T, border={e: (1, INK) for e in ("top", "bottom", "start", "end")},
                      pad=(14, 16, 16, 16))
        big(inner, t("Technical Skills"), 12, size=29)
        col = (T - 32 - 24) / 2
        skills = r["skills"]
        rows = (len(skills) + 1) // 2
        tbl = inner.table([tw(col + 24), tw(col)], rows=rows)
        for i, sk in enumerate(skills):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 24 if i % 2 == 0 else 0))
            # Word sets each name + bar row ~2px taller than the PDF (measured,
            # run 6): the gap between rows gives it back
            cb = Box(ctx, cell, 0, pad_top=6 if i >= 2 else 0)
            p = cb.p(tabs=[(col, "end", None)])
            run(ctx, p, sk["name"], size=11.5, color=INK)
            if rated(sk):
                pct, label = skill_pct(sk)
                run(ctx, p, "\t", size=10)
                run(ctx, p, label, "bold", size=10, color=INK)
                bar(ctx, cb, pct, col, on=INK, off=TRACK, height=7, before=4)
            cb.finish()
        if len(skills) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()
        inner.finish()

    for j, ed in enumerate(r["education"]):
        box = row() if j == 0 else page.main_row(pad_top=9)
        if j == 0:
            big(box, t("Education"), 10)
        run(ctx, box.p(), ed["degree"], H, size=15, color=INK, caps=True, spacing=0.2)
        meta = joined([ed["school"], date_range(ed["start"], ed["end"])], " · ")
        if meta:
            run(ctx, box.p(), meta, "bold", size=11.5, color=INK, caps=True, spacing=0.4)
        if ed["gpa"]:
            run(ctx, box.p(), f"{t('GPA')} {ed['gpa']}", "bold", size=11.5, color=INK)

    if r["recognition"]:
        box = row()
        big(box, t("Recognition"), 10)
        for i, rec in enumerate(r["recognition"]):
            p = box.p(before=6 if i else 0)
            run(ctx, p, rec["title"], H, size=12.5, color=INK, caps=True, spacing=0.2)
            if rec["detail"]:
                run(ctx, p, " — " + rec["detail"], size=12.5, color=INK)
    page.finish()
