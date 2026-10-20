"""The cover letter: ONE shared layout in every template's identity.

A cover letter is a page that has to look like it came from the same hand as
the CV beside it. 49 bespoke letter designs would be 49 more things to keep
in step; instead there is one layout (templates/resumes/_letter.j2) that reads
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


def readable(colour: str, on: str, minimum: float = 4.5) -> str:
    """`colour`, darkened (or lightened, on a dark surface) just far enough
    to reach `minimum` contrast on `on`: the template's HUE survives - a gold
    headline stays gold, only deeper - where swapping in another colour
    would lose the identity the letter is meant to carry."""
    if contrast(colour, on) >= minimum:
        return colour
    target = (255, 255, 255) if _lum(on) < 0.2 else (0, 0, 0)
    h = colour.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    for step in range(1, 21):
        t = step / 20
        mixed = "#" + "".join(f"{round(c + (g - c) * t):02X}" for c, g in zip(rgb, target))
        if contrast(mixed, on) >= minimum:
            return mixed
    return _ink_on(on)


def _ink_on(bg: str) -> str:
    return "#FFFFFF" if contrast("#FFFFFF", bg) >= contrast("#14161A", bg) else "#14161A"


def theme(template_key: str, lang: str) -> dict[str, Any]:
    """Everything _letter.j2 needs, with every colour checked against the
    surface it will actually be drawn on (the letter places the headline and
    contact next to the name, which the CV does not always do)."""
    m = _themes()[template_key][lang]
    page = m["page"]
    text = _first((m["text"], page), (_ink_on(page), page), minimum=4.5)
    accent = m["accent"]
    head_bg = m["head"].get("bg") if m["head"]["kind"] != "open" else None
    surface = head_bg or page
    name = _first((m["name"]["color"], surface), (_ink_on(surface), surface), minimum=3)
    # The headline (12.5-15px) and the subject line (14px) are bold but not
    # LARGE text (18.7px bold), so they need 4.5:1 - reached by deepening the
    # template's own colour (`readable`), not by replacing it.
    title = readable(_first((m["title"], surface), (accent, surface), (name, surface), minimum=3),
                     surface)
    contact = _first((m["contact"], surface), (text if not head_bg else None, surface),
                     (name, surface), minimum=4.5)
    heading = m["heading"] or {}
    head_colour = readable(_first((heading.get("color"), page), (accent, page), (text, page),
                                  minimum=3), page)
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
        # The template's own Arabic section-face flag, carried over as is
        # (rendering.RTL_TYPOGRAPHY). Spelled here and not in the .j2: the
        # count of templates carrying it is a gate (test_template_fonts).
        "split_class": " cv-sections-taj" if m.get("taj") else "",
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
    tpl = rendering._env().get_template("_letter.j2")
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


# ---- the letterhead: the CV's own page, its CV content taken out -------------------

def _classes(el) -> list[str]:
    return (el.get("class") or "").split()


def _text(el) -> str:
    import re
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _norm(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", s.replace(rendering._LRI, "").replace(rendering._PDI, "")).strip()


def letterhead_canvas(data: dict[str, Any], template_key: str,
                      body_px: float | None = None) -> str:
    """The letter page: the CV's canvas for this template - its bands, side
    columns, photo, name, headline, contact, colours, fonts and sizes, the
    template's OWN markup - with the CV's content taken out (every section,
    the summary, the stat band) and the plain letter body set where the main
    column's first section began (user, 2026-10-20: "the letter's header is
    the CV's own header block, not a measured approximation").

    What stays: everything outside a section, and a section that carries the
    contact details (a side column's "Contact" block is the letterhead's
    contact line in those templates)."""
    from lxml import html as LH

    lang = lang_of(data)
    cv = rendering.canvas_html(data, template_key)
    frag = LH.fragment_fromstring(cv, create_parent="div")
    tpl = next(e for e in frag.iter() if "tpl" in _classes(e))
    r = normalize(data)
    c = r.get("contact") or {}
    contact_vals = {_norm(v) for v in (c.get("email"), c.get("phone")) if v}
    name_el = next((e for e in tpl.iter() if "cv-name" in _classes(e)), None)

    def holds_contact(el) -> bool:
        t = _norm(_text(el))
        return any(v and v in t for v in contact_vals)

    heads = [e for e in tpl.iter() if "cv-section" in _classes(e)]

    def n_heads(el) -> int:
        return sum(1 for h in heads if h is el or any(a is el for a in h.iterancestors()))

    def group_of(h):
        """The section a heading opens: its highest ancestor holding no other
        section heading and not the name."""
        g = h
        while True:
            p = g.getparent()
            if p is None or p is tpl or n_heads(p) > 1:
                return g
            if name_el is not None and (p is name_el or any(a is p for a in name_el.iterancestors())):
                return g
            g = p

    removed = []
    main_anchor = None                      # the section the body replaces
    exp_role = _norm((r.get("experience") or [{}])[0].get("role") or "")
    for h in heads:
        g = group_of(h)
        if g.getparent() is None or holds_contact(g) or g in removed:
            continue
        if exp_role and exp_role in _norm(_text(g)) and main_anchor is None:
            main_anchor = g
        removed.append(g)
    # the summary and the stat band are content without a heading in some
    # templates (a summary under the name, a chip row in the header)
    summary = _norm(r.get("summary") or "")
    metrics = [_norm(a.get("label") or "") for a in r.get("achievements") or []]
    for el in list(tpl.iter()):
        if el in removed or any(a in removed for a in el.iterancestors()):
            continue
        t = _norm(_text(el))
        if summary and t == summary or (summary and t.startswith(summary[:40]) and len(t) <= len(summary) + 40):
            g = el
            while g.getparent() is not tpl and _norm(_text(g.getparent())) == t:
                g = g.getparent()
            removed.append(g)
        elif metrics and all(m in t for m in metrics) and not any(
                all(m in _norm(_text(k)) for m in metrics) for k in el if isinstance(k.tag, str)):
            removed.append(el)
    body = LH.fragment_fromstring(_letter_body(data, template_key, lang, body_px))
    ink = _text_colour(tpl, r)
    if ink:
        # the colour of the CV text the body replaces: a template that colours
        # each text element (white on a dark panel, modern-t14) is not dark
        # on dark for the letter
        body.set("style", (body.get("style") or "") + f" color:{ink};")
    first = _body_anchor(tpl, r, removed, main_anchor)
    if first is not None:
        # the body goes where the main column's first CV content stood: it
        # keeps that column's width, padding and position, whatever the layout
        import re
        st = first.get("style") or ""
        if "position:absolute" in st.replace(" ", ""):
            # a positioned panel (modern-t23): the body takes its place
            keep = [d for d in st.split(";") if re.match(
                r"\s*(position|left|right|top|inset[\w-]*|width|padding[\w-]*)\s*:", d)]
            body.set("style", (body.get("style") or "") + " " + ";".join(keep) + ";")
        else:
            # the section's own side padding (ats-t22 pads each section
            # "0 60px" inside an unpadded page): the body keeps the measure
            side = _side_padding(st)
            if side:
                body.set("style", (body.get("style") or "") + " " + side)
        first.addprevious(body)
    else:
        tpl.append(body)
    for g in removed:
        p = g.getparent()
        if p is not None:
            p.remove(g)
    _sweep(tpl, body, r)
    # a CV divider left below the body (modern-t13's hairline between two
    # sections): empty, small, after the body in reading order
    after = False
    for el in list(tpl.iter()):
        if el is body:
            after = True
            continue
        if (after and isinstance(el.tag, str) and len(el) == 0 and not _text(el)
                and not any(a is body for a in el.iterancestors())
                and not _structural(el, tpl) and not _has_media(el)):
            el.getparent().remove(el)
    if name_el is not None:
        sign = next((e for e in body.iter() if "cl-sign" in _classes(e)), None)
        if sign is not None:
            # the signature in the name's own face; its colour stays the
            # body's (a name drawn white on a band, modern-t13, would vanish
            # on the page)
            import re
            st = name_el.get("style") or ""
            keep = [d for d in st.split(";") if re.match(r"\s*(font-family|font-weight)\s*:", d)]
            sign.set("style", (sign.get("style") or "") + " " + ";".join(keep) + ";")
    tpl.set("class", " ".join(_classes(tpl) + ["cv-letter"]))
    from lxml import etree
    return etree.tostring(tpl, encoding="unicode", method="html")


def _chrome(el) -> bool:
    """A structural box of the page: a fill, a border, a fixed size, a
    positioned or flexible column. Its content may go; the box stays."""
    for decl in (el.get("style") or "").split(";"):
        k, _, v = decl.partition(":")
        k, v = k.strip().lower(), v.strip().lower()
        if k in ("background", "background-color") and v not in ("none", "transparent"):
            return True
        if k.startswith("border") and v not in ("0", "none"):
            return True
        if k in ("width", "height") and v not in ("auto",):
            return True
        if (k, v) in (("position", "absolute"), ("flex", "1")):
            return True
    return False


@lru_cache(maxsize=1)
def _labels() -> frozenset:
    from . import labels
    return frozenset(set(labels._AR) | {labels._key(v) for v in labels._AR.values()})


def _is_label(text: str) -> bool:
    """A fixed template label (a section name), English or Arabic."""
    from . import labels
    return bool(text) and labels._key(text) in _labels()


#: labels that belong to the letterhead (the contact block), never dropped
_CONTACT_LABELS = ("Contact", "Contact Details", "Contact Info", "Personal Information",
                   "Phone", "Email", "E-mail", "Address", "Web", "Website", "Portfolio",
                   "Location", "Studio")


def _is_label_contact(text: str) -> bool:
    from . import labels
    keys = {labels._key(x) for x in _CONTACT_LABELS}
    keys |= {labels._key(labels._AR[k]) for k in list(keys) if k in labels._AR}
    return labels._key(text) in keys


def _structural(el, tpl) -> bool:
    """A column, a band, a positioned panel: the page's own geometry."""
    import re
    if el.getparent() is tpl:
        return True
    st = (el.get("style") or "").replace(" ", "")
    if "position:absolute" in st or re.search(r"(?:^|;)flex:1", st):
        return True
    for m in re.finditer(r"(?:^|;)(?:width|height):([\d.]+)px", st):
        if float(m.group(1)) >= 150:
            return True
    return False


