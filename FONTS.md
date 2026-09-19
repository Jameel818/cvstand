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
| Cairo | OFL 1.1 | Arabic behind Montserrat, Poppins |
| Amiri | OFL 1.1 | Arabic behind Fraunces, Merriweather (Naskh, for serif pairings) |
| Noto Kufi Arabic | OFL 1.1 | Arabic behind Anton (display weight) |
| Anton, Archivo, Archivo Narrow, Fraunces, IBM Plex Mono, Inter, Merriweather, Montserrat, Open Sans, Poppins, Source Sans 3 | OFL 1.1 | the Latin families the 49 templates declare |

**Noto Naskh Arabic** is allowed by the policy as an alternative to Amiri and
is not currently used. **Noto Kufi Arabic** is used instead, and is the same
OFL grant from the same foundry — it is a display face, which is what the Anton
pairing needs; Naskh is a text face and would be wrong there.

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
