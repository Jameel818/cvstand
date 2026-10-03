"""modern-t22 — The RESUME rail: a giant orange "RESUME" set vertically down a
215px strip at the start edge (bottom-to-top; top-to-bottom in Arabic, as the
PDF's RTL rule turns it), then a white column: a caps name and tracked title,
ABOUT ME with a trailing 2px rule, orange stats between hairlines, and two
columns - Work Experience and Education on a 2px rail with hollow nodes
("Role (dates)", orange company, one paragraph) | end-aligned contact under
big labels and a 2-up grid of skill RINGS. From modern/t22.j2.

The rail word is a picture anchored to the page in the header (fixed artwork,
on every page; see _rail)."""
from __future__ import annotations

from pathlib import Path

from docx.shared import Pt

from ..docx_design import (
    Box, Ctx, cant_split, design, fmt_cell, header_picture, pt, rated, ring_anchored, rule_heading, run,
    skill_pct, tw, vml_oval,
)
from .common import ColumnPage, Stack, joined, single_px

ORANGE, INK, BODY, GREY, RULE = "CB3500", "111111", "333333", "444444", "D8D8D8"
RAIL_W, PAD_T, GAP = 215, 40, 34
RAILS = Path(__file__).resolve().parents[2] / "static" / "rails"


def _rail(ctx: Ctx) -> None:
    """The vertical rail word: a PICTURE anchored to the page in the header,
    behind the text, at the PDF rail's exact place and size (the 215px strip,
    full page height). Fixed artwork by user requirement (run 6): it never
    follows the Fonts panel, cannot be edited as text, cannot wrap or break,
    and looks the same in Word, LibreOffice and Google Docs - a text box
    showed horizontal and broken into lines in LibreOffice. The picture is the
    template's own rail, rendered by tools/build_t22_rail.py at 300 dpi."""
    # (no white page fill: Word stacks it IN FRONT of the picture - measured
    # with Shapes.ZOrderPosition - and the page is white anyway)
    lang = "ar" if ctx.rtl else "en"
    x = 850 - RAIL_W if ctx.rtl else 0          # physical: the start edge
    header_picture(ctx, RAILS / f"modern-t22-{lang}.png", x_pt=pt(x), y_pt=0,
                   w_pt=pt(RAIL_W), h_pt=pt(1100), name="cvstand_rail")


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

    def head(box, label, width, size=24, after=14, keep=False):
        rule_heading(ctx, box, label, width_px=width, size=size, color=INK, rule=INK,
                     spacing=1, gap=14, rule_px=2, after=after, keep=keep)

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

    def rail(box, label, entries):
        # one unbreakable row per entry, the heading in the first entry's row
        # (Stack): the columns break across pages in a long CV, and Word
        # ignores keep-with-next in a cell that breaks. Each entry draws its
        # stretch of the 2px rail as its own cell border, gap included, so
        # the rail stays continuous.
        stack = Stack(ctx, box, LEFT)
        for i, (title, sub, text, lh) in enumerate(entries):
            sb = stack.row()
            if i == 0:
                head(sb, label, LEFT)
            inner = sb.table([tw(LEFT)])
            cell = inner.rows[0].cells[0]
            fmt_cell(ctx, cell, pad=(0, 20, 0, 0), borders={"start": (2, INK)})
            eb = Box(ctx, cell, 0)
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
        stack.done()

    def paren(x):
        d = joined([x["start"], x["end"]], "–")
        return f" ({d})" if d else ""

    # the two columns may break across pages (a long CV): kept whole, the
    # block jumped to page 2 and left page 1 with only the header
    box = page.main_row(pad_top=20, split=True)
    tbl = box.table([tw(LEFT + GAP), tw(RIGHT)])
    lc, rc = tbl.rows[0].cells
    fmt_cell(ctx, lc, pad=(0, 0, 0, GAP))
    lb = Box(ctx, lc, 0)
    if r["experience"]:
        rail(lb, t("WORK EXPERIENCE"), [(j["role"] + paren(j), joined([j["company"], j["location"]], " · "),
                   " ".join(j["bullets"]), 1.55) for j in r["experience"]])
    if r["education"]:
        if r["experience"]:
            lb.pad_top = 24
        rail(lb, t("EDUCATION"), [(e["degree"] + paren(e), e["school"], " ".join(e["bullets"]), 1.5)
                  for e in r["education"]])
    lb.finish()

    rb0 = Box(ctx, rc, 0)
    stack = Stack(ctx, rb0, RIGHT)       # each label stays with what it labels
    c = r["contact"]
    k = 0
    for label, value in ((t("Address"), c["address"]), (t("Phone"), c["phone"]),
                         (t("Email"), c["email"]), (t("Web"), c["site"])):
        if value:
            rb = stack.row()
            run(ctx, rb.p(align="end", before=18 if k else 0), label, "heading", size=22,
                color=INK)
            run(ctx, rb.p(align="end", before=6, line=1.6), value, size=11.5, color=GREY)
            k += 1
    skills = r["skills"]
    if skills:
        col = (RIGHT - 4) / 2
        # one unbreakable unit per pair of rings (a ring never leaves its
        # label behind), the heading in the first: the grid may continue on
        # the next page instead of moving there whole
        for r0 in range(0, len(skills), 2):
            rb = stack.row()
            if r0 == 0:
                run(ctx, rb.p(align="end", before=18 if k else 0, after=14), t("Skills"),
                    "heading", size=22, color=INK)
            st = rb.table([tw(col + 4), tw(col)])
            pair = skills[r0:r0 + 2]
            for j, sk in enumerate(pair):
                i = r0 + j
                cell = st.rows[0].cells[j]
                fmt_cell(ctx, cell, pad=(0, 0, 0, 4 if j == 0 else 0))
                cb = Box(ctx, cell, 0, pad_top=16 if i >= 2 else 0)
                if rated(sk):
                    pct, _ = skill_pct(sk)
                    line = single_px(ctx, "bold", 13)
                    pd = (66 - line) / 2
                    p = cb.p(align="center", before=pd, after=pd + 7)
                    run(ctx, p, f"{round(pct)}%", "bold", size=13, color=INK)
                    ring_anchored(p, x_pt=pt((col - 66) / 2), y_pt=pt(16 if i >= 2 else 0),
                                  d_px=66, width_px=10, pct=pct, on=INK, off=RULE)
                run(ctx, cb.p(align="center", line=1.25), sk["name"], "bold", size=9.5,
                    color=INK)
                if sk["level"]:
                    run(ctx, cb.p(align="center"), sk["level"], "bold", size=8.5, color="5F5F5F")
                cb.finish()
            if len(pair) == 1:
                Box(ctx, st.rows[0].cells[1], 0).finish()
    stack.done()
    rb0.finish()
    page.finish()
