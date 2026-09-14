"""The résumés the suites run in BOTH directions (bilingual, phase 8).

Phases 1-7 each proved one layer bilingual and gated that layer. What none of
them did is run the suites that find CONTENT defects — the half-filled entry,
the unrated skill, the dangling separator — through Arabic. Those suites are
the ones that have historically found real bugs in this project, and every one
of them rendered `data/sample_resume.json`, which is English.

So this module is the shared vocabulary for "the same test, the other way
round":

    ENGLISH   data/sample_resume.json      — no `lang` key at all, which is
                                             itself the back-compat case
    ARABIC    data/sample_resume_ar.json   — lang="ar", Arabic throughout
    BOTH      [("en", ENGLISH), ("ar", ARABIC)] — for @parametrize

and the two MIXED résumés, which are phase 8's own case rather than a rerun of
an earlier one:

    MIXED     an Arabic document carrying Latin values — an Arabic CV naming
              the English-language employers the person actually worked for
    REVERSED  an English document carrying Arabic values — the same person
              applying the other way round

Mixed content is called out separately because it is the one case where the
two languages meet INSIDE a line, and therefore the only one where the Unicode
bidi algorithm has to make a choice about text neither the template nor the
schema controls. `tests/test_bidi_mixed.py` is where that choice is measured.

Every value planted here is deliberately neutral-heavy — `&`, `+`, `(`, `)`,
`-`, `,` — because a neutral character is the ONLY thing whose direction is
decided by its neighbours. A field of pure Latin letters beside a field of pure
Arabic letters cannot reorder; a field with a `&` in it can.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENGLISH: dict = json.loads(
    (ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
ARABIC: dict = json.loads(
    (ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))

#: For `@pytest.mark.parametrize("lang,sample", BOTH)`. The English entry
#: carries NO `lang` key, so parametrising over this also keeps the
#: absent-means-English promise under test in every suite that adopts it.
BOTH = [("en", ENGLISH), ("ar", ARABIC)]


# Latin values planted into the Arabic résumé. Each one is a real shape a
# bilingual applicant produces, and each carries a neutral that has to be
# placed by the bidi algorithm rather than by the template:
#
#   "Halden & Row"      an ampersand BETWEEN two Latin words — if the run is
#                       resolved right-to-left this reads "Row & Halden"
#   "+1 (555) 0138-64"  a leading `+` and a bracketed group; `+` and `(` are
#                       the classic characters that jump to the wrong end
#   Latin inside prose  an employer named mid-sentence in Arabic, which is the
#                       commonest mixed line in a real Arabic CV
_LATIN_COMPANY = "Halden & Row"
_LATIN_PHONE = "+1 (555) 0138-64"
_LATIN_SCHOOL = "Northfield College of Art"
_LATIN_SKILL = "Figma"
_LATIN_IN_PROSE = "تدير استوديو Halden & Row عبر الهوية والتحرير والموشن."

#: The runs that carry STRONG Latin letters, so their reading direction is a
#: fact rather than a matter of context. `test_bidi_mixed` asserts these read
#: left-to-right even inside an Arabic page. Kept beside the résumé that plants
#: them so the two cannot drift apart.
MIXED_LATIN = (_LATIN_COMPANY, _LATIN_SCHOOL, _LATIN_SKILL)

#: Deliberately NOT in MIXED_LATIN. `+1 (555) 0138-64` is digits and neutrals
#: with no strong character at all, so it has no direction of its own — it
#: takes one from its neighbours, and both answers are legitimate. It is
#: planted for the tearing and separator checks, which are unambiguous, and
#: excluded from the direction check, which for this value would be asserting
#: a preference rather than a defect.
MIXED_NEUTRAL = (_LATIN_PHONE,)

_ARABIC_COMPANY = "هالدن آند رو"
_ARABIC_CITY = "بورتسايد"
_ARABIC_IN_PROSE = "Runs the هالدن آند رو studio across brand and motion."

#: The Arabic runs planted into the English résumé, likewise.
REVERSED_ARABIC = (_ARABIC_COMPANY, _ARABIC_CITY)


def _mixed() -> dict:
    """Arabic document, Latin employers. `lang` stays "ar"."""
    r = copy.deepcopy(ARABIC)
    r["contact"]["phone"] = _LATIN_PHONE
    r["experience"][0]["company"] = _LATIN_COMPANY
    r["experience"][0]["bullets"][0] = _LATIN_IN_PROSE
    r["experience"][1]["company"] = "Bellrock Studio"
    r["education"][0]["school"] = _LATIN_SCHOOL
    r["skills"][0] = {"name": _LATIN_SKILL, "level": r["skills"][0]["level"]}
    r["languages"] = [{"name": "English", "level": "متقدم"},
                      {"name": "العربية", "level": "خبير"}]
    return r


def _reversed() -> dict:
    """English document, Arabic employers. No `lang` key — English by default,
    which is the case a bilingual user actually hits: they never think to set
    a language, they just type a company name in Arabic."""
    r = copy.deepcopy(ENGLISH)
    r["contact"]["address"] = _ARABIC_CITY
    r["experience"][0]["company"] = _ARABIC_COMPANY
    r["experience"][0]["location"] = "Portside"
    r["experience"][0]["bullets"][0] = _ARABIC_IN_PROSE
    return r


MIXED: dict = _mixed()
REVERSED: dict = _reversed()
