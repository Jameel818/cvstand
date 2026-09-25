"""What a document carries for the user's typography choices (spec §6.1).

`document_blocks(values, lang)` turns the VALIDATED six keys (from
`clean_typography`) into two strings for `rendering.document_html()`:

    head   <link> to typography.css, and the family rules
    body   the config JSON and the inline runtime (static/js/typography.js)

Both are "" when every key is None, so a résumé that never chose anything
emits exactly the document it did before this feature existed.

WHY FAMILY IS CSS BUT WEIGHT AND SIZE ARE NOT
    All 49 templates set font-family, font-weight and font-size in inline
    `style` attributes, so only an `!important` stylesheet rule reaches them -
    the same reason `RTL_TYPOGRAPHY` is written that way. That works for the
    family. It does not work for:

      weight  "weight None" means the template's OWN weight mapped to the
              nearest offered one, per element - a lookup no selector can do.
              The runtime reads each element's computed weight and looks it up
              in `nearest`, a table computed HERE by registry.nearest_weight(),
              so the JavaScript never re-implements the rule.
      size    autofit.js owns inline font-size: it clears and rewrites it on
              every fit. So a size choice is a per-role FACTOR that autofit
              multiplies into what it already writes (see autofit.js).

WHY THESE SELECTORS WIN
    Each carries one more type selector (`html`) than its RTL_TYPOGRAPHY
    counterpart and comes after it in the document, so a chosen font beats the
    Arabic policy's defaults, and the policy still applies to any role the user
    left on "Template default":

      [dir=rtl] .tpl *                       (0,2,0) < html[data-cvt] .tpl :not(...)  (0,2,1)
      [dir=rtl] .tpl .cv-name                (0,3,0) < html[data-cvt] .tpl .cv-name   (0,3,1)
      [dir=rtl] .cv-sections-taj .cv-section (0,3,0) < html[data-cvt] .tpl .cv-section (0,3,1)

    `data-cvt` is set by the runtime AFTER it has written every weight. Until
    then no rule matches, so Chromium cannot lay out a chosen family at the
    template's raw weight and fetch a face nobody chose.

    The Details rule excludes the headline roles with `:not(:where(...))`,
    whose specificity is zero, so choosing a Details font never touches the
    name or the section titles.

Nothing here reads a raw user string: every family name comes from the
registry, having been matched there exactly by `clean_typography`.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .faces import built_faces
from .registry import (
    CSS_FAMILY_PREFIX, EMPHASIS_FROM, EMPHASIS_WEIGHT, FONT_KEY, FONTS,
    LATIN_EXT_FALLBACK, NAME_TEMPLATE, SIZE_KEY, WEIGHT_KEY, nearest_weight,
)

TYPOGRAPHY_CSS_URL = "/static/fonts/typography.css"
_RUNTIME = Path(__file__).resolve().parent.parent / "static" / "js" / "typography.js"

PT_TO_PX = 4 / 3

_HEADLINE_ALL = ".cv-name, .cv-name *, .cv-section, .cv-section *"

#: The document's three roles -> the registry role whose lists apply and the
#: elements they style. Section titles are the registry's "heading" role.
DOC_ROLES = {"name": "name", "section": "heading", "body": "body"}
_ROLE_SELECTORS = {"name": (".cv-name", ".cv-name *"),
                   "section": (".cv-section", ".cv-section *")}


@lru_cache(maxsize=1)
def _families_without_latin_ext() -> frozenset[str]:
    data = json.loads((Path(__file__).with_name("build.json")).read_text(encoding="utf-8"))
    return frozenset(f for f, info in data["families"].items() if not info["latin_ext"])


def family_stack(family: str) -> str:
    """The CSS font-family value for a registry family.

    'CVT <Family>' first; for an Arabic family whose files stop at Latin-1, a
    Latin family that has Latin-Ext next, so a rare letter (Ł, ř) is drawn in
    a real face of the same weight instead of whatever the OS picks. The
    browser fetches that fallback only if a glyph actually falls through."""
    font = FONTS[family]
    parts = [f"'{CSS_FAMILY_PREFIX}{family}'"]
    if family in _families_without_latin_ext():
        parts.append(f"'{CSS_FAMILY_PREFIX}{LATIN_EXT_FALLBACK[font.generic]}'")
    parts.append(font.generic)
    return ", ".join(parts)


def effective(values: dict) -> dict[str, dict]:
    """Per document role: the family, weight and size that actually apply.

    Only the NAME needs resolving. Its font null means "Same as Headings" -
    the Headings font AND weight, unless the name has its own weight - which
    is also exactly how a résumé saved before the split rendered its name, so
    an old CV looks the same without migrating a weight. NAME_TEMPLATE means
    the template's own face."""
    heading = {"family": values[FONT_KEY["heading"]], "weight": values[WEIGHT_KEY["heading"]],
               "size": values[SIZE_KEY["heading"]]}
    font = values[FONT_KEY["name"]]
    if font == NAME_TEMPLATE:
        name_family, inherited_weight = None, None
    elif font is None:
        name_family, inherited_weight = heading["family"], heading["weight"]
    else:
        name_family, inherited_weight = font, None
    name_weight = values[WEIGHT_KEY["name"]] or inherited_weight
    return {
        "name": {"family": name_family, "weight": name_weight if name_family else None,
                 "size": values[SIZE_KEY["name"]]},
        "section": heading,
        "body": {"family": values[FONT_KEY["body"]], "weight": values[WEIGHT_KEY["body"]],
                 "size": values[SIZE_KEY["body"]]},
    }


