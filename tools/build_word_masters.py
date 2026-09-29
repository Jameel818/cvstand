"""Build the Word masters under word_masters/ from source.

    venv/Scripts/python tools/build_word_masters.py

Each master is a .docx carrying docxtpl (Jinja2) tags, filled at request time by
`app/exporters/docx.py` from the same resume dict the HTML templates use.

WHY A SCRIPT, NOT HAND-AUTHORED IN WORD
  word_masters/README.md originally specified authoring each master by hand in
  Word / LibreOffice. Generating them instead keeps the master reviewable as
  source rather than an opaque binary, makes a spec change one command to apply,
  and structurally removes docxtpl's most common failure: Word silently splits a
  run mid-tag, so `{{ r.name }}` reaches docxtpl as fragments it cannot parse.
  python-docx writes each tag as exactly one run, so that cannot happen.

DIVERGENCES FROM THE HTML FAMILY (Word has no CSS layout engine)
  1. One master per category, not per template — 49 HTML layouts collapse onto
     2 Word LAYOUTS. Since typography step 5 each download is still themed:
     the template's accent and fonts (or the user's chosen fonts) are written
     into the role styles at export (app/exporters/docx_theme.py). What does
     not carry over is the layout itself.
  2. The fonts written HERE (Georgia, Arial, Times New Roman) are only the
     masters' placeholders; an export replaces them. Step 6 embeds the faces
     an export names, so they render on a PC that lacks them.
  3. Ring / bar / slider skill graphics -> dot glyphs (●●●●○) plus the level
     word, both real selectable text.
  4. Modern is a single wide column: sidebar content (contact, skills, tools,
     languages) folds into the main flow in reading order.
  5. Stat chips are a fixed 4-cell borderless row, not one column per surviving
     chip — docxtpl's {%tc %} horizontal loop emits an empty <w:tr/> here.
     schema.normalize() already drops blank-metric chips and caps the row at 4,
     so cells past the chip count render empty and, being borderless, invisible.

ROLE STYLES (typography step 5)
  Every run whose face, weight or accent colour depends on the TEMPLATE or on
  the user's font choice carries a named character style instead of direct
  formatting: CV Name, CV Heading (section titles and stat metrics), CV Role,
  CV Body Bold, CV Accent Text; body text is the Normal style. At export,
  app/exporters/docx_theme.py rewrites those styles for the chosen template
  and fonts - one place per role, so no run can be missed. The fonts and
  colours written here are only the master's own placeholders.

  Such a run must NOT carry direct font, colour or bold: direct formatting
  beats a style, so a leftover `<w:b w:val="0"/>` (what python-docx writes for
  `run.bold = False`) would silently un-bold a heading. `_p` therefore leaves
  bold and italic unset unless asked. The accent-coloured contact rule keeps
  RULE_ACCENT as its colour so the export can find and recolour it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.exporters.docx_theme import (  # noqa: E402
    RULE_ACCENT, ST_ACCENT_TEXT, ST_BODY_BOLD, ST_HEADING, ST_NAME, ST_ROLE,
)
from app.labels import reset_lang, set_lang, t  # noqa: E402

OUT_DIR = ROOT / "word_masters"

CHIP_SLOTS = 4  # schema.normalize() caps the chip row at 4

# Arabic-capable substitutes. Neither master's Latin faces carry Arabic: Georgia
# has no Arabic glyphs at all, so an Arabic Modern resume set in it would fall
# back to whatever Word chose - the same silent substitution the HTML side
# solved by self-hosting fonts. These two ship with every Windows install and
# hold the register: Arial stays Arial (it has full Arabic coverage), and the
# Georgia display face becomes Times New Roman, the serif Word guarantees.
AR_BODY_FONT = "Arial"
AR_DISPLAY_FONT = "Times New Roman"


def L(text: str) -> str:
    """A master's own heading text, in the language being built.

    Reads the SAME catalogue the HTML templates use (app/labels.py), so a Word
    heading and its on-screen counterpart cannot drift apart.
    """
    return str(t(text))

INK = RGBColor(0x17, 0x18, 0x1A)
MUTED = RGBColor(0x55, 0x56, 0x5A)
ATS_ACCENT = RGBColor(0x00, 0x00, 0x00)      # ATS master stays monochrome
MODERN_ACCENT = RGBColor(0x1F, 0x3A, 0x5F)   # navy, stands in for 24 palettes


# ---------------------------------------------------------------- primitives

def _char_style(doc, name: str, *, font: str, bold: bool, color):
    """A role's character style, with the master's placeholder face and colour
    (the export rewrites both). All four rFonts slots, so neither Latin nor
    Arabic text falls through to another face; bCs so Arabic is bold too."""
    style = doc.styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
    style.font.name = font
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), font)
    if bold:
        style.font.bold = True
        style.element.rPr.insert_element_before(OxmlElement("w:bCs"), *_BCS_SUCCESSORS)
    if color is not None:
        style.font.color.rgb = color
    return style


def _doc(body_font: str, margin: float, *, head_font: str, role_font: str,
         name_color, accent) -> Document:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = body_font
    normal.font.size = Pt(10)
    normal.font.color.rgb = INK
    # python-docx sets only the latin face; pin the others so Word does not
    # substitute a fallback for punctuation and glyphs.
    rpr = normal.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rpr.set(qn(attr), body_font)
    # CONTENT FLOWS (user decision, typography step 6): with the fonts embedded,
    # a Word file may run to a second page, and that is accepted. Line spacing
    # stays Word's Auto default (Multiple 1.15 on each font's natural height),
    # never "Exactly", so no glyph or Arabic mark is clipped. What must not
    # happen at a page break: a heading alone at the bottom (every heading
    # keeps with next), a job title parted from its company/date line (both
    # keep with next), or a paragraph leaving one line alone - widow/orphan
    # control, set here on Normal so every paragraph inherits it.
    normal.paragraph_format.widow_control = True
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Inches(margin)
        section.left_margin = section.right_margin = Inches(margin)
    _char_style(doc, ST_NAME, font=head_font, bold=True, color=name_color)
    _char_style(doc, ST_HEADING, font=head_font, bold=True, color=accent)
    _char_style(doc, ST_ROLE, font=role_font, bold=True, color=None)
    _char_style(doc, ST_BODY_BOLD, font=body_font, bold=True, color=None)
    _char_style(doc, ST_ACCENT_TEXT, font=body_font, bold=False, color=accent)
    return doc


def _p(doc, text="", *, size=10, bold=None, italic=None, color=None,
       font=None, before=0, after=2, align=None, style=None, rstyle=None):
    """One paragraph, one run — so a docxtpl tag is never split across runs.

    `rstyle` is the run's ROLE style (see ROLE STYLES). Bold and italic stay
    unset unless given, so they cannot override the role style's."""
    para = doc.add_paragraph(style=style)
    run = para.add_run(text, style=rstyle)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    if font is not None:
        run.font.name = font
        run.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), font)
    fmt = para.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    if align is not None:
        fmt.alignment = align
    return para


