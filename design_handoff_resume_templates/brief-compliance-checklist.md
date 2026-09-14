# Brief-compliance checklist

Run this against the rendered template after every generation or edit.
Each row is pass/fail — no "mostly." A fail is fixed and re-checked, not noted
and shipped.

Order matters: the gates that block delivery come first, so a fail there stops
the pass before time is spent on craft nits.

---

## Gate 1 — literal instruction compliance (blocks delivery)

The most common real failure is not a design flaw, it is an instruction that
was read loosely. Check each explicit instruction from the request as its own
row, quoted verbatim.

| # | Instruction (quote it) | Pass? | Evidence |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

Rules for this gate:

- **Quote the instruction, don't paraphrase it.** "Enlarge the name" and "make
  the name the same size as the Summary title" are different requirements and
  paraphrasing loses the second one.
- **Size/color instructions need a measured value, not an eyeball.** If the
  request says "same size as X," read the actual value on X and on the target
  and confirm they match.
- **"Keep everything else as it is" is itself a checkable row.** Diff what
  changed; anything touched beyond the request is a fail.
- **A locked element stays locked.** If the user said an element is final,
  confirm it is byte-identical to before.

## Gate 2 — accessibility and machine-readability (blocks delivery)

| Check | Pass? |
|---|---|
| Every skill's name is real selectable text | |
| Every skill's level is real selectable text, not only a bar/ring/dot fill | |
| No information conveyed by color alone | |
| No content in CSS pseudo-elements | |
| Text contrast on its actual background meets 4.5:1 for body, 3:1 for large | |
| Reading order in source matches visual order | |

## Gate 3 — data-mapping readiness (blocks the Jinja port)

| Check | Pass? |
|---|---|
| Repeating units are true siblings with identical structure | |
| No specially-styled first or last entry | |
| Every field a template would fill is a discrete element, not a merged string | |
| Empty-value degrade path defined for each optional field | |
| Stat chip with empty metric hides the whole chip, caption included | |
| Class or structure names stable enough to target from a template | |

## Gate 4 — spec fidelity

| Check | Pass? |
|---|---|
| Every palette hex matches the locked spec exactly, digit for digit | |
| Type pairing matches the locked spec; no substituted face | |
| Full type scale present — no flattened hierarchy | |
| Section order matches the locked spec | |
| Chosen skill pattern is the one requested (bars / circular / dot-grid) | |
| Pure-white templates: no background tints beyond graphic + accent marker | |
| If a reference was supplied: three divergence axes named in writing | |

## Gate 5 — craft

Pure white has no forgiveness; this gate is where that gets paid for.

| Check | Pass? |
|---|---|
| Left edges align across all sections at the same nesting level | |
| Gaps between peer elements are equal — no one-off spacing | |
| Timeline bullets centered on their rail, rail terminating deliberately | |
| Section headings sit on a consistent baseline | |
| No orphaned heading at a column or page break | |
| No skill label wrapping to two lines when its peers use one | |
| Rule weights consistent — hairlines all the same thickness | |
| Page box measures exactly its declared size — padding inside the box (`border-box`), not added to it | |
| Content fits the page box with no clipping or overflow — verify `scrollHeight <= ` declared height, don't assume slack absorbs it | |

## Gate 6 — content sanity

| Check | Pass? |
|---|---|
| No real person's data anywhere — placeholders only | |
| No sample content carried over from a reference image | |
| No vendor watermark, brand name, or trademark from a reference | |
| Placeholder copy is plausible for the archetype's seniority | |
| Stat chips read as scale/ownership, not craft output volume | |

---

## Reporting format

Report deltas only:

```
Compliance pass — template #N
Fixed:   <what failed> → <what changed>
Fixed:   ...
Open:    <anything still non-compliant, and why>
```

If everything passed first time, say so in one line. Do not restate the spec.
