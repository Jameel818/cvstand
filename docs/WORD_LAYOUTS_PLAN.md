# Word layout archetypes for the Modern templates — PLAN (not approved, no code)

Written 2026-09-29 for the user's review. This is option 2 of the Word export
investigation (RESUME_HERE.md, 2026-09-26). Nothing here is built. Every
decision marked **DECIDE** needs the user's answer before implementation.

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

## 9. Decisions needed before implementation

1. Approve the four archetypes and the mapping in §3, or move templates
   between them.
2. Skill bars: keep dots + level word, or add bar mini-tables (§4)?
3. Sidebar height: stop where the content stops, or an "at least" full-page
   row (R2)?
4. Drop the page background tints (t5, t14) and t22's rotated word: OK?
5. Download-menu wording about tables and ATS (R5).
6. Branch: new `feature/word-layouts` from `main` after typography step 7, or
   before it?