def _tag(doc, tag: str):
    """A control-flow paragraph. docxtpl deletes the whole paragraph, so it must
    hold the tag and nothing else."""
    return _p(doc, tag, size=1, before=0, after=0)


# OOXML property elements are an ORDERED SEQUENCE, not a bag. Appending to the
# end of w:pPr / w:rPr / w:tblPr produces well-formed but schema-INVALID XML and
# Word refuses to open the document ("unreadable content") — python-docx and
# lxml both accept it happily, so this only shows up in Word. Each element must
# be inserted before its schema successors.
_PBDR_SUCCESSORS = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
                    "w:wordWrap", "w:overflowPunct", "w:topLinePunct",
                    "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
                    "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
                    "w:contextualSpacing", "w:jc", "w:rPr", "w:sectPr")
_RSPACING_SUCCESSORS = ("w:w", "w:kern", "w:position", "w:sz", "w:szCs",
                        "w:highlight", "w:u", "w:effect", "w:bdr", "w:shd",
                        "w:vertAlign", "w:rtl", "w:cs", "w:lang")
_TBLBORDERS_SUCCESSORS = ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook",
                          "w:tblCaption", "w:tblDescription")


# Schema successors for the RTL elements, same rule as the three above: OOXML
# property elements are an ORDERED SEQUENCE and Word rejects a document whose
# order is wrong, while python-docx and lxml parse it happily.
_BIDI_SUCCESSORS = ("w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
                    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap",
                    "w:jc", "w:textDirection", "w:textAlignment",
                    "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle",
                    "w:rPr", "w:sectPr", "w:pPrChange")
_RTL_SUCCESSORS = ("w:cs", "w:em", "w:lang", "w:eastAsianLayout",
                   "w:specVanish", "w:oMath")
_SZCS_SUCCESSORS = ("w:highlight", "w:u", "w:effect", "w:bdr", "w:shd",
                    "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em",
                    "w:lang", "w:eastAsianLayout", "w:specVanish", "w:oMath")
_BCS_SUCCESSORS = ("w:i", "w:iCs", "w:caps", "w:smallCaps", "w:strike",
                   "w:dstrike", "w:outline", "w:shadow", "w:emboss", "w:imprint",
                   "w:noProof", "w:snapToGrid", "w:vanish", "w:webHidden",
                   "w:color", "w:spacing", "w:w", "w:kern", "w:position",
                   "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr",
                   "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs")
_BIDIVISUAL_SUCCESSORS = ("w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd",
                          "w:tblBorders", "w:shd", "w:tblLayout", "w:tblCellMar",
                          "w:tblLook", "w:tblCaption", "w:tblDescription")
_SECT_BIDI_SUCCESSORS = ("w:rtlGutter", "w:docGrid", "w:printerSettings",
                         "w:sectPrChange")


