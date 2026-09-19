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
    }


def svg(text: str, family: str = "serif-display", size: int = 100,
        fill: str = "currentColor") -> str:
    """A complete inline <svg> for `text`, scaling with its container.

    `aria-hidden` and a `<title>`: the call site is responsible for keeping the
    real string in the DOM. See the module docstring.
    """
    o = outline(text, family, size)
    h = o["ascent"] + o["descent"]
    body = "".join(o["parts"])
    return (
        f'<svg class="outlined" viewBox="0 0 {o["width"]:.2f} {h:.2f}" '
        f'width="{o["width"]:.2f}" height="{h:.2f}" fill="{fill}" '
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
HERO_PARTIAL = ROOT / "app" / "templates" / "_hero_ar.html"


def build_hero() -> int:
    """Regenerate `app/templates/_hero_ar.html` from the Arabic hero strings.

    Re-run this if the hero copy changes — the outlines are a build artefact of
    those exact strings, and `test_hero_outline.py` fails if they drift apart.
    """
    sys.path.insert(0, str(ROOT))
    from app.labels import ui_t

    parts = [
        ("Your résumé,", False),
        ("designed", True),          # the .accent span — brand colour
        ("and done in minutes.", False),
    ]
    out = [
        "{# GENERATED by tools/outline_text.py --build-hero — do not edit.",
        "   Thmanyah Serif Display, converted to SVG paths. No font file is",
        "   served: its licence forbids web embedding that lets a visitor",
        "   download the font, and geometry is not a font. See FONTS.md.",
        "",
        "   The real strings stay in the DOM in the visually-hidden <span>",
        "   below, so screen readers, search engines and translation tools get",
        "   text; the SVG is aria-hidden. Regenerate with:",
        "     venv/Scripts/python tools/outline_text.py --build-hero #}",
        '<span class="sr-only">',
    ]
    arabic = [ui_t(text, "ar") for text, _ in parts]
    out.append("  " + " ".join(str(a) for a in arabic))
    out.append("</span>")
    out.append('<span class="hero-outlined" aria-hidden="true">')
    for (text, is_accent), ar in zip(parts, arabic):
        fill = "var(--brand)" if is_accent else "currentColor"
        out.append("  " + svg(str(ar), "serif-display", 100, fill))
    out.append("</span>")

    HERO_PARTIAL.write_text("\n".join(out) + "\n", encoding="utf-8")
    kb = HERO_PARTIAL.stat().st_size / 1024
    print(f"wrote {HERO_PARTIAL.relative_to(ROOT).as_posix()} "
          f"({len(parts)} outlined runs, {kb:.0f} KB)")
    for ar in arabic:
        print(f"   {ar}")
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
