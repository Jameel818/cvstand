# Claude Design brief — Resume template portfolio remediation v1
---

## RENUMBERED — read this before reconciling any template number below

The file was renumbered to a contiguous **1–13**. Every template number written
elsewhere in this brief refers to the OLD serial. Map:

| old | new | template |
|---|---|---|
| 2 | **1** | Editorial sidebar · FinTech Elite |
| 23 | **2** | Rounded dark sidebar, black pill headers, coral slider skills |
| 24 | **3** | Two-tone ribbon banners, photo top-right |
| 25 | **4** | Vertical RESUME rail + bold typographic, rings |
| 26 | **5** | Full-bleed typographic mono, ring diagrams |
| 27 | **6** | Navy sidebar + gold band, levelled skill bars |
| 28 | **7** | Cotton sidebar + cherry rail, dot-grid |
| 29 | **8** | Forest sidebar + amber band, seam photo |
| 30 | **9** | Navy/gold interlocking bars, dot-grid |
| 31 | **10** | Squared replica of new #2 |
| 32 | **11** | Modern Tech Lead |
| 33 | **12** | Data Scientist |
| 34 | **13** | ATS-safe single column |

Retired and no longer referenced: 1, 4, 5, 9, 12, 15 (old serials).
This supersedes the earlier "retired numbers stay retired / never renumber"
rule — that rule was written before the renumbering was requested.

New work numbers from **14** up, contiguously.


LOCKED SPEC. Palette hexes, type pairings and section orders below are fixed —
do not substitute or "improve" them. Creative latitude is layout, spacing,
and detail only.

Target file: `Resume Templates Coded.dc.html`
Convention: each template is a numbered block with a `<!-- N -->` marker and an
`id="tN"` wrapper. Keep that convention. Do not renumber existing templates.
Deliverable: coded HTML, inline styles, ready for a Jinja2 port.
Every page box is exactly 850×1100px, `box-sizing:border-box`, no overflow.

---

## PART 0 — Shared invariants (apply to EVERY template you touch)

These five defects recurred across the whole portfolio. Implement each ONCE as a
repeated pattern and apply identically everywhere — do not solve them per-template.

1. **Photo placeholder cannot squash.** Any circular photo that is a flex-column
   child must carry `flex-shrink:0; aspect-ratio:1` alongside its width/height and
   `border-radius:50%`. Without it, sidebar content pressure renders it oval.

2. **Both columns terminate together.** In every two-column template the sidebar
   and main column must end within ~40px of each other, and both inside the
   1100px box. Fill shortfall with real content (an extra entry, a Languages or
   Certifications block) — never with `margin-top:auto`, `space-between`, or
   padding, which only relocate the gap.

3. **Skill level is always real text.** Every bar, ring, or dot row carries the
   skill name AND its level as selectable text (a `%` value or a level word).
   The graphic is never the only carrier. This is a blocking requirement.

4. **Stat chips hide when empty.** A chip is a discrete element holding a metric
   and a caption. When the metric is empty the WHOLE chip is hidden, caption
   included — never a bordered box with a floating label and no number.

5. **No ellipsis truncation on skill names.** Never
   `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` on a skill
   label. Names wrap or the type size drops; they are never clipped.

Also: repeating entries are true siblings with identical structure (no specially
styled first entry); no content in CSS `::before`/`::after`; source order matches
visual order; body text ≥4.5:1 contrast on its actual background, large text ≥3:1.

---

## PART 1 — RESOLVED: five under-built templates were CUT

DECIDED: #1, #4, #5, #9, #12 have been deleted rather than brought up to standard.
Do not re-add them. Their numbers stay retired — numbering is non-contiguous by
design, so never renumber surviving templates to close a gap.

Reference only, for the future expansion in PART 7 — the palettes that were retired:

| retired # | palette |
|---|---|
| 1 | `#2f3237` sidebar, `#242424` ink, `#d8d8d8` track |
| 4 | `#2d3748` sidebar, `#c9d3dd` / `#e7edf2` tints, `#4a5568` ink |
| 5 | `#1e3653` sidebar, `#3d5a7c` mid, `#7fb3e0` accent |
| 9 | `#0d2a4f` sidebar, `#1c3f6e` mid, `#e4e4e4` track |
| 12 | `#e08a2b` accent, `#1c1c1c` sidebar |

<details><summary>superseded original instruction</summary>

Templates #1, #4, #5, #9, #12 are early sketches at 2.7–5.0k characters while the
rest of the portfolio runs 10–17k. Side by side they read as broken, not simpler.
Bring each to parity. Keep each one's existing palette exactly:

| # | Keep this palette | Current gap to close |
|---|---|---|
| 1 | `#2f3237` sidebar, `#242424` ink, `#d8d8d8` track | 3 dot meters carry NO level text — blocking |
| 4 | `#2d3748` sidebar, `#c9d3dd` / `#e7edf2` tints, `#4a5568` / `#6b7688` ink | No skill visualization at all |
| 5 | `#1e3653` sidebar, `#3d5a7c` / `#4a6f94` mid, `#7fb3e0` accent | Two stray percentages, no coherent skills section |
| 9 | `#0d2a4f` sidebar, `#1c3f6e` mid, `#e4e4e4` track | Two stray percentages, no coherent skills section |
| 12 | `#e08a2b` accent, `#1c1c1c` sidebar | No skill visualization at all |

For each: add a proper skills section (6 skills minimum) using the pattern named
below, add a stat-chip row per PART 2, and bring section depth up so the page
fills without dead space. Section order stays as each template already has it.

Skill pattern per template — do not swap these:
- #1 → dot-grid, 5 dots, level word beside each row (`Expert` / `Advanced` /
  `Proficient` / `Foundational`)
- #4 → horizontal bars with `%` text right-aligned on the row
- #5 → circular rings, `%` centred in the ring, name below
- #9 → horizontal bars with `%` text right-aligned on the row
- #12 → dot-grid, 5 dots, level word beside each row

</details>

Dot-grid mapping, fixed and identical everywhere it appears, and still binding
for every template in the file:
`Foundational 2 · Proficient 3 · Advanced 4 · Expert 5` (of 5).

---

## PART 2 — Stat chips across the portfolio

