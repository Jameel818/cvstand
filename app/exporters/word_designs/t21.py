"""modern-t21 — Lime & Forest cards: a rounded lime header card (a ringed round
photo at its start, the name and title end-aligned, a dark rounded contact bar
with up to four items spread across it), a rounded forest side card (lime
pills over About Me, dot-row Skills, Tools, Languages at its foot) and a main
column of lime pills over entries on a grey start rail (a small line above a
bold green line, one paragraph), closed by a rounded forest stats card at the
foot. From modern/t21.j2.

The side card ends 24px above the page foot, rounded, as the PDF's does,
on the CV AND the cover letter: a page-anchored rounded card behind the side
cell (side_card) carries it below the cell, whatever the column holds."""
from __future__ import annotations

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, dots_shape, fmt_cell, fmt_table, photo_run, pt, run, tiny, tw,
)
from .common import (
    SidebarPage, Stack, date_range, joined, round_corners, rounded_block, text_px,
)

LIME, FOREST, PAGE, INK, GREY = "E1F04A", "013F32", "FDFDFD", "161616", "4A4A4A"
SOFT, MUTED, DOT_OFF, RAIL = "E8EDEA", "A9C0B8", "2A5C4E", "D8D8D8"
PAD, SIDE_W, GAP = 24, 300, 24
# What the rounded corners are masked with: Word's page, which is WHITE - the
# design draws no page fill (full_height_fill=False). The PDF's page is
# #FDFDFD; masks in that colour showed in Word as faint boxes around every
# lime pill and the stats card (user's .docx, 2026-11-18). Text that the PDF
# draws in #FDFDFD (the contact bar) keeps PAGE.
WORD_PAGE = "FFFFFF"
#: where the side card's cell starts on the page in real Word (px; 254-255
#: on both papers, both languages, CV and letter - the PDF's is 252, as the
#: header card is a fixed 212px). The page card starts one corner radius
#: lower: above that the cell's own fill and its corner masks draw the card.
SIDE_TOP_PX = 254 + 18


