"""Server-side whitelist for the six typography keys (spec §1.5, §2).

`clean_typography()` never raises. Anything the registry does not offer for
this résumé's language and role becomes None — "template default" — and is
reported in `resets`, so the builder can tell the user what changed (§2: a
language switch resets the choices that are not valid in the new language).

Normalising rather than rejecting is deliberate: the document language can
change from the interface side, and a stored CV must never become unsaveable
because a font it chose belongs to the other language or left the registry.
Only a wrong JSON TYPE is refused, and that is the schema's job (422).

Raw strings never reach CSS: a family name survives only if it is, exactly, a
registry key.
"""
from __future__ import annotations

import math
from typing import Any

from .registry import (
    FONT_KEY, LEGACY_SECTION_CLAMP_PT, LEGACY_SECTION_RATIO, NAME_TEMPLATE, SIZE_KEY,
    TYPOGRAPHY_KEYS, WEIGHT_KEY, is_offered, offered_weights, size_scale,
)

# Reason codes in `resets`. Codes, not prose: the notice text is the builder's,
# in the interface language (step 3).
NOT_OFFERED = "not_offered"        # not in the registry for this language/role
NO_FONT = "needs_font"             # a weight only means something for a chosen font


def _number(value: Any) -> float | None:
    """A finite JSON number, or None. bool is excluded: True == 1 in Python."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        n = float(value)   # an int beyond float range raises, not returns inf
    except OverflowError:
        return None
    return n if math.isfinite(n) else None


def _weight(value: Any) -> int | None:
    n = _number(value)
    return int(n) if n is not None and n.is_integer() else None


def _clean_number(n: float) -> int | float:
    """int for whole sizes so 32 round-trips as 32, not 32.0"""
    return int(n) if n.is_integer() else n


def migrate_typography(data: dict[str, Any], lang: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Carry a résumé saved before step 3c onto the three-group model.

    Until then `font_heading_size` was the NAME size (EN 24-44, AR 26-48) and
    section titles were derived from it as clamp(size x 0.42, lo, hi). Now it
    is the section-title size (EN 11-18, AR 12-20). The two ranges do not
    overlap, so an old value is recognised by its value alone - no version
    field. It moves to `font_name_size` (unless one is already set), and the
    sections keep the size they had, rounded to the new 1pt grid (13.44 -> 13):
    nothing a user chose changes by more than half a point.

    Returns (data, migrations); `data` is a copy only when something moved.
    Migrations are silent - the builder applies them to its stored copy, and
    nothing is announced, because nothing the user sees changes.
    """
    hs = _number(data.get(SIZE_KEY["heading"]))
    if hs is None or size_scale(lang, "heading").allows(hs)             or not size_scale(lang, "name").allows(hs):
        return data, []
    out = dict(data)
    migrations: list[dict[str, Any]] = []
    if data.get(SIZE_KEY["name"]) is None:
        out[SIZE_KEY["name"]] = _clean_number(hs)
        migrations.append({"key": SIZE_KEY["name"], "value": out[SIZE_KEY["name"]],
                           "from": SIZE_KEY["heading"]})
    lo, hi = LEGACY_SECTION_CLAMP_PT[lang]
    derived = min(max(hs * LEGACY_SECTION_RATIO, lo), hi)
    section = int(math.floor(derived + 0.5))          # half up, not banker's
    out[SIZE_KEY["heading"]] = section
    migrations.append({"key": SIZE_KEY["heading"], "value": section, "from": _clean_number(hs)})
    return out, migrations


def clean_typography(data: dict[str, Any], lang: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (values, resets).

    `values` holds all nine keys; None means template default - except
    `font_name`, where None means "Same as Headings" and NAME_TEMPLATE means
    the template's own face. `resets` lists every non-null input that was
    dropped, as {"key", "value", "reason"}. A pre-3c résumé is migrated first
    (see migrate_typography), so its old headline size is not reset.
    """
    data, _ = migrate_typography(data, lang)
    values: dict[str, Any] = dict.fromkeys(TYPOGRAPHY_KEYS)
    resets: list[dict[str, Any]] = []

    def reset(key: str, reason: str) -> None:
        resets.append({"key": key, "value": data.get(key), "reason": reason})

    # Headings before Name: the name's effective font can be the Headings one.
    for role in ("heading", "body", "name"):
        fkey, wkey, skey = FONT_KEY[role], WEIGHT_KEY[role], SIZE_KEY[role]

        family = data.get(fkey)
        effective = None
        if role == "name" and family == NAME_TEMPLATE:
            values[fkey] = NAME_TEMPLATE
        elif role == "name" and family is None:
            effective = values[FONT_KEY["heading"]]        # Same as Headings
        elif family is not None:
            if isinstance(family, str) and is_offered(lang, role, family):
                values[fkey] = effective = family
            else:
                reset(fkey, NOT_OFFERED)

        weight = data.get(wkey)
        if weight is not None:
            w = _weight(weight)
            if effective is None:
                # The template's own face has weights the registry cannot vouch
                # for, and an unbacked weight is a faux-bold (hard rule 1).
                reset(wkey, NO_FONT)
            elif w is not None and w in offered_weights(lang, role, effective):
                values[wkey] = w
            else:
                reset(wkey, NOT_OFFERED)

        size = data.get(skey)
        if size is not None:
            s = _number(size)
            if s is not None and size_scale(lang, role).allows(s):
                values[skey] = _clean_number(s)
            else:
                reset(skey, NOT_OFFERED)

    return values, resets