def _has_media(el) -> bool:
    """A photo (or its placeholder), an icon, or any box drawn 40px or more
    both ways - page furniture, never a skill's dots or bar."""
    import re
    for e in el.iter():
        if not isinstance(e.tag, str):
            continue
        if e.tag in ("img", "svg"):
            return True
        st = (e.get("style") or "").replace(" ", "")
        w = re.search(r"(?:^|;)width:([\d.]+)px", st)
        h = re.search(r"(?:^|;)height:([\d.]+)px", st)
        if w and h and float(w.group(1)) >= 40 and float(h.group(1)) >= 40:
            return True
    return False


def _content_values(r: dict[str, Any]) -> list[str]:
    """Every CV value that is content, not letterhead."""
    out = [a.get("label") for a in r.get("achievements") or []]
    for j in r.get("experience") or []:
        out += [j.get("role"), j.get("company"), *(j.get("bullets") or [])]
        out += [x for x in (j.get("start"), j.get("end")) if x and len(x) >= 4]
    for e in r.get("education") or []:
        out += [e.get("degree"), e.get("school")]
        out += [x for x in (e.get("start"), e.get("end")) if x and len(x) >= 4]
    for s in r.get("skills") or []:
        out += [s.get("name"), s.get("level")]
        if s.get("percent") is not None:
            out.append(f'{s["percent"]}%')
    out += [x.get("title") for x in r.get("recognition") or []]
    out += list(r.get("tools") or [])
    out += [x.get("name") for x in r.get("references") or []]
    for x in r.get("languages") or []:
        out += [x.get("name"), x.get("level")]
    out.append(r.get("summary"))
    return [_norm(v) for v in out if v and len(_norm(v)) >= 2]


