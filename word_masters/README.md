# Word masters — the DOCX export family

DOCX is a **parallel template family**, not a render of the HTML. Word has no
CSS layout engine, no `conic-gradient`, no reliable two-column-with-shaded-
sidebar. Each master is a `.docx` file carrying `docxtpl` (Jinja2) tags, filled
at request time from the same resume dict the HTML templates use
(`app/exporters/docx.py`).

## The masters are GENERATED, not hand-authored

```
venv/Scripts/python tools/build_word_masters.py            # rewrites both .docx
venv/Scripts/python tools/build_word_masters.py --verify    # + open them in real Word
```

`--verify` drives Word over COM: it opens each master and reports whether it
opens at all and whether anything spills past page 1. **Run it after every
change.** It is the only check that says anything about pagination — the pytest
suite validates structure and schema, neither of which can see a stranded
heading or a résumé that runs onto a second page. Windows + Word only; it skips
cleanly elsewhere.

This supersedes the original instruction to author each master by hand in Word
/ LibreOffice. **Edit `tools/build_word_masters.py` and re-run it — never edit
the `.docx` directly**, or the next build silently discards your changes.

Why the change:

- The master stays reviewable as source instead of an opaque binary.
- A spec change is one command to apply to both masters.
- It removes docxtpl's most common failure mode. Word splits text into runs as
  it pleases, so a hand-typed `{{ r.name }}` can reach docxtpl as
  `{{ r.n` + `ame }}`, which it cannot parse. `python-docx` writes each tag as
  exactly one run, so that class of bug cannot occur.

## Families (one per template category)

| File | Feeds | Structure |
|---|---|---|
| `modern_editorial.docx` | every `modern-*` template | single wide column in Word; sidebar content (contact, skills, tools, languages) folded into the main flow in reading order. Palette + type pairing + section order preserved. |
| `ats_standard.docx` | every `ats-*` template | genuinely single column, canonical headings, plain hyphen date ranges. Mirrors the on-screen ATS layout closely. |
| `modern_editorial_rtl.docx` | every `modern-*` template, Arabic résumé | the same layout, right-to-left. Georgia carries no Arabic glyphs, so the display face becomes Times New Roman. |
| `ats_standard_rtl.docx` | every `ats-*` template, Arabic résumé | the same, right-to-left. |

**The RTL pair is a separate FILE, not a switch inside the LTR one.** A .docx
has no conditional layout, and the English masters are tuned to fit exactly one
page — re-tuning them to also hold Arabic would risk what sessions 6 and 8 were
spent on. `exporters/docx.py::_master_for` picks by the résumé's `lang`, and
**raises rather than falling back** if an RTL master is missing: falling back
would hand an Arabic résumé a left-to-right file with English headings, which is
output that is wrong rather than absent.

### Making a document right-to-left in Word

`dir="rtl"` buys nothing here. Four separate things must be said, and saying
only the first produces a document that opens, fits, passes a structural test
and still lays its Arabic out left-to-right:

| element | where | what it does |
|---|---|---|
| `w:bidi` | `w:sectPr` | the section reads right-to-left |
| `w:bidi` | `w:pPr` | the paragraph does, so its default alignment flips |
| `w:rtl` | `w:rPr` | the RUN does — without it Word lays glyphs left-to-right inside a right-aligned paragraph |
| `w:rFonts/@w:cs`, `w:szCs`, `w:bCs` | `w:rPr` | Arabic is a COMPLEX SCRIPT: Word takes face, size and weight from the `cs` attributes, not `ascii`/`hAnsi` |

Plus `w:bidiVisual` on `w:tblPr` so the stat-chip row mirrors. All of it is
applied by `_apply_rtl()` as a POST-PASS over the finished document, so a
component added later cannot be left half-mirrored.

