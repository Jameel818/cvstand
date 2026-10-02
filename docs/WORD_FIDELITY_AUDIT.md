# Word fidelity audit: Modern templates, PDF vs the Word file as Word draws it

Branch `feature/word-fidelity` (from `feature/word-layouts` `393f655`).
Method: for each of the 24 Modern templates, EN and AR, the shipped sample
résumé was exported to PDF (the app's own renderer) and to .docx (the current
layout exporter), the .docx was opened **in Microsoft Word on this PC** and
saved as PDF by Word, and both were rasterised (pdf.js) and put side by side.
Every row below was read off those pictures, not off the XML.

**Verdict on the current Word files:** they keep the column split, the zone
colours and the section order. Almost everything that makes each template
recognisable is lost. "48/48 pass" measured structure and page flow only.

## Cross-cutting losses (every or nearly every template)

| # | Lost in Word | PDF has | Where |
|---|---|---|---|
| X1 | Name case and weight | UPPERCASE name (text-transform), often on two lines, tight leading | t1 2 3 4 5 7 9 11 12 13 15 16 17 18 19 22 23 24 |
| X2 | Letter-spaced role/title | `letter-spacing` 2-5px, caps (CREATIVE LEAD) | t2 3 6 7 8 11 13 16 18 19 22 24 |
| X3 | Section heading decoration | tracked caps, trailing hairline rule, rule under, filled bar, pill, ribbon with fold | all |
| X4 | Skill display | bar length/position beside the name with % as text, level word right-aligned, dot rows under the name, sliders with knob, rings with % inside | all; Word draws a full-width 5-segment bar under "Name — Level" or dots glued after the text |
| X5 | Date placement | dates right-aligned on the role line (or in a date column / above the title) | t1 2 4 5 6 9 10 12 13 16 18 19 20 22 24 |
| X6 | Company line colour | muted grey (accent only in t6 t15 t16 t20 t22) | Word paints every company/date line in the accent |
| X7 | Bullets vs paragraph | t2 t8 t12 t14 t17 t21 t22 join bullets into one paragraph | Word always bullets |
| X8 | Stats row | rules above/below, tiny tracked caps labels, centred numbers, accent numbers | Word: plain numbers, sentence-case labels, no rules |
| X9 | Photo slot | round / ringed / square-framed / full block placeholder or photo | Word draws nothing when there is no photo |
| X10 | Contact | labelled grids (PHONE / EMAIL ...), centred lists, pills, right-aligned big labels | Word: plain stacked lines or a pipe line |
| X11 | Education / certification entries | degree bold, school muted, year in accent on its own line; or "Degree (2014)" | Word: one run-on line "Degree — School, 2014" |
| X12 | Tools | 2-3 column grid (t1 t6 t16 t19) or centred list | Word: one "·" line |
| X13 | Arabic numbers/phones | `555-0138-64`, `$3.2M` | **Word reverses them**: `64-0138-555`, `3.2M$` (every run is marked RTL, so neutral digits reorder) |
| X14 | Accent colour | template's own accent | **t6 (brown→blue), t14 (orange→magenta), t15 (amber→green), t10 bars** |
| X15 | Justified summary, italic summary | t2 (justify), t11 (italic) | plain |

## Per template (what is missing in Word, beyond X1-X15)