def _sweep(tpl, body, r: dict[str, Any]) -> None:
    """Take out what is left of the CV's content: entries without a section
    heading of their own, a combined trailing block. An element holding a
    content value goes, climbing as far as - never into - a structural box
    (a fill, a border, a fixed size: the page's chrome stays) or anything
    holding the name, headline, contact or the letter body."""
    c = r.get("contact") or {}
    # compared without spaces: a name set on two lines ("Wren<br>Ashworth",
    # modern-t4) reads "WrenAshworth"
    marks = [_norm(v).replace(" ", "") for v in (r.get("name"), c.get("email"), c.get("phone")) if v]
    exact = {_norm(v) for v in (c.get("address"), c.get("site")) if v}
    # the headline: the FIRST element reading exactly the title (a job may
    # carry the same words - "Creative Lead" - further down)
    title = _norm(r.get("title") or "")
    headline = next((e for e in tpl.iter() if isinstance(e.tag, str) and title
                     and _norm(_text(e)) == title), None)
    head_set = {headline} | set(headline.iterancestors()) if headline is not None else set()

    def keeps(el) -> bool:
        """Holds the letterhead or the body: never removed."""
        if el is tpl or el is body or el in head_set or any(a is el for a in body.iterancestors()):
            return True
        t = _norm(_text(el))
        return any(m in t.replace(" ", "") for m in marks) or t in exact

    chrome = _chrome

    for v in _content_values(r):
        while True:
            hits = [e for e in tpl.iter() if isinstance(e.tag, str) and v in _norm(_text(e))
                    and not any(isinstance(k.tag, str) and v in _norm(_text(k)) for k in e)
                    and not any(a is body for a in e.iterancestors()) and not keeps(e)]
            if not hits:
                break
            g = hits[0]
            while (g.getparent() is not None and not keeps(g.getparent())
                   and not chrome(g.getparent())):
                g = g.getparent()
            g.getparent().remove(g)
    # what the content leaves behind: a skill's dots or bar in a row whose
    # words are gone, and a section heading over nothing
    changed = True
    while changed:
        changed = False
        for el in list(tpl.iter()):
            if not isinstance(el.tag, str) or keeps(el) or el.getparent() is None:
                continue
            if any(a is body for a in el.iterancestors()):
                continue
            kids = [k for k in el if isinstance(k.tag, str)]
            if kids and not _text(el) and not _has_media(el):
                # a text-less graphic (dots, a bar) - or an emptied bordered
                # box that only held one
                if not chrome(el) or (not _structural(el, tpl)
                                      and all(chrome(k) or not _text(k) for k in kids)):
                    el.getparent().remove(el)
                    changed = True
                    break
            if "cv-section" in _classes(el) or _is_label(_text(el)):
                # the heading with its own decoration (a ribbon, a pill);
                # some templates mark theirs only by its words (modern-t4)
                g = el
                while (g.getparent() is not None and not keeps(g.getparent())
                       and _text(g.getparent()) == _text(el) and not _has_media(g.getparent())):
                    g = g.getparent()
                nxt = g.getnext()
                orphan = nxt is None or not _text(nxt) or _is_label(_text(nxt)) or any(
                    "cv-section" in _classes(x) for x in nxt.iter() if isinstance(x.tag, str))
                if _text(g) == _text(el) and orphan:
                    g.getparent().remove(g)
                    changed = True
                    break


