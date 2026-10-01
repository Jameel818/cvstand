"""modern-t22 — The RESUME rail: a giant orange "RESUME" set vertically down a
215px strip at the start edge (bottom-to-top; top-to-bottom in Arabic, as the
PDF's RTL rule turns it), then a white column: a caps name and tracked title,
ABOUT ME with a trailing 2px rule, orange stats between hairlines, and two
columns - Work Experience and Education on a 2px rail with hollow nodes
("Role (dates)", orange company, one paragraph) | end-aligned contact under
big labels and a 2-up grid of skill RINGS. From modern/t22.j2.

The rail is a text box anchored to the page in the header (editable text, on
every page); the PDF's 5px text stroke is not reproduced."""
from __future__ import annotations

from docx.oxml import parse_xml
from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, design, fmt_cell, page_rects, pt, rated, ring_anchored, rule_heading, run,
    skill_pct, tw, vml_oval,
)
from .common import ColumnPage, joined, single_px

ORANGE, INK, BODY, GREY, RULE = "CB3500", "111111", "333333", "444444", "D8D8D8"
RAIL_W, PAD_T, GAP = 215, 40, 34


def _rail(ctx: Ctx) -> None:
    """The vertical RESUME word: a page-anchored text box behind the text."""
    page_rects(ctx, [(0, 850, 0, 1100, "FFFFFF")])
    t = ctx.t
    word = t("RESUME")
    if ctx.rtl:
        size, flow, jc = 140, "top-to-bottom", "center"
        style_id = "CVRole"            # the PDF draws it in the body face (bold)
        cx = 850 - 118.5
        tdir = "tbRl"
    else:
        size, flow, jc = 214, "bottom-to-top", "left"
        style_id = "CVHeading"
        cx = 118.5
        tdir = "btLr"
    w_px, h_px = RAIL_W, 1090.0              # a little longer than the PDF's 1043.5px track
    top = 553.25 - h_px / 2
    x = cx - w_px / 2
    hp = int(round(size * 0.72 * 2))
    spacing = ""      # Word's Archivo 900 already sets wider than Chromium's
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:v="urn:schemas-microsoft-com:vml" '
          'xmlns:o="urn:schemas-microsoft-com:office:office"')
    rtl = "<w:rtl/>" if ctx.rtl else ""
    bidi = "<w:bidi/>" if ctx.rtl else ""
    xml = (
        f'<w:r {ns}><w:pict><v:rect id="cvstand_rail" o:allowincell="f" '
        f'style="position:absolute;margin-left:{pt(x):.2f}pt;margin-top:{pt(top):.2f}pt;'
        f'width:{pt(w_px):.2f}pt;height:{pt(h_px):.2f}pt;z-index:-251640000;'
        f'mso-position-horizontal-relative:page;mso-position-vertical-relative:page" '
        f'filled="f" stroked="f"><v:textbox style="mso-layout-flow-alt:{flow}" inset="0,0,0,0">'
        f'<w:txbxContent><w:p><w:pPr>{bidi}<w:spacing w:before="0" w:after="0" w:line="172" '
        f'w:lineRule="auto"/><w:jc w:val="{jc}"/><w:textDirection w:val="{tdir}"/></w:pPr>'
        f'<w:r><w:rPr><w:rStyle w:val="{style_id}"/><w:color w:val="{ORANGE}"/>{spacing}'
        f'<w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/>{rtl}</w:rPr><w:t>{word}</w:t></w:r>'
        f'</w:p></w:txbxContent></v:textbox></v:rect></w:pict></w:r>')
    para = ctx.doc.sections[0].header.paragraphs[0]
    para._p.append(parse_xml(xml))