def _apply_rtl(doc, body_font: str):
    """Turn a finished document right-to-left.

    A POST-PASS rather than a flag threaded through every primitive: it touches
    every paragraph, run and table by construction, so a component added later
    cannot be left half-mirrored - the failure that would otherwise be one
    English-aligned paragraph nobody notices.

    Four different things have to be said, and saying only the obvious one is
    the usual mistake:

      w:bidi   on w:sectPr   the section reads right-to-left
      w:bidi   on w:pPr      the paragraph does, so its default alignment flips
      w:rtl    on w:rPr      the RUN does; without it Word lays the glyphs out
                             left-to-right inside a right-aligned paragraph
      w:rFonts w:cs=         Arabic is a COMPLEX SCRIPT: Word takes its face
                             from the `cs` attribute, not `ascii`/`hAnsi`, so a
                             run whose ascii font has no Arabic renders in a
                             substituted face unless cs is set too. w:szCs and
                             w:bCs are the same story for size and weight.
    """
    for section in doc.sections:
        sect = section._sectPr
        if sect.find(qn("w:bidi")) is None:
            el = OxmlElement("w:bidi")
            sect.insert_element_before(el, *_SECT_BIDI_SUCCESSORS)

    for para in doc.element.body.iter(qn("w:p")):
        ppr = para.find(qn("w:pPr"))
        if ppr is None:
            ppr = OxmlElement("w:pPr")
            para.insert(0, ppr)
        if ppr.find(qn("w:bidi")) is None:
            ppr.insert_element_before(OxmlElement("w:bidi"), *_BIDI_SUCCESSORS)

    for run in doc.element.body.iter(qn("w:r")):
        rpr = run.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            run.insert(0, rpr)
        if rpr.find(qn("w:rtl")) is None:
            rpr.insert_element_before(OxmlElement("w:rtl"), *_RTL_SUCCESSORS)
        # complex-script face, size and weight must mirror the latin ones. A
        # run with no direct face takes it from its style - Normal or a role
        # style, both of which carry w:cs (see _doc / _char_style); forcing
        # one here would beat the style and pin every run to the body face.
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is not None and fonts.get(qn("w:ascii")):
            fonts.set(qn("w:cs"), fonts.get(qn("w:ascii")))
        sz = rpr.find(qn("w:sz"))
        if sz is not None and rpr.find(qn("w:szCs")) is None:
            szcs = OxmlElement("w:szCs")
            szcs.set(qn("w:val"), sz.get(qn("w:val")))
            rpr.insert_element_before(szcs, *_SZCS_SUCCESSORS)
        b = rpr.find(qn("w:b"))
        if b is not None and rpr.find(qn("w:bCs")) is None:
            bcs = OxmlElement("w:bCs")
            if b.get(qn("w:val")) is not None:
                bcs.set(qn("w:val"), b.get(qn("w:val")))
            rpr.insert_element_before(bcs, *_BCS_SUCCESSORS)

    for tbl in doc.element.body.iter(qn("w:tbl")):
        tbl_pr = tbl.find(qn("w:tblPr"))
        if tbl_pr is not None and tbl_pr.find(qn("w:bidiVisual")) is None:
            tbl_pr.insert_element_before(OxmlElement("w:bidiVisual"),
                                         *_BIDIVISUAL_SUCCESSORS)
    return doc


def _rule(para, color="BFBFBF", size=6):
    """Bottom border on a paragraph — Word's equivalent of a hairline rule."""
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    para._p.get_or_add_pPr().insert_element_before(pbdr, *_PBDR_SUCCESSORS)
    return para


def _letter_spacing(run, twentieths: int):
    """Track-out a run. w:spacing sits between w:color and w:sz in CT_RPr."""
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:val"), str(twentieths))
    run._r.get_or_add_rPr().insert_element_before(spacing, *_RSPACING_SUCCESSORS)
    return run


def _borderless(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tbl_pr.insert_element_before(borders, *_TBLBORDERS_SUCCESSORS)
    return table


def _cell_p(cell, text, *, first, size=10, color=None, font=None, after=0,
            rstyle=None):
    para = cell.paragraphs[0] if first else cell.add_paragraph()
    run = para.add_run(text, style=rstyle)
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    if font is not None:
        run.font.name = font
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(after)
    return para


# ---------------------------------------------------------------- components

def _heading(doc, label: str, *, ruled=True, before=7, after=3):
    para = _p(doc, label, size=9, rstyle=ST_HEADING, before=before, after=after)
    # Word repaginates freely with variable-length user content, so a heading
    # must be bound to what follows it or it strands alone at a page break.
    para.paragraph_format.keep_with_next = True
    para.runs[0].font.all_caps = True
    _letter_spacing(para.runs[0], 24)  # 1.2px-equivalent, per the ATS label spec
    if ruled:
        _rule(para)
    return para


def _chip_row(doc):
    """Fixed 4-cell borderless row. A slot past the chip count renders both its
    metric and its caption as "" — the whole chip disappears together, never a
    floating caption with no number."""
    table = doc.add_table(rows=1, cols=CHIP_SLOTS)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _borderless(table)
    for i, cell in enumerate(table.row_cells(0)):
        guard = f'r.achievements[{i}].{{}} if r.achievements|length > {i} else ""'
        _cell_p(cell, "{{ %s }}" % guard.format("metric"),
                first=True, size=16, rstyle=ST_HEADING)
        _cell_p(cell, "{{ %s }}" % guard.format("label"),
                first=False, size=8.5, color=MUTED, after=4)
    return table


def _experience(doc, *, meta_style=None, meta_color=None):
    _tag(doc, "{%p for job in r.experience %}")
    role = _p(doc, "{{ job.role }}", size=11, rstyle=ST_ROLE, before=5, after=0)
    role.paragraph_format.keep_with_next = True  # never split a role from its dates
    # The whole meta line is guarded, not just its separators: "+ Add role" then
    # typing the job title leaves company/location/start/end all blank, and the
    # inner conditionals would then emit an EMPTY PARAGRAPH — a stray blank line
    # in Word where the HTML drops the row entirely, costing vertical space in a
    # master tuned to fit exactly one page. Safe as a `{%p if %}` here because
    # this paragraph is in the document body; the zero-paragraph trap that broke
    # the chip row applies to TABLE CELLS, which must keep at least one.
    _tag(doc, "{%p if job.company or job.location or job.start or job.end %}")
    meta = _p(doc, "{{ job.company }}{% if job.company and job.location %}, {% endif %}"
              "{{ job.location }}{% if (job.company or job.location) and "
              "(job.start or job.end) %}  ·  {% endif %}{{ job.start }}"
              "{% if job.start and job.end %} - {% endif %}{{ job.end }}",
              size=9, rstyle=meta_style, color=meta_color, after=2)
    meta.paragraph_format.keep_with_next = True  # nor from its first bullet
    _tag(doc, "{%p endif %}")
    _tag(doc, "{%p for b in job.bullets %}")
    _p(doc, "{{ b }}", size=10, after=0, style="List Bullet")
    _tag(doc, "{%p endfor %}")
    _tag(doc, "{%p endfor %}")


def _skills(doc):
    """Name, level word and dot glyphs all as real selectable text — the Word
    stand-in for the ring / bar / slider graphics."""
    _tag(doc, "{%p for sk in r.skills %}")
    _p(doc, "{{ sk.name }}{% if sk.level %} — {{ sk.level }}{% endif %}"
            "{% if sk.dot_glyphs %}   {{ sk.dot_glyphs }}{% endif %}", size=10, after=0)
    _tag(doc, "{%p endfor %}")


def _education(doc):
    _tag(doc, "{%p for ed in r.education %}")
    _p(doc, "{{ ed.degree }}{% if ed.school %} — {{ ed.school }}{% endif %}"
            "{% if ed.start or ed.end %}, {{ ed.start }}"
            "{% if ed.start and ed.end %} - {% endif %}{{ ed.end }}{% endif %}"
            "{% if ed.gpa %} · GPA {{ ed.gpa }}{% endif %}", size=10, after=0)
    _tag(doc, "{%p endfor %}")


def _tail_sections(doc, *, head_before=7):
    """Certifications / Tools / Languages — each guarded so an absent one leaves
    no orphan heading."""
    _tag(doc, "{%p if r.recognition %}")
    _heading(doc, L("Certifications"), before=head_before)
    _tag(doc, "{%p for rec in r.recognition %}")
    _p(doc, "{{ rec.title }}{% if rec.detail %} — {{ rec.detail }}{% endif %}",
       size=10, after=0)
    _tag(doc, "{%p endfor %}")
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.tools %}")
    _heading(doc, L("Tools"), before=head_before)
    _p(doc, '{{ r.tools | join("  ·  ") }}', size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.languages %}")
    _heading(doc, L("Languages"), before=head_before)
    _tag(doc, "{%p for lang in r.languages %}")
    _p(doc, "{{ lang.name }}{% if lang.level %} — {{ lang.level }}{% endif %}"
            "{% if lang.dot_glyphs %}   {{ lang.dot_glyphs }}{% endif %}",
       size=10, after=0)
    _tag(doc, "{%p endfor %}")
    _tag(doc, "{%p endif %}")


