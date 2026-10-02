"""modern-t24 — Charcoal & Yellow: a #F2F2F2 page frame (24px) holding an inset
charcoal rail - round grey photo, yellow section bars (Contact, Summary,
Education, Languages, Tools), light education cards with a stacked date,
languages with the level in yellow - and a main column with a caps name, a
tracked caps title, stats between rules, black section bars, a dated
timeline (date column, black rail, black node), a ruled 3-column grid of
skill RINGS (grey arc on a yellow track, the percent as text) and two-column
certifications. From modern/t24.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, fmt_cell, page_rects, photo_run, pt, rated, ring_anchored, run,
    skill_pct, tw, vml_oval,
)
from .common import SidebarPage, Stack, block, bullets, joined, single_px, text_px

FRAME, RAIL, YELLOW, INK, CARD = "F2F2F2", "4A4C4A", "FFD633", "1A1A1A", "DFDEDD"
LEVEL, MUTED, RULE = "EEC300", "555555", "D9D9D9"
PAD, SIDE_W, GAP = 24, 280, 24


@design("modern-t24")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(PAD))
    sec.bottom_margin = Pt(pt(PAD + 30))
    page = SidebarPage(ctx, SIDE_W, side_fill=RAIL, side_pad=(30, 26, 30, 26),
                       main_pad_x=(GAP, PAD), full_height_fill=False, ind_px=PAD)
    page_rects(ctx, [(0, 850, 0, 1100, FRAME), (PAD, SIDE_W, PAD, 1100 - 2 * PAD, RAIL)])
    side = page.side
    W = SIDE_W - 52
    photo_run(ctx, side.p(align="center"), size_px=150, placeholder="9F9F9E")
    heads = []

    def bar(b, label, fill, color, spacing, width, before=0, after=0):
        if before:
            b.pad_top += before
        bb = block(ctx, b, width, fill=fill, pad=(9, 22, 9, 22))
        run(ctx, bb.p(), label, "heading", size=15, color=color, spacing=spacing)
        bb.finish()
        if after:
            b.pad_top += after

    def section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row()
            if i == 0:
                b.pad_top = 16
                bar(b, label, YELLOW, INK, 0.4, W, after=16)
                heads.append(next(b.c._tc.iter("{http://schemas.openxmlformats.org/"
                                               "wordprocessingml/2006/main}p")))
            write(b, i, it)
        st.done()

    def lines(line, size):
        def w(b, i, s):
            run(ctx, b.p(line=line, ind_start=4, ind_end=4), s, size=size, color="FFFFFF")
        return w

    c = r["contact"]
    contact = [x for x in (c["phone"], c["email"], c["address"], c["site"]) if x]
    contact += [s.get("label") for s in c["social"] if s.get("label")]
    section(t("Contact"), contact, lines(1.75, 12.5))
    section(t("Summary"), [r["summary"]] if r["summary"] else [], lines(1.6, 12))

    def education(b, i, ed):
        if i:
            b.pad_top += 10
        card = block(ctx, b, W, fill=CARD, pad=(12, 14, 12, 14))
        dates = [x for x in (ed["start"], "—" if ed["start"] and ed["end"] else "", ed["end"])
                 if x]
        # the date column is as wide as its widest line (flex-shrink:0) + the
        # 12px gap - a fixed 44px set the degree ~6px late beside "2014"
        # (+3px spare). Arabic keeps 44px: the digits' estimate in the Arabic
        # bold face ran short and "2013" wrapped (real Word, run 4)
        dw = (max(text_px(ctx, "bold", x, 11.5) for x in dates) + 15) if dates else 1
        if ctx.rtl and dates:
            dw = 44
        tbl = card.table([tw(dw), tw(W - 28 - dw)])
        d, txt = tbl.rows[0].cells
        fmt_cell(ctx, d, pad=(0, 0, 0, 12 if dates else 0))
        db = Box(ctx, d, 0)
        for x in dates:
            run(ctx, db.p(line=1.4), x, "bold", size=11.5, color=INK)
        db.finish()
        tb = Box(ctx, txt, 0)
        run(ctx, tb.p(line=1.4), ed["degree"], "bold", size=11.5, color=INK)
        for v in (ed["school"], f"{t('GPA')} {ed['gpa']}" if ed["gpa"] else ""):
            if v:
                run(ctx, tb.p(line=1.4), v, size=11.5, color="666666")
        tb.finish()
        card.finish()
    section(t("Education"), r["education"], education)

    def language(b, i, lg):
        p = b.p(before=7 if i else 0, ind_start=4, tabs=[(W, "end", None)])
        run(ctx, p, lg["name"], size=12, color="FFFFFF")
        if lg["level"]:
            run(ctx, p, "\t", size=12)
            run(ctx, p, lg["level"], "bold", size=12, color=LEVEL)
    section(t("Languages"), r["languages"], language)
    section(t("Tools"), [" · ".join(r["tools"])] if r["tools"] else [], lines(1.55, 12))
    page.fit_side(heads)

    # ---- main column
    T = page.main_text_px
    top = page.main_row(pad_top=6, pad_x=(GAP + 6, PAD + 6))
    run(ctx, top.p(line=0.98), r["name"], "name", size=50, color=INK, caps=True, spacing=-1)
    if r["title"]:
        run(ctx, top.p(before=8), r["title"], size=17, color="333333", caps=True, spacing=1)
    if r["achievements"]:
        box = page.main_row(pad_top=10)
        ach = [a for a in r["achievements"] if a["metric"]]
        n = max(1, len(ach))
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, ach):
            fmt_cell(ctx, cell, pad=(0, 6, 0, 6))
            cb = Box(ctx, cell, 0, pad_top=13, pad_bottom=13)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=25, color=INK)
            run(ctx, cb.p(align="center", before=5), a["label"], "bold", size=9, color=MUTED,
                spacing=1, caps=True)
            cb.finish()

    H = "role" if ctx.rtl else "bold"
    node = [0]
    for j, job in enumerate(r["experience"]):
        box = page.main_row(pad_top=10 if j == 0 else 14)
        if j == 0:
            bar(box, t("Professional Experience"), INK, "FFFFFF", 1, T, after=4)
        tbl = box.table([tw(6 + 52 + 16), tw(T - 74)])
        d, body = tbl.rows[0].cells
        fmt_cell(ctx, d, pad=(0, 6, 0, 16))
        fmt_cell(ctx, body, pad=(0, 16, 0, 6), borders={"start": (2, INK)})
        db = Box(ctx, d, 0)
        for x in [x for x in (job["start"], "—" if job["start"] and job["end"] else "",
                              job["end"]) if x]:
            run(ctx, db.p(align="end", line=1.4), x, size=11.5, color="333333")
        db.finish()
        bb = Box(ctx, body, 0)
        p = bb.p()
        node[0] += 1
        col_w = T - 74 - 22
        x = (col_w + 16 - 6) if ctx.rtl else (-16 - 6)
        vml_oval(ctx, p, x_pt=pt(x), y_pt=0, d_pt=pt(10), fill=INK, stroke=None,
                 n=200 + node[0])
        run(ctx, p, job["role"], H, size=14, color=INK)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, bb.p(after=4), meta, size=12, color=MUTED)
        bullets(ctx, bb, job["bullets"], size=11.5, color="333333", line=1.5)
        bb.finish()

    if r["skills"]:
        skills = r["skills"]
        G = T - 8                                   # margin 6px 4px 0
        col = G / 3
        for rr in range((len(skills) + 2) // 3):
            box = page.main_row(pad_top=10 if rr == 0 else 0)
            if rr == 0:
                bar(box, t("Creative & Technical Skills"), INK, "FFFFFF", 1, T, after=6)
            tbl = box.table([tw(col)] * 3, ind=tw(4))
            for k in range(3):
                cell = tbl.rows[0].cells[k]
                borders = {"end": (1, RULE), "bottom": (1, RULE)}
                if k == 0:
                    borders["start"] = (1, RULE)
                if rr == 0:
                    borders["top"] = (1, RULE)
                fmt_cell(ctx, cell, pad=(0, 14, 0, 14), borders=borders)
                cb = Box(ctx, cell, 0, pad_top=9, pad_bottom=9)
                i = rr * 3 + k
                if i < len(skills):
                    sk = skills[i]
                    if rated(sk):
                        pct, _ = skill_pct(sk)
                        line = single_px(ctx, "bold", 14)
                        pad = (66 - line) / 2
                        p = cb.p(align="center", before=pad, after=pad + 7)
                        run(ctx, p, f"{round(pct)}%", "bold", size=14, color=INK)
                        ring_anchored(p, x_pt=pt((col - 28 - 66) / 2), y_pt=pt(9), d_px=66,
                                      width_px=10, pct=pct, on=RAIL, off=YELLOW)
                    run(ctx, cb.p(align="center", line=1.3, ind_start=-8, ind_end=-8),
                        sk["name"], "bold", size=12.5, color=INK)
                    if sk["level"]:
                        run(ctx, cb.p(align="center"), sk["level"], size=10, color="666666")
                cb.finish()

    if r["recognition"]:
        box = page.main_row(pad_top=10)
        bar(box, t("Certifications"), INK, "FFFFFF", 1, T, after=4)
        recs = r["recognition"]
        col = (T - 12 - 26) / 2
        tbl = box.table([tw(col + 26 + 6), tw(col + 6)], rows=(len(recs) + 1) // 2)
        for i, rec in enumerate(recs):
            cell = tbl.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 6 if i % 2 == 0 else 0, 0, 26 if i % 2 == 0 else 6))
            cb = Box(ctx, cell, 0, pad_top=8 if i >= 2 else 0)
            run(ctx, cb.p(), rec["title"], "bold", size=13, color=INK)
            if rec["detail"]:
                run(ctx, cb.p(), rec["detail"], size=11.5, color=MUTED)
            cb.finish()
        if len(recs) % 2:
            Box(ctx, tbl.rows[-1].cells[1], 0).finish()
    page.finish()