@design("modern-t21")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(PAD))
    # the PDF cards end 24px above the page foot; 6px spare for the tiny
    # trailing paragraph and rounding (was 24: the cards stopped ~22px short)
    sec.bottom_margin = Pt(pt(PAD + 6))
    H = "role" if ctx.rtl else "body"

    # ---- the header card (802 x 212, radius 18)
    head = ctx.doc.add_table(rows=1, cols=1)
    fmt_table(head, [tw(850 - 2 * PAD)], ind=tw(PAD))
    hcell = head.rows[0].cells[0]
    fmt_cell(ctx, hcell, fill=LIME, pad=(0, 0, 0, 0))
    # a tiny first paragraph ABOVE the inner table: the card's top corner
    # masks hang on the cell's first paragraph, which was the one after the
    # table - they drew as stray lime wedges at the card's foot (run 7)
    hb = Box(ctx, hcell, tw(850 - 2 * PAD), pad_top=0.01)
    # the name column runs to the card's edge; its 34px end padding is the
    # cell's (it was subtracted twice: the name ended 34px short of the PDF's)
    inner = hb.table([tw(34 + 118 + 26), tw(850 - 2 * PAD - 178)])
    pcell, ncell = inner.rows[0].cells
    fmt_cell(ctx, pcell, valign="bottom", pad=(0, 34, 0, 26))
    fmt_cell(ctx, ncell, valign="center", pad=(0, 0, 0, 34))
    # the photo's line runs ~6px taller than the picture in Word: 12, not 18
    # (the contact bar sat 6px low - measured, run 6). The PDF's 8px under
    # the photo goes above it here (20 = 12 + 8, after 0): the picture sits at
    # its line's top, so with the 8 below it the photo drew 9px higher than
    # the PDF's (feature/word-audit, measured); the cell keeps its height
    pb = Box(ctx, pcell, 0, pad_top=20)
    photo_run(ctx, pb.p(line=1.0, after=0), size_px=118, ring_px=5, ring=FOREST,
              placeholder="D8D8D8")
    pb.finish()
    nb = Box(ctx, ncell, 0)
    run(ctx, nb.p(align="end", line=1.05), r["name"], "name", size=44, color=FOREST)
    if r["title"]:
        run(ctx, nb.p(align="end", before=2), r["title"], size=18, color=FOREST)
    nb.finish()
    c = r["contact"]
    bits = [x for x in (c["site"], c["email"], c["phone"], c["address"]) if x]
    bits += [s.get("label") for s in c["social"] if s.get("label")]
    bits = bits[:4]
    if bits:
        hb.pad_top = 10
        bar = rounded_block(ctx, hb, 850 - 2 * PAD - 36, fill=FOREST, bg=LIME, radius=23,
                            pad=(0, 32, 0, 32))
        n = len(bits)
        bw = 850 - 2 * PAD - 36 - 64
        size = 13
        # space-between: each item its natural width, the rest shared as gaps
        nat = [text_px(ctx, "bold", b, size, 0.6) + 4 for b in bits]
        extra = max(0.0, bw - sum(nat)) / n
        bt = bar.table([tw(w + extra) for w in nat])
        for k, (cell, b) in enumerate(zip(bt.rows[0].cells, bits)):
            al = "start" if k == 0 else ("end" if k == n - 1 else "center")
            fmt_cell(ctx, cell, valign="center")
            cb = Box(ctx, cell, 0, pad_top=13, pad_bottom=13)
            run(ctx, cb.p(align=al), b, "bold", size=size, color=PAGE, spacing=0.6)
            cb.finish()
        bar.finish_round()
        # the bar sits 18px in from the card's sides: indent its table
        tblpr = bar.c._tc.getparent().getparent()
        from ..docx_design import fmt_table as _ft  # noqa: F401
        from docx.oxml.ns import qn
        ind = tblpr.find(qn("w:tblPr") + "/" + qn("w:tblInd"))
        if ind is not None:
            ind.set(qn("w:w"), str(tw(18)))
        hb.pad_top = 18
    hb.finish()
    round_corners(ctx, hb, 850 - 2 * PAD, 18, WORD_PAGE, 0)
    spacer = ctx.doc.add_paragraph()
    tiny(spacer, before_px=16)

    # ---- the columns
    page = SidebarPage(ctx, SIDE_W, side_fill=FOREST, side_pad=(24, 26, 24, 24),
                       main_pad_x=(GAP, PAD), full_height_fill=False, ind_px=PAD)
    side_card(ctx)
    side = page.side
    W = SIDE_W - 50

    def pill(b, label, size, py, px, after, bgc):
        w = text_px(ctx, "heading", label, size, 0.5) + 2 * px + 4
        blk = rounded_block(ctx, b, w, fill=LIME, bg=bgc, radius=99, pad=(py, px, py, px))
        run(ctx, blk.p(), label, "heading", size=size, color=FOREST, spacing=0.5)
        blk.finish_round()
        b.pad_top = after

    heads = []

    def section(label, items, write, after=12, gap=18):
        if not items:
            return None
        st = Stack(ctx, side, W)
        first = None
        for i, it in enumerate(items):
            b = st.row()
            if i == 0:
                if heads:
                    b.pad_top = gap
                pill(b, label, 14, 6, 18, after, FOREST)
                first = next(b.c._tc.iter("{http://schemas.openxmlformats.org/"
                                          "wordprocessingml/2006/main}p"))
                heads.append(first)
            write(b, i, it)
        st.done()
        return first

    section(t("About Me"), [r["summary"]] if r["summary"] else [],
            lambda b, i, s: run(ctx, b.p(line=1.7), s, size=12, color=SOFT))

    def skill(b, i, sk):
        p = b.p(before=11 if i else 0, tabs=[(W, "end", None)])
        run(ctx, p, sk["name"], "bold", size=12.5, color="FFFFFF")
        if sk["level"]:
            run(ctx, p, "\t", size=10.5)
            run(ctx, p, sk["level"], size=10.5, color=MUTED)
            dots_shape(ctx, b.p(before=5), sk["dots"], sk["dot_total"], on=LIME, off=DOT_OFF,
                       d=9, gap=5)
    section(t("Skills"), r["skills"], skill)
    section(t("Tools"), [" · ".join(r["tools"])] if r["tools"] else [],
            lambda b, i, s: run(ctx, b.p(line=1.7), s, size=12, color=SOFT), after=10)
    lang = section(t("Languages"), [joined([x["name"], x["level"]], " — ")
                                    for x in r["languages"]],
                   lambda b, i, s: run(ctx, b.p(line=1.7), s, size=12, color=SOFT), after=10)
    if lang is not None:
        page.spread_side([lang], reserve_pt=16)     # margin-top:auto in the PDF
    # the card's top corners
    round_corners_top = True
    if round_corners_top:
        from .common import corner_mask
        first_p = next(side.c._tc.iter("{http://schemas.openxmlformats.org/"
                                       "wordprocessingml/2006/main}p"))
        from docx.text.paragraph import Paragraph
        fp = Paragraph(first_p, side.c)
        left_pad = 24 if ctx.rtl else 26
        for key, x in (("tl", -left_pad), ("tr", SIDE_W - left_pad - 18)):
            corner_mask(fp, key, x_pt=pt(x), y_pt=0, r_pt=pt(18), fill=WORD_PAGE)

    # ---- main column
    T = page.main_text_px
    gap = [0]

    def rpill(box, label):
        pill(box, label, 15, 7, 22, 14, WORD_PAGE)

    def rail_entry(box, top_line, org, detail, para, gap_px=0):
        # ONE grey rail per group, as the PDF's (one border on the list): the
        # 14px gap between entries is INSIDE the bordered cell, as its first
        # paragraph's space before (the t22 pattern). It used to be a spacer
        # paragraph between the rows, outside any border: the rail broke into
        # one segment per entry (user's .docx, 2026-11-18).
        tbl = box.table([tw(T)])
        cell = tbl.rows[0].cells[0]
        fmt_cell(ctx, cell, pad=(0, 18, 0, 0), borders={"start": (2, RAIL)})
        eb = Box(ctx, cell, 0, pad_top=gap_px)
        if top_line:
            run(ctx, eb.p(), top_line, size=12.5, color=GREY)
        if org:
            run(ctx, eb.p(), org, H if H == "role" else "heading", size=14, color=FOREST)
        if detail:
            run(ctx, eb.p(), detail, size=12, color=GREY)
        if para:
            run(ctx, eb.p(before=3, line=1.6), para, size=12, color=INK)
        eb.finish()

    def group(label, entries, make):
        for j, e in enumerate(entries):
            box = page.main_row(pad_top=(gap[0] if j == 0 else 0))
            if j == 0:
                rpill(box, label)
                gap[0] = 18
            rail_entry(box, *make(e), gap_px=0 if j == 0 else 14)

    group(t("Education"), r["education"], lambda ed: (
        ed["degree"], ed["school"],
        joined([" ".join(ed["bullets"]), f"{t('GPA')} {ed['gpa']}" if ed["gpa"] else "",
                date_range(ed["start"], ed["end"])], " · "), ""))
    group(t("Work Experience"), r["experience"], lambda job: (
        joined([job["role"], date_range(job["start"], job["end"])], " · "),
        joined([job["company"], job["location"]], " · "), "", " ".join(job["bullets"])))
    group(t("Certifications"), r["recognition"], lambda rec: (
        "", rec["title"], rec["detail"], ""))

    ach = [a for a in r["achievements"] if a["metric"]]
    if ach:
        box = page.main_row(pad_top=18)
        # margin-top:auto in the PDF. In Arabic the default 24pt reserve left
        # the foot cards ~18px short of the PDF's; English needs all of it (10
        # spilled the stats card onto page 2) - measured in Word, run 6
        page.push_to_bottom(box, reserve_pt=10.0 if ctx.rtl else 24.0)
        card = rounded_block(ctx, box, T, fill=FOREST, bg=WORD_PAGE, radius=18,
                             pad=(16, 26, 16, 26))
        n = len(ach)
        st = card.table([tw(T - 52) // n] * n)
        for k, (cell, a) in enumerate(zip(st.rows[0].cells, ach)):
            fmt_cell(ctx, cell, pad=(0, 0, 0, 12 if k < n - 1 else 0))
            cb = Box(ctx, cell, 0)
            # number and label centred in the chip, as in the PDF (user, 2026-10-08)
            run(ctx, cb.p(align="center"), a["metric"], "metric", size=23, color=LIME)
            run(ctx, cb.p(align="center", before=3), a["label"], "bold", size=9, color=MUTED, spacing=1,
                caps=True)
            cb.finish()
        card.finish_round()
    page.finish()


def side_card(ctx: Ctx) -> None:
    """The side card below its cell: a rounded FOREST rectangle on the page,
    behind the text, from SIDE_TOP_PX to 24px above the page foot - the PDF's
    card (bottom: 24px, radius 18). The cell's shading ended where its
    content did: the card stopped ~24px short on the CV, cutting under the
    Languages lines, and at ~1/3 to 2/3 of the page on the cover letter,
    whose side column holds no content (user's .docx, 2026-11-24). Drawn in
    the header (every page: Word section = one CV or one letter page) and
    copied to the body by docx_design.body_page_shapes."""
    from docx.oxml import parse_xml
    from ..docx_design import page_h_px
    from ..docx_dml import Sp, anchored_run
    top = SIDE_TOP_PX
    h = page_h_px() - PAD - top
    x = (850 - PAD - SIDE_W) if ctx.rtl else PAD
    arc = 18 / (min(SIDE_W, h) / 2)
    X, Y, W, Hh = pt(x), pt(top), pt(SIDE_W), pt(h)
    z = 40 - 251658240
    vml = (f'<v:roundrect id="cvstand_sidecard" o:allowincell="f" '
           f'style="position:absolute;margin-left:{X:.2f}pt;margin-top:{Y:.2f}pt;'
           f'width:{W:.2f}pt;height:{Hh:.2f}pt;z-index:{z};'
           f'mso-position-horizontal-relative:page;mso-position-vertical-relative:page" '
           f'arcsize="{arc:.3f}" fillcolor="#{FOREST}" stroked="f"/>')
    sp = Sp("roundRect", X, Y, W, Hh, fill=FOREST, radius=arc)
    header = ctx.doc.sections[0].header
    header.is_linked_to_previous = False
    para = header.paragraphs[0]
    para.paragraph_format.space_after = 0
    para._p.append(parse_xml(anchored_run("cvstand_sidecard", sp, vml, rel_h="page",
                                          rel_v="page", z=z, in_cell=False)))
