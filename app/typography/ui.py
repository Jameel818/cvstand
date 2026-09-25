"""What the builder's Fonts section needs, for one document language.

Built from the registry and nothing else (hard rule 4), and handed to
`builder.js` in the page payload, like the level vocabularies: the form is
generated in the browser, so it cannot call the registry itself.

Only the DOCUMENT's language is sent. Switching language reloads the builder
(the header switch is the only way to change it), so the other language's
lists are never needed on the page; a stored choice that is not valid in the
new language comes back from `/api/render` as a reset.

Labels travel as English msgids and the client translates them with T(), so
there is one catalogue (`labels._UI_AR`) and one lookup, as for every other
builder string.
"""
from __future__ import annotations

from .registry import (
    CSS_FAMILY_PREFIX, GROUP_LABEL, GROUP_ORDER, LIGHT_WARNING_PT,
    LIGHT_WEIGHT, ROLES, WEIGHT_LABEL, fonts_for, is_single_weight, nearest_weight,
    offered_weights, size_scale,
)
from .render import family_stack

#: The sample each font dropdown draws in its chosen face (§3.5).
SAMPLE = {"en": "Jameel Ahmad", "ar": "جميل أحمد"}


def builder_payload(lang: str) -> dict:
    roles = {}
    for role in ROLES:
        fams = fonts_for(lang, role)
        groups = []
        for cat in GROUP_ORDER[lang]:
            members = [f for f in fams if f.category == cat]
            if not members:
                continue
            groups.append({"label": GROUP_LABEL[cat], "families": [{
                "family": f.family,
                "stack": family_stack(f.family),
                "weights": list(offered_weights(lang, role, f.family)),
                "single": is_single_weight(lang, role, f.family),
                "playful": f.playful,
                # The server's nearest_weight(), tabulated, so a font change
                # keeps the closest weight without the rule living in JS too.
                "nearest": {str(w): nearest_weight(lang, role, f.family, w)
                            for w in range(100, 1000, 100)},
            } for f in members]})
        scale = size_scale(lang, role)
        roles[role] = {"groups": groups, "sizes": list(scale.options()),
                       "default_size": scale.default}
    return {
        "lang": lang,
        "roles": roles,
        "weight_labels": {str(w): n for w, n in WEIGHT_LABEL.items()},
        "light": {"weight": LIGHT_WEIGHT, "below_pt": LIGHT_WARNING_PT[lang]},
        "sample": SAMPLE[lang],
        "css_prefix": CSS_FAMILY_PREFIX,
    }


def payload_msgids(lang: str) -> set[str]:
    """Every label builder_payload() asks the client to translate - for the
    test that each has Arabic."""
    p = builder_payload(lang)
    out = {g["label"] for r in p["roles"].values() for g in r["groups"]}
    return out | set(p["weight_labels"].values())
