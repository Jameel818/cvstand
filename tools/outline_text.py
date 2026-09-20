"""Render fixed Arabic text to SVG outlines, shipping no font file.

WHY THIS EXISTS

    Thmanyah is free for commercial use and its licence still forbids the one
    delivery method a web app would reach for. It permits embedding "only as
    part of a compiled, packaged, or obfuscated product" and prohibits making
    the font available so that end users can "extract, download, access, reuse,
    or redistribute the Font Software independently as font files, including
    through web embedding". A @font-face serving a .woff2 is that case: the
    file sits at a public URL and any visitor can save it.

    Outlines are the compliant route, and the user's own font brief names it:
    "export it as outlined vectors or flattened image, not as extractable
    font". An SVG path is geometry. There is no font file to extract, no
    @font-face, and nothing in the network tab but the page itself.

    This is therefore for FIXED text only — a hero headline, a wordmark. It is
    not a way to typeset the site. Body copy, headings and buttons stay on the
    OFL faces (FONTS.md), because outlining them would ship a wall of geometry
    no screen reader can read and no translator can change.

ACCESSIBILITY IS NOT OPTIONAL HERE

    Text converted to paths stops being text. Every call site must keep the
    real string in the DOM for assistive technology and mark the SVG
    `aria-hidden`. `_svg()` emits `<title>` too, but that is a belt, not the
    braces — see `landing.html`.

WHY HARFBUZZ AND NOT A GLYPH LOOKUP

    Arabic is cursive and contextual: every letter has up to four forms, and
    pairs like lam-alef are a single ligature. Mapping codepoints to glyphs
    one at a time produces disconnected letters in isolated forms — legible to
    nobody, and the exact failure this project already recorded as "letter
    -spacing does nothing to joined Arabic". HarfBuzz does the shaping the
    browser would have done.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Not under app/static/. These files are the project's own working copies,
#: used at BUILD time to produce geometry; nothing here is ever served.
THMANYAH = ROOT / "Fonts" / "Thmanyah" / "thmanyah typeface"


def _font_path(family: str) -> Path:
    stem = {
        "serif-display": "thmanyahserifdisplay/otf/thmanyahserifdisplay-Bold.otf",
        "sans-bold": "thmanyahsans/otf/thmanyahsans-Bold.otf",
        "sans-black": "thmanyahsans/otf/thmanyahsans-Black.otf",
    }[family]
    return THMANYAH / stem


def outline(text: str, family: str = "serif-display", size: int = 100) -> dict:
    """Shaped SVG path data for `text`, plus the box it occupies.

    Returns {"d": <path data>, "width": float, "height": float,
             "ascent": float, "descent": float} in `size` units.
    """
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    path = _font_path(family)
    data = path.read_bytes()

    face = hb.Face(data)
    font = hb.Font(face)
    font.scale = (size * 64, size * 64)          # 26.6 fixed point
    hb.ot_font_set_funcs(font)

    buf = hb.Buffer()
    buf.add_str(text)
    # Explicit rather than guessed: `guess_segment_properties` reads the first
    # strong character, so a headline starting with a digit or a Latin word
    # would be shaped left-to-right and come out reversed.
    buf.direction = "rtl"
    buf.script = "Arab"
    buf.language = "ar"
    hb.shape(font, buf)

    tt = TTFont(str(path))
    glyph_set = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    upem = tt["head"].unitsPerEm
    scale = size / upem

    pen_parts: list[str] = []
    x = y = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(pen)
        d = pen.getCommands()
        if d:
            # y is flipped: font space is y-up, SVG is y-down.
            tx = (x + pos.x_offset / 64)
            ty = (y + pos.y_offset / 64)
            pen_parts.append(
                f'<g transform="translate({tx:.2f},{ty:.2f}) '
                f'scale({scale:.6f},{-scale:.6f})"><path d="{d}"/></g>'
            )
        x += pos.x_advance / 64
        y += pos.y_advance / 64

    hhea = tt["hhea"]
    return {
        "parts": pen_parts,
        "width": x,
        "ascent": hhea.ascent * scale,
        "descent": abs(hhea.descent) * scale,
        # The em square itself. The SVG box is ascent+descent, which is TALLER
        # than the em (1.25x for this face), so a call site that sets the box
        # to 1em renders the type at 1/1.25 = 0.8em. Reported here so the size
        # can be expressed against the em, the way font-size is.
        "em": float(size),
    }


def space_advance(family: str = "serif-display", size: int = 100) -> float:
    """The font's own word space, in `size` units.

    The runs are laid out by CSS, so the gap between them has to be the space
    the FONT would have drawn. A hand-picked gap is a guess that goes wrong on
    the first headline with a different word count."""
    import uharfbuzz as hb

    face = hb.Face(_font_path(family).read_bytes())
    font = hb.Font(face)
    font.scale = (size * 64, size * 64)
    hb.ot_font_set_funcs(font)
    buf = hb.Buffer()
    buf.add_str("ا ا")          # alef SPACE alef - a real shaped space
    buf.direction, buf.script, buf.language = "rtl", "Arab", "ar"
    hb.shape(font, buf)
    adv = [p.x_advance / 64 for p in buf.glyph_positions]
    # middle glyph is the space
    return adv[1] if len(adv) == 3 else size * 0.25


def svg(text: str, family: str = "serif-display", size: int = 100,
        fill: str = "currentColor") -> str:
    """A complete inline <svg> for `text`, scaling with its container.

    `aria-hidden` and a `<title>`: the call site is responsible for keeping the
    real string in the DOM. See the module docstring.
    """
    o = outline(text, family, size)
    h = o["ascent"] + o["descent"]
    body = "".join(o["parts"])
    # --outline-box is the box's height in EMS. CSS multiplies 1em by it, so
    # the EM SQUARE ends up equal to the font-size and the outlines match the
    # size that live text at the same font-size would have been. Emitted per
    # run rather than hardcoded in the stylesheet because it is a property of
    # the FACE (ascent+descent over upem) and would silently go stale.
    return (
        f'<svg class="outlined" viewBox="0 0 {o["width"]:.2f} {h:.2f}" '
        f'width="{o["width"]:.2f}" height="{h:.2f}" fill="{fill}" '
        f'style="--outline-box:{h / o["em"]:.4f}" '
        f'role="img" aria-hidden="true" focusable="false" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="translate(0,{o["ascent"]:.2f})">{body}</g></svg>'
    )


#: The Arabic landing hero, outlined at build time.
#:
#: Built here rather than per request for two reasons. Shaping costs ~200ms and
#: would be paid on every cold landing page; and the production image would
#: then need fontTools, uharfbuzz AND the Thmanyah .otf inside it — a font file
#: on the server, which is the thing this whole approach exists to avoid.
#: The committed output is geometry. Nothing in the deployed tree is a font.
TEMPLATES = ROOT / "app" / "templates"
HERO_PARTIAL = TEMPLATES / "_hero_ar.html"

#: Every outlined block: partial name -> the msgids it is built from, each with
#: whether it takes the brand colour.
#:
#: FIXED headings only. Anything a user types, anything from the database, and
#: anything that varies per request stays live text on the OFL faces — outlines
#: cannot be searched, selected, translated or restyled, so they are a headline
#: treatment, not a way to typeset a site.
OUTLINED: dict[str, list[tuple[str, bool]]] = {
    "_hero_ar.html": [
        ("Your résumé,", False),
        ("designed", True),          # the .accent span — brand colour
        ("and done in minutes.", False),
    ],
    # The gallery's three h1 variants. Which one renders depends on the active
    # category, so all three are built and the template picks.
    "_gallery_head_ar.html": [("All templates", False)],
    "_gallery_head_modern_ar.html": [("Modern templates", False)],
    "_gallery_head_ats_ar.html": [("ATS-friendly templates", False)],
}


def _build_one(name: str, parts: list[tuple[str, bool]]) -> tuple[int, str]:
    from app.labels import ui_t

    arabic = [str(ui_t(text, "ar")) for text, _ in parts]
    out = [
        f"{{# GENERATED by tools/outline_text.py --build-hero — do not edit.",
        "   Thmanyah Serif Display, converted to SVG paths. No font file is",
        "   served: its licence forbids web embedding that lets a visitor",
        "   download the font, and geometry is not a font. See FONTS.md.",
        "",
        "   The real strings stay in the DOM in the visually-hidden <span>",
        "   below, so screen readers, search engines and translation tools get",
        "   text; the SVG is aria-hidden. Regenerate with:",
        "     venv/Scripts/python tools/outline_text.py --build-hero #}",
        '<span class="sr-only">',
        "  " + " ".join(arabic),
        "</span>",
        f'<span class="hero-outlined" aria-hidden="true"'
        f' style="--outline-space:{space_advance("serif-display", 100) / 100:.4f}">',
    ]
    # ONE RUN PER WORD, not one per phrase. A phrase is a single <svg> with a
    # fixed aspect ratio: it cannot break, so "قوالب متوافقة مع أنظمة التوظيف" was
    # one 1374-unit box that overflowed a phone the moment the size was
    # corrected. Arabic words are independent shaping units - letters never
    # join across a space - so splitting on spaces changes no glyph, and the
    # flex row can then wrap the way live text would.
    for (_text, is_accent), ar in zip(parts, arabic):
        fill = "var(--brand)" if is_accent else "currentColor"
        for word in ar.split():
            out.append("  " + svg(word, "serif-display", 100, fill))
    out.append("</span>")
    path = TEMPLATES / name
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path.stat().st_size, " ".join(arabic)


def build_hero() -> int:
    """Regenerate every outlined partial from the label catalogue.

    Re-run this if any of the copy changes — the outlines are a build artefact
    of those exact strings, and `test_hero_outline.py` fails if they drift.
    """
    sys.path.insert(0, str(ROOT))
    total = 0
    for name, parts in OUTLINED.items():
        size, text = _build_one(name, parts)
        total += size
        print(f"  {name:<32} {len(parts)} run(s)  {size/1024:5.1f} KB  {text}")
    print(f"wrote {len(OUTLINED)} partials, {total/1024:.0f} KB total")
    return 0


def main(argv: list[str]) -> int:
    if "--build-hero" in argv:
        return build_hero()
    if len(argv) < 2:
        print(__doc__)
        print("usage: outline_text.py <text> [family] [size]")
        print("       outline_text.py --build-hero")
        return 2
    text = argv[1]
    family = argv[2] if len(argv) > 2 else "serif-display"
    size = int(argv[3]) if len(argv) > 3 else 100
    out = svg(text, family, size)
    sys.stdout.reconfigure(encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
