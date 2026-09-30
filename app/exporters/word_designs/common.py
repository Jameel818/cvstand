"""Building blocks several designs share: the sidebar page (a full-height
side column + one unbreakable row per main-column block) and small entry
helpers. Everything in template px (docx_design.PX)."""
from __future__ import annotations

from ..docx_design import (
    Box, Ctx, PAGE_W_PX, cant_split, fmt_cell, fmt_table, page_rects, tw, vmerge,
)


class SidebarPage:
    """One table: [side | main]. The side cell is ONE cell merged down every
    row; each main block is its own row that cannot split (Word honours that,
    not keep-with-next, inside tables). A last, splittable row takes whatever
    the side column holds beyond the main column, so a long side column flows
    to the next page instead of being cut."""

    def __init__(self, ctx: Ctx, side_px: float, *, side_fill=None, side_pad=(34, 28, 30, 28),
                 main_pad_x=(40, 40), full_height_fill=True, side_end=False, top_px=0.0):
        self.ctx = ctx
        self.side_w = tw(side_px)
        self.main_w = tw(PAGE_W_PX) - self.side_w
        self.side_px, self.main_px = side_px, PAGE_W_PX - side_px
        self.side_end = side_end
        self.main_pad_x = main_pad_x
        self.side_fill = side_fill
        widths = [self.main_w, self.side_w] if side_end else [self.side_w, self.main_w]
        self.tbl = ctx.doc.add_table(rows=1, cols=2)
        fmt_table(self.tbl, widths)
        self.rows = []
        side = self._side_cell(self.tbl.rows[0])
        vmerge(side, "restart")
        fmt_cell(ctx, side, fill=side_fill, pad=(0, side_pad[1], 0, side_pad[3]))
        self.side = Box(ctx, side, self.side_w - tw(side_pad[1] + side_pad[3]),
                        pad_top=side_pad[0], pad_bottom=side_pad[2])
        self._first = True
        if full_height_fill and side_fill:
            x = PAGE_W_PX - side_px if side_end else 0
            page_rects(ctx, [(x, side_px + 1, 0, 1100, side_fill)])

    def _side_cell(self, row):
        return row.cells[1] if self.side_end else row.cells[0]

    def _main_cell(self, row):
        return row.cells[0] if self.side_end else row.cells[1]

    def main_row(self, *, pad_top=0, pad_bottom=0, fill=None, pad_x=None, split=False) -> Box:
        if self._first:
            row = self.tbl.rows[0]
            self._first = False
        else:
            row = self.tbl.add_row()
            vmerge(self._side_cell(row), "continue")
            fmt_cell(self.ctx, self._side_cell(row), fill=self.side_fill)
        if not split:
            cant_split(row)
        cell = self._main_cell(row)
        px = pad_x or self.main_pad_x
        fmt_cell(self.ctx, cell, fill=fill, pad=(0, px[0], 0, px[1]))
        box = Box(self.ctx, cell, self.main_w - tw(px[0] + px[1]), pad_top=pad_top,
                  pad_bottom=pad_bottom)
        self.rows.append(box)
        return box

    @property
    def main_text_px(self) -> float:
        return self.main_px - sum(self.main_pad_x)

    def finish(self):
        tail = self.main_row(split=True)
        self.side.finish()
        for b in self.rows:
            b.finish()
        return tail


def joined(parts, sep):
    return sep.join(p for p in parts if p)


def date_range(a, b, dash=" – "):
    return f"{a}{dash if a and b else ''}{b}"


class Stack:
    """A column section as a one-column nested table, one row per entry, every
    row unbreakable, the heading in the FIRST entry's row: inside a cell that
    breaks across pages Word ignores keep-with-next, but it keeps a row that
    cannot split whole - so a heading never ends a page alone."""

    def __init__(self, ctx: Ctx, box: Box, width_px: float):
        self.ctx, self.box, self.w = ctx, box, tw(width_px)
        self.tbl = None
        self.boxes: list[Box] = []

    def row(self, pad_top: float = 0) -> Box:
        if self.tbl is None:
            self.tbl = self.box.table([self.w])
            row = self.tbl.rows[0]
        else:
            self.boxes[-1].finish()
            row = self.tbl.add_row()
        cant_split(row)
        cell = row.cells[0]
        fmt_cell(self.ctx, cell, pad=(pad_top, 0, 0, 0))
        b = Box(self.ctx, cell, self.w)
        self.boxes.append(b)
        return b

    def done(self):
        if self.boxes:
            self.boxes[-1].finish()