# ------------------------------------------------------------------ masters

def build_ats(path: Path, lang: str = "en"):
    """Genuinely single column, canonical single-word headings, plain-hyphen
    date ranges, monochrome. Mirrors the on-screen ATS layout closely."""
    token = set_lang(lang)
    try:
        return _build_ats(path, lang)
    finally:
        reset_lang(token)


def _build_ats(path: Path, lang: str):
    font = AR_BODY_FONT if lang == "ar" else "Arial"
    doc = _doc(font, 0.62, head_font=font, role_font=font, name_color=None,
               accent=ATS_ACCENT)

    _p(doc, "{{ r.name }}", size=22, rstyle=ST_NAME, after=2)
    _tag(doc, "{%p if r.title %}")
    _p(doc, "{{ r.title }}", size=11, rstyle=ST_BODY_BOLD, color=MUTED, after=2)
    _tag(doc, "{%p endif %}")
    _tag(doc, "{%p if r.contact_line %}")
    _p(doc, "{{ r.contact_line }}", size=9, color=MUTED, after=4)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.summary %}")
    _heading(doc, L("Summary"))
    _p(doc, "{{ r.summary }}", size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.achievements %}")
    _heading(doc, L("Key Achievements"))
    _chip_row(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.experience %}")
    _heading(doc, L("Experience"))
    _experience(doc, meta_color=MUTED)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.skills %}")
    _heading(doc, L("Skills"))
    _skills(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.education %}")
    _heading(doc, L("Education"))
    _education(doc)
    _tag(doc, "{%p endif %}")

    _tail_sections(doc)
    if lang == "ar":
        _apply_rtl(doc, font)
    doc.save(str(path))
    return path


def build_modern(path: Path, lang: str = "en"):
    """See _build_modern; this only binds the language for L()."""
    token = set_lang(lang)
    try:
        return _build_modern(path, lang)
    finally:
        reset_lang(token)