def _nearest_table(lang: str, role: str, family: str) -> dict[str, int]:
    return {str(w): nearest_weight(lang, role, family, w) for w in range(100, 1000, 100)}


def config(values: dict, lang: str) -> dict | None:
    """The runtime's instructions, or None when nothing was chosen."""
    eff = effective(values)
    # Judged on what APPLIES, not on the raw keys: `font_name: "template"` on
    # its own is a choice to keep the template's look, and emits nothing.
    if all(e["family"] is None and e["size"] is None for e in eff.values()):
        return None
    out: dict = {}
    for role, e in eff.items():
        family, size = e["family"], e["size"]
        r = {
            "family": family and CSS_FAMILY_PREFIX + family,
            "weight": e["weight"],
            "nearest": _nearest_table(lang, DOC_ROLES[role], family) if family else None,
            "size_px": size * PT_TO_PX if size is not None else None,
        }
        if role == "body":
            r["emphasis"] = EMPHASIS_WEIGHT if family else None
            r["emphasis_from"] = EMPHASIS_FROM
        out[role] = r
    return out


def _css(values: dict) -> str:
    eff = effective(values)
    rules = []
    # Hard rule 1: never fake a weight. Scoped to documents that chose a font,
    # so a template's own faces render exactly as they always have.
    rules.append("html[data-cvt] .tpl { font-synthesis: none !important; }")
    if eff["body"]["family"]:
        rules.append(
            f"html[data-cvt] .tpl,\nhtml[data-cvt] .tpl :not(:where({_HEADLINE_ALL})) "
            f"{{ font-family: {family_stack(eff['body']['family'])} !important; }}")
    for role in ("section", "name"):
        fam = eff[role]["family"]
        if fam:
            sel = ",\n".join(f"html[data-cvt] .tpl {s}" for s in _ROLE_SELECTORS[role])
            rules.append(f"{sel} {{ font-family: {family_stack(fam)} !important; }}")
    return '<style id="cv-typography">\n' + "\n".join(rules) + "\n</style>"


@lru_cache(maxsize=1)
def _runtime() -> str:
    return "<script>\n" + _RUNTIME.read_text(encoding="utf-8") + "\n</script>"


def document_blocks(values: dict, lang: str) -> tuple[str, str]:
    """(head, body) strings for document_html; ("", "") when nothing was chosen."""
    cfg = config(values, lang)
    if cfg is None:
        return "", ""
    chose_family = any(e["family"] for e in effective(values).values())
    head = ""
    if chose_family:
        head = f'<link rel="stylesheet" href="{TYPOGRAPHY_CSS_URL}">' + _css(values)
    # `</` cannot appear in the JSON (every value is a registry name or a
    # number), but escape it anyway: this sits inside a <script> element.
    blob = json.dumps(cfg, sort_keys=True).replace("</", "<\\/")
    body = (f'<script type="application/json" id="cv-typography-config">{blob}</script>'
            + _runtime())
    return head, body


def faces_for(values: dict, lang: str) -> set[tuple[str, int]]:
    """Every built (family, weight) this document can request - used by the
    tests that assert only these faces are ever downloaded."""
    from .registry import built_weights
    out: set[tuple[str, int]] = set()
    for role, e in effective(values).items():
        if e["family"]:
            out |= {(e["family"], w) for w in built_weights(lang, DOC_ROLES[role], e["family"])}
    assert out <= set(built_faces())
    return out
