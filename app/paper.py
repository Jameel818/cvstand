"""Paper size: A4 or US Letter, chosen per CV (feature/paper-size, 2026-11-17).

THE ONE SOURCE for every page dimension in the app. The preview canvas, the
PDF and the Word export all read the paper from here, so the three can never
disagree about the page they are drawing.

THE CANVAS IS ALWAYS 850px WIDE. Only the height changes:

    letter   850 x 1100px   1px = 0.72pt     612 x 792pt     12240 x 15840 twips
    a4       850 x 1202px   1px = 0.70033pt  595.28 x 841.89pt 11906 x 16838 twips

Keeping the width is what lets all 49 templates take A4 unchanged: every
width-keyed and absolutely-positioned layout (Modern t7/t8/t11/t14/t15/t18/t21)
is drawn against 850. The cost: on A4 a px prints 2.7% smaller in points.
1202px x 0.70033 = 841.80pt, 0.09pt short of the sheet, so a second page is
impossible.

WHICH PAPER A CV IS ON
    `paper` is an optional root field of the résumé. MISSING MEANS LETTER: every
    CV saved before this feature was approved on Letter and keeps that page (and
    every Letter golden stays valid). A NEW CV gets A4, or Letter when the
    browser language is en-US / en-CA (app/static/js/builder.js); the user can
    switch it in the ribbon.

THE EXPORTERS read the current paper through a ContextVar (`use()` /
`current()`) rather than an argument threaded through every helper: docx_design
and friends compute points in dozens of small functions.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class Paper:
    key: str
    w: int                  # canvas px
    h: int                  # canvas px
    pt_per_px: float        # printed points per canvas px (PDF and Word)
    w_pt: float             # the sheet, in points
    h_pt: float
    pdf_format: str         # Playwright page.pdf(format=...)
    css_size: str           # the PDF's @page size
    twips: tuple[int, int]  # Word section page size
    #: The sheet Chromium actually emits, in points. Chromium quantises the
    #: PDF page size: whatever @page says (210mm 297mm, 595.28pt 841.89pt,
    #: "A4"), its A4 comes out 594.96 x 841.92pt - measured 2026-11-17, and
    #: what Chrome's own "Save as PDF > A4" produces. 0.32pt from ISO A4, well
    #: inside ISO 216's +-2mm. Letter is exact (8.5in = 816 CSS px).
    pdf_pt: tuple[float, float] = (0.0, 0.0)

    @property
    def pdf_scale(self) -> float:
        """Chromium prints a CSS px as 0.75pt; this scales the 850px canvas
        onto the PDF sheet's width (Letter 0.96, A4 0.93327), so it is never
        wider than the sheet."""
        return (self.pdf_pt[0] or self.w_pt) / (self.w * 0.75)


LETTER = Paper("letter", 850, 1100, 0.72, 612.0, 792.0, "Letter", "8.5in 11in", (12240, 15840),
               (612.0, 792.0))
A4 = Paper("a4", 850, 1202, 595.28 / 850, 595.28, 841.89, "A4", "210mm 297mm", (11906, 16838),
           (594.96, 841.92))

PAPERS: dict[str, Paper] = {"letter": LETTER, "a4": A4}
#: What a résumé with no `paper` field is on (see the module docstring).
DEFAULT_SAVED = "letter"
#: What a fresh CV gets, unless the browser is en-US / en-CA.
DEFAULT_NEW = "a4"
LETTER_LOCALES = ("en-us", "en-ca")


def paper_key(data: dict[str, Any] | None) -> str:
    v = (data or {}).get("paper")
    v = v.strip().lower() if isinstance(v, str) else ""
    return v if v in PAPERS else DEFAULT_SAVED


def paper_of(data: dict[str, Any] | None) -> Paper:
    return PAPERS[paper_key(data)]


def default_for_locale(locale: str | None) -> str:
    """The paper a NEW CV starts on for this browser language."""
    loc = (locale or "").strip().lower().replace("_", "-")
    return "letter" if loc in LETTER_LOCALES else DEFAULT_NEW


_CURRENT: ContextVar[Paper] = ContextVar("cvstand_paper", default=LETTER)


def current() -> Paper:
    return _CURRENT.get()


@contextmanager
def use(paper: Paper | dict[str, Any] | str | None) -> Iterator[Paper]:
    """Bind the paper for the exporters for the duration of one export."""
    if isinstance(paper, Paper):
        p = paper
    elif isinstance(paper, str):
        p = PAPERS.get(paper, LETTER)
    else:
        p = paper_of(paper)
    token = _CURRENT.set(p)
    try:
        yield p
    finally:
        _CURRENT.reset(token)