def _side_padding(style: str) -> str:
    """The horizontal padding of an inline style, as declarations."""
    import re
    out = []
    for decl in style.split(";"):
        k, _, v = decl.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "padding":
            vals = v.split()
            if len(vals) >= 2:
                left = vals[3] if len(vals) > 3 else vals[1]
                out.append(f"padding-left:{left}; padding-right:{vals[1]};")
        elif re.fullmatch(r"padding-(left|right|inline|inline-start|inline-end)", k):
            out.append(f"{k}:{v};")
    return " ".join(out)


def _text_colour(tpl, r: dict[str, Any]) -> str | None:
    """The colour the CV draws its first job bullet (or summary) in."""
    import re
    jobs = r.get("experience") or [{}]
    probe = _norm(((jobs[0].get("bullets") or [""])[0]) or r.get("summary") or "")
    if not probe:
        return None
    hit = None
    for e in tpl.iter():
        if isinstance(e.tag, str) and probe in _norm(_text(e)):
            hit = e                           # the deepest holder wins (iter is pre-order)
    for a in [hit] + list(hit.iterancestors()) if hit is not None else []:
        m = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", a.get("style") or "")
        if m:
            return m.group(1).strip()
    return None


def _body_anchor(tpl, r: dict[str, Any], removed: list, fallback):
    """The element the letter body goes in front of: in the column (the
    nearest structural box) holding the first job, its first child that holds
    CV content - a removed section, a section heading, the job itself."""
    title = _norm(r.get("title") or "")
    vals = [_norm(v) for v in ((r.get("experience") or [{}])[0].get("company"),
                                (r.get("experience") or [{}])[0].get("role")) if v]
    job = None
    for v in vals:
        hits = [e for e in tpl.iter() if isinstance(e.tag, str) and v in _norm(_text(e))
                and not any(isinstance(k.tag, str) and v in _norm(_text(k)) for k in e)
                and _norm(_text(e)) != title]
        if hits:
            job = hits[0]
            break
    if job is None:
        return fallback if fallback is not None else (removed[0] if removed else None)
    def row(el) -> bool:
        st = (el.get("style") or "").replace(" ", "")
        return "display:flex" in st and "flex-direction:column" not in st

    def column(el) -> bool:
        """A real column: structural, and if it sits in a row, a row of
        columns (not a timeline entry's cell beside its date - modern-t5)."""
        if row(el) or not (_chrome(el) and _structural(el, tpl)):
            return False
        p = el.getparent()
        if p is not None and p is not tpl and row(p):
            return all(_structural(k, tpl) for k in p if isinstance(k.tag, str))
        return True

    col = job.getparent()
    while col is not tpl and not column(col):
        col = col.getparent()
    if row(col):
        # a page laid out as a row of columns: the job's own column
        col = next(c for c in [job] + list(job.iterancestors()) if c.getparent() is col)
    # the elements themselves, not id()s: lxml hands out proxies, and the
    # id of a freed proxy is reused (the header once read as "removed")
    in_removed = {x for g in removed for x in g.iter()}
    name = _norm(r.get("name") or "")
    chosen = None
    while chosen is None:
        for child in col:
            if not isinstance(child.tag, str):
                continue
            holds_job = job is child or any(a is child for a in job.iterancestors())
            holds_name = bool(name) and name.replace(" ", "") in _norm(_text(child)).replace(" ", "")
            if holds_name and not holds_job:
                continue                       # the letterhead itself
            if holds_name and holds_job and child is not job:
                col = child                    # a wrapper of both: look inside
                break
            if (child in in_removed or any(x in in_removed for x in child.iter())
                    or any("cv-section" in _classes(x) for x in child.iter() if isinstance(x.tag, str))
                    or holds_job):
                chosen = child
                break
        else:
            return fallback
    # never inside a section that is about to be removed: the body would go
    # with it - in front of the outermost such section instead
    for a in [chosen] + list(chosen.iterancestors()):
        if any(a is g for g in removed):
            chosen = a
    return chosen


def _letter_body(data: dict[str, Any], template_key: str, lang: str,
                 px: float | None = None) -> str:
    tpl = rendering._env().get_template("_letter_body.j2")
    token = set_lang(lang)
    try:
        letter = letter_of(data)
        return tpl.render(L=letter, body_px=px or body_px(letter), recipient=recipient_lines(letter),
                          top_px=0)
    finally:
        reset_lang(token)


def document_html(data: dict[str, Any], template_key: str, *, for_pdf: bool = False) -> str:
    name = (data.get("name") or "").strip()
    return rendering.document_html(data, template_key, for_pdf=for_pdf,
                                   canvas=letterhead_canvas(data, template_key),
                                   title=f"{name} — cover letter" if name else "Cover letter")
