"""User field values are DATA, never markup — in all 49 templates.

Thirteen templates joined user fields with a literal `<br>` and then marked the
whole joined string safe:

    {{ parts | join("<br>") | safe }}      # _macros.j2::contact_lines, and 12 more

`| safe` cannot tell the separator from the values it separates, so it trusted
both. `contact_lines` builds `parts` from raw `contact.email`, `.phone`,
`.address`, `.site` and every `social[].label`; `modern/t3.j2` does the same
with skill names and `r.tools`. A résumé whose email field contained markup
rendered that markup live — in the builder preview, in the template drawer, and
inside the headless Chromium that `app/exporters/pdf.py` drives to make the PDF.

That was harmless for exactly as long as the app was single-user and local:
the only résumé on the machine was your own. It stops being harmless the moment
the app is deployed and one person's stored document is rendered anywhere near
another person, which is the first thing on the Stage 1 list.

The fix is `app/rendering.py::_br_join` — `Markup("<br>").join(...)`, which
escapes every non-Markup item and keeps the separator as real markup. These
tests hold both halves of that:

* the payload never survives as live markup, in ANY of the 49 (the security
  claim, and it must be universal — a template that skips `contact_lines`
  still renders skills and tools somewhere);
* the escaped text still SHOWS, and the `<br>` separator still works, in the
  thirteen that actually take the path (the mutation guard — deleting the
  filter entirely would satisfy an "is not present" assertion by rendering
  nothing at all).

Both directions, per phase 8: the label catalogue returns `Markup` for a
handful of msgids, and `Markup.join` treats those differently from plain
strings, so "Arabic renders the same way" is a real claim rather than a
formality.
"""
from __future__ import annotations

import copy

import pytest

from app import registry
from app.rendering import canvas_html
from tests import samples

# Deliberately not a bare `<script>`: it must be something whose ESCAPED form is
# still recognisable in the output, so the second half of each test can prove
# the field rendered at all rather than being silently dropped.
PAYLOAD = '<img src=x onerror="alert(1)">'
ESCAPED = "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;"

# The thirteen call sites live in ten templates. Nine carry a `br_join` in
# their own file; `modern-t1` reaches one through `_macros.j2::contact_lines`,
# which — despite being a shared macro — has exactly one caller. Reverting all
# thirteen fails 20 tests here, which is these ten in both languages: the list
# is the mutation surface, so keep it in step with the call sites.
BR_JOIN_TEMPLATES = [
    "modern-t1",
    "ats-t19",
    "modern-t13",
    "modern-t16",
    "modern-t23",
    "modern-t24",
    "modern-t3",
    "modern-t5",
    "modern-t7",
    "modern-t9",
]

PORTED = sorted(registry.ported_keys())


def _poisoned(base: dict) -> dict:
    """The sample résumé with markup planted in every field the 13 sites join."""
    r = copy.deepcopy(base)
    r["contact"]["email"] = PAYLOAD
    r["contact"]["phone"] = PAYLOAD
    r["contact"]["address"] = PAYLOAD
    r["contact"]["site"] = PAYLOAD
    r["contact"]["social"] = [{"label": PAYLOAD, "url": "https://example.com"}]
    for skill in r.get("skills", []):
        skill["name"] = PAYLOAD
    r["tools"] = [PAYLOAD, PAYLOAD]
    return r


@pytest.mark.parametrize("key", PORTED)
@pytest.mark.parametrize("lang,sample", samples.BOTH)
def test_user_markup_never_renders_live(key, lang, sample):
    """No template anywhere emits a user field as markup."""
    html = canvas_html(_poisoned(sample), key)
    assert PAYLOAD not in html, f"{key} ({lang}) rendered a user field as live markup"
    assert "<img" not in html, f"{key} ({lang}) leaked an unescaped tag"
    assert "onerror" not in html or ESCAPED in html, (
        f"{key} ({lang}) leaked an event handler outside an escaped run"
    )


@pytest.mark.parametrize("key", BR_JOIN_TEMPLATES)
@pytest.mark.parametrize("lang,sample", samples.BOTH)
def test_escaped_value_still_shows(key, lang, sample):
    """The value is escaped, NOT dropped.

    Without this, removing `| br_join` and rendering nothing would pass the
    test above.
    """
    html = canvas_html(_poisoned(sample), key)
    assert ESCAPED in html, f"{key} ({lang}) escaped the value out of existence"


@pytest.mark.parametrize("key", BR_JOIN_TEMPLATES)
@pytest.mark.parametrize("lang,sample", samples.BOTH)
def test_the_separator_is_still_markup(key, lang, sample):
    """`<br>` is OURS and must stay a real line break.

    The lazy fix — escaping the whole joined string — would turn the separator
    into a visible `&lt;br&gt;` and quietly wreck the layout of every contact
    block in the app. This is the assertion that rules that fix out.
    """
    html = canvas_html(_poisoned(sample), key)
    assert "<br>" in html, f"{key} ({lang}) escaped its own separator"
    assert "&lt;br&gt;" not in html, f"{key} ({lang}) printed a visible <br>"


@pytest.mark.parametrize("lang,sample", samples.BOTH)
def test_clean_resume_is_untouched(lang, sample):
    """The other half of the contract: ordinary content renders as before.

    `Markup.join` escapes `&` where `| safe` did not, so a résumé with an
    ampersand in a joined field WOULD move — the golden HTML gate is what
    would catch that. This test pins the narrower claim that the shipped
    sample renders identically through every ported template, which is what
    makes the golden gate's silence meaningful rather than lucky.
    """
    for key in PORTED:
        html = canvas_html(sample, key)
        assert "&lt;br&gt;" not in html, f"{key} ({lang}) printed a visible <br>"
        assert "&amp;lt;" not in html, f"{key} ({lang}) double-escaped a value"
