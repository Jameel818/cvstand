"""The cover letter: ONE shared layout in every template's identity.

A cover letter is a page that has to look like it came from the same hand as
the CV beside it. 49 bespoke letter designs would be 49 more things to keep
in step; instead there is one layout (templates/resumes/letter.j2) that reads
the selected template's identity:

    - its HEADER: where the name sits (a coloured band, a coloured side
      column, or open on the page), in that surface's colour, with the name,
      headline and contact lines in the template's own colours and case;
    - its COLOURS: page, text, section titles, accent;
    - its ACCENT SHAPES: a full-height side column becomes a rail on the
      same side, an accent stripe under a band, an accent rule under an open
      header, an accent square before the subject line;
    - its FONTS: the name is a `.cv-name`, the subject a `.cv-section`, the
      rest body text under `.tpl` - the same role hooks the CV uses, so the
      font ribbon, the Arabic font policy and auto-fit all apply to the letter
      with no code of their own.

The identity is MEASURED from the rendered templates into letter_themes.json
by tools/build_letter_themes.py (see there), never transcribed.

OFF BY DEFAULT. The letter is `resume["cover_letter"]`, absent or
`enabled: false` for every résumé saved before it existed. No CV template
reads the key and normalize() never adds it, so the CV preview, PDF and Word
file are byte-identical whether a letter exists or not
(tests/test_cover_letter.py).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import rendering
from .labels import reset_lang, set_lang
from .schema import dir_of, lang_of, normalize

ROOT = Path(__file__).resolve().parent.parent
THEMES_PATH = Path(__file__).resolve().parent / "letter_themes.json"
DEMO_LETTER_PATHS = {
    "en": ROOT / "data" / "demo_letter.json",
    "ar": ROOT / "data" / "demo_letter_ar.json",
}

TEXT_FIELDS = ("recipient_name", "recipient_title", "company", "company_address", "date",
               "subject", "greeting", "closing", "signature")

#: Which document(s) an export carries. "cv" is the default and the only
#: thing an export did before the letter existed.
PARTS = ("cv", "letter", "both")


def enabled(data: dict[str, Any]) -> bool:
    cl = data.get("cover_letter")
    return isinstance(cl, dict) and bool(cl.get("enabled"))


def letter_of(data: dict[str, Any]) -> dict[str, Any]:
    """The letter with every field present: strings stripped, blank
    paragraphs dropped, the signature falling back to the résumé's name."""
    cl = data.get("cover_letter") if isinstance(data.get("cover_letter"), dict) else {}
    out = {k: (cl.get(k) or "").strip() if isinstance(cl.get(k), str) else "" for k in TEXT_FIELDS}
    paras = cl.get("paragraphs") if isinstance(cl.get("paragraphs"), list) else []
    out["paragraphs"] = [p.strip() for p in paras if isinstance(p, str) and p.strip()]
    if not out["signature"]:
        out["signature"] = (data.get("name") or "").strip()
    return out


def limits() -> dict[str, int]:
    """The schema's caps, for the builder's maxlength attributes."""
    from . import schema
    return {"field": schema.LETTER_FIELD_MAX, "address": schema.LETTER_ADDRESS_MAX,
            "paragraphs": schema.LETTER_MAX_PARAGRAPHS, "paragraph": schema.LETTER_PARAGRAPH_MAX}


def demo(lang: str) -> dict[str, Any]:
    path = DEMO_LETTER_PATHS.get(lang, DEMO_LETTER_PATHS["en"])
    return json.loads(path.read_text(encoding="utf-8"))


# ---- the identity -----------------------------------------------------------------

@lru_cache(maxsize=1)
def _themes() -> dict:
    return json.loads(THEMES_PATH.read_text(encoding="utf-8"))["templates"]


def _lum(hex6: str) -> float:
    h = hex6.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _first(*pairs: tuple[str | None, str], minimum: float) -> str:
    """The first colour that reads on its surface; the last one is the
    fallback that always does (black or white)."""
    for colour, on in pairs:
        if colour and contrast(colour, on) >= minimum:
            return colour
    return pairs[-1][0] or "#000000"


