# Word layout archetypes for the Modern templates — PLAN (approved 2026-09-29, being built)

Written 2026-09-29 for the user's review. This is option 2 of the Word export
investigation (RESUME_HERE.md, 2026-09-26). The user approved it on
2026-09-29 (decisions in §9) and it is being built on `feature/word-layouts`.
What was decided while building, with nobody to ask, is in §10.

## 1. Why

Today the Word download follows the template's **colour** and the **fonts**
(option 1, shipped in typography steps 5–6), but every Modern template comes
out in ONE layout: `modern_editorial` (one column, the sidebar folded into the
main flow). Next to the PDF it looks plain. On 2026-09-29 the user downloaded
`modern-t8` "Interlocking Blocks" from the live site. The file was correctly
themed, but it is one column, where the design has blocks and a sidebar.

Goal: a Modern Word file is **recognisably the same shape** as its PDF, stays
**editable**, and keeps every rule already agreed for Word:

- natural line spacing ("Auto", Multiple 1.15), **never "Exactly"**, and no
  exact row heights;
- content may flow to a 2nd page; failures are only clipping, a heading
  orphaned at a page foot, or a job title separated from its company/date line;
- fonts embedded (step 6);
- skill name AND level as real text;
- no text in images or backgrounds.

**ATS stays one column** (`ats_standard`): tables hurt résumé parsers, and the
ATS HTML is already close to its master. Out of scope.

## 2. What the 24 Modern templates look like (measured 2026-09-29)

Each template was rendered in Chromium with the shipped sample (a contact
sheet of all 24, plus a geometric probe of full-height columns, header bands
and name position), in English AND Arabic. Photo slots and skill styles come
from the recorded investigation table. The probe could not see them; that is
an instrument limit, and the probe's output was not used for them.

**In Arabic every sidebar mirrors** (measured: t2 and t16 go from the left to
the right, t1 and t7 from the right to the left). So each Word layout needs
its RTL twin to mirror its columns too.

## 3. The archetypes

Four layouts. Each is one Word master plus its `_rtl` twin (8 new files next
to the 4 existing ones). The template-specific parts are **parameters**
measured into `app/word_themes.json`, never 24 hand-built masters.

### A. SIDEBAR — shaded side column (12 templates)

A 2-column table with one row that may break across pages. The narrow column
(about 33–40% of the width, measured per template) is shaded in the template's
sidebar colour. It holds the contact details, skills, languages, tools and
certifications, plus the photo where the template has one. The wide column
holds the summary, stat chips, experience and education.

- **Parameter `name_in`:** `main` (the name and role sit at the top of the
  wide column), or `sidebar` (the name sits at the top of the shaded column,
  as in t3, t9, t10, t23).
- **Parameter `side`:** `left` for all 12 in English. The RTL twin mirrors it
  with `w:bidiVisual`.
- **Sidebar text colour:** measured from the HTML (white on navy or charcoal;
  dark on yellow for t3, t9).

| Template | Label | Name in | Photo | Skills |
|---|---|---|---|---|
| modern-t2 | Navy & Gold | main | yes | bars |
| modern-t3 | Yellow Photo Rail | sidebar | yes | bars |
| modern-t4 | Ribbon Sidebar | main | yes | dot-grid |
| modern-t5 | Rounded Dark | main | yes | bars |
| modern-t9 | Boxed Sections | sidebar | – | bars |
| modern-t10 | FinTech Elite | sidebar | yes | bars |
| modern-t15 | Forest & Amber | main | yes | bars |
| modern-t16 | Charcoal Rings | main | yes | rings |
| modern-t17 | Two-Tone Ribbon | sidebar (header block) | yes | rings |
| modern-t20 | Cotton & Cherry | main | yes | dot-grid |
| modern-t23 | Spine Timeline | sidebar | – | bars |
| modern-t24 | Hard-Edged Sidebar | main | yes | rings |

### B. BAND — full-width shaded header over a two-column body (7 templates)

The first table row spans the page and is shaded in the band colour. It holds
the name, the role, the contact line, and the photo where the template has
one. Below it comes a 2-column body; the side column is shaded or open,
following the template.

