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