- **t1 (Open)** summary highlight (lime marker) on "survive handover"; name 2-line caps; rules above/below the stats; skills = name + level right, dot row UNDER; tools 2-col grid; education 2 lines (degree / school · year); vertical split rule stops short of page end.
- **t2 (Sidebar, navy/gold)** round photo with gold ring (placeholder grey); gold hairline after every heading (side and main); letter-spaced headings; name caps in the gold band, title letter-spaced; labelled 2×2 contact grid; stats row between grey rules; experience TIMELINE: gold vertical line with hollow circle nodes, dates right italic, company on its own line, bullets joined as one paragraph; skills: name | short gold bar | "95%"; languages level right-aligned in gold; education 3 lines (year gold); certifications title / detail gold; **REFERENCES section missing in Word** (AR sample has references); gold band starts 34px below the top.
- **t3 (Sidebar, yellow)** square black-framed photo box; name centred caps; title tracked caps; side headings centred caps with thick rule under; contact centred bold; competencies/software/languages centred lists; main headings very large display caps; stats between black rules; job titles caps, meta line caps; TECHNICAL SKILLS inside a black-bordered BOX, 2-col black bars with %; education/recognition in caps.
- **t4 (Sidebar, navy/orange)** round photo with white ring; orange heading ribbons that overhang the sidebar edge (fold); labelled contact (Phone/Email/Address/Portfolio); stats: orange numbers, tracked caps labels, rules; experience = date column (2021 – Present stacked) + vertical rule + content; skills name + level right + orange dot row under; languages level right; Recognition + inline "Tools" line.
- **t5 (Sidebar, blue on grey page)** grey page background with inset blue sidebar (margins round it); round photo; white rounded pill headings in sidebar, black rounded pill headings in main; stats: coral numbers, centred; timeline with date column + black dot nodes; skills = 3-col grid of cards with slider + knob + %; education cards (year + degree/school on light cards).
- **t6 (Open, centred)** name letter-spaced caps centred; title tracked caps accent between two rules; contact centred with "·"; stats accent numbers; summary centred; headings tracked caps with rule under; skills name + % with a bar UNDER (brown); recognition bulleted; systems 2-col grid; **accent is brown in PDF, blue in Word**.
- **t7 (Band, yellow/navy)** photo block (grey square) in the top-right; name condensed caps 2 lines; title tracked caps; side headings tracked; skills bars stacked with % right; contact at the bottom of the navy column; Training 2-col grid; stats with rules.
- **t8 (Band blocks)** pale-blue strips across the top and bottom of the page; grey portrait block top-left (full column width); navy "ABOUT ME" block with a short white rule; full-width pale-blue section bars (tracked 5px); header block: name light + heavy centred, title tracked caps, white rule, stats row with rule; skills = name + LEVEL word under + dots right-aligned; labelled contact rows; education/experience "Title (dates)" + paragraph (inline, not bullets); **"ALSO" block** regrouping Recognition / Tools / Languages as labelled inline lines (Word splits them into 3 sections).
- **t9 (Sidebar, yellow boxes)** name caps centred; sidebar sections in black-bordered boxes with header row; labelled centred contact; main headings huge; summary in a bordered box; each job in a bordered box (company caps + dates right, role · location); education boxes; TECHNICAL box with 2-col bars; **Word breaks the name "Ashwort / h"**.
- **t10 (Sidebar, rust)** round grey photo; name + title centred; labelled contact; tools as a list; languages level right bold; certification detail bold; skills = bordered card with 3-col sliders (blue) and %; stats accent-blue numbers with rules; dates right-aligned.
- **t11 (Band, dark/yellow)** dark top-left block (photo area); italic summary with a short yellow rule; dot rows under skill names, level right; experience entries with a yellow start bar; job titles tracked caps; title tracked caps; stats tracked labels; contact line with "·"; LANGUAGE pushed to the bottom.
- **t12 (Open, off-white)** off-white page; name condensed caps + title right-aligned on the same line; headings condensed caps with long trailing rule; timeline with hollow circle nodes; contact right-aligned with big condensed labels (PHONE/EMAIL/WEB); skills as pink RINGS with % inside, name + level under; titles "Role (2021–Present)".
- **t13 (Band navy)** contact right-aligned stacked in the band; title tracked caps gold; stats gold numbers under a rule; timeline with filled navy nodes on a gold line; skills 2-col, level right, dot rows under; bottom row: Education | Certifications side by side under a rule.
- **t14 (Band, cream/navy/orange)** **right column is navy in the PDF, white in Word**; large photo block (navy square) top of right column; orange name block overlapping the columns; name condensed tracked caps; orange full-width heading bars with tracked caps text centred; labelled contact (PHONE/EMAIL/STUDIO/PORTFOLIO) in orange tiny caps; timeline with white nodes; experience inline paragraph; **accent orange→magenta in Word**.
- **t15 (Sidebar, green/amber)** amber band from 70px down across the page; big cream circle photo overlapping band and sidebar; name caps 2 lines; stats amber numbers with rules; dates right italic amber; company italic; skills bars with % right; languages inline "English Native · German Fluent"; certification detail amber; **accent amber→green in Word**.
- **t16 (Sidebar, charcoal/red)** round photo with red ring; title tracked caps red; stats red numbers + rules; skills = pink RINGS 2-col; dates right; education 2-col; tools 3-col grid; certifications as plain lines.
- **t17 (Band, navy/lavender)** photo block (lavender) top right; navy name block; section bars in navy; education/experience with filled navy bullets (node) and inline paragraph; skills RINGS 4-col; stats with rules.
- **t18 (Band, navy)** framed photo (white frame, square) overlapping the band edge; title tracked caps gold; gold tiny labelled contact; education year above degree; stats gold condensed numbers; dates ABOVE the role; role caps; skills name | bar | % in the main column.
- **t19 (Gutter)** rule under the name (thick); title tracked caps accent + contact line right on the same row; stats tracked labels; hairline rules between every section; skills 2-col bars with %; tooling 3-col grid; education/certifications 2-col; languages inline with accent level.
- **t20 (Sidebar, beige/maroon)** square beige photo block; headings light tracked caps (thin weight); labelled contact (tiny maroon labels); dot rows under skills, level right; languages level bold maroon; main headings centred tracked; timeline on the RIGHT edge with maroon nodes; dates right maroon; job titles caps; education "SCHOOL" caps with year.
- **t21 (Band, lime/green)** rounded lime header card with round ringed photo left and name right-aligned; dark pill contact bar with 4 items spread; rounded green sidebar card; lime pill headings; education "degree small / school large accent / year"; experience "Role · dates" small above "Company · Location" large; inline paragraph; vertical rule before each section; stats in a dark rounded card at the bottom.
- **t22 (Open)** giant vertical "RESUME" word in orange down the left edge; name caps, title tracked caps; headings with trailing rule; timeline hollow nodes; contact right with big labels; skills RINGS; education with nodes; **Word omits the "RESUME" band entirely**.
- **t23 (Sidebar, grey)** a black vertical line along the column seam with three black dots; title in a black pill (right); stats with rules; skills stacked black bars with %; EDUCATION pushed to the bottom of the sidebar.
- **t24 (Sidebar, grey page)** grey page with inset charcoal sidebar; round photo; yellow heading bars in sidebar, black bars in main; education on light cards with year; languages level yellow right; date column + timeline nodes; skills RINGS in a 3-col card grid; certifications 2-col.