| Template | Label | Band | Body side column | Photo | Skills |
|---|---|---|---|---|---|
| modern-t7 | Poster Band | yellow (name block) | navy, right | yes | bars |
| modern-t8 | Interlocking Blocks | navy (name block) | light blocks, left | yes | dot-grid |
| modern-t11 | Colour Header Rail | yellow | dark, left | yes | dot-grid |
| modern-t13 | Band Timeline | navy | none (one column) | – | dot-grid |
| modern-t14 | Offset Plaque | orange plaque | beige, left | yes | dot-grid |
| modern-t18 | Interlocking Block | navy | navy, left | yes | bars |
| modern-t21 | Rounded Card Shell | lime | dark green, left | yes | dot-grid |

The interlocking and offset shapes (t8, t14, t18) can only be **approximated**:
Word tables cannot overlap blocks. They become a band plus a side column in
the same colours and in the same positions.

### C. OPEN — name across the top, a narrow unshaded column split by a rule (4 templates)

No shading. The name runs full width at the top. Below it, the main column and
a narrow column (on the right in English) are divided by a thin vertical rule
(a table cell border, not a drawn line). Parameter `centred` for t6 (centred
name and role).

| Template | Label | Narrow column | Skills |
|---|---|---|---|
| modern-t1 | Editorial Redline | right: contact, capabilities, tools | dot-grid |
| modern-t6 | Centred Symmetric | right: skills, education, languages (**centred header**) | bars |
| modern-t12 | Typographic Mono | right: contact, skills | rings |
| modern-t22 | Vertical Rail Rings | right: address, phone, email, skills | rings |

t22's vertical "RESUME" word is dropped. Word rotated text is a text box,
which is poorly editable and invisible to parsers.

### D. GUTTER — section labels in a narrow left gutter (1 template)

| Template | Label | Skills |
|---|---|---|
| modern-t19 | Label Gutter | bars |

A 2-column table with one row per section: the section title sits in a narrow
unshaded gutter (about 20%), and its content sits beside it. This is the
lowest-risk layout (no shading, each row short), and it could later also serve
ATS-like Modern designs.

### Timeline treatment (a flag, not a layout)

Templates whose experience has a vertical line with markers (t4, t5, t12, t13,
t14, t22, t23, t24) get `timeline: true`. Each experience entry gets a left
paragraph border in the accent colour and a "●" marker; the RTL twin uses a
RIGHT border. It works inside any archetype.

**Count: A 12 + B 7 + C 4 + D 1 = 24.** Every Modern template maps to exactly
one archetype.

## 4. What each looks like in Word (limits, stated up front)