def _build_modern(path: Path, lang: str = "en"):
    """One wide column. Sidebar content folds into the main flow in reading
    order; Georgia display heads over Arial body; navy accent.

    Spacing here is tighter than the ATS master because the optional photo adds
    ~79pt: the layout is tuned to fit WITH a photo, so the (more common)
    photo-less resume simply carries more bottom margin. Sized once here rather
    than conditionally, since a static master cannot vary its own spacing."""
    body_font = AR_BODY_FONT if lang == "ar" else "Arial"
    # Georgia carries no Arabic glyphs at all, so the Arabic Modern master
    # takes the serif Word guarantees instead. Same register, real coverage.
    head_font = AR_DISPLAY_FONT if lang == "ar" else "Georgia"
    doc = _doc(body_font, 0.5, head_font=head_font, role_font=head_font,
               name_color=MODERN_ACCENT, accent=MODERN_ACCENT)
    HEAD_BEFORE = 4

    # Photo slot — Modern only. 16 Modern templates have one; NO ATS template
    # does, because images defeat resume parsers, so ats_standard has none
    # either. The guard is on `photo` (falsy when absent OR when the upload has
    # been deleted), not on r.photo_url, so a dangling URL leaves no blank gap.
    _tag(doc, "{%p if photo %}")
    _p(doc, "{{ photo }}", after=3)
    _tag(doc, "{%p endif %}")

    _p(doc, "{{ r.name }}", size=23, rstyle=ST_NAME, after=1)
    _tag(doc, "{%p if r.title %}")
    # Upright, not italic: none of the built faces has an italic, so Word
    # would slant the glyphs itself - a faked style (user, 2026-09-27).
    _p(doc, "{{ r.title }}", size=11, color=MUTED, after=2)
    _tag(doc, "{%p endif %}")
    _tag(doc, "{%p if r.contact_line %}")
    _rule(_p(doc, "{{ r.contact_line }}", size=9, color=MUTED, after=4),
          color=RULE_ACCENT, size=8)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.summary %}")
    _heading(doc, L("Profile"), before=HEAD_BEFORE)
    _p(doc, "{{ r.summary }}", size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.achievements %}")
    _heading(doc, L("Key Achievements"), before=HEAD_BEFORE)
    _chip_row(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.experience %}")
    _heading(doc, L("Experience"), before=HEAD_BEFORE)
    _experience(doc, meta_style=ST_ACCENT_TEXT)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.skills %}")
    _heading(doc, L("Skills"), before=HEAD_BEFORE)
    _skills(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.education %}")
    _heading(doc, L("Education"), before=HEAD_BEFORE)
    _education(doc)
    _tag(doc, "{%p endif %}")

    _tail_sections(doc, head_before=HEAD_BEFORE)
    if lang == "ar":
        _apply_rtl(doc, body_font)
    doc.save(str(path))
    return path


# ------------------------------------------------------------ the Word LAYOUTS
#
# docs/WORD_LAYOUTS_PLAN.md. The Modern templates' SHAPE in Word: a side
# column, a band, a plain header, a gutter. Two masters (+ RTL twins) serve all
# 24, because what differs per template is DATA, measured into
# app/word_layouts.json by tools/build_word_layouts.py:
#
#   modern_layout   one 2x2 table: [top side | top main] over [side | main].
#                   Each cell loops over ITS ordered item list (lay.top_side,
#                   lay.side, ...), so every template's sections land in the
#                   same column and order as its PDF. At export
#                   app/exporters/docx_layout.py merges the top row (a band
#                   across both columns, an open layout's header), drops an
#                   empty row or the side column, swaps the columns for a
#                   right-hand side column, sets widths, fills and colours.
#   modern_gutter   modern-t19: section titles in a narrow gutter beside
#                   their content, one table row per section.
#
# Every cell is written from ONE dispatch (_cell_items), so a section looks
# the same wherever a template puts it; only its cell's styles differ.

from app.exporters.docx_theme import (  # noqa: E402
    BAR_OFF, BAR_ON, LAYOUT_CELLS, PS_CONTACT, ST_CONTACT, cell_style, head_para_style,
)

BAR_SEGMENTS = 5          # one per dot: the level is dots_for(level) of 5


def _cp(box, text="", *, size=10, rstyle=None, pstyle=None, before=0, after=2):
    """One paragraph, one run, in a cell (or the body): `_p` for containers."""
    para = box.add_paragraph(style=pstyle)
    run = para.add_run(text, style=rstyle)
    if size is not None:
        run.font.size = Pt(size)
    fmt = para.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    return para


def _cruns(box, parts, *, size=10, after=1, pstyle=None, keep=False):
    """One paragraph of several runs, each (text, style) - a tag never spans runs."""
    para = box.add_paragraph(style=pstyle)
    for text, style in parts:
        run = para.add_run(text, style=style)
        run.font.size = Pt(size)
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(after)
    if keep:
        para.paragraph_format.keep_with_next = True
    return para


def _ctag(box, tag: str):
    return _cp(box, tag, size=1, after=0)


def _mark_size(para, half_points: int):
    """The paragraph MARK's size: an empty paragraph is as tall as its mark."""
    ppr = para._p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)          # w:rPr is last in CT_PPr but for sectPr/pPrChange
    for tag in ("w:sz", "w:szCs"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), str(half_points))
        rpr.append(el)


def _cell_margins(table, twips: int = 0):
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(twips))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")


def _pct_width(table, cells_pct):
    """Percent widths (fiftieths of a percent), fixed layout: the bar and chip
    rows fill whatever column they are in."""
    tbl_pr = table._tbl.tblPr
    tblw = tbl_pr.find(qn("w:tblW"))
    if tblw is None:
        tblw = OxmlElement("w:tblW")
        tbl_pr.insert_element_before(tblw, "w:jc", "w:tblCellSpacing", "w:tblInd",
                                     "w:tblBorders", "w:shd", "w:tblLayout", "w:tblCellMar",
                                     "w:tblLook", "w:tblCaption", "w:tblDescription")
    tblw.set(qn("w:type"), "pct")
    tblw.set(qn("w:w"), "5000")
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.insert_element_before(layout, "w:tblCellMar", "w:tblLook", "w:tblCaption",
                                 "w:tblDescription")
    for cell, pct in zip(table.rows[0].cells, cells_pct):
        tcw = cell._tc.get_or_add_tcPr().get_or_add_tcW()
        tcw.set(qn("w:type"), "pct")
        tcw.set(qn("w:w"), str(pct))


