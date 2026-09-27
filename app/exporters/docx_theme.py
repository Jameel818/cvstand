"""Per-template colours and fonts for the Word export (typography step 5).

There are only two Word layouts (`word_masters/`), shared by all 49 templates.
This pass is what makes a download look like ITS template: after docxtpl has
filled the master, it rewrites the master's role styles with the template's
accent and fonts - or the fonts the user chose in the Fonts section, which
win per group exactly as they do in the preview (`typography.render.effective`).

WHAT IT TOUCHES
    styles.xml    the five role styles the builder puts on every themed run
                  (CV Name, CV Heading, CV Role, CV Body Bold, CV Accent Text)
                  and Normal, which carries the body face. One place per role,
                  so no run can be missed - see tools/build_word_masters.py
                  "ROLE STYLES".
    document.xml  only the accent RULE under the Modern contact line, found by
                  its placeholder colour RULE_ACCENT.

COLOUR
    Text takes `accent_text`: the template's accent, mixed toward black just
    until it reads at 4.5:1 on white (13 accents are lighter than that - lime,
    yellow, coral, cyan). Rules keep the ORIGINAL accent: a hairline is not
    text, and the user asked for the brand colour there (2026-09-27).

FONTS
    Word knows a face by FAMILY NAME plus a bold flag, not by weight, so every
    (family, weight) is written as build.json's `word_family_name` and
    `word_bold` (spec §6.2) - never a name rebuilt here. Every face a
    document can reach is built: the dropdowns' faces, plus the template
    defaults no dropdown offers (registry.TEMPLATE_DEFAULT_FACES, step 6).

    Weights are never faked: a template weight snaps to the nearest weight the
    build has, and a chosen font with no chosen weight takes
    `registry.nearest_weight()` of the template's own, as in the preview.

    ARABIC takes its face, weight and size from `w:cs`, `w:bCs` and `w:szCs`,
    not from the Latin attributes. The styles set all four rFonts slots and
    bCs beside b; szCs is already on every RTL run (`_apply_rtl`).

OOXML property elements are ordered sequences; everything here is inserted
at its schema position (RPR_ORDER), never appended - the mistake that once
made Word refuse the masters outright.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Role style names. python-docx derives the styleId by dropping the spaces.
ST_NAME = "CV Name"
ST_HEADING = "CV Heading"
ST_ROLE = "CV Role"
ST_BODY_BOLD = "CV Body Bold"
ST_ACCENT_TEXT = "CV Accent Text"

#: The Modern master's contact rule is drawn in this colour so the export can
#: find it and recolour it with the template's own accent.
RULE_ACCENT = "1F3A5F"

INK = "17181A"

THEMES_PATH = Path(__file__).resolve().parent.parent / "word_themes.json"

#: Families a template names that Word should not get as-is. modern-t10 names
#: DM Sans, which is vendored nowhere (so the preview and PDF draw a system
#: fallback); Word gets Poppins, which DM Sans was derived from and which the
#: build has (user decision 2026-09-27; follow-up: vendor DM Sans properly).
WORD_SUBSTITUTES = {"DM Sans": "Poppins"}

# ECMA-376 CT_RPr child order (the same list tests/test_docx_validity.py checks).
RPR_ORDER = ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
             "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
             "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
             "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
             "eastAsianLayout", "specVanish", "oMath")


# ---- colour ------------------------------------------------------------------

def _luminance(hex6: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex6[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_on_white(hex6: str) -> float:
    return 1.05 / (_luminance(hex6.lstrip("#")) + 0.05)


def text_safe(hex6: str, minimum: float = 4.5) -> str:
    """The accent as TEXT: itself if it reads at `minimum`:1 on white, else
    mixed toward black in 1% steps until it does (the hue stays)."""
    h = hex6.lstrip("#").upper()
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    for pct in range(0, 101):
        k = 1 - pct / 100
        out = "%02X%02X%02X" % (round(r * k), round(g * k), round(b * k))
        if contrast_on_white(out) >= minimum:
            return out
    return "000000"  # pragma: no cover - black always passes


# ---- fonts -------------------------------------------------------------------

def _built_weights(family: str) -> list[int]:
    from ..typography import built_faces
    return sorted(w for (f, w) in built_faces() if f == family)


def snap_weight(family: str, weight: int) -> int:
    """The nearest weight the build has (heavier wins a tie), so Word never
    fakes one."""
    built = _built_weights(family)
    if not built:
        raise KeyError(f"{family!r} is not built - add it to "
                       "registry.TEMPLATE_DEFAULT_FACES and run tools/build_fonts.py")
    return min(built, key=lambda w: (abs(w - weight), -w))


def word_font(family: str, weight: int) -> tuple[str, bool]:
    """(Word family name, bold flag) for one face, exactly as build.json
    measured it from the TTF (nameID 1 and the fsSelection bold bit) - the
    names the embedded font will answer to."""
    from ..typography import face
    built = face(family, weight)
    if not built:
        raise KeyError(f"no built face {family} {weight}")
    return built["word_family_name"], bool(built["word_bold"])


@lru_cache(maxsize=1)
def themes() -> dict:
    return json.loads(THEMES_PATH.read_text(encoding="utf-8"))["templates"]


def resolve(data: dict, template_key: str) -> dict:
    """Every role's (family, weight) and the colours, for this résumé in this
    template: the user's choice per group, else the template's own."""
    from ..schema import lang_of, typography_of
    from ..typography import EMPHASIS_WEIGHT, nearest_weight
    from ..typography.render import DOC_ROLES, effective

    lang = lang_of(data)
    theme = themes()[template_key][lang]
    eff = effective(typography_of(data)[0])

    def pick(role: str, tpl: dict, chosen: dict) -> dict:
        if chosen["family"]:
            w = chosen["weight"] or nearest_weight(lang, DOC_ROLES[role], chosen["family"],
                                                   tpl["weight"])
            return {"family": chosen["family"], "weight": w, "chosen": True}
        return {"family": tpl["family"], "weight": snap_weight(tpl["family"], tpl["weight"]),
                "chosen": False}

    name = pick("name", theme["name"], eff["name"])
    heading = pick("section", theme["heading"], eff["section"])
    body = pick("body", {"family": theme["body"], "weight": 400}, eff["body"])
    if body["chosen"]:
        body_bold = {"family": body["family"], "weight": EMPHASIS_WEIGHT, "chosen": True}
    else:
        body_bold = {"family": body["family"], "weight": snap_weight(body["family"], 700),
                     "chosen": False}
    role = ({"family": heading["family"], "weight": snap_weight(heading["family"], 700),
             "chosen": heading["chosen"]}
            if template_key.startswith("modern-") else dict(body_bold))
    faces = {"name": name, "heading": heading, "role": role, "body": body,
             "body_bold": body_bold}
    _one_face_per_word_name(faces)
    return {"lang": lang, "faces": faces, "accent": theme["accent"].lstrip("#").upper(),
            "accent_text": text_safe(theme["accent"]),
            "modern": template_key.startswith("modern-")}


def _one_face_per_word_name(faces: dict) -> None:
    """Two different faces must not share a Word (family name, bold) in one
    document: Word would draw both with whichever it finds first. It happens
    in the build: Archivo at 900 and the separate Archivo Black family are
    both "Archivo Black", not bold. The face the user CHOSE wins; the other
    role takes it. A Regular and its Bold share a NAME by design (RIBBI), so
    the bold flag is part of the key."""
    by_key: dict[tuple[str, bool], dict] = {}
    for role in ("name", "heading", "role", "body", "body_bold"):
        f = faces[role]
        key = word_font(f["family"], f["weight"])
        seen = by_key.get(key)
        if seen is None:
            by_key[key] = f
        elif (seen["family"], seen["weight"]) != (f["family"], f["weight"]):
            winner = f if f["chosen"] and not seen["chosen"] else seen
            for r in faces:
                if word_font(faces[r]["family"], faces[r]["weight"]) == key:
                    faces[r] = dict(winner)
            by_key[key] = winner


# ---- the pass ----------------------------------------------------------------

def _set(rpr, tag: str, attrs: dict | None) -> None:
    """Replace (or with None remove) one rPr child, at its schema position."""
    old = rpr.find(qn(f"w:{tag}"))
    if old is not None:
        rpr.remove(old)
    if attrs is None:
        return
    el = OxmlElement(f"w:{tag}")
    for k, v in attrs.items():
        el.set(qn(k), v)
    later = RPR_ORDER[RPR_ORDER.index(tag) + 1:]
    for i, child in enumerate(rpr):
        local = child.tag.rsplit("}", 1)[-1]
        if local in later:
            rpr.insert(i, el)
            return
    rpr.append(el)


def _style_rpr(document, style_id: str):
    for st in document.styles.element.findall(qn("w:style")):
        if st.get(qn("w:styleId")) == style_id:
            rpr = st.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                st.append(rpr)
            return rpr
    raise KeyError(f"master has no style {style_id!r} - rebuild word_masters")


def _face(rpr, family: str, weight: int, color: str | None, *, keep_color=False) -> None:
    wname, bold = word_font(family, weight)
    _set(rpr, "rFonts", {"w:ascii": wname, "w:hAnsi": wname, "w:eastAsia": wname,
                         "w:cs": wname})
    _set(rpr, "b", {} if bold else None)
    _set(rpr, "bCs", {} if bold else None)
    if not keep_color:
        _set(rpr, "color", {"w:val": color} if color else None)


def apply(document, resolved: dict) -> None:
    """Rewrite the role styles and the accent rule of a filled master."""
    f, text = resolved["faces"], resolved["accent_text"]
    name_color = text if resolved["modern"] else INK
    _face(_style_rpr(document, "Normal"), f["body"]["family"], f["body"]["weight"], None,
          keep_color=True)
    _face(_style_rpr(document, ST_NAME.replace(" ", "")), f["name"]["family"],
          f["name"]["weight"], name_color)
    _face(_style_rpr(document, ST_HEADING.replace(" ", "")), f["heading"]["family"],
          f["heading"]["weight"], text)
    _face(_style_rpr(document, ST_ROLE.replace(" ", "")), f["role"]["family"],
          f["role"]["weight"], None)
    _face(_style_rpr(document, ST_BODY_BOLD.replace(" ", "")), f["body_bold"]["family"],
          f["body_bold"]["weight"], None)
    _face(_style_rpr(document, ST_ACCENT_TEXT.replace(" ", "")), f["body"]["family"],
          f["body"]["weight"], text)
    for bottom in document.element.body.iter(qn("w:bottom")):
        if (bottom.get(qn("w:color")) or "").upper() == RULE_ACCENT:
            bottom.set(qn("w:color"), resolved["accent"])


def faces_used(resolved: dict) -> set[tuple[str, int]]:
    """Every (family, weight) the theme ASSIGNS to a role - whether or not
    this particular document has text in that role."""
    return {(f["family"], f["weight"]) for f in resolved["faces"].values()}


_STYLE_ROLE = {ST_NAME: "name", ST_HEADING: "heading", ST_ROLE: "role",
               ST_BODY_BOLD: "body_bold", ST_ACCENT_TEXT: "body"}


def faces_drawn(document, resolved: dict) -> set[tuple[str, int]]:
    """Every (family, weight) the filled document's TEXT draws - what step 6
    embeds (§6.3: "collect them while building the document", and nothing
    unused). A role style no run references - the Modern layout never uses
    CV Body Bold; a résumé with no experience never uses CV Role - adds
    nothing. Text in no role style is Normal, the body face."""
    by_id = {name.replace(" ", ""): role for name, role in _STYLE_ROLE.items()}
    roles: set[str] = set()
    for run in document.element.body.iter(qn("w:r")):
        text = "".join(t.text or "" for t in run.iter(qn("w:t")))
        if not text.strip():
            continue
        rpr = run.find(qn("w:rPr"))
        rstyle = rpr.find(qn("w:rStyle")) if rpr is not None else None
        roles.add(by_id.get(rstyle.get(qn("w:val")), "body") if rstyle is not None else "body")
    faces = resolved["faces"]
    return {(faces[r]["family"], faces[r]["weight"]) for r in roles}
