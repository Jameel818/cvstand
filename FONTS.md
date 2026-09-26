# Font policy

Every typeface this project ships must be **free for commercial use inside a
product that is sold**, and its licence text must travel with the files. That
is stricter than "free to download", and the difference is the whole reason
this file exists.

Adopted 2026-09-19 from the user's own written policy. `LICENSES.md` is
generated and lists what IS shipped; this file says what MAY be, and
`tests/test_font_policy.py` is what makes it true rather than aspirational.

## The allowlist

Nothing outside this list may be served from `app/static/fonts/` or referenced
by a template.

| Family | Licence | Role here |
|---|---|---|
| IBM Plex Sans Arabic | OFL 1.1 | Arabic behind Inter, Open Sans, Source Sans 3, Plex Mono |
| Tajawal | OFL 1.1 | Arabic behind Archivo, Archivo Narrow |
| Cairo | OFL 1.1 | Arabic behind Montserrat, Poppins; shell headings. **VARIABLE, wght 200-1000** |
| Amiri | OFL 1.1 | Arabic behind Fraunces, Merriweather (Naskh, for serif pairings) |
| Noto Kufi Arabic | OFL 1.1 | Arabic behind Anton (display weight) |
| Anton, Archivo, Archivo Narrow, Fraunces, IBM Plex Mono, Inter, Merriweather, Montserrat, Open Sans, Poppins, Source Sans 3 | OFL 1.1 | the Latin families the 49 templates declare |
| Anton SC, Archivo Black, Bebas Neue, Raleway, Playfair Display, Source Serif 4, Work Sans, Lora | OFL 1.1 | typography controls, English (user's choice) |
| Almarai, Alexandria, Mada, Readex Pro, Noto Sans Arabic, El Messiri, Markazi Text, Scheherazade New, Lateef, Aref Ruqaa, Lalezar, Jomhuria, Rakkas, Marhey, Baloo Bhaijaan 2, Lemonada | OFL 1.1 | typography controls, Arabic (user's choice) |

The typography controls also offer families already listed above (Anton,
Archivo, Montserrat, Poppins, Inter, Tajawal, Cairo, Amiri, Noto Kufi Arabic,
Noto Naskh Arabic, IBM Plex Sans Arabic), from their own files — see
"Typography controls" below. All 35 are licensed OFL 1.1, which permits use in
a sold product; each OFL.txt is in `app/static/fonts/licenses/`.

**Noto Naskh Arabic** is allowed by the policy as an alternative to Amiri and
is not currently used. **Noto Kufi Arabic** is used instead, and is the same
OFL grant from the same foundry — it is a display face, which is what the Anton
pairing needs; Naskh is a text face and would be wrong there.

## Variable fonts: declare the RANGE, not a weight

Cairo's vendored `.woff2` is a **variable** font covering `wght 200-1000`
(checked with fontTools). Google serves one file for the whole range —
requesting weight 700 and weight 800 return the identical URL, which is how
this was found.

Declaring it `font-weight: 900` in `@font-face` **pins the axis to Black**, so
`font-weight: 700` in a stylesheet renders at 900 anyway and nothing warns. The
shell headings shipped far heavier than this policy asks for until the
declaration was changed to `font-weight: 200 1000`.

`VARIABLE_RANGE` in `tools/fetch_fonts_ar.py` holds the families this applies
to. Tajawal has no `fvar` table and is correctly declared per static weight —
check before assuming, in either direction.

**The same trap, in the PDF's inline sheet (fixed in typography step 4).**
`fonts.css` declares the Latin variable families the way Google emits them:
one discrete rule per weight, each pointing at the same file. That is
correct. `fonts_inline.css` used to MERGE the rules sharing a file, to embed
each payload once, and so kept only the first rule's `font-weight: 400`.
The PDF, and every pixel golden, drew Inter, Montserrat, Archivo, Archivo
Narrow, Source Sans 3, Open Sans, Merriweather and Fraunces at 400 while the
preview drew their real weights (48 of 49 English templates). The inline
sheet is now `fonts.css` with each url() replaced by the file's bytes, rule
for rule (~4.2 MB). A weight RANGE would have been smaller but not the
preview: four templates ask for a weight their family does not declare,
which discrete rules round to the nearest and a range draws exactly.

## Roles, and where they are applied

The policy assigns faces by ROLE, not by element. The roles live as CSS custom
properties in `app.css` (`--font-hero`, `--font-heading`, `--font-body`,
`--font-cta`, `--font-nav`), and in English every one of them resolves to what
the shell already used, so the Arabic block is the only thing that moves.

| role | Arabic | reaches |
|---|---|---|
| hero | Tajawal 800 (Thmanyah, outlined) | the landing h1 |
| heading | Cairo 700 | `h1`-`h4`, `.eyebrow`, `.stat-strip b`, `.num`, `.faq summary` |
| nav | Cairo | `.site-nav a`, `.footer-cols a`, `.lang-switch a` |
| body | IBM Plex Sans Arabic | everything else, plus `input`/`select`/`textarea` |
| CTA | Tajawal 800 | `.btn`, `.tab` |

**`--font-nav` exists because the policy names Thmanyah Sans for site
navigation specifically.** Thmanyah cannot ship as a file, and Cairo is its
recorded stand-in: the two measured nearly metric-compatible (232.5 vs 230.4
wide, 94 vs 99 ink). Navigation was falling through to body copy until this.

**Heading role is not the same set as `h1`-`h4`.** `.eyebrow`, the stat
numerals and a `<summary>` all read as headings and all inherited body copy.
A role map that only lists tags will keep missing them.

**Chips declare their own face.** `[dir="rtl"] button { font-family: ... }`
sets the CTA family on every DESCENDANT, so the same `.chip-modern` rendered in
Tajawal inside a button and in IBM Plex Sans Arabic on a card. A component's
face must not depend on what contains it.

## The CV roles, inside the 49 templates

The policy names three faces for a CV by role, and they are applied to the
résumé documents themselves — **in Arabic only**:

| role | face | hook |
|---|---|---|
| name | Tajawal ExtraBold 800 | `class="cv-name"` (49, one per template) |
| section title | Tajawal (27) / Cairo (22) — see below | `class="cv-section"` (229) |
| body | IBM Plex Sans Arabic | everything else under `.tpl` |

### Section titles are split across the catalogue, on purpose

The written policy says both things, and they cannot both be true of the same
element:

> "Tajawal Bold ExtraBold for CV name headline **and section titles inside CV
> template**"

> "Word CV template styles … Section Title **Cairo Bold** 12pt all caps"

Asked which wins, the answer was *"50% Cairo, 50% Tajawal"*. So the catalogue
carries both — and the split follows each template's own Latin register rather
than a coin toss, because two templates that look alike in English must not
diverge in Arabic for no reason:

| Latin section head | Arabic section title | n |
|---|---|---|
| Archivo, Archivo Narrow (grotesque) | **Tajawal** | 27 |
| Montserrat, Poppins, Anton (geometric); Fraunces, Merriweather (serif); Inter, Open Sans, Source Sans 3, IBM Plex Mono (humanist) | **Cairo** | 22 |

That lands 27/22 — as near even as a non-arbitrary rule gets. Measured, not
guessed: Archivo leads the section heads in 25 of the 49.

The Tajawal half carries `cv-sections-taj` on its `.tpl` root. The Cairo rule
is the default and the `.cv-sections-taj` rule overrides it at the **same**
specificity (0,2,0), so it must stay after it in source order. **To collapse
back to a single face, delete one of the two rules.**

The rules live in `app/rendering.py::RTL_TYPOGRAPHY`, which `document_html()`
emits **only for `dir="rtl"`**. An English CV never carries a byte of it, and
the classes are inert in LTR because nothing selects them there. Verified: all
49 templates render the three roles in Arabic, and **zero** of the 49 show any
Arabic face in English.

**The alias layer could not express this, and that is why the markup changed.**
`fonts_ar.css` keys on (family, weight), so it can say "Archivo becomes
Tajawal" but never "the name becomes Tajawal". Weight is not a usable proxy
for role, measured across all 49: `Archivo 900` appears at 25px (×30) **and**
at 12px (×25), and `Open Sans 700` is 12px in 42 of its uses — the heavy
weights are mostly bold words inside paragraphs. Mapping them to a display
face would have put Cairo and Tajawal inside body copy everywhere.

**`!important` is required, not emphasis.** All 49 templates set `font-family`
in inline `style` attributes, which outrank any stylesheet rule. The inline
styles carry no `!important` themselves, so ordinary specificity still decides
between the three rules: `.tpl .cv-name` (0,2,0) beats `.tpl *` (0,1,0).

**Family only.** Size, colour, tracking and layout stay as each template set
them — that is the template's identity, and the policy assigns faces.

**`cv-section` is not `sec-head`.** `sec-head` already existed, on four
templates only, and `RTL_TYPOGRAPHY` forces it to `font-size: 14px !important`
to rescue headings that read as body text. Reusing that name for the role hook
would have crushed every section heading in all 49 Arabic templates to 14px,
including 24px mastheads. The two classes coexist: ten elements carry both.

**What this cost.** All 196 HTML goldens changed, and nothing else: strip the
two class attributes back out and the HTML is byte-identical to what shipped
before. All 50 pixel goldens pass unchanged, which is the real proof English
did not move. The Arabic overflow gate stays 49/49 clean after the face swap.

## The outlined headline is sized by its EM, not its box

`tools/outline_text.py` writes `--outline-box` onto every run: the SVG box
height in ems. The box is the face's ascent+descent, which for Thmanyah Serif
Display is **1.25x the em** — so `height: 1em` squeezed a 1.25em box into 1em
and rendered every outlined headline at **0.80em**. Measured in the browser
before the fix: the landing h1 asked for 57.6px and painted a 46.1px em; the
gallery asked for 41.6px and painted 33.3px.

`app.css` multiplies `1em` by that property, so the em square equals the
font-size and the outlines match what live text at that size would do.

**No optical correction is applied on top, and that is a measured decision.**
Thmanyah's Arabic x-height (medial heh — no dots, ascender or descender) is
0.695em, against Cairo 0.770 and Tajawal 0.560: it sits between the two faces
the shell already uses. Against Latin it is 0.695 to Inter's 0.730 CAP height,
and a display headline reads by its caps — so the Arabic h1 wants the SAME
`clamp()` as the English one, which is what it already had. The headline was
wrong by 0.80, not by its scale.

**Runs are one per WORD.** A phrase is a single box with a fixed aspect ratio
and cannot break; the ATS gallery heading was one 1374-unit run that overflowed
a phone the moment the size was corrected. Arabic never joins across a space,
so splitting on spaces changes no glyph. The gap between runs is the font's own
space advance, measured by the shaper and written onto the wrapper.

## Every family a template names must be real

`tests/test_template_fonts.py` asserts that the FIRST family of every
`font-family` stack in the 49 templates is in `fonts.css` AND has a pairing in
`fetch_fonts_ar.py`. Later entries may be generic or system families — naming
Helvetica as a fallback engages no licence and renders nowhere Archivo exists.

`modern/t10.j2` declares `'DM Sans'`, which is vendored nowhere. It therefore
renders in the browser's default sans in Latin -- which differs between
Windows and macOS -- and in the OS default in Arabic, making it **the one
template of 49 the Arabic font work does not reach**. The pixel golden was
captured with that fallback in place, so the baseline agrees with it.

**It is left as it is, on purpose.** Correcting it moves that template's
ENGLISH pixels, and the standing instruction is that the Arabic font policy
must not alter English CV templates. There is no Arabic-only fix available:
the alias generator only emits rules for families present in `fonts.css`, so a
family absent there cannot be given Arabic coverage without also making it
render in English. `tests/test_template_fonts.py::EXEMPT` names it, and
`test_every_exemption_is_still_real` fails if it is ever fixed and the
carve-out left behind.

## Never

**Paid families.** Named explicitly so a search finds them: `29LT Bukra`,
`29LT Zarid`, `GE SS`, `DIN Next LT Arabic`, `FF Shamel`. These are commonly
recommended for Arabic and are licensed per-seat or per-domain.

**Thmanyah Sans / Serif Display / Serif Text.** Free for commercial use, and
still not shippable here. Its licence permits embedding in a web product *"only
as part of a compiled, packaged, or obfuscated product"* and prohibits making
the font *"available in any manner that allows end users... to extract,
download, access... independently as font files, **including through web
embedding**."* A `@font-face` rule serving a `.woff2` is that prohibited case —
the file sits at a public URL and any visitor can save it.

This applies to the **app shell exactly as much as to the résumé templates**:
the prohibition is about the font FILE being fetchable, not about what text it
renders. Serving it for the site chrome publishes the same file.

**The compliant route IS used, for the Arabic landing hero.**
`tools/outline_text.py --build-hero` shapes the headline with HarfBuzz and
converts it to SVG paths at build time, writing `app/templates/_hero_ar.html`.
Geometry is not a font: there is no `@font-face`, no `.woff2`, nothing in the
network tab but the page. The user's own brief names this route — *"export it
as outlined vectors or flattened image, not as extractable font"*.

It is for FIXED text only. Body copy, headings and buttons stay on the OFL
faces, because outlining them would ship a wall of geometry no screen reader
can read and no translator can change. The hero partial keeps the real string
in an `.sr-only` span and marks the SVG `aria-hidden`, so nothing is lost;
`tests/test_hero_outline.py` fails if the copy and the outlines ever drift
apart, which is otherwise invisible.

`outreach/thmanyah-webfont-licence.md` is a ready-to-send request for a
single-domain grant, which their licence invites. **If it arrives, keep the
grant in `outreach/` and add Thmanyah here with a pointer to it.** Cairo and
Thmanyah Sans measured nearly metric-compatible (232.5 vs 230.4 wide, 94 vs 99
ink), so the swap will barely move the layout.

**Any family with no licence file.** `Fonts/Nice fonts/` in the project root
holds fourteen commercial retail faces — `sakkal-majalla`, `bahij-muna`,
`lyon-arabic-display`, `alyamama` and others — with **zero licence files
between them**. Not shipped, not in `app/static/fonts/`, and not to be added
without written terms.

## Typography controls: the user's font choices

`docs/CVSTAND_FONT_CONTROLS.md` lets the user pick a font, weight and size for
headlines and details. Every face a dropdown can offer — 106 of them across
35 families — is built by `tools/build_fonts.py` from `google/fonts` (pinned
to one commit, recorded in `app/typography/build.json`) into:

| path | what | used by |
|---|---|---|
| `ttf/<slug>-<weight>.ttf` | every face | Word embedding (spec §6.3) |
| `web/<slug>-<weight>.woff2` | every face EXCEPT the six below | preview and PDF |
| `typography.css` | one `@font-face` per face | preview and PDF |

**The CSS families are `'CVT <Family>'`.** `fonts.css` already declares
`'Montserrat'`, `'Inter'` and others for the 49 templates, from different
files at different weights. Reusing those names would add faces to families
the templates already render with, and could move an existing CV. With the
prefix, nothing a template names can resolve to these files.
`tests/test_typography_build.py` asserts no collision.

**These are static files, so they declare ONE weight each.** The
variable-font rule above (declare the RANGE) is about serving a variable
file. Here every variable source is cut into static instances first, one per
offered weight, so a single `font-weight` per rule is correct.

Each face is made in one of three ways, decided per family from its own
`OFL.txt`:

| method | faces | what happens |
|---|---|---|
| instanced | 69 | variable font → static instance (wght pinned, other axes at default), renamed per spec §5.3, then subset |
| subset-static | 20 | official static TTF, subset |
| unmodified | 17 | official static TTF, byte-for-byte, **no woff2** |

**Subsetting is by script, never by a CV's characters:** Latin + Latin-Ext
for every family, plus Arabic for Arabic ones. **Arabic families keep their
Latin**, so English words, emails and URLs in an Arabic CV render in the
same family. The build fails if an Arabic face lacks printable ASCII, or if
subsetting dropped any Latin character the source had. Measured: eight Arabic
families stop at Latin-1 UPSTREAM (Almarai, Aref Ruqaa, El Messiri, IBM Plex
Sans Arabic, Jomhuria, Lateef, Scheherazade New, Tajawal), so a "Ł" or "ř"
in those falls through to the generic fallback. The test pins that list.

**Thin/ExtraLight weight class.** Google's official static TTFs store
ExtraLight as `usWeightClass` 275 (Poppins, Tajawal) or 250 (Raleway), a
Windows GDI convention. The build reads the weight from the style name and
accepts only those legacy values; instances it makes always get the exact
weight.

### Why six families ship as unmodified TTF

Raleway, Playfair Display, Lora, IBM Plex Sans Arabic ("Plex"), Scheherazade
New and Lateef each declare a **Reserved Font Name** in their `OFL.txt` that
their own name contains. OFL 1.1 condition 3 says a Modified Version may not
use a Reserved Font Name. So for these six, anything this project changes must
be renamed, and a renamed "Raleway" is not what the user picked. The
alternative is to change nothing. The OFL FAQ
(https://openfontlicense.org/ofl-faq/) settles what counts as a change:

- **Subsetting is modification.** FAQ **2.6**: *"Removing any parts of the
  font when delivering a webfont to a browser, including unused glyphs and
  smart font code, is considered modification. This is permitted by the OFL
  but would not normally allow the use of RFNs."* So these six are not subset.
  They ship with every glyph.
- **WOFF/WOFF2 conversion is modification unless it provably is not.** FAQ
  **2.2**: *"A change in font format normally is considered modification, and
  Reserved Font Names (RFNs) cannot be used."* **2.2.1** allows a WOFF version
  under the original name *"only if the original font data remains unchanged
  except for WOFF compression"* and the metadata is carried unaltered. **2.2.2**:
  *"Some WOFF conversion tools and online services do not meet the two
  requirements… and so their output must be considered a Modified Version."*
  The converter here (fontTools) decompiles and recompiles every table, and
  WOFF2 applies its glyf/loca transform. So we cannot show the font data is
  unchanged, and under 2.2.2 that output counts as modified. The browser
  therefore gets the official `.ttf` (`format('truetype')`), and the cost is
  size, not legality.
- **Embedding in a document is allowed in full or subset.** FAQ **1.12**: *"So
  can I embed OFL fonts in my document? Yes, either in full or a subset. The
  restrictions regarding font modification and redistribution do not apply,
  as the font is not intended for use outside the document."* So when Chromium
  subsets a face into a PDF, or step 6 embeds the TTF in a `.docx`, no Reserved
  Font Name question arises. That applies to these six too.

`tests/test_typography_build.py` enforces this. It re-derives the RFN
families from the vendored `OFL.txt` files and requires exactly these six. It
also requires each of their files to hash to the upstream bytes, with no
woff2 present. Raleway, Playfair Display and Lora exist only as variable fonts
in `google/fonts`, so their statics come from Google Fonts' own family
download (the official statics; the URL and hash are in `build.json`).

**Open question, not changed here:** the older alias layer (`fonts_ar.css`)
serves IBM Plex Sans Arabic as `.woff2` subsets fetched from Google's CSS API
under the original name. That predates this rule and is Arabic-only. Whether
Google's own served subsets count as the Original Version is not settled here.

**Not yet done for these families** (later steps of the spec): the
optical-size measurement that "Adding a family" asks for Arabic faces (spec
step 7), and the Word embedding (step 6).

### Applying the choices (spec step 3)

`app/typography/render.py` writes the choices into the preview document, and
only when the résumé chose something. A CV with no typography keys carries
none of it. There is no link to `typography.css`, no rules, and no runtime.

- **Three groups since step 3c:** Name (`.cv-name`), Headings (`.cv-section`)
  and Details. The Name defaults to "Same as Headings" (font and weight), and
  `font_name: "template"` keeps the template's own face. See spec §2.
- **The family is CSS.** The rules are `!important` on the role hooks
  (`.cv-name`, `.cv-section`, everything else under `.tpl`) for the same
  reason `RTL_TYPOGRAPHY` is: every template sets `font-family` inline. The
  selectors carry one more type selector than the Arabic policy's rules, so a
  chosen font wins in RTL, while a role left on "Template default" keeps the
  policy's face. The Details rule excludes the headline hooks. A headline
  that INHERITS its family (ats-t1's name has none of its own) is pinned to
  its pre-switch face by the runtime; the browser suite found this. The
  same pin keeps a Name on "Template default" untouched under a Headings font.
- **Weight and size are the runtime** (`static/js/typography.js`). Weight
  "Template default" means `nearest_weight()` of each element's own weight,
  from a table the server computes. Template-bold Details text (600 and up)
  renders in the family's real **700 emphasis face**. That face is built for
  every Details family and never offered in a dropdown. Sizes scale each role
  by one factor, through autofit, so a job title that was 1.17× body stays
  1.17× body.
- **Rules switch on only after the weights are written** (`html[data-cvt]`).
  Otherwise Chromium could lay the text out in a chosen family at the
  template's raw weight and fetch a face nobody chose. Mutation-tested: without
  the gate, the "only chosen faces download" test fails.
- **The Latin-Ext fallback.** For the eight Arabic families that stop at
  Latin-1, the stack is `'CVT <Family>', 'CVT Work Sans'` (sans) or
  `'CVT Source Serif 4'` (serif), then the generic. Both fallbacks are built
  at every weight, and the browser fetches one only when a glyph falls
  through. Measured: in Tajawal, "Dvořák Şahin" draws exactly 2 glyphs from
  Work Sans.
- **The PDF (spec step 4).** The PDF document has no base URL, so a linked
  face would fail silently. `document_blocks(..., for_pdf=True)` inlines the
  faces this document can request instead: `faces_for()` plus the Latin-Ext
  fallback where the stack names one, from `typography.css`'s own rules
  (woff2, or the unmodified TTF for the Reserved-Font-Name families).
  `pdf.py` then loads each chosen face explicitly and refuses to print if
  one did not load.

## Word masters are a deliberate exception

`word_masters/*.docx` reference **Arial, Courier, Georgia and Times New Roman**
— system fonts, none of them on the allowlist.

That is not a violation, and the distinction matters: **naming a font in a
document is not redistributing it.** Nothing is embedded; Word resolves the
name against whatever the reader has installed. No licence is engaged at all.

It is chosen for a reason the allowlist cannot serve. A `.docx` is opened on a
machine this project does not control. An OFL family would have to be EMBEDDED
to render, which does engage the licence, inflates every export, and is
precisely what broke the masters once before. The four system families are
present on effectively every Windows and macOS install, and all four carry
Arabic coverage.

The cost is real and worth stating: Arabic in these exports renders in Arial
rather than in a face chosen for it. **Upgrading this means embedding, and
embedding is a change to the paid export path — treat it as its own piece of
work with its own gates, not a font swap.**

## Adding a family

1. Confirm the licence permits use inside a product that is **sold**, not
   merely "free to use". Free-for-personal is not enough.
2. Add the licence text to `app/static/fonts/licenses/<Family>-OFL.txt`.
3. Add the family to the allowlist above, with its role.
4. Run `venv/Scripts/python -m pytest tests/test_font_policy.py`.
5. If it is an Arabic face, measure its optical size against the others before
   wiring it — see `SIZE_ADJUST` in `tools/fetch_fonts_ar.py`. Two of the five
   were 12% and 9% off the mean.