def _ink_on(bg: str) -> str:
    return "#FFFFFF" if contrast("#FFFFFF", bg) >= contrast("#14161A", bg) else "#14161A"


def theme(template_key: str, lang: str) -> dict[str, Any]:
    """Everything letter.j2 needs, with every colour checked against the
    surface it will actually be drawn on (the letter places the headline and
    contact next to the name, which the CV does not always do)."""
    m = _themes()[template_key][lang]
    page = m["page"]
    text = _first((m["text"], page), (_ink_on(page), page), minimum=4.5)
    accent = m["accent"]
    head_bg = m["head"].get("bg") if m["head"]["kind"] != "open" else None
    surface = head_bg or page
    name = _first((m["name"]["color"], surface), (_ink_on(surface), surface), minimum=3)
    title = _first((m["title"], surface), (accent, surface), (name, surface), minimum=3)
    contact = _first((m["contact"], surface), (text if not head_bg else None, surface),
                     (name, surface), minimum=4.5)
    heading = m["heading"] or {}
    head_colour = _first((heading.get("color"), page), (accent, page), (text, page), minimum=3)
    # A name that sat IN a coloured side column gets a band in that colour
    # (head_kind "side"), and the rail still marks the column's side.
    side = m["side"]
    stripe = accent if contrast(accent, surface) >= 1.5 else text
    return {
        "page": page, "text": text, "accent": accent,
        "head_bg": head_bg, "head_kind": m["head"]["kind"],
        "name": name, "title": title, "contact": contact,
        "name_caps": m["name"]["caps"], "name_tracking": m["name"]["tracking"],
        "centred": m["name"]["centred"],
        "name_font": m["name"]["family"], "name_weight": m["name"]["weight"],
        "heading": head_colour, "heading_caps": bool(heading.get("caps")),
        "heading_font": heading.get("family") or m["name"]["family"],
        "heading_weight": heading.get("weight") or 700,
        "body_font": m["body"],
        "rail": side, "stripe": stripe,
        "taj": m.get("taj", False),
    }


# ---- type size: the longest allowed letter stays on one page ------------------------

#: (most characters of greeting + paragraphs + closing, body px). The schema's
#: caps (schema.LETTER_*) bound the total; auto-fit does the rest.
BODY_SIZES = ((1400, 13.0), (2000, 12.5), (2600, 12.0), (10 ** 9, 11.5))


def body_px(letter: dict[str, Any]) -> float:
    n = len(letter["greeting"]) + len(letter["closing"]) + sum(len(p) for p in letter["paragraphs"])
    return next(px for limit, px in BODY_SIZES if n <= limit)


def recipient_lines(letter: dict[str, Any]) -> list[str]:
    lines = [letter["recipient_name"], letter["recipient_title"], letter["company"]]
    lines += letter["company_address"].splitlines()
    return [x.strip() for x in lines if x and x.strip()]


def contact_items(r: dict[str, Any]) -> list[str]:
    c = r.get("contact") or {}
    return [c[k] for k in ("email", "phone", "address", "site") if c.get(k)]


# ---- HTML -------------------------------------------------------------------------

def canvas_html(data: dict[str, Any], template_key: str) -> str:
    """The letter's `.tpl` page for `template_key`, in the document's language."""
    rendering._template_path(template_key)          # an unknown key raises as the CV does
    tpl = rendering._env().get_template("letter.j2")
    lang = lang_of(data)
    token = set_lang(lang)
    try:
        r = normalize(data)
        if dir_of(data) == "rtl":
            r = rendering._isolate_phones(r)
        letter = letter_of(data)
        return tpl.render(r=r, L=letter, th=theme(template_key, lang), key=template_key,
                          body_px=body_px(letter), recipient=recipient_lines(letter),
                          contact=contact_items(r))
    finally:
        reset_lang(token)


def document_html(data: dict[str, Any], template_key: str, *, for_pdf: bool = False) -> str:
    name = (data.get("name") or "").strip()
    return rendering.document_html(data, template_key, for_pdf=for_pdf,
                                   canvas=canvas_html(data, template_key),
                                   title=f"{name} — cover letter" if name else "Cover letter")
