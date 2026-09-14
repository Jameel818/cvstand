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
     2 Word documents, so each master carries ONE fixed palette, not the per
     template accent.
  2. Fonts substituted for ones present on any Word install: the Modern display
     face -> Georgia, all body text -> Arial.
  3. Ring / bar / slider skill graphics -> dot glyphs (●●●●○) plus the level
     word, both real selectable text.
  4. Modern is a single wide column: sidebar content (contact, skills, tools,
     languages) folds into the main flow in reading order.
  5. Stat chips are a fixed 4-cell borderless row, not one column per surviving
     chip — docxtpl's {%tc %} horizontal loop emits an empty <w:tr/> here.
     schema.normalize() already drops blank-metric chips and caps the row at 4,
     so cells past the chip count render empty and, being borderless, invisible.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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

def _doc(body_font: str, margin: float) -> Document:
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
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Inches(margin)
        section.left_margin = section.right_margin = Inches(margin)
    return doc


def _p(doc, text="", *, size=10, bold=False, italic=False, color=None,
       font=None, before=0, after=2, align=None, style=None):
    """One paragraph, one run — so a docxtpl tag is never split across runs."""
    para = doc.add_paragraph(style=style)
    run = para.add_run(text)
    run.bold = bold
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
        # complex-script face, size and weight must mirror the latin ones
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        ascii_face = fonts.get(qn("w:ascii")) or body_font
        fonts.set(qn("w:cs"), ascii_face)
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


def _cell_p(cell, text, *, first, size=10, bold=False, color=None, font=None, after=0):
    para = cell.paragraphs[0] if first else cell.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    if font is not None:
        run.font.name = font
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(after)
    return para


# ---------------------------------------------------------------- components

def _heading(doc, label: str, accent: RGBColor, font: str, *, ruled=True,
             before=7, after=3):
    para = _p(doc, label, size=9, bold=True, color=accent, font=font,
              before=before, after=after)
    # Word repaginates freely with variable-length user content, so a heading
    # must be bound to what follows it or it strands alone at a page break.
    para.paragraph_format.keep_with_next = True
    para.runs[0].font.all_caps = True
    _letter_spacing(para.runs[0], 24)  # 1.2px-equivalent, per the ATS label spec
    if ruled:
        _rule(para)
    return para


def _chip_row(doc, accent: RGBColor, font: str):
    """Fixed 4-cell borderless row. A slot past the chip count renders both its
    metric and its caption as "" — the whole chip disappears together, never a
    floating caption with no number."""
    table = doc.add_table(rows=1, cols=CHIP_SLOTS)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _borderless(table)
    for i, cell in enumerate(table.row_cells(0)):
        guard = f'r.achievements[{i}].{{}} if r.achievements|length > {i} else ""'
        _cell_p(cell, "{{ %s }}" % guard.format("metric"),
                first=True, size=16, bold=True, color=accent, font=font)
        _cell_p(cell, "{{ %s }}" % guard.format("label"),
                first=False, size=8.5, color=MUTED, after=4)
    return table


def _experience(doc, accent: RGBColor, font: str):
    _tag(doc, "{%p for job in r.experience %}")
    role = _p(doc, "{{ job.role }}", size=11, bold=True, font=font,
              before=5, after=0)
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
              size=9, color=accent, after=2)
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


def _tail_sections(doc, accent, head_font, *, head_before=7):
    """Certifications / Tools / Languages — each guarded so an absent one leaves
    no orphan heading."""
    _tag(doc, "{%p if r.recognition %}")
    _heading(doc, L("Certifications"), accent, head_font, before=head_before)
    _tag(doc, "{%p for rec in r.recognition %}")
    _p(doc, "{{ rec.title }}{% if rec.detail %} — {{ rec.detail }}{% endif %}",
       size=10, after=0)
    _tag(doc, "{%p endfor %}")
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.tools %}")
    _heading(doc, L("Tools"), accent, head_font, before=head_before)
    _p(doc, '{{ r.tools | join("  ·  ") }}', size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.languages %}")
    _heading(doc, L("Languages"), accent, head_font, before=head_before)
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
    doc = _doc(font, 0.62)
    accent = ATS_ACCENT

    _p(doc, "{{ r.name }}", size=22, bold=True, font=font, after=2)
    _tag(doc, "{%p if r.title %}")
    _p(doc, "{{ r.title }}", size=11, bold=True, color=MUTED, after=2)
    _tag(doc, "{%p endif %}")
    _tag(doc, "{%p if r.contact_line %}")
    _p(doc, "{{ r.contact_line }}", size=9, color=MUTED, after=4)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.summary %}")
    _heading(doc, L("Summary"), accent, font)
    _p(doc, "{{ r.summary }}", size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.achievements %}")
    _heading(doc, L("Key Achievements"), accent, font)
    _chip_row(doc, accent, font)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.experience %}")
    _heading(doc, L("Experience"), accent, font)
    _experience(doc, MUTED, font)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.skills %}")
    _heading(doc, L("Skills"), accent, font)
    _skills(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.education %}")
    _heading(doc, L("Education"), accent, font)
    _education(doc)
    _tag(doc, "{%p endif %}")

    _tail_sections(doc, accent, font)
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
    doc = _doc(body_font, 0.5)
    # Georgia carries no Arabic glyphs at all, so the Arabic Modern master
    # takes the serif Word guarantees instead. Same register, real coverage.
    accent = MODERN_ACCENT
    head_font = AR_DISPLAY_FONT if lang == "ar" else "Georgia"
    HEAD_BEFORE = 4

    # Photo slot — Modern only. 16 Modern templates have one; NO ATS template
    # does, because images defeat resume parsers, so ats_standard has none
    # either. The guard is on `photo` (falsy when absent OR when the upload has
    # been deleted), not on r.photo_url, so a dangling URL leaves no blank gap.
    _tag(doc, "{%p if photo %}")
    _p(doc, "{{ photo }}", after=3)
    _tag(doc, "{%p endif %}")

    _p(doc, "{{ r.name }}", size=23, bold=True, color=accent, font=head_font, after=1)
    _tag(doc, "{%p if r.title %}")
    _p(doc, "{{ r.title }}", size=11, italic=True, color=MUTED, after=2)
    _tag(doc, "{%p endif %}")
    _tag(doc, "{%p if r.contact_line %}")
    _rule(_p(doc, "{{ r.contact_line }}", size=9, color=MUTED, after=4),
          color="1F3A5F", size=8)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.summary %}")
    _heading(doc, L("Profile"), accent, head_font, before=HEAD_BEFORE)
    _p(doc, "{{ r.summary }}", size=10)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.achievements %}")
    _heading(doc, L("Key Achievements"), accent, head_font, before=HEAD_BEFORE)
    _chip_row(doc, accent, head_font)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.experience %}")
    _heading(doc, L("Experience"), accent, head_font, before=HEAD_BEFORE)
    _experience(doc, accent, head_font)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.skills %}")
    _heading(doc, L("Skills"), accent, head_font, before=HEAD_BEFORE)
    _skills(doc)
    _tag(doc, "{%p endif %}")

    _tag(doc, "{%p if r.education %}")
    _heading(doc, L("Education"), accent, head_font, before=HEAD_BEFORE)
    _education(doc)
    _tag(doc, "{%p endif %}")

    _tail_sections(doc, accent, head_font, head_before=HEAD_BEFORE)
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
    for name, builder in MASTERS.items():
        path = builder(OUT_DIR / name)
        written.append(path)
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    if "--verify" in sys.argv:
        return verify_in_word(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
