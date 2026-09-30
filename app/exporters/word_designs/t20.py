"""modern-t20 — Beige rail, maroon accents: a square portrait block, light
tracked headings, labelled contact (tiny maroon kickers), dot rows under the
skill names with the level right, bold maroon language levels; a centred
tracked main heading, caps job titles with maroon dates right, and a timeline
down the END edge with maroon nodes. From modern/t20.j2."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import Box, Ctx, design, dots, fmt_cell, photo_run, pt, run, tiny, tw, vml_oval
from .common import SidebarPage, Stack, bullets, date_range, joined, node_x

BEIGE, INK, MAROON, DARK, MUTED, BODY, RULE = ("EDEBDD", "1B1717", "810100", "630000",
                                              "4A453C", "33302B", "D9D5C4")
SIDE_PX = 322


@design("modern-t20")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(0.1)
    sec.bottom_margin = Pt(pt(30))
    page = SidebarPage(ctx, SIDE_PX, side_fill=BEIGE, side_pad=(32, 30, 32, 30),
                       main_pad_x=(38, 38))
    side = page.side
    W = SIDE_PX - 60
    p = side.p()
    photo_run(ctx, p, size_px=W, height_px=70 if ctx.rtl else 214, shape="rect", placeholder="DCD9C8",
              ring_px=1, ring="CFCBB6")

    def section(label, items, write):
        if not items:
            return
        st = Stack(ctx, side, W)
        for i, it in enumerate(items):
            b = st.row(pad_top=13 if i == 0 else 0)
            if i == 0:
                run(ctx, b.p(after=8), label, "heading", size=21, color=INK, spacing=3)  # after 12px in the PDF
            write(b, i, it)
        st.done()

    def contact(b, i, item):
        run(ctx, b.p(before=9 if i else 0), item[0], "bold", size=9.5, color=MAROON,
            spacing=1.5)
        run(ctx, b.p(), item[1], size=12, color=INK)

    def skill(b, i, sk):
        p = b.p(before=7 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, sk["name"], "bold", size=12.5, color=INK)
        if sk["level"]:
            run(ctx, p, "\t", size=10.5)
            run(ctx, p, sk["level"], size=10.5, color="5C5C66")
            dots(ctx, b.p(before=2), sk["dots"], sk["dot_total"], on=MAROON, off="B3AE99",
                 size=12, gap=1.5)

    def language(b, i, lg):
        p = b.p(before=6 if i else 0)
        run(ctx, p, lg["name"], size=12, color=INK)
        if lg["level"]:
            run(ctx, p, " — ", size=12, color=INK)
            run(ctx, p, lg["level"], "bold", size=12, color=DARK)

    def tools(b, i, s):
        run(ctx, b.p(line=1.6), s, size=12, color=INK)

    def cert(b, i, rec):
        run(ctx, b.p(before=10 if i else 0), rec["title"], "bold", size=12.5, color=INK)
        if rec["detail"]:
            run(ctx, b.p(), rec["detail"], size=11.5, color=MUTED)

    def ref(b, i, rf):
        run(ctx, b.p(before=12 if i else 0), rf["name"], "bold", size=13, color=INK)
        for v in (rf["title"], rf["phone"], rf["email"]):
            if v:
                run(ctx, b.p(), v, size=11.5, color=MUTED)

    c = r["contact"]
    items = [(t("EMAIL"), c["email"]), (t("PHONE"), c["phone"]), (t("LOCATION"), c["address"]),
             (t("PORTFOLIO"), c["site"])]
    items += [(t("LINK"), s.get("label") or "") for s in c["social"]]
    section(t("CONTACT"), [x for x in items if x[1]], contact)
    section(t("EXPERTISE"), r["skills"], skill)
    section(t("LANGUAGES"), r["languages"], language)
    section(t("TOOLS"), [" · ".join(r["tools"])] if r["tools"] else [], tools)
    section(t("CERTIFICATIONS"), r["recognition"], cert)
    section(t("REFERENCES"), r["references"], ref)

    # ---- main column
    T = page.main_text_px
    top = page.main_row(pad_top=40)
    run(ctx, top.p(line=1.0), r["name"], "name", size=42, color=INK, spacing=0.5)
    if r["title"]:
        run(ctx, top.p(before=10), r["title"], "bold", size=18, color=MAROON)
    if r["summary"]:
        run(ctx, top.p(before=26, align="both", line=1.7), r["summary"], size=12.5, color=BODY)
    if r["achievements"]:
        box = page.main_row(pad_top=26)
        n = len(r["achievements"])
        tbl = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, a in zip(tbl.rows[0].cells, r["achievements"]):
            fmt_cell(ctx, cell, pad=(0, 4, 0, 4))
            cb = Box(ctx, cell, 0, pad_top=16, pad_bottom=16)
            run(ctx, cb.p(align="center", line=1.0), a["metric"], "metric", size=25,
                color=MAROON)
            run(ctx, cb.p(align="center", before=5), a["label"], "bold", size=9, color=MUTED,
                spacing=1, caps=True)
            cb.finish()

    node = 27
    count = [0]

    def timeline(label, entries, write, rule_above):
        for j, e in enumerate(entries):
            box = page.main_row(pad_top=26 if j == 0 else 0)
            if j == 0:
                if rule_above:
                    rp = box.p()
                    tiny(rp)
                    from ..docx_design import fmt_p
                    fmt_p(ctx, rp, after=26, border={"bottom": (1, RULE, 0)})
                run(ctx, box.p(align="center", after=22), label, "heading", size=23,
                    color=INK, spacing=4)
            last = j == len(entries) - 1
            tbl = box.table([tw(T - node), tw(node)])
            body, a = tbl.rows[0].cells
            fmt_cell(ctx, body, pad=(0, 0, 0, 22), borders={"end": (2, BEIGE)})
            bb = Box(ctx, body, 0, pad_bottom=0 if last else 22)
            write(bb, e)
            bb.finish()
            count[0] += 1
            vml_oval(ctx, a.paragraphs[0], x_pt=node_x(ctx, node, "start", 11), y_pt=pt(4),
                     d_pt=pt(11), fill=MAROON, stroke=None, n=count[0])
            Box(ctx, a, 0).finish()

    def job(bb, job):
        p = bb.p(tabs=[(T - node - 22, "end", None)])
        run(ctx, p, job["role"], "role", size=14, color=INK, spacing=0.5, caps=True)
        dates = date_range(job["start"], job["end"])
        if dates:
            run(ctx, p, "\t", size=11.5)
            run(ctx, p, dates, "bold", size=11.5, color=DARK)
        meta = joined([job["company"], job["location"]], " · ")
        if meta:
            run(ctx, bb.p(before=2), meta, size=12, color=MUTED)
        bullets(ctx, bb, job["bullets"], size=11.5, color=BODY, line=1.55, before=6)

    def school(bb, ed):
        p = bb.p(tabs=[(T - node - 22, "end", None)])
        run(ctx, p, ed["school"] or ed["degree"], "role", size=13.5, color=INK, caps=True)
        dates = date_range(ed["start"], ed["end"])
        if dates:
            run(ctx, p, "\t", size=11.5)
            run(ctx, p, dates, "bold", size=11.5, color=DARK)
        if ed["school"]:
            run(ctx, bb.p(before=3), ed["degree"], size=12, color=BODY)
        if ed["gpa"]:
            run(ctx, bb.p(before=2), f"{t('GPA')} {ed['gpa']}", size=11.5, color=MUTED)

    if r["experience"]:
        timeline(t("WORK EXPERIENCE"), r["experience"], job,
                 bool(r["summary"] or r["achievements"]))
    if r["education"]:
        timeline(t("EDUCATION"), r["education"], school, bool(r["experience"]))
    page.finish()