⚠ **`PageSetup.Bidi` does not exist** in Word's object model. Reading it over
COM yields `$null`, so a verification script that checks it reports every
document as left-to-right. Use `Paragraph.Format.ReadingOrder`, whose constants
are **wdReadingOrderRtl = 0**, **wdReadingOrderLtr = 1**.

`registry.Template.docx_master` names the file for each key. Both masters now
exist, so `/export/docx` returns a real `.docx`. If a master is ever deleted
the route still degrades to **501** with a clear message rather than a 500.

One master serves a whole category, so **49 HTML layouts collapse onto 2 Word
documents**: a master carries one fixed palette (ATS monochrome, Modern navy
`#1F3A5F`), not the per-template accent.

## Word-safe mapping (applies to every master)

- **Ring / bar / slider skills** → dot glyphs `●●●●○` + level word, both real
  text (`docx.py::_dot_glyphs`, dot count from `schema.dots_for`). A level word
  off the `LEVEL_DOTS` scale (e.g. a language's "Native") gets **no glyphs at
  all** — five empty circles would contradict the word next to them.
- **Stat-chip row** → a single-row borderless table of **exactly 4 cells**.
  `docxtpl`'s `{%tc %}` horizontal loop was tried first and emits an empty
  `<w:tr/>` here, so slots are fixed and each guards its own content with an
  inline conditional; `schema.normalize()` already drops blank-metric chips and
  caps the row at 4. An unused slot renders metric **and** caption as `""`, so a
  chip always disappears whole. The guard is inline rather than `{%p if %}`
  because a paragraph-level `if` can strip a cell to zero paragraphs, which is
  invalid OOXML.
- **Photo** → `modern_editorial.docx` only, 22 mm inline, no wrap. The ATS
  master has **no photo slot at all**, mirroring the HTML family exactly: 16 of
  24 Modern templates have a photo slot and **zero** of the 25 ATS templates do,
  because images defeat résumé parsers. The master guards on `photo`, not on
  `r.photo_url`, so a URL whose upload has been deleted leaves no blank gap.
  The Modern master's spacing is tuned to fit **with** a photo, so a photo-less
  résumé simply carries more bottom margin; enlarging the 22 mm pushes the tail
  sections onto page 2.
- **Fonts** → mapped to safe substitutes (Archivo→Arial, Fraunces→Georgia,
  etc.) unless a licence to embed is confirmed. Record the substitution in the
  master's own notes.
- **No hyphenation** anywhere (the table architecture assumes it off).
- **Every section heading carries `keep_with_next`**, as does each job role and
  its company/date line. User content is variable-length, so Word *will*
  repaginate; without this a heading strands alone at the top of page 2.
- **OOXML property elements are an ordered sequence.** `w:pPr`, `w:rPr` and
  `w:tblPr` children must appear in schema order — appending to the end yields
  well-formed but invalid XML and Word refuses the whole document. python-docx
  and lxml accept it silently, so this is invisible to a round-trip test. Insert
  with `insert_element_before(el, *successors)`; `tests/test_docx_validity.py`
  guards it.

## Change checklist per master

1. Edit the builder in `tools/build_word_masters.py`. Use `{%p %}` paragraph
   tags for loops and guards that span blocks; keep each tag in a paragraph of
   its own (docxtpl deletes the whole paragraph).
2. Re-run the builder, then `venv/Scripts/python -m pytest -q -k docx`. Those
   tests render from `data/sample_resume.json` and assert: no unrendered tags
   survive, every section is present, `&` survives, loops emit one block per
   entry, an empty section leaves no orphan heading, and a partial chip row
   hides caption with metric.
3. Run `--verify` (above). It catches "Word won't open this" and "this spills to
   page 2"; it still cannot tell you a master is *ugly*, so open the file
   yourself after any layout change.
4. Record any new divergence in the header of `tools/build_word_masters.py`.

`render_docx()` must keep passing `autoescape=True`. Without it docxtpl writes
user text straight into the document XML: an `&` in a company name is silently
dropped and a `<` can corrupt the package.