def _bar(box):
    """A skill bar: BAR_SEGMENTS borderless cells, filled BAR_ON up to the
    level and BAR_OFF after it (the fill is a docxtpl expression). Row height
    comes from a tiny paragraph mark - never an exact height."""
    table = box.add_table(rows=1, cols=BAR_SEGMENTS)
    _borderless(table)
    _cell_margins(table, 0)
    _pct_width(table, [5000 // BAR_SEGMENTS] * BAR_SEGMENTS)
    for i, cell in enumerate(table.rows[0].cells):
        tc_pr = cell._tc.get_or_add_tcPr()
        colour = "{{ '%s' if sk.dots > %d else '%s' }}" % (BAR_ON, i, BAR_OFF)
        # a hairline border in the segment's own colour: adjacent fills alone
        # leave a light seam between the segments on screen
        borders = OxmlElement("w:tcBorders")
        for edge in ("left", "right"):
            b = OxmlElement(f"w:{edge}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "4")
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), colour)
            borders.append(b)
        tc_pr.insert_element_before(borders, "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
                                    "w:tcFitText", "w:vAlign", "w:hideMark")
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), colour)
        tc_pr.insert_element_before(shd, "w:noWrap", "w:tcMar", "w:textDirection",
                                    "w:tcFitText", "w:vAlign", "w:hideMark")
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)
        _mark_size(para, 8)          # 4pt: the bar's thickness
    trailing = box.paragraphs[-1]    # python-docx adds one after a nested table
    trailing.paragraph_format.space_after = Pt(0)
    _mark_size(trailing, 6)
    return table


def _chips(box, cell: str):
    """The stat chips, as in the Modern master: a fixed 4-cell row whose empty
    slots render nothing (never a caption without a number)."""
    table = box.add_table(rows=1, cols=CHIP_SLOTS)
    _borderless(table)
    _pct_width(table, [5000 // CHIP_SLOTS] * CHIP_SLOTS)
    for i, c in enumerate(table.row_cells(0)):
        guard = f'r.achievements[{i}].{{}} if r.achievements|length > {i} else ""'
        _cell_p(c, "{{ %s }}" % guard.format("metric"), first=True, size=15,
                rstyle=cell_style(cell, "Metric"))
        _cell_p(c, "{{ %s }}" % guard.format("label"), first=False, size=8.5,
                rstyle=cell_style(cell, "Text"), after=2)
    trailing = box.paragraphs[-1]
    trailing.paragraph_format.space_after = Pt(0)
    _mark_size(trailing, 8)


def _cell_items(box, cell: str, source: str | None, *, headings: bool = True):
    """Everything a cell can hold, dispatched on `it.k`, in the order of the
    list `lay.<source>` (None: the caller's own loop defines `it`)."""
    S = lambda role: cell_style(cell, role)   # noqa: E731
    if source:
        _ctag(box, "{%%p for it in lay.%s %%}" % source)

    _ctag(box, "{%p if it.k == 'name' %}")
    _cp(box, "{{ r.name }}", size=None, rstyle=S("Name"), after=2)
    _ctag(box, "{%p endif %}")
    _ctag(box, "{%p if it.k == 'title' %}")
    _cp(box, "{{ r.title }}", size=11, rstyle=S("Text"), after=4)
    _ctag(box, "{%p endif %}")
    _ctag(box, "{%p if it.k == 'photo' %}")
    _cp(box, "{{ photo }}", size=None, after=6)
    _ctag(box, "{%p endif %}")
    _ctag(box, "{%p if it.k == 'contact_line' %}")
    _cp(box, "{{ r.contact_line }}", size=9, rstyle=ST_CONTACT, pstyle=PS_CONTACT, after=4)
    _ctag(box, "{%p endif %}")

    if headings:
        _ctag(box, "{%p if it.label %}")
        head = _cp(box, "{{ it.text }}", size=None, rstyle=S("Heading"),
                   pstyle=head_para_style(cell), before=8, after=3)
        head.paragraph_format.keep_with_next = True
        _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'contact' %}")
    _ctag(box, "{%p for c in r.contact_items %}")
    _cp(box, "{{ c }}", size=9.5, rstyle=S("Text"), after=1)
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'summary' %}")
    _cp(box, "{{ r.summary }}", size=10, rstyle=S("Text"), after=2)
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'achievements' %}")
    _chips(box, cell)
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'experience' %}")
    _ctag(box, "{%p for job in it.jobs %}")
    role = _cp(box, "{{ job.role }}", size=11, rstyle=S("Role"), before=5, after=0)
    role.paragraph_format.keep_with_next = True     # never split a role from its dates
    _ctag(box, "{%p if job.company or job.location or job.start or job.end %}")
    meta = _cp(box, "{{ job.company }}{% if job.company and job.location %}, {% endif %}"
                    "{{ job.location }}{% if (job.company or job.location) and "
                    "(job.start or job.end) %}  ·  {% endif %}{{ job.start }}"
                    "{% if job.start and job.end %} - {% endif %}{{ job.end }}",
               size=9, rstyle=S("Accent"), after=2)
    meta.paragraph_format.keep_with_next = True     # nor from its first bullet
    _ctag(box, "{%p endif %}")
    _ctag(box, "{%p for b in job.bullets %}")
    _cp(box, "{{ b }}", size=10, rstyle=S("Text"), pstyle="List Bullet", after=0)
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'education' %}")
    _ctag(box, "{%p for ed in r.education %}")
    _cruns(box, [("{{ ed.degree }}", S("Bold")),
                 ("{% if ed.school %} — {{ ed.school }}{% endif %}"
                  "{% if ed.start or ed.end %}, {{ ed.start }}"
                  "{% if ed.start and ed.end %} - {% endif %}{{ ed.end }}{% endif %}"
                  "{% if ed.gpa %} · GPA {{ ed.gpa }}{% endif %}", S("Text"))], after=2)
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'skills' %}")
    _ctag(box, "{%p for sk in r.skills %}")
    # name AND level as real text; the graphic beside it follows the template:
    # bars where the PDF has bars, dots where it has dots or rings
    _cruns(box, [("{{ sk.name }}", S("Text")),
                 ("{% if sk.level %} — {{ sk.level }}{% endif %}", S("Text")),
                 ("{% if not lay.bars and sk.dot_glyphs %}   {{ sk.dot_glyphs }}{% endif %}",
                  S("Accent"))], after=1)
    _ctag(box, "{%p if lay.bars and sk.dots %}")
    _bar(box)
    _ctag(box, "{%p endif %}")
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'recognition' %}")
    _ctag(box, "{%p for rec in r.recognition %}")
    _cruns(box, [("{{ rec.title }}", S("Bold")),
                 ("{% if rec.detail %} — {{ rec.detail }}{% endif %}", S("Text"))], after=2)
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'tools' %}")
    _cp(box, '{{ r.tools | join("  ·  ") }}', size=10, rstyle=S("Text"))
    _ctag(box, "{%p endif %}")

    _ctag(box, "{%p if it.k == 'languages' %}")
    _ctag(box, "{%p for lang in r.languages %}")
    _cruns(box, [("{{ lang.name }}", S("Text")),
                 ("{% if lang.level %} — {{ lang.level }}{% endif %}", S("Text")),
                 ("{% if lang.dot_glyphs %}   {{ lang.dot_glyphs }}{% endif %}", S("Accent"))],
           after=1)
    _ctag(box, "{%p endfor %}")
    _ctag(box, "{%p endif %}")

    if source:
        _ctag(box, "{%p endfor %}")