Only 2 of 16 templates (#27, #29) currently have quantified-achievement chips.
This is the single highest-leverage element on a premium CV — a recruiter's
six-second scan lands on a number or on nothing.

Add a 4-chip row to every template that lacks one: #2, #23, #24, #25, #26, #28,
#30, #31. (#27 and #29 already have one. #1/#4/#5/#9/#12/#15 no longer exist.)

Spec:
- 4 chips in an equal-width row, rule-bounded top and bottom (1px hairline in
  the template's existing neutral), no fills, no rounded boxes.
- Metric: large, heaviest weight available, in the template's accent colour.
- Caption: ~9px, letter-spaced, uppercase, in the template's muted ink.
- Placed directly beneath the summary paragraph.
- Metric and caption are separate sibling elements so the Jinja port can hide
  the whole chip on an empty metric.

Chips must read as **scale and ownership**, not craft output volume — budget
owned, team size, markets, growth, retention, AUM, uptime. Not "42 logos designed."

---

## PART 3 — RESOLVED: #2 and #15 merged

DECIDED and already applied: they were one template differing only in palette.
#15 is deleted; **#2 survives** and carries a `<!-- MERGED: ... -->` comment
recording the retired burnt-orange palette as a documented theme variant:
sidebar `#CB3500`, sidebar text `#ffffff`, skill bar fill `#d4a574` on
track `#efe0d1`.

Treat palette as the single theme variable on this template. Do not fork it into
two blocks again — a second palette is a variable, not a template.

---

## PART 4 — Two missing archetypes

The portfolio is heavy on Creative Agency and Executive Consultant and has
nothing for two archetypes where current demand sits. Add both as new numbered
blocks (old #32/#33 — now **11** and **12**), pure white ground, following all PART 0 invariants.

### #32 — Modern Tech Lead
- Palette: ink `#0F172A`, surface `#F6F7F9`, accent `#2563EB`, muted `#64748B`.
- Type: Archivo 900 for the name and section headings; monospace
  (`ui-monospace, SFMono-Regular, Menlo, monospace`) for stack badges and
  metric numerals only. Body in Archivo 400.
- Signature: monospace stack badges (thin 1px-bordered inline chips, no fill) and
  dashboard-style impact callouts — a 2×2 grid of bordered metric cards.
- Skill pattern: dot-grid, 5 dots, level word beside each row.
- Section order: name/role → summary → impact callouts → experience → stack →
  education.
- Stat chips: deploys/month, uptime, services owned, team size.

### #33 — Data Scientist
- Palette: ink `#14213D`, surface `#F4F5F7`, accent `#0F766E`, muted `#5B6472`.
- Type: Archivo 900 headings, Archivo 400 body, tabular numerals throughout.
- Signature: modular KPI cards (4-up, hairline-bordered, metric + caption +
  one-line context) and small-multiple mini charts — three 90px sparkline-style
  blocks built from flex bars, each with a text label and value beneath.
- Skill pattern: circular rings, `%` centred, name below, grouped into
  Languages / ML / Infrastructure.
- Section order: name/role → summary → KPI cards → experience → skills →
  publications → education.
- Stat chips: models in production, dataset scale, lift delivered, papers.

---

## PART 5 — One ATS-safe single-column variant

14 of 16 templates are coloured-sidebar two-column layouts — the worst-parsing
structure for applicant tracking systems. As a showcase gallery this is fine; in
an application portal most of the catalogue underperforms regardless of how good
it looks.

Add old #34 (now **13**), an ATS-safe variant of the strongest design (old #27, now **6**):
- Single column, full width, no sidebar, no colour blocks, white ground.
- Headings as plain bold text on their own line — no bars, no reversed-out type.
- Skills as a dot-grid list with name and level word, one per line.
- Stat chips as plain `metric — caption` text lines, no borders.
- Same content model and field names as #27 so one JSON payload feeds both.
- Caption it explicitly: `34 — ATS-safe single column (portal submissions)`.

---

## PART 6 — Word/.docx path for the ring templates

#24, #25, #26, #31 use `conic-gradient` rings, which have no python-docx
equivalent. Add an HTML comment directly above each rings block:

```
<!-- docx: conic-gradient has no python-docx equivalent.
     Word export renders this section as a dot-grid (5 dots,
     Foundational 2 / Proficient 3 / Advanced 4 / Expert 5),
     name and level word as real text. HTML keeps the rings. -->
```

Also confirm no skill name in these templates hyphenates or wraps mid-word —
the docx table architecture assumes zero hyphenation.

---

## Acceptance gates

Do not report done until every row passes, measured rather than eyeballed:

1. Every template fits its 850×1100 box. Measure BOTH `scrollHeight - clientHeight === 0`
   AND every descendant's `getBoundingClientRect()` bottom/right against the page box —
   `.tpl` carries `overflow:hidden`, which clamps `scrollHeight` while content is still
   visually clipped, and an absolutely-positioned child measures against its nearest
   positioned ancestor, not the page.
2. Sidebar and main column terminate within 40px of each other in every
   two-column template.
3. Every skill row in all templates has name AND level as selectable text.
4. Every template has a 4-chip stat row; every chip's metric and caption are
   separate elements.
5. No `text-overflow:ellipsis` on any skill label anywhere in the file.
6. Every circular photo carries `flex-shrink:0; aspect-ratio:1`.
7. Palette hexes match this brief digit for digit.
8. No real person's data; placeholder copy plausible for each archetype's
   seniority; no vendor watermark or sample text from any reference image.

Report deltas only — what failed and what changed. Do not restate the spec.

---

## PART 7 — Expansion to 20 templates (next phase, not this pass)

Current file: **13 templates**, numbered 1–13.
PARTS 4 and 5 are DONE — they became **11** Modern Tech Lead, **12** Data
Scientist, and **13** ATS-safe single column.

The remaining seven to reach 20 should be commissioned as deliberate archetype
and structure coverage, not more sidebar variants. Current portfolio skew: 8 of
10 are coloured-sidebar two-column layouts.

Proposed slate — one per row, each differing from every existing template on at
least two named axes (structure AND archetype, not palette alone):

| # | Archetype | Structure (must not repeat an existing one) | Skill pattern |
|---|---|---|---|
| 14 | FinTech Elite | Single column, tabular figures, bordered metric chips | bars |
| 15 | Creative Agency | Asymmetric grid, duotone blocking, project tag chips | dot-grid |
| 16 | Modern Tech Lead | Two-column with monospace right rail, no photo | dot-grid |
| 17 | Data Scientist | Full-width KPI band above a two-column body | rings |
| 18 | Executive Consultant | Single column, wide margins, one accent, no photo | dot-grid |
| 19 | Creative Agency | Horizontal-band layout, no vertical sidebar at all | rings |
| 20 | FinTech Elite | Dense two-page-safe layout, `break-inside: avoid` on entries | bars |

Rules for the expansion phase:
- Every new template inherits PART 0 invariants and the PART 2 stat-chip spec.
- No new template may be an existing one re-skinned. If the only difference is
  palette, it is a theme variable on the existing block instead.
- The file is now contiguous 1–13. Number new work from **14** up, contiguously.
- Keep at least three single-column ATS-safe templates in the final 20.