| HTML feature | In Word |
|---|---|
| shaded sidebar | shaded table cell; the shading ends where the row ends (see risk R2) |
| full-width band | shaded first table row |
| circular photo | the photo pre-cropped to a circle PNG with transparency (Pillow), inline in the cell; square templates stay square |
| skill bars | **DECIDE:** (a) keep dots + level word (today's), or (b) a 1-row mini-table per skill with a shaded cell whose width is the level, plus the level word. Either way the name and level are real text |
| rings | dots + level word (Word has no rings) |
| stat chips | a 4-cell table row, number over caption; empty metrics are hidden, as in HTML |
| page background tint (t5 grey, t14 beige/navy) | dropped. Word page colour doesn't print by default and fights editing |
| overlapping or offset blocks (t8, t14, t18), rotated "RESUME" (t22), rounded cards (t5, t21) | approximated as square blocks in the same colours and positions, or dropped (rotated text) |

## 5. How it is built (reuses what exists)

1. **Measure the new parameters.** Extend `tools/build_word_themes.py`
   (Chromium computed style, both languages, `--check`) to record per Modern
   template: `archetype`, `side`, `name_in`, `centred`, `timeline`,
   `sidebar_bg` / `sidebar_fg`, `band_bg` / `band_fg`, and the column width
   ratio. Into `app/word_themes.json`, kept current by the existing e2e test.
   The mapping in §3 is a proposal; the measurement confirms or corrects it.
2. **Build the masters.** Extend `tools/build_word_masters.py` (python-docx +
   docxtpl tags) with the 4 archetypes × LTR/RTL. Same role styles (`CV Name`,
   `CV Heading`, `CV Role`, `CV Body Bold`, `CV Accent Text`, `Normal`), so the
   step-5 theme pass and step-6 font embedding work unchanged.
   Every inserted element goes in schema order (`insert_element_before`).
3. **Choose the master.** `registry.Template.docx_master` for Modern becomes
   the archetype master (by key, from `word_themes.json`) instead of the
   category.
4. **Apply the parameters at export.** A post-pass (like `docx_theme.apply`)
   applies the shading colours, text colours, column widths, the side, and
   the timeline borders.
5. **RTL.** The four declarations the RTL masters already need stay:
   `w:bidi` on `w:sectPr`, `w:bidi` on `w:pPr`, `w:rtl` on runs, and
   `w:rFonts/@w:cs` + `w:szCs` + `w:bCs`. Plus a fifth, new with tables:
   `w:bidiVisual` in every `w:tblPr`, or the columns do not mirror.

## 6. Risks

- **R1 Arabic / RTL.** The tables must mirror (`w:bidiVisual`). The column
  widths are then listed in visual order, and Word and LibreOffice disagree on
  that order, so it is verified in real Word only. The timeline border must
  move to the right. The digits and Latin text inside Arabic cells stay as
  today (no isolation needed, per the bidi memory).
- **R2 Shading height.** A shaded cell is only as tall as its row. A short CV
  gets a sidebar that stops mid-page; a long one flows to page 2, and the
  shading continues there. **DECIDE:** accept that, or give the row an
  "at least" height of one page. That is not "Exactly" and cannot clip, but a
  near-full page then always pushes to 2 pages.
- **R3 2-page flow.** Word only keeps a heading with the next paragraph
  reliably within one cell. A row broken across pages can leave a heading at
  the foot of the sidebar cell. Mitigation: keep-with-next on every heading in
  both cells, sidebar content ordered short-first, and verification in real
  Word (§7).
- **R4 Editability.** Tables are editable and are how Word users build
  sidebars. But a user adding a job to a one-row table grows both cells, and a
  user deleting the table's end marker can merge cells. Mitigation: one
  simple table per layout, no nested tables (except the optional skill
  mini-tables and the stat row), no text boxes, no floating shapes.
- **R5 Parsers.** Modern Word files become tables. Some ATS read tables
  poorly. Mitigation: a note in the download menu already says that ATS
  templates are the parser-safe choice. **DECIDE:** whether that note needs
  stronger wording.
- **R6 Photo.** Circle crops and cell widths must keep the photo inside the
  cell at all widths. The photo is ~22–30 mm; a photo taller than its band
  row pushes the band.
- **R7 Theme contrast.** The sidebar text colour is measured from the HTML.
  Light sidebars (yellow) need dark text; the "readable accent" rule from
  step 5 applies to text on white only. The sidebar's own text contrast gets
  a WCAG 4.5:1 test.
- **R8 Cloud fonts.** Unchanged from step 6 (M365 may draw its own copy of
  Montserrat, Open Sans and Poppins).

## 7. Test plan

1. **Mapping (fast):** every Modern key maps to exactly one archetype; every
   ATS key still maps to `ats_standard`; `word_themes.json` is current
   (`--check`).
2. **XML (fast), per archetype × LTR/RTL:**
   - schema-valid element order (`test_docx_validity.py`);
   - `w:bidiVisual` on every table in RTL, none in LTR;
   - shading = the theme's colours;
   - no `w:spacing w:lineRule="exact"`, no `w:trHeight w:hRule="exact"`;
   - every heading and job title `keepNext`;
   - widow control in Normal;
   - role styles present;
   - skill name and level present as text;
   - empty stat chips absent.
3. **Unchanged:** the ATS Word files are unchanged; the HTML/PDF pixel goldens
   are unchanged (Word work cannot move them); the step-6 embedding tests pass
   on every archetype.
4. **Real browser:** `tests/e2e/test_word_follows_the_builder.py` gains an
   archetype assertion (e.g. modern-t16 has a shaded 2-column table on the
   correct side in EN and in AR).
5. **Real Word (COM):** `tools/verify_word_embedding.py` over 24 templates ×
   EN/AR × {sample, sparse, long} = 144 files:
   - opens without a repair prompt;
   - page breaks: no orphan heading, no job title split from its line;
   - nothing clipped;
   - fonts drawn from the embedded files.
6. **Review page:** the Word-made PDF beside the HTML PDF for all 24, EN + AR,
   for the user's approval (as in step 5).
7. **Manual check:** a new "CVStand Word layouts check" folder, one file per
   archetype per language, on the Word 2013 PC.

## 8. Estimate

| Session | Work |
|---|---|
| 1 | Measure the parameters, confirm the mapping, circle-crop photo helper, mapping + XML test scaffolding. User reviews the mapping |
| 2 | SIDEBAR + BAND masters, LTR + RTL, theme post-pass, XML tests |
| 3 | OPEN + GUTTER masters, timeline flag, skill-bar decision, stat row |
| 4 | Real-Word verification of 144 files, fixes, review page |
| 5 | User review fixes + the manual check folder; merge per §9 of the typography spec (branch, full suite, approval; pushing main deploys) |

**About 4–5 sessions, medium risk.** The riskiest part is R2/R3 (row breaks
and orphaned headings in real Word), which is why real-Word verification has
its own session.

## 9. Decisions (user, 2026-09-29)

1. **Approved:** the four archetypes (Sidebar, Band, Open, Gutter) and the
   mapping in §3.
2. **Skills follow the template:** bars where the PDF has bars, dots where it
   has dots.
3. **Sidebar at full page height on page 1, as in the PDF.** If Word cannot do
   it reliably, build both variants and show both on the review page.
4. **Drop** the page tints (t5, t14) and t22's rotated word.
5. **Clearer download-menu wording (EN + AR):** drafted in §11 only; the UI is
   not changed yet.
6. **Word layouts first**, typography step 7 after.

Hard rules given with them: new branch `feature/word-layouts` from `main`
(`e56240d`); never push `main`, merge or deploy; no change to the PDF/HTML
templates or their goldens; keep everything already working (embedded fonts,
the user's font choices, template colours, widow/orphan control, natural line
spacing, keep-with-next, the ATS layout unchanged); Arabic mirrors every
layout; a 2-page file is fine; only files that python-docx opens, that pass
the validity test and that Word opens without a repair prompt.

## 10. Decisions made overnight (2026-09-29/30)

The user asked for the option closest to the PDF whenever something was
unclear, written down here.

1. **The layout is measured, not hand-mapped.** Beyond the archetype (§3,
   approved), where each item sits, its order, its heading words and every
   colour are read from the rendered template in Chromium
   (`tools/build_word_layouts.py` → `app/word_layouts.json`, with `--check`).
   The measurement fails loudly unless it finds exactly the sections the
   template's source uses, in both languages.
2. **A section the template does not show is not in its Word file either.**
   Five templates leave sections out of their PDF (t4: no summary; t12, t18,
   t22, t23: no certifications/tools/languages; t13: no tools/languages; t14:
   no stat chips; t1: no title; t2: no tools). The PDF is the design, so the
   Word file matches it. The old single-column Word file showed everything.
3. **Headings use the template's own words** ("About me", "Core
   Competencies", "Software", "الملف الشخصي"...), in capitals where the
   template sets them in capitals (never in Arabic). If a template gives a
   section no heading in one language, Word uses the catalogue's default
   word for it in that language (only t6's tools in Arabic).
4. **Colours follow the PDF zone by zone, not one accent.** Each cell (side
   column, band, main) takes its measured text, heading and name colours.
   The job company/date line keeps the step-5 readable accent. A contrast
   guard swaps any text colour that would not read on its cell's fill for
   black or white (4.5:1 body text, 3:1 headings and names), so nothing can
   vanish (modern-t21's white contact text sits on its own dark pill, as in
   the PDF).
5. **Full-height sidebar, one variant.** Decision 3 is met with a coloured
   rectangle in the page HEADER, behind the text, at the side column's width.
   It is full height on every page, however long the content runs, and it
   mirrors to the right in Arabic. The side cells are filled in the same
   colour too, so a reader that ignores header shapes still shows the column
   down to where its content ends. This proved reliable in real Word, so no
   second variant was built.
6. **The band reaches the top edge on page 1 only.** A band's cell starts at
   the 0.4in top margin. A strip in the band's colour fills the margin above
   it on the first page (a different first-page header), so page 2 has no
   stray strip.
7. **Word 2013 layout mode for the layout masters only**
   (`compatibilityMode 15`). In the Word 2010 mode the masters used, Word
   shifts a table left by its first cell's padding, which put the side
   column's text on the paper's edge. ATS and the single-column master keep
   their mode, and their files are byte-identical.
8. **Rings become dots** (decision 2 names bars and dots only). A ring is a
   circular gauge, and the dot row (●●●●○) is the closest circular form Word
   can draw as text.
9. **Photos:** at the template's measured width, clamped to 20–45 mm (a
   template's large photo box would otherwise take half the page in Word),
   and cut to a circle where the template's photo is round (8 of 16). With
   no photo uploaded, Word shows nothing: never the PDF's "PORTRAIT
   PLACEHOLDER" box.
10. **Sizes:** the name at its measured size, clamped to 18–40 pt; section
    headings at theirs, clamped to 8.5–13 pt. Body text stays at 10 pt (9.5
    in the stacked contact lines).
11. **Page breaks by rows, not by keep-with-next.** Real Word ignores
    keep-with-next between paragraphs in a table cell that breaks across
    pages (modern-t5 in Arabic stranded "الشهادات" at the foot of page 1). So
    the main column is one cannot-split row per block: a section with its
    heading, or one job (the first carries the Experience heading). The side
    column is one cell merged down all rows. A block moves to the next page
    whole. A block taller than a page still splits, since Word must split it.
12. **Heading words the template does not give are not invented.** A default
    catalogue heading is used only when the template gives that section a
    heading in the OTHER language (t6's tools in Arabic). Where the PDF has
    no heading (t1's summary, t2's contact grid, t22's labelled contact
    lines), Word has none. Per-line field labels ("Email", "Phone") are never
    taken as a section heading.
14. **The open layouts' rule is measured too:** a vertical line between the
    columns only where the PDF draws one at the split (t1, t6, in their own
    light grey). t12 has none, and t22's line is its rail, not a split.
15. **A side column is never narrower than 30% of the page.** t22's measured
    24.7% (and t1's 27.8%) broke the email address mid-word in Word, where
    the PDF's smaller type fits it. Stacked contact lines are 9 pt.
13. **Skill bars are 5 segments,** one per level step, each with a hairline
    border in its own colour so the fills meet without a seam. They read as
    a stepped bar, the 5-point scale the level words map to.

## 11. Download-menu wording — DRAFT (decision 5: not in the UI yet)

Today (`app/templates/builder.html`, `app/labels.py`):

| Where | English | Arabic |
|---|---|---|
| Word item caption | Editable, for job portals | (catalogue) |
| Note under the menu | Word: editable version · PDF: exact design | Word: نسخة قابلة للتحرير · PDF: التصميم الدقيق |

Why it has to change: with the layouts, a Modern Word file keeps its design,
so "editable version" undersells it. And it is now built from tables, so
"for job portals" oversells it. Some applicant-tracking systems read table
columns out of order (R5). The ATS templates stay one column and remain the
parser-safe choice.

Proposed, chosen by the template's category (the builder knows it):

| Where | Category | English | Arabic |
|---|---|---|---|
| Word item caption | Modern | Editable, same design | قابل للتحرير، بنفس التصميم |
| Word item caption | ATS | Editable, for job portals (unchanged) | (unchanged) |
| Note | Modern | Word keeps this design and you can edit it. Applying through a job portal? Choose an ATS template. | ملف Word يحتفظ بهذا التصميم ويمكنك تعديله. تتقدّم عبر بوابة توظيف؟ اختر قالباً من فئة ATS. |
| Note | ATS | Word and PDF: one column, easy for job portals to read. | Word وPDF: عمود واحد تقرؤه بوابات التوظيف بسهولة. |

To build it later: two new catalogue keys per language (`app/labels.py`),
the note chosen by category in `builder.html` / `builder.js`, and the
label-catalogue test for the Arabic keys. The Arabic needs a wording review
by the user, like every new Arabic string.
