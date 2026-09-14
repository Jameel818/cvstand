# Handoff — Resume Layout Directions (24 templates)

Design source for a Flask/Jinja2 resume builder. Everything here is current as of
this export; anything dated earlier is stale.

## What this is

24 original full-page resume layouts, each a distinct structural skeleton with its
own palette and type pairing. They are a **design reference in HTML** — real markup
and inline CSS showing intended structure, spacing and colour — not production code
to serve verbatim. The task is to recreate them as Jinja2 templates populated from
resume data.

## Files

| File | What it is |
|---|---|
| `Resume Templates Coded.html` | All 24 layouts. Source of truth for structure, spacing and colour. Opens in any browser. |
| `Resume Template Specs.md` | Per-template inventory, divergence declarations, and the invariants the port must preserve. |
| `Scope Section Spec.html` | Render contract for the stat-chip row: schema, degrade ladder, Jinja loop. Open in a browser. |
| `brief-compliance-checklist.md` | Six acceptance gates. Run after every template edit. |
| `claude-design-brief-portfolio-v1.md` | Locked specs, the renumbering map, and the documented slate for future templates. |

## Structure of the coded file

Each template is:

```
<!-- N -->
<!-- INGEST / divergence / docx notes for this template -->
<div id="tN">
  <div>…badge line…</div>
  <div class="tpl" style="width:850px; height:1100px; …">  ← the page itself
```

- Page box is **exactly 850×1100px** (US Letter at 100dpi), `box-sizing:border-box`.
- **Inline styles only.** No stylesheet to resolve, no class names to trace. The one
  class, `.tpl`, carries only the page shadow for the reference view — drop it in the port.
- The badge line above each page is reference chrome. Not part of the template.

## Porting notes

**Do not change visual values.** Colours, sizes, spacing and fonts are locked and were
audited. The port's job is to replace placeholder content with data holes.

**Invariants the port must not break** (full list in the specs doc):

- Skill name *and* level are real selectable text in every skill graphic.
- No content in CSS pseudo-elements.
- Repeating entries stay true siblings with identical structure.
- Scope rows derive their column count from the surviving chip count.

**Scope rows** — every one uses `grid-auto-flow:column; grid-auto-columns:minmax(0,1fr)`
so three chips spread correctly. Drop empty chips *before* the loop, cap at four. See
`Scope Section Spec.html`.

**Ring skills and Word** — `conic-gradient` has no python-docx equivalent. Documented
switch: rings in HTML, dot-grid in Word, name and level as text in both. Search the
coded HTML for `docx:` to find the affected blocks.

**Print** — target US Letter; apply `break-inside: avoid` to timeline and experience
entries so a PDF render doesn't split an entry mid-bullet.

## Data model

One dict per resume:

```
name, title, photo_url, summary,
contact { email, phone, address, site, social[] },
achievements [ { metric, label } ],          ← Scope chips; metric is a STRING
experience  [ { company, role, start, end, bullets[] } ],
education   [ { school, degree, start, end, gpa, bullets[] } ],
skills      [ { name, level } ],             ← level is a word, not only a number
languages   [ { name, level } ],
references  [ { name, title, phone, email } ]
```

Keep `metric` a string — `"$4.1M"`, `"95%"`, `"2×"` carry formatting the user chose.

## Fonts

Poppins, Inter, Montserrat, Archivo, Archivo Narrow, Anton, Fraunces, Source Sans 3,
Merriweather, Open Sans — loaded from Google Fonts in the coded file's `<head>`.
Self-host equivalents in the app. Do not embed a licensed face into a distributed
`.docx` without the licence to do so.