**Arabic:** every template shows the same losses mirrored; plus X13 (digits and
`$` reordered in phones, metrics and date ranges: `2013 - 2015` order flips) and
eight templates already flow to 2 pages with the full sample.

## Feasibility in Word (what can be rebuilt, editable)

| Feature | Word technique | Fidelity |
|---|---|---|
| caps / letter-spacing / weights | `w:caps`, `w:spacing` on runs (text stays as typed) | exact |
| trailing heading rule | tab to the column end with an underscore leader in the rule colour, raised with `w:position` | close |
| rule under / above | paragraph borders | exact |
| filled bars / ribbons / section bars | paragraph or cell shading | close (no rounded corners) |
| pills (rounded) | shading, square corners | close |
| skill bars beside the name, % text | a 4-cell row: name / fill / track / % with shaded cells | close |
| dot rows | ● ○ glyphs in the accent | close |
| rings with % inside | rings are not drawable as editable text in a table; fallback: % in a ringed cell? -> decided per template | approximate |
| timelines with circle nodes | cell border as the line + node glyph in the node column | close |
| photo round + ring | image cut to a circle, ring drawn into the image; placeholder circle where the PDF shows one | close |
| full-height column fill, page strips | shapes in the page header (every page) | exact |
| labelled contact grid | nested 2-col table | exact |
| vertical giant "RESUME" | rotated text box (`textDirection`) in a cell | possible |

## Decisions made during the run

1. **The Word design is built in code, per template** (`app/exporters/docx_design.py`),
   directly with python-docx on the layout master's styles, instead of the
   generic 2x2 Jinja master. The generic layout stays for templates not yet
   rebuilt. Why: each template's details (grids, timelines, bars beside the
   name) cannot be expressed as data for one shared master.
2. **Photo placeholder:** where the PDF draws an empty portrait placeholder, Word
   draws the same shape (circle/square, same colours, same ring) WITHOUT the
   "PORTRAIT PLACEHOLDER" words (no text in images); Word users can right-click
   > Change Picture. Closest to the PDF.
3. **Arabic digits (X13):** in the new designs only runs that contain Arabic
   letters are marked RTL; phones, emails, `$3.2M` and years are LTR runs inside
   the RTL paragraph, so Word shows them as the PDF does.
4. **Demo CV:** the builder's starting sample becomes `data/demo_resume*.json`
   (shorter content, same sections + References); `data/sample_resume*.json`
   stay unchanged for the tests and the gallery/landing showcase.
5. **Vertical padding is paragraph spacing, never a cell margin** (measured in
   Word: it applies the LARGEST top margin in a row to every cell of that row,
   so the header's padding pushed t8's merged side column down 25pt).