@design("modern-t22")
def build(ctx: Ctx) -> None:
    r, t = ctx.r, ctx.t
    sec = ctx.doc.sections[0]
    sec.top_margin = Pt(pt(PAD_T))
    sec.bottom_margin = Pt(pt(PAD_T))
    _rail(ctx)
    page = ColumnPage(ctx, pad_x=(RAIL_W + 12, 44))
    T = page.main_text_px
    LEFT = (T - GAP) * 1.6 / 2.6
    RIGHT = T - GAP - LEFT
    H = "role" if ctx.rtl else "bold"

    top = page.main_row()
    run(ctx, top.p(line=0.95), r["name"], "name", size=56, color=INK, caps=True, spacing=-2)
    if r["title"]:
        run(ctx, top.p(before=6), r["title"], "bold", size=19, color=INK, caps=True, spacing=3)

    def head(box, label, width, size=24, after=14):
        rule_heading(ctx, box, label, width_px=width, size=size, color=INK, rule=INK,
                     spacing=1, gap=14, rule_px=2, after=after)

    if r["summary"]:
        box = page.main_row(pad_top=20)
        head(box, t("ABOUT ME"), T, size=26, after=10)
        run(ctx, box.p(line=1.6), r["summary"], size=12, color=BODY)
    ach = [x for x in r["achievements"] if x["metric"]]
    if ach:
        box = page.main_row(pad_top=20)
        n = len(ach)
        st = box.table([tw(T) // n] * n, borders={"top": (1, RULE), "bottom": (1, RULE)})
        for cell, x in zip(st.rows[0].cells, ach):
            fmt_cell(ctx, cell, pad=(0, 6, 0, 6))
            cb = Box(ctx, cell, 0, pad_top=14, pad_bottom=14)
            run(ctx, cb.p(align="center", line=1.0), x["metric"], "metric", size=25,
                color=ORANGE)
            run(ctx, cb.p(align="center", before=5), x["label"], "bold", size=9, color="666666",
                spacing=1, caps=True)
            cb.finish()

    node = [0]

    def rail(box, entries):
        tb = box.table([tw(LEFT)])
        cell = tb.rows[0].cells[0]
        fmt_cell(ctx, cell, pad=(0, 20, 0, 0), borders={"start": (2, INK)})
        eb = Box(ctx, cell, 0)
        for i, (title, sub, text, lh) in enumerate(entries):
            p = eb.p(before=16 if i else 0)
            node[0] += 1
            cw = LEFT - 20
            x = (cw + 20 + 1 - 7) if ctx.rtl else (-20 - 1 - 7)
            vml_oval(ctx, p, x_pt=pt(x), y_pt=pt(-2), d_pt=pt(14), fill="FFFFFF", stroke=INK,
                     weight_pt=pt(2), n=700 + node[0])
            run(ctx, p, title, H, size=14, color=INK)
            if sub:
                run(ctx, eb.p(before=2), sub, size=11.5, color=ORANGE)
            if text:
                run(ctx, eb.p(before=4, line=lh), text, size=11.5, color=GREY)
        eb.finish()

    def paren(x):
        d = joined([x["start"], x["end"]], "–")
        return f" ({d})" if d else ""

    box = page.main_row(pad_top=20)
    tbl = box.table([tw(LEFT + GAP), tw(RIGHT)])
    lc, rc = tbl.rows[0].cells
    fmt_cell(ctx, lc, pad=(0, 0, 0, GAP))
    lb = Box(ctx, lc, 0)
    if r["experience"]:
        head(lb, t("WORK EXPERIENCE"), LEFT)
        rail(lb, [(j["role"] + paren(j), joined([j["company"], j["location"]], " · "),
                   " ".join(j["bullets"]), 1.55) for j in r["experience"]])
    if r["education"]:
        if r["experience"]:
            lb.pad_top = 24
        head(lb, t("EDUCATION"), LEFT)
        rail(lb, [(e["degree"] + paren(e), e["school"], " ".join(e["bullets"]), 1.5)
                  for e in r["education"]])
    lb.finish()

    rb = Box(ctx, rc, 0)
    c = r["contact"]
    k = 0
    for label, value in ((t("Address"), c["address"]), (t("Phone"), c["phone"]),
                         (t("Email"), c["email"]), (t("Web"), c["site"])):
        if value:
            run(ctx, rb.p(align="end", before=18 if k else 0), label, "heading", size=22,
                color=INK)
            run(ctx, rb.p(align="end", before=6, line=1.6), value, size=11.5, color=GREY)
            k += 1
    skills = r["skills"]
    if skills:
        run(ctx, rb.p(align="end", before=18 if k else 0, after=14), t("Skills"), "heading",
            size=22, color=INK)
        col = (RIGHT - 4) / 2
        st = rb.table([tw(col + 4), tw(col)], rows=(len(skills) + 1) // 2)
        for i, sk in enumerate(skills):
            cell = st.rows[i // 2].cells[i % 2]
            fmt_cell(ctx, cell, pad=(0, 0, 0, 4 if i % 2 == 0 else 0))
            cb = Box(ctx, cell, 0, pad_top=16 if i >= 2 else 0)
            if rated(sk):
                pct, _ = skill_pct(sk)
                line = single_px(ctx, "bold", 13)
                pd = (66 - line) / 2
                p = cb.p(align="center", before=pd, after=pd + 7)
                run(ctx, p, f"{round(pct)}%", "bold", size=13, color=INK)
                ring_anchored(p, x_pt=pt((col - 66) / 2), y_pt=pt(16 if i >= 2 else 0), d_px=66,
                              width_px=10, pct=pct, on=INK, off=RULE)
            run(ctx, cb.p(align="center", line=1.25), sk["name"], "bold", size=9.5, color=INK)
            if sk["level"]:
                run(ctx, cb.p(align="center"), sk["level"], "bold", size=8.5, color="5F5F5F")
            cb.finish()
        if len(skills) % 2:
            Box(ctx, st.rows[-1].cells[1], 0).finish()
    rb.finish()
    page.finish()
