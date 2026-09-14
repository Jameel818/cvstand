"""The public brand, in exactly one place.

WHY THIS FILE EXISTS
    This is the SECOND rename (RésuméCraft -> CVStand), which is evidence the
    string moves. The first one was six scattered edits and it cost an hour of
    grepping to find them all.

    The specific trap: the wordmark is split across tags so the head and tail
    can be styled differently -- it used to be `Résumé<b>Craft</b>` and it is
    now `CV<b>Stand</b>`. **`grep -i cvstand` does not find it**, exactly as
    `grep -i resumecraft` did not find the old one. That produced one
    confidently wrong answer on 2026-09-12 ("the brand slot is empty" -- the
    brand was already shipped on every page). A constant in a `.py` file makes
    the ASCII string greppable and makes the third rename a one-liner.

    `tests/test_brand.py` is the guard that makes the trap harmless: it asserts
    the brand reaches the header, the footer and the <title> of every page, in
    both UI languages. Memory is not the guard. The test is.

NOT TRANSLATED, DELIBERATELY
    A brand does not change script when the interface does, so `NAME` is the
    same bytes in Arabic and English -- see labels.py's header comment. That
    policy predates this file and carries over untouched; "Stand" has no
    Arabic morpheme, but neither did "Craft", so this costs nothing in code.

THE INTERNAL NAMESPACE WAS RENAMED TOO, AND THE TIMING WAS THE WHOLE ARGUMENT
    Until 2026-09-14 the rule here was the opposite: never rename the
    `RESUMECRAFT_*` env vars, `data/resumecraft.db`, or the
    `resumecraft:resume` / `resumecraft:template` localStorage keys, because
    the BROWSER owns the résumé and renaming those keys silently wipes every
    existing user's document.

    That reasoning protects DEPLOYED users. There were none -- the app had
    never been hosted -- so the only data at risk was one developer's sample.
    The rename was therefore free exactly once, and permanently expensive
    afterwards, so it happened before launch rather than never.

    **That window is now closed.** Anything reaching a real browser is live
    state from here on: renaming `cvstand:resume` after launch really would
    wipe documents, and the old justification applies again in full. The
    public brand and the internal namespace do not HAVE to match -- they just
    happen to, now, and that is not a reason to re-open either.

    `sw.js` still sweeps the old `resumecraft-` cache prefix on activate. A
    cleanup filter only deletes keys it recognises, so dropping the old name
    would strand it in any browser that had loaded the previous shell.
"""
from __future__ import annotations

#: The wordmark, as one greppable ASCII string.
NAME = "CVStand"

#: The wordmark split for the two-weight logo: `{{ brand_head }}<b>{{ brand_tail }}</b>`.
#: Concatenating these MUST reproduce NAME -- tests/test_brand.py asserts it.
HEAD = "CV"
TAIL = "Stand"

#: The human mailbox on the brand domain.
#:
#: Kept here rather than inside a msgid because `t()`'s key IS its English
#: string (see labels.py): baking the address into a sentence would make the
#: address itself translatable and would re-key the catalogue -- invalidating
#: the Arabic translation -- every time the address changes. Templates render
#: the label and this constant side by side instead.
#:
#: Transactional mail (`noreply@`) is a separate address and does not exist
#: yet; it lands with password reset, which needs mail code that is not
#: written (there is no smtplib/flask_mail anywhere under app/).
SUPPORT_EMAIL = "info@cvstand.com"

#: The domain, for copy that needs it without the mailbox.
DOMAIN = "cvstand.com"

#: The tagline, and it has a job beyond decoration.
#:
#: "Stand" is ambiguous in this market: it reads as a booth (جناح) just as
#: readily as "stand out". The name cannot fix that by itself -- "Stand" has
#: no Arabic morpheme, exactly as "Craft" did not -- so the ambiguity is paid
#: for in positioning and the remedy is this line, not a third name. It must
#: therefore always contain the disambiguating verb; a prettier tagline that
#: drops "stand out" gives up the only thing this one is for.
#:
#: English only, because the msgid IS the English string (labels.py). The
#: Arabic lives in `_UI_AR` beside every other shell string.
TAGLINE = "Make your CV stand out."


def context() -> dict[str, str]:
    """The brand as template globals, for the app factory's context processor.

    A context processor rather than a per-route variable because base.html
    renders on EVERY page, and a route that forgot to pass the brand would
    render a header with an empty wordmark.
    """
    return {
        "brand_name": NAME,
        "brand_head": HEAD,
        "brand_tail": TAIL,
        "brand_email": SUPPORT_EMAIL,
        "brand_domain": DOMAIN,
        "brand_tagline": TAGLINE,
    }