6. **Side-column sections are nested tables with unbreakable rows** (heading in
   the first entry's row): a heading can no longer end a page alone in the
   side column (t2's long CV left CERTIFICATIONS at the foot of page 1).
7. **Arabic line height:** a template's CSS line-height is applied relative to
   the face's own "single" line: 1.2x size for Latin faces, 1.75x for the Arabic
   ones, never below single (the first cut doubled Arabic line gaps: t2 AR ran to
   2 pages). Letter-spacing is never applied to runs holding Arabic letters
   (Word pulls the joined letters apart; the PDF draws none there).
8. **Bidi facts measured in Word:** in a bidi paragraph `w:ind` left/right and
   `w:jc` left/right are LOGICAL (start/end); paragraph and cell borders are
   PHYSICAL. Dot rows are marked RTL in Arabic so the filled dots start on the
   right, as in the PDF.
9. **Exact heights stay banned** (`tests/test_docx_flow.py`): bars and spacer
   rows use "at least" heights around a 1pt empty paragraph instead.
10. **Tests:** the layout-master tests (`tests/test_docx_layouts.py`) now cover
    the templates still exported through the layout masters; designed
    templates get the same promises in `tests/test_docx_designs.py` (headings,
    skill text + graphics, unrated skill, contrast on fills, photo, Arabic
    mirroring + digits not RTL, embedded fonts) and the flow rule in
    `tests/test_docx_flow.py` (every heading/title in an unbreakable row shared
    with what follows). No assertion was loosened.
11. **Arabic vertical gaps x0.8** (`docx_design.AR_GAP`): the Arabic faces'
    lines are taller than the PDF's CSS lines; the gaps shrink, the lines never
    do (t4 AR spilled one line).
12. **Where Word's natural lines make a column longer than the PDF's, the gaps
    are trimmed, never the text** (t20: dot glyph lines are taller than 9px CSS dots).
13. **t20 Arabic portrait block is 70px tall**, as the Arabic PDF draws it (its
    flex column shrinks the 214px block to fit the taller Arabic text).
14. **Per-template checkpoints run the Word test subset** (`-k "docx or word or
    demo"`, ~3 min, ~1080 tests); the full fast suite runs at the item
    checkpoints and at the end.
15. **Full `--e2e` run not completed:** at 10% after 35 minutes (it shared the
    PC with Word's verification), it was stopped; instead the whole fast suite
    ran (3876 passed) plus every browser test touching the builder seed, the
    exports and Word (68 passed). The full `--e2e` run is left for the merge gate.
16. **`tests/e2e/test_word_follows_the_builder.py`** finds the name by its
    PARAGRAPH (a design may set it in two runs, like t8's PDF); for a designed
    template the name colour is the run's own and must read on its fill.
17. **Golden images:** none changed and none were updated (no HTML/PDF template
    was touched; the pixel and HTML goldens pass in the fast suite).

## Pilot results (item 3): modern-t2 and modern-t8, rendered by Word on this PC

Test (a) = demo CV with photo + references; (b) = long CV (5 jobs, 12 skills,
4 languages, references).

| File | (a) pages | (b) pages | Grade | Remaining differences |
|---|---|---|---|---|
| t2 EN | 1 | 2 | **CLOSE** (near MATCHES) | bar ends square (PDF rounded); heading rule a hairline via tab leader, sits ~1pt lower; vertical rhythm ~5% looser; placeholder circle has no words |
| t2 AR | 1 | 2 | **CLOSE** | as EN; the stat "2×" reads as typed (the PDF's bidi shows "×2") |
| t8 EN | 1 | 1 | **CLOSE** | name's first word is the regular face (the PDF's 300 weight is not built); dot glyphs slightly smaller; bar text 1-2px lower |
| t8 AR | 1 | 2 | **CLOSE** | as EN |

Long CV page 2: sidebar colour continues (header shape), section bars and
heading rules keep their style, no clipped text, every heading stays with its
first entry (checked in the Word renders and by the flow test).

### pdf2docx comparison (installed in the scratchpad only)
Converted the same PDFs (demo CV with photo) and opened them in Word:
- **English t2:** looks close at a glance, but the fonts are not embedded (Word
  falls back to a serif), the photo is dropped (only the ring survives), and
  every paragraph has an EXACT line height (~70 per file: text grows -> clips).
- **English t8:** the header block breaks (title bar misplaced, stats labels lost).
- **Arabic:** broken - names and words reordered ("خليلليلى"), "$3.2M" -> "3.2$ M4",
  labels merged; t2 AR spills a stray line to page 2.
- **Editability:** static positioned text boxes/tables sized to the PDF; a longer
  CV cannot flow. **Not usable** as the export; the per-template design wins.

## Results after item 4 (templates rebuilt this run)

All graded from Word's own rendering on this PC, side by side with the PDF
(`docs/review/word_fidelity_review.html`, Desktop "CVStand Word fidelity review").

| Template | EN | AR | Demo CV (photo + refs) | Long CV |
|---|---|---|---|---|
| modern-t2 | CLOSE | CLOSE | 1 page / 1 page | 2 pages, clean |
| modern-t4 | CLOSE | CLOSE | 1 / 1 | 2, clean |
| modern-t8 | CLOSE | CLOSE | 1 / 1 | EN 1, AR 2, clean |
| modern-t10 | CLOSE | CLOSE | 1 / 1 | 2, clean |
| modern-t15 | CLOSE | CLOSE | 1 / 1 | 2, clean |
| modern-t20 | CLOSE | CLOSE | 1 / 1 | 2, clean |
| modern-t23 | CLOSE | CLOSE | 1 / 1 | 2, clean |

Remaining differences common to all: rounded corners are square (bars, pills,
cards); dot rows are Arial glyphs (slightly smaller than the CSS dots); the
photo placeholder has no words. Per template: see the review page.

**Not reached (still on the generic layout export):** Sidebar t3 t5 t9 t16 t17
t24; Band t7 t11 t13 t14 t18 t21; Open t1 t6 t12 t22; Gutter t19. Item 5 (font
sizes) not reached.

**Estimate for the rest:** with the shared blocks now in place (SidebarPage,
Stack, block, bullets, bars, dots, timeline nodes, page shapes, photo frames),
a plain template takes ~20-30 min including two Word render rounds: ~6 h for
the 17. Longer: the five RING templates (t12 t16 t17 t22 t24) need a ring
drawn as a shape with the percent as text over it (~1 h to build once), t22's
giant vertical "RESUME" (rotated text box) and t14/t21's overlapping blocks
(~30 min extra each). Item 5 (sizes): ~1.5 h.

---

# Run of 2026-10-01 (15 h, user away) — queue in `docs/WORD_FIDELITY_QUEUE.md`

## How fidelity is measured now
Scratchpad `ovl.py`: the app's PDF and the .docx as **Microsoft Word on this PC**
saves it as PDF, both rasterised by pdf.js at the same size (797×1031 px).
- **strict %** = pixels whose colour differs by more than 40/255 (the number asked for);
- **tolerant %** = pixels with no matching pixel within 2 px in the other page
  (forgives the 1-2 px glyph drift between Word's and Chromium's rasterisers;
  what remains are elements in different places);
- `dy.py`: every text line matched between the two PDFs, vertical offset per line
  (section-by-section positions).

Word and Chromium never rasterise the same text identically (kerning, hinting,
sub-pixel x positions), so a text-dense page keeps several % strict difference
even when every line is in place. **Strict < 5 % is out of reach on text pages;
the realistic bar is strict < 10 % with tolerant < 5 %.** Arabic strict % is
further inflated by the PDF finding below (different faces).

## Decisions made during the run (continued)
18. **Word's single line is measured per face**, in Word on this PC, for all 41
    built families (scratch `calib.py`): the typo line when the font sets
    USE_TYPO_METRICS, else the win line. A CSS line-height (a multiple of the
    SIZE) becomes Word's multiple = CSS / that face's single
    (`docx_design.true_lines`). The old flat 1.2 made Archivo body lines 9 % too
    tight (the "Word packs higher" the user saw) and display names too tall.
19. **Below single** only down to 0.75 (Latin) / 0.78 (Arabic): measured in Word,
    Latin caps at 0.72 do not clip; Arabic marks touch the next line below ~0.75.
    Never "Exactly" (the flow test bans it). Cost: Arabic two-line names run
    ~15 px taller than the PDF's `line-height:0.98`.
20. **Half-leading** (measured): for multiples ≥ 1 Word keeps the first baseline
    at the ascent and puts all extra leading BELOW the line; CSS splits it. Each
    paragraph with a CSS line-height gets the half-leading as space before and
    loses it from space after (`docx_design.half_leading`): same height, the
    PDF's baselines.
21. **Flexbox in Word**: `justify-content:space-between` columns and
    `margin-top:auto` blocks are reproduced by MEASURING what was written
    (`app/exporters/docx_measure.py`: font advance widths incl. joined Arabic
    forms, word wrap, the measured line heights, tables, inline shapes) and
    handing the slack out as ordinary paragraph spacing
    (`SidebarPage.spread_side`, `SidebarPage.push_to_bottom`). A 4 pt reserve
    keeps an estimate error from spilling a column to page 2. Checked against
    Word's own PDF: section tops within ~1-4 pt (t2 sidebar).
22. **Header paragraph flattened** (`flat_headers`): the paragraph holding the
    page shapes was ~14 pt tall at header distance 0 and pushed the body down
    when a template's top margin is smaller (t4's name sat 14 pt low).
23. **Skill bars and dot rows are inline VML drawings** (`bar_shape`,
    `dots_shape`): rounded ends as in the PDF, exact 9 px dots, the line no
    taller than the graphic (glyph dots made every t4 skill row 4 px too tall).
    Editable shapes; name and level stay real text. The graphics test counts
    these drawings too.
24. **Folded ribbon tab (t4)**: the 14 px overhang past the rail and the fold
    triangle are shapes anchored to the ribbon's own line (`vml_anchored`), so
    they move with the text; the same physical shape in Arabic, as the PDF's
    clip-path draws it.
25. **Arabic bidi of neutrals**: a date range "2013 – 2015" is written as start,
    " – " (its own RTL run), end; a stat "2×" as "2" + "×" (RTL run). Word then
    shows "2015 – 2013" and "×2" as the PDF does. Digits, Latin, "$", "@" and "%"
    are still never in an RTL run (the test now checks exactly that).
26. **Arabic faces by role follow the PDF's CSS policy** (`rendering.RTL_TYPOGRAPHY`):
    only the name (Tajawal 800) and the section titles (Tajawal or Cairo, per
    template) take display faces; job titles, reference names, dates and stat
    numbers are IBM Plex Sans Arabic bold (`docx_theme.resolve`, Arabic, no user
    choice). Before, Word drew them in the heading face (Tajawal).
27. **Tiny structural paragraphs** (cell ends, spacers) use an AUTO multiple of
    0.25 (~0.3 pt) instead of single: Word needs them, they should add nothing
    (each added ~1 pt per job/skill row).
28. **AR_GAP 0.8 removed** (now 1.0): it compensated the wrong line heights;
    with true lines the Arabic gaps are the template's.
29. **A cell-end paragraph after a nested table** (measured): when EMPTY, Word
    does not lay it out at all, so padding written on it vanished (t8's header
    lost 26 px; every side column's bottom padding was silently dropped).
    `Box.finish` now puts a 1 pt space in it when it carries padding.
30. **Side column bottom padding = the page's bottom margin**, never both
    (every design set them equal; once item 29 made the cell padding real the
    side column counted it twice and spilled an empty page 2 - t4 Arabic).
31. **flex-shrink photo (t20)**: the PDF's side photo block shrinks when the
    column is full (214 px -> 175 px EN, ~70 px AR). Word measures the column
    and crops the photo's height by the overflow (`crop_picture_height`,
    object-fit: cover), replacing last run's hard-coded 70 px.
32. **Absolutely placed flows (t15)** start where the PDF puts them:
    `SidebarPage.pin_top` measures the rows above and makes up the gap
    (replaces a formula guessed from the name length).
33. **Reserves** (final): spread 4 pt, side fit 12 pt, push-to-bottom 24 pt,
    main near-one-page fit 10 pt EN / 50 pt AR (the Arabic estimate runs short).
    A 2-page demo is worse than a block sitting a few pt high.
34. **Near-one-page fit = the PDF's auto-fit**: when a CV almost fits one page
    (estimate over by <= 160 pt) Word shrinks the row gaps, then all paragraph
    spacing (never below 40 %, never the text), as autofit.js compresses the
    PDF's rhythm. Long CVs (far over) flow untouched.
35. **t12**: the PDF prints SKILLS / EDUCATIONAL HISTORY even over an empty
    section; Word does not leave an empty heading (the tests' rule).
36. **python-docx trap**: once a cell is marked vMerge "continue",
    `row.cells` returns the merge's TOP cell - hold the cell before merging.
37. **Measured helpers** count the content above the page table (a header
    card) and at-least row heights (bands).
38. **Chosen SIZES in Word** (item 4): the PDF's factor per role
    (static/js/typography.js) - name: chosen / its largest size; each section
    heading: chosen / its own largest; details: chosen / the dominant body size
    (by characters), applied to all other text. Designs know a section heading
    as a heading-style run whose paragraph is a label the design printed;
    ATS/editorial masters: every CV Heading run. Graphics keep their size.
39. **Tests made design-aware, none weakened in what they protect**:
    test_docx_theme (run colours are the template's own in a design; faces and
    bold still only from styles), test_smoke (design bullets / caps headings),
    test_unrated_skill (name<tab>level), test_docx_font_embed (the unused-role
    case strips every bold-body element of t1's design).

## FINDING for the user (not changed: PDF/HTML are out of scope this run)
**The Arabic PDF does not use the Arabic faces its CSS names.** The RTL policy
CSS asks for "IBM Plex Sans Arabic", "Tajawal" and "Cairo" by family name, but
`document_html(for_pdf=True)` inlines only `fonts_inline.css` +
`fonts_ar_inline.css`, which declare Arabic glyphs under the LATIN family names.
The three policy families are declared only in the app shell's
`fonts_ar_shell.css`. So Chromium draws Arabic CVs with system fallbacks: on
this PC Segoe UI (body), Times New Roman Bold (names, some headings), Tahoma,
Segoe UI Black (numbers), as read from the PDFs' font tables. On the Linux
server it will be whatever fallback is installed there; the preview iframe
likely has the same gap. Word keeps the faces the CSS INTENDS (table below).

## Arabic font table (t2, t4): role by role
| Role | PDF CSS intends | PDF actually embeds (this PC) | Word before | Word after |
|---|---|---|---|---|
| Name | Tajawal 800 | Times New Roman Bold (fallback) | Tajawal 800 | Tajawal 800 |
| Section titles | Tajawal (t2 700, t4 900) | Segoe UI Bold (t2) / Times New Roman Bold (t4) | Tajawal 700 / 900 | Tajawal 700 / 900 |
| Body | IBM Plex Sans Arabic 400 | Segoe UI | IBM Plex Sans Arabic 400 | IBM Plex Sans Arabic 400 |
| Bold labels, degrees | IBM Plex Sans Arabic 700 | Segoe UI Bold / Semibold | IBM Plex Sans Arabic 700 | IBM Plex Sans Arabic 700 |
| Job titles, reference names | IBM Plex Sans Arabic 700 | Segoe UI Bold (t2) / Times New Roman Bold (t4) | **Tajawal 700** | IBM Plex Sans Arabic 700 |
| Stat numbers | IBM Plex Sans Arabic (900 -> 700 built) | Segoe UI Black | **Tajawal 700 / 900** | IBM Plex Sans Arabic 700 |
| t4 date column | IBM Plex Sans Arabic 700 | Segoe UI Bold | **Tajawal 700** | IBM Plex Sans Arabic 700 |

Also found: 7 offered faces (Lora, Raleway, Work Sans, Playfair Display,
Lalezar, Aref Ruqaa, Bebas Neue) are embedded, but Word on this PC draws Calibri
for them: their names are in Microsoft 365's cloud-font catalogue (same class
as the known Open Sans case). Only matters when a user CHOOSES one of them.

## Item 1 results (t2, t4 polished), demo CV with photo + References
| File | strict % | tolerant % | pages (demo / long) | Grade |
|---|---|---|---|---|
| t2 EN | 10.5 -> 7.8 | 3.0 | 1 / 2 | CLOSE (near MATCHES) |
| t2 AR | 9.8 -> 9.1 | 7.1 | 1 / 2 | CLOSE (PDF draws fallback faces) |
| t4 EN | 18.9 -> 8.4 | 3.9 | 1 / 2 | CLOSE (near MATCHES) |
| t4 AR | 11.5 -> 11.2 | 8.7 | 1 / 2 | CLOSE (fallback faces; Arabic name ~15 px taller) |

## Run 4 (2026-10-02) - decisions made during the run
40. **Problems 1 and 2 had one cause: the local server's single-user mode.**
    `run.py` started with CVSTAND_SERVER_STORE=1 (default), so every visitor
    got the one stored `data/resume.json` - the user's own document: an Arabic
    name over English text, no photo, level words, chosen fonts - in English
    AND in Arabic. The live site runs CVSTAND_SERVER_STORE=0 (the browser owns
    the document, a new visitor starts from the demo CV in the interface
    language). main behaves identically locally (checked on a scratch worktree),
    so it was not a regression of this branch. The Word designs DID reach the
    download (checked through the real builder for t2 t4 t8 t11 t22, EN/AR) -
    they only looked plainer on that document.
41. **`run.py` now starts live-like** (browser store, a throwaway SECRET_KEY per
    process, as the multi-visitor guard requires); `run.py --server-store`
    keeps the old single-user mode. Production never runs run.py (gunicorn).
42. **Real-data fixes** found on the user's kind of document: level WORDS in
    t2/t5/t18's fixed value cells broke mid-word ("Proficie/nt") - the cell
    now takes the word's width; t11 Arabic lost its last language line - the
    side spread's reserve is 24 pt in Arabic (4 pt English); a NameError in t2
    with a chosen font + level words (a shadowed name) - caught by the new e2e.
43. **New e2e on the REAL builder path**: gallery "Use this" -> language ->
    Fonts panel (heading font + body size) -> Download Word; fails unless the
    file carries the template's design drawings, its own headings, the chosen
    font and size, RTL in Arabic. Arabic e2e runs on the live-configured server.
44. **Arabic PDF/preview fonts fixed on the branch** (not only "prepared"):
    every golden is rendered from the ENGLISH sample, and the change touches
    only right-to-left documents, so no golden changes (English before/after:
    0.00 % of pixels changed in all five templates checked). The policy CSS now
    names 'CVT IBM Plex Sans Arabic' / 'CVT Tajawal' / 'CVT Cairo' first;
    Arabic previews link typography.css, Arabic PDFs inline those ten faces
    (+~3 MB of HTML per Arabic PDF render, not in the PDF: only the glyphs used
    are embedded). A chosen font still wins. The LIVE site keeps the fallback
    fonts until this is merged and deployed (your decision).
45. test_typography_render's `_own()` now also removes the RTL policy block:
    those tests prove the typography FEATURE emits nothing without a choice;
    the policy is a separate layer that now reuses its 'CVT ' faces.
46. **Arabic phone numbers: one fix for all 50 templates, in `canvas_html`.**
    Cause: Unicode bidi rule W2 - European digits that follow Arabic letters
    become Arabic numbers, the hyphens between them turn neutral, and
    "الهاتف: 555-0100-22" draws as "22-0100-555" (t4 references). In a
    right-to-left document every contact and reference phone is wrapped in an
    LRI...PDI isolate before the template sees it, so wherever a template puts
    it, it stays one left-to-right unit. English output is byte-identical (no
    isolates; before/after 0.00 % on t2/t4/t20), Word is untouched (its own
    path already splits runs). Goldens that would change: none (English only).
47. **The seven "Calibri" fonts: cause found, no code change.** Lora, Raleway,
    Work Sans, Playfair Display, Lalezar, Aref Ruqaa and Bebas Neue are all in
    Microsoft 365's cloud-font catalogue. Word prefers Microsoft's copy to the
    embedded one; on a PC that has not fetched the family yet it shows a
    stand-in (Calibri) while it downloads. Proof: their cache folders
    (%LOCALAPPDATA%/Microsoft/FontCache/4/CloudFonts) are dated 2026-10-01
    21:45, the minute of the run-2 check that saw Calibri (logged 23:25 that
    night). Real Word today: all 7 draw the exact face (advance widths equal
    our TTFs) in ats-t1, modern-t2 and modern-t11, EN and AR, with the roles
    the dropdowns offer. Rejected: renaming the embedded faces to private
    names to dodge the cloud lookup - Word's font box would then show a name
    the user never chose ("keep font choices"), and it would have to apply to
    Montserrat, Poppins and Open Sans too. Word without Microsoft 365 and
    LibreOffice use the embedded copy, which tests/test_docx_cloud_fonts.py
    pins for every offered role. (Raleway and Playfair Display are heading-
    only; a body set to them falls back to the template's body face, as the
    dropdowns never offer that.)
48. **The height estimator now shares a vertically merged cell across its
    rows** (docx_measure.Measure.table). It added the merged cell to its first
    row, so modern-t14's header (photo merged over three rows) read 415pt
    instead of 249pt; `_fit_main` then believed the demo overflowed and cut the
    navy column's spacing by ~20 %. Measured after: 249.5pt = the 346px the
    CSS sets. Affects only tables with vMerge measured as a whole (_above:
    t14, t21) - t21's estimate did not change.
49. **Right-to-left cell borders are logical in Word: fixed for every design.**
    Measured in real Word: in a bidiVisual table w:right on a cell drew on its
    LEFT (leading-edge semantics), while w:tcMar left/right stayed physical.
    fmt_cell mapped "start" to w:right in Arabic, so every Arabic timeline rail
    / side rule sat on the far side of its cell (t14, t22: away from the
    nodes; t2, t4 ...). Now "start" is always w:left for borders. Re-measured
    AR: t14 17.0 -> 9.7 %, t4 11.2 -> 7.9, t2 9.1 -> 8.6, t22 11.35 -> 11.2.
    English output is unchanged (same mapping). Paragraph borders (pBdr) were
    not changed - none of the designs draw a side paragraph border in Arabic.
50. **Foot blocks are pushed AFTER the near-one-page fit** (common.py): the
    push measured the column, then `_fit_main` took spacing out, so the foot
    block (t21's stats card) ended short of the page foot - ~55px in Arabic.
    Tried first and rejected: lowering t21's Arabic reserves (the demo went to
    2 pages - the estimate was not high, the order was wrong). t4 and t18,
    the other two users, re-measured: unchanged.
51. **Measuring instrument error found: pdf.js cannot draw the PDF's skill
    rings.** Chromium prints a conic-gradient ring as a function-based shading
    (ShadingType 1, PostScript function); pdf.js has none and painted the
    rings solid magenta, so every ring template's PDF image was wrong in the
    overlay and its % inflated (t2, t5, t11, t12, t22, t24 ... in runs 1-3).
    The REAL PDF is fine (Acrobat/Chrome draw it). The scratch tool now takes
    the app PDF's page 1 from Chromium itself (same HTML, print media, the
    auto-fit awaited); Word's PDFs stay on pdf.js (no such shadings). Only
    numbers measured from run 4 item 6 onward use it.