def _finish_cell(cell):
    """Drop the empty paragraph a new cell starts with, and end with a tiny
    one: a cell must END with a paragraph even when every loop renders
    nothing (the trap that once emptied the chip row)."""
    first = cell.paragraphs[0]
    if not first.text and len(cell.paragraphs) > 1:
        first._p.getparent().remove(first._p)
    end = cell.add_paragraph()
    end.paragraph_format.space_after = Pt(0)
    _mark_size(end, 2)


def _word2013(doc) -> None:
    """Lay the document out as Word 2013+ does (compatibilityMode 15), not as
    Word 2010. In the older mode Word shifts every table left by its first
    cell's padding so the TEXT meets the margin; with the layout table running
    edge to edge that pushed the side column's text onto the paper's edge and
    every cell 21.6pt off its column. In mode 15 a table's edge sits at its
    indent. Only the layout masters: the others keep their measured layout."""
    for cs in doc.settings.element.iter(qn("w:compatSetting")):
        if cs.get(qn("w:name")) == "compatibilityMode":
            cs.set(qn("w:val"), "15")


def _layout_doc(lang: str):
    body_font = AR_BODY_FONT if lang == "ar" else "Arial"
    head_font = AR_DISPLAY_FONT if lang == "ar" else "Georgia"
    doc = _doc(body_font, 0.5, head_font=head_font, role_font=head_font,
               name_color=MODERN_ACCENT, accent=MODERN_ACCENT)
    for cell in LAYOUT_CELLS:
        for role, font, bold in (("Name", head_font, True), ("Heading", head_font, True),
                                 ("Text", body_font, False), ("Bold", body_font, True),
                                 ("Accent", body_font, False), ("Metric", head_font, True)):
            _char_style(doc, cell_style(cell, role), font=font, bold=bold, color=INK)
    _char_style(doc, cell_style("Main", "Metric"), font=head_font, bold=True, color=INK)
    _char_style(doc, ST_CONTACT, font=body_font, bold=False, color=MUTED)
    doc.styles.add_style(PS_CONTACT, WD_STYLE_TYPE.PARAGRAPH).base_style = doc.styles["Normal"]
    for cell in (*LAYOUT_CELLS, "Main"):
        st = doc.styles.add_style(head_para_style(cell), WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles["Normal"]
        st.paragraph_format.keep_with_next = True
    _word2013(doc)
    return doc, body_font


def build_layout(path: Path, lang: str = "en"):
    token = set_lang(lang)
    try:
        return _build_layout(path, lang)
    finally:
        reset_lang(token)


def _cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def _build_layout(path: Path, lang: str):
    """The top row, then ONE ROW PER BLOCK of the main column.

    Why rows: Word ignores keep-with-next between paragraphs inside a table
    cell that breaks across pages (measured in real Word, 2026-09-30: modern-t5
    in Arabic left "Certifications" alone at the foot of page 1). What Word
    does honour is a row that cannot split. So each block - a section with
    its heading, or one job of the experience (the first one carrying the
    heading) - is its own `cantSplit` row, and the side column is ONE cell
    merged down all of them (w:vMerge restart / continue)."""
    doc, body_font = _layout_doc(lang)
    # The table runs edge to edge: a side column's fill reaches the paper's
    # edge as in the PDF, and each cell's own margins keep the text in.
    for section in doc.sections:
        section.left_margin = section.right_margin = Inches(0)
        section.top_margin = section.bottom_margin = Inches(0.4)
        section.header_distance = section.footer_distance = Inches(0)
    table = doc.add_table(rows=4, cols=2)
    _borderless(table)
    for source, name, cell in (("top_side", "TopSide", table.cell(0, 0)),
                               ("top_main", "TopMain", table.cell(0, 1))):
        _cell_items(cell, name, source)
        _finish_cell(cell)
    table.cell(1, 0).paragraphs[0].add_run("{%tr for blk in lay.blocks %}")
    side = table.cell(2, 0)
    vmerge = OxmlElement("w:vMerge")
    vmerge.set(qn("w:val"), "{{ 'restart' if loop.first else 'continue' }}")
    side._tc.get_or_add_tcPr().append(vmerge)
    _ctag(side, "{%p if loop.first %}")
    _cell_items(side, "Side", "side")
    _ctag(side, "{%p endif %}")
    _finish_cell(side)
    main = table.cell(2, 1)
    _ctag(main, "{%p for it in blk %}")
    _cell_items(main, "Main", None)
    _ctag(main, "{%p endfor %}")
    _finish_cell(main)
    _cant_split(table.rows[0])    # the band / header: never split either
    _cant_split(table.rows[2])
    table.cell(3, 0).paragraphs[0].add_run("{%tr endfor %}")
    end = doc.add_paragraph()
    end.paragraph_format.space_after = Pt(0)
    _mark_size(end, 2)
    if lang == "ar":
        _apply_rtl(doc, body_font)
    doc.save(str(path))
    return path


def build_gutter(path: Path, lang: str = "en"):
    token = set_lang(lang)
    try:
        return _build_gutter(path, lang)
    finally:
        reset_lang(token)


def _build_gutter(path: Path, lang: str):
    """modern-t19: the header items in the body, then one table row per
    labelled section - its title in a narrow gutter, its content beside it."""
    doc, body_font = _layout_doc(lang)
    _cell_items(doc, "Main", "head", headings=False)
    table = doc.add_table(rows=3, cols=2)
    _borderless(table)
    table.cell(0, 0).paragraphs[0].add_run("{%tr for it in lay.rows %}")
    label = table.cell(1, 0)
    head = label.paragraphs[0]
    head.style = doc.styles[head_para_style("Main")]
    run = head.add_run("{{ it.text }}", style=cell_style("Main", "Heading"))
    head.paragraph_format.space_before = Pt(6)
    head.paragraph_format.keep_with_next = True
    _cell_items(table.cell(1, 1), "Main", None, headings=False)
    _finish_cell(table.cell(1, 1))
    table.cell(2, 0).paragraphs[0].add_run("{%tr endfor %}")
    end = doc.add_paragraph()
    end.paragraph_format.space_after = Pt(0)
    _mark_size(end, 2)
    if lang == "ar":
        _apply_rtl(doc, body_font)
    doc.save(str(path))
    return path


# One master per (category, direction). The RTL pair is a SEPARATE FILE rather
# than a switch inside the LTR one: a .docx has no conditional layout, and the
# English masters are tuned to fit exactly one page - re-tuning them to also
# hold Arabic would risk the thing sessions 6 and 8 spent their time on.
MASTERS = {
    "ats_standard.docx": lambda p: build_ats(p, "en"),
    "modern_editorial.docx": lambda p: build_modern(p, "en"),
    "ats_standard_rtl.docx": lambda p: build_ats(p, "ar"),
    "modern_editorial_rtl.docx": lambda p: build_modern(p, "ar"),
    "modern_layout.docx": lambda p: build_layout(p, "en"),
    "modern_layout_rtl.docx": lambda p: build_layout(p, "ar"),
    "modern_gutter.docx": lambda p: build_gutter(p, "en"),
    "modern_gutter_rtl.docx": lambda p: build_gutter(p, "ar"),
}


# ------------------------------------------------------------------- verify

_WORD_PROBE = r"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
foreach ($p in @(%s)) {
  try {
    $d = $w.Documents.Open($p, $false, $true)
    $spill = 0
    for ($i = 1; $i -le $d.Paragraphs.Count; $i++) {
      if ($d.Paragraphs.Item($i).Range.Information(3) -ge 2) { $spill++ }
    }
    Write-Output ("OK`t" + [IO.Path]::GetFileName($p) + "`t" + $spill)
    $d.Close(0)
  } catch { Write-Output ("FAIL`t" + [IO.Path]::GetFileName($p) + "`t" + $_.Exception.Message) }
}
$w.Quit()
"""


def verify_in_word(paths) -> int:
    """Open each file in real Word and report failures + page-2 spill.

    This is the only check that proves anything about APPEARANCE or pagination.
    Schema-order tests catch files Word refuses outright; only Word itself
    catches content spilling to page 2 or a heading stranded at a break.
    Windows + Word only; skipped cleanly elsewhere.
    """
    import subprocess

    quoted = ",".join(f"'{Path(p).resolve()}'" for p in paths)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _WORD_PROBE % quoted],
            capture_output=True, text=True, timeout=180,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"  (skipped Word verification: {exc})")
        return 0

    rc = 0
    for line in (ln for ln in out.splitlines() if "\t" in ln):
        status, name, detail = (line.split("\t") + ["", ""])[:3]
        if status == "OK" and detail.strip() in ("0", ""):
            print(f"  Word OK    {name} — opens, fits one page")
        elif status == "OK":
            print(f"  Word WARN  {name} — {detail} paragraph(s) spill past page 1")
            rc = 1
        else:
            print(f"  Word FAIL  {name} — {detail}")
            rc = 1
    if not out.strip():
        print("  (Word not available — verification skipped)")
    return rc


def main():
    OUT_DIR.mkdir(exist_ok=True)
    written = []
    # Named masters only, if any are given: a rebuild re-saves the file (new
    # timestamps in docProps), so masters nobody changed are left alone.
    wanted = [a for a in sys.argv[1:] if a in MASTERS] or list(MASTERS)
    for name, builder in ((n, MASTERS[n]) for n in wanted):
        path = builder(OUT_DIR / name)
        written.append(path)
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    if "--verify" in sys.argv:
        return verify_in_word(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
