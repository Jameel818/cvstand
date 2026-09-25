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
    FONT_KEY, ROLES, SIZE_KEY, TYPOGRAPHY_KEYS, WEIGHT_KEY,
    is_offered, offered_weights, size_scale,
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


def clean_typography(data: dict[str, Any], lang: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (values, resets).

    `values` holds all six keys; None means template default. `resets` lists
    every non-null input that was dropped, as {"key", "value", "reason"}.
    """
    values: dict[str, Any] = dict.fromkeys(TYPOGRAPHY_KEYS)
    resets: list[dict[str, Any]] = []

    def reset(key: str, reason: str) -> None:
        resets.append({"key": key, "value": data.get(key), "reason": reason})

    for role in ROLES:
        fkey, wkey, skey = FONT_KEY[role], WEIGHT_KEY[role], SIZE_KEY[role]

        family = data.get(fkey)
        if family is not None:
            if isinstance(family, str) and is_offered(lang, role, family):
                values[fkey] = family
            else:
                reset(fkey, NOT_OFFERED)

        weight = data.get(wkey)
        if weight is not None:
            w = _weight(weight)
            if values[fkey] is None:
                # The template's own face has weights the registry cannot vouch
                # for, and an unbacked weight is a faux-bold (hard rule 1).
                reset(wkey, NO_FONT)
            elif w is not None and w in offered_weights(lang, role, values[fkey]):
                values[wkey] = w
            else:
                reset(wkey, NOT_OFFERED)

        size = data.get(skey)
        if size is not None:
            s = _number(size)
            if s is not None and size_scale(lang, role).allows(s):
                # int for whole sizes so 32 round-trips as 32, not 32.0
                values[skey] = int(s) if s.is_integer() else s
            else:
                reset(skey, NOT_OFFERED)

    return values, resets
