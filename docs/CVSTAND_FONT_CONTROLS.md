# CVStand: Typography Controls (Font / Weight / Size dropdowns)

> **Instructions for Claude Code.** Read this whole file before you touch code. Start in **Plan Mode**: inspect the repo, then propose a file-level plan. Wait for approval before you implement.
> Project: Flask / Python 3.12. PDF is made by Playwright/Chromium and Word by python-docx. The flat JSON schema has a single `language` field (`"en"` | `"ar"`). The form is a 7-step wizard. Template categories are A (Simple), B (Modern Sidebar) and C (ATS-Friendly).

---

## 0. Goal

Give the user **three optional dropdowns** for each of the three text groups on every template:

| Group | Dropdown 1 | Dropdown 2 | Dropdown 3 |
|---|---|---|---|
| **Name** (`.cv-name`) | Font | Weight | Size |
| **Headings** (section titles, `.cv-section`) | Font | Weight | Size |
| **Details** (body text, bullets, dates, contact lines) | Font | Weight | Size |

That makes 9 controls in total. (Until step 3c, Name and Headings were one "Headlines" group; see §2 for how résumés saved then are carried over.) The **language of the CV** (`language`) decides which font lists appear.

Every control is optional. Its first option is always **"Template default"**, which keeps the template's current look (for example, the existing Cormorant Garamond + Inter pairing). CVs saved before this feature must render exactly as they do today.

---

## 1. Hard rules (do not break these)

1. **No faux bold / faux light.** Load real font files for every offered weight. Set `font-synthesis: none;` on the CV root. Chromium must never fake a weight that doesn't exist.
2. **Only offer weights the font actually has.** The weight dropdown is filtered per font (see §3). You must never show a weight that would fall back silently.
3. **Self-host every font.** Do not load from `fonts.googleapis.com` at render time. PDF rendering must work offline and give the same result every time.
4. **One source of truth.** All fonts, weights, roles, size ranges and defaults live in one registry file (`app/typography/registry.py` or `registry.json`). The UI, validation, CSS, PDF and DOCX all read from it. There are no hard-coded font lists anywhere else.
5. **Server-side whitelist validation.** Reject or normalise any font, weight or size that is not in the registry for that language and role. Never inject raw user strings into CSS.
6. **Arabic text never gets `letter-spacing`** (it breaks cursive joining) and never gets `text-transform`.
7. **Backward compatible.** A missing key means "Template default".
8. **Word downloads embed their fonts.** Every .docx the user downloads must embed the TTF files for all faces it uses, so it looks right on computers without those fonts (see §6.3). The chosen fonts use the SIL Open Font License, which allows embedding fonts in documents; the build still checks this for each file (§5).

---

## 2. Data model (flat schema, 9 new optional keys)

```json
{
  "language": "en",
  "font_name": null,
  "font_name_weight": 900,
  "font_name_size": 32,
  "font_heading": "Montserrat",
  "font_heading_weight": 800,
  "font_heading_size": 13,
  "font_body": "Inter",
  "font_body_weight": 400,
  "font_body_size": 10
}
```

- `null` or a missing key means template default, **except `font_name`**:
  - `font_name: null` (or missing) means **"Same as Headings"**, the default. The name uses the Headings font **and the Headings weight**, unless `font_name_weight` is set. With no Headings font, that is the template's own face.
  - `font_name: "template"` (a reserved value that is never a font name) means **"Template default"**. The name keeps the template's face even when Headings has a font.
  - `font_name_weight` is checked against the name's *effective* font. Without one it resets (`needs_font`), like every weight without a font.
- `font_heading_size` sets the **section titles directly** (§4).
- **Résumés saved before the split** stored the name size in `font_heading_size` (EN 24–44, AR 26–48). The old and new Headings ranges don't overlap, so such a value is recognised by value alone.
  - It moves to `font_name_size`, unless that is already set.
  - `font_heading_size` becomes the section size those résumés used to derive, `clamp(old × 0.42, 11, 18)` (AR `12, 20`), rounded to the nearest point (32 → 13).
  - The server reports this as `migrations` on `/api/render` and `PUT /api/resume`, and the builder applies it silently.
  - The name renders exactly as before. Section titles move by at most 0.5 pt.
- Sizes are in **points (pt)**, because this is a print document. Use `pt` in the CSS and `Pt()` in python-docx so PDF and Word match.
- If the user switches `language`, reset any value that isn't valid in the new language to the default and show a short notice.

---

## 3. Font registry (verified weight data)

The weights below were checked against the Fontsource packages on npm, which mirror Google Fonts (checked 2026-09-25). **Re-verify** them when you download the files: the build script in §5 must assert that every weight listed here really exists in the downloaded files, and fail loudly if one doesn't.

**Weight rule:** Allowed weights = (the role's range) ∩ (the weights the font has).
- Name and Headings range: **700–900**. Details range: **200–400**.
- **Name uses exactly the Headings lists** (§3.1 / §3.3) and the same rule.
- If the intersection is empty, offer the font's **single nearest weight** with a label, e.g. `400 — only weight (heavy by design)`.

### 3.1 English, Headlines (700–900)

| Font | Weights the font has | Offered weights | Category / note |
|---|---|---|---|
| Anton | 400 | **400 only** | Condensed display. Already very heavy |
| Anton SC | 400 | **400 only** | Small-caps display. Already very heavy |
| Archivo | 100–900 | 700, 800, 900 | Grotesque sans |
| Archivo Black | 400 | **400 only** | Black by design |
| Bebas Neue | 400 | **400 only** | Caps-only design (lowercase shows as caps) |
| Montserrat | 100–900 | 700, 800, 900 | Geometric sans |
| Raleway | 100–900 | 700, 800, 900 | Elegant sans |
| Playfair Display | 400–900 | 700, 800, 900 | High-contrast serif |
| Source Serif 4 | 200–900 | 700, 800, 900 | Text serif |
| Work Sans | 100–900 | 700, 800, 900 | Grotesque sans |

### 3.2 English, Details (200–400)

| Font | Weights the font has | Offered weights |
|---|---|---|
| Poppins | 100–900 | 200, 300, 400 |
| Montserrat | 100–900 | 200, 300, 400 |
| Inter | 100–900 | 200, 300, 400 |
| Lora | 400–700 | **400 only** |
| Source Serif 4 | 200–900 | 200, 300, 400 |
| Work Sans | 100–900 | 200, 300, 400 |
| Archivo | 100–900 | 200, 300, 400 |

### 3.3 Arabic, Headlines (700–900)

| Font | Weights the font has | Offered weights | Category |
|---|---|---|---|
| Tajawal | 200, 300, 400, 500, 700, 800, 900 | 700, 800, 900 | Kufi / geometric sans |
| Cairo | 200–900 | 700, 800, 900 | Kufi / geometric sans |
| Almarai | 300, 400, 700, 800 | 700, 800 | Kufi / geometric sans |
| Alexandria | 100–900 | 700, 800, 900 | Kufi / geometric sans |
| Noto Kufi Arabic | 100–900 | 700, 800, 900 | Kufi / geometric sans |
| Mada | 200–900 | 700, 800, 900 | Kufi / geometric sans |
| Readex Pro | 200–700 | **700** | Kufi / geometric sans |
| El Messiri | 400–700 | **700** | Modern / stylised |
| Noto Naskh Arabic | 400–700 | **700** | Naskh (classic text) |
| Markazi Text | 400–700 | **700** | Naskh (classic text) |
| Scheherazade New | 400–700 | **700** | Naskh (classic text) |
| Lateef | 200–800 | 700, 800 | Naskh (classic text) |
| Aref Ruqaa | 400, 700 | **700** | Calligraphic (Ruqaa) |
| Lalezar | 400 | **400 only** | Display (heavy by design) |
| Jomhuria | 400 | **400 only** | Display (very compact; needs large size) |
| Rakkas | 400 | **400 only** | Display (heavy by design) |
| Marhey | 300–700 | **700** | Display / playful |
| Baloo Bhaijaan 2 | 400–800 | 700, 800 | Display / rounded, playful |
| Lemonada | 300–700 | **700** | Display / rounded, playful |

### 3.4 Arabic, Details (200–400)

| Font | Weights the font has | Offered weights |
|---|---|---|
| Markazi Text | 400–700 | **400 only** |
| Noto Naskh Arabic | 400–700 | **400 only** |
| Readex Pro | 200–700 | 200, 300, 400 |
| Amiri | 400, 700 | **400 only** |
| Scheherazade New | 400–700 | **400 only** |
| Noto Kufi Arabic | 100–900 | 200, 300, 400 |
| IBM Plex Sans Arabic | 100–700 | 200, 300, 400 |
| Noto Sans Arabic | 100–900 | 200, 300, 400 |
| Lateef | 200–800 | 200, 300, 400 |
| Mada | 200–900 | 200, 300, 400 |
| Baloo Bhaijaan 2 | 400–800 | **400 only** |
| Tajawal | 200–900 (no 600) | 200, 300, 400 |
| Cairo | 200–900 | 200, 300, 400 |
| Alexandria | 100–900 | 200, 300, 400 |
| El Messiri | 400–700 | **400 only** |

All Arabic fonts above also include Latin glyphs. English words, emails and URLs inside Arabic CVs will render in the same family, so no second fallback font is needed. Still set a generic fallback stack (`…, sans-serif` / `…, serif`).

### 3.5 Dropdown UX

- **Group the font dropdown** with `<optgroup>`s using the categories above (e.g. *Sans*, *Serif*, *Display* for English; *Kufi / Sans*, *Naskh*, *Calligraphic*, *Display / Playful* for Arabic). This matters most for the 19-item Arabic headline list.
- **Render each option in its own font** (a short sample: `Jameel Ahmad` / `جميل أحمد`) where the browser allows it. Otherwise show a live preview line next to the dropdown.
- **When the font changes, rebuild the weight dropdown** from the registry and keep the nearest valid weight. For example, switching from Montserrat 900 to Almarai gives 800.
- If only one weight exists, show the weight dropdown **disabled**, with the one value and its label. Don't hide it, because the layout should stay stable.
- Add a small tag to the playful display fonts (Marhey, Baloo Bhaijaan 2, Lemonada, Jomhuria, Rakkas, Lalezar): *"Creative, best for design/creative roles"*. This is informational only; do not block them.
- **Light-weight warning.** If the Details weight is **200** and the size is under **10 pt (EN)** or **11 pt (AR)**, show a non-blocking hint: *"Very light text may look faint when printed."*
- Every change updates the live preview immediately (CSS variables, no page reload).

---

## 4. Size ranges (pt)

The values below are starting design recommendations. They are not measured industry standards, so tune them after the calibration page in §7.

| Language / Group | Dropdown values | Step | Default |
|---|---|---|---|
| EN Name | 24 → 44 pt | 2 | 32 |
| EN Headings (section titles) | 11 → 18 pt | 1 | 13 |
| EN Details | 9 → 12 pt | 0.5 | 10 |
| AR Name | 26 → 48 pt | 2 | 34 |
| AR Headings (section titles) | 12 → 20 pt | 1 | 14 |
| AR Details | 10 → 14 pt | 0.5 | 11.5 |

**Each group sets its own size (as built):**

- **Name:** the name, at the chosen size. If a name is wider than its box, autofit shrinks it to fit, never below 70% of that size and never by wrapping (step 3b).
- **Headings:** every section title, at the chosen size. The earlier `clamp(name × 0.42)` derivation was removed in step 3c; it survives only in the migration (§2).
- **Details:** *proportional*. The chosen size becomes the template's dominant body size, and every other details element scales by the same ratio, so job titles and dates keep the template's own hierarchy. This replaced the earlier ×1.15 / ×0.9 derived sizes, which the templates have no hooks for (step 3 decision).
- Autofit may still shrink everything by up to 10% to seat one page.

Arabic ranges are about one step larger because Arabic glyphs look smaller at the same point size.

### 4.1 Optical size normalisation (important)

Different fonts look very different at the same pt size. Jomhuria in particular is extremely compact, and Lateef, Amiri and Scheherazade look smaller than Cairo or Tajawal. Add a per-font `optical_scale` in the registry and multiply the user's size by it when rendering, so that "10 pt" looks the same across fonts:

- **Don't guess these numbers.** Write `tools/calibrate_fonts.py`. It uses Playwright to render a reference string per script (EN: `Hxpg`, AR: `محمد`) in each font at 100 px, measures the rendered ink height, and sets `optical_scale = reference_height / font_height`. Use Inter as the reference for EN and Cairo for AR. Clamp the result to 0.85–1.8 and write it into the registry.
- Also store a per-font `line_height`. Naskh-style fonts (Amiri, Scheherazade New, Lateef, Noto Naskh, Markazi) need more than Kufi/sans fonts. Measure it from the font's `hhea`/`OS/2` ascender and descender and the rendered result, not from guesses.
- The pt value the user picked is what is stored and shown. The scale only affects rendering.

---

## 5. Font files: acquisition and build

Create `tools/build_fonts.py`, a one-time or occasional script whose output is committed:

1. Download each family's TTFs from the official **google/fonts** GitHub repository (`ofl/<familyname>/`), along with its `OFL.txt`. Discover the paths with the GitHub API; don't hard-code them.
2. **Licence check (the OFL Reserved Font Name clause).** Read each `OFL.txt`. If it declares a **"Reserved Font Name"**, the OFL treats a modified font (instanced or subset) as a *Modified Version*, which may not keep that name. For those families, **don't modify the file**. Use the family's **official, unmodified static TTFs** (from the upstream project's release or Google Fonts' own family download). If no official static file exists for a needed weight, stop and list the family in the build report for a human decision; don't ship a renamed or unclear file. Print a table of all families with their RFN status.
3. **Variable fonts** (`[wght]`) without a Reserved Font Name: use `fontTools.varLib.instancer` to create **static instances for only the offered weights** (§3). Give every static instance proper name-table entries:
   - nameID 1 = `"<Family> <WeightName>"` (e.g. `Montserrat ExtraBold`), nameID 2 = `Regular`
   - nameID 16 = `<Family>`, nameID 17 = `<WeightName>`
   - nameID 4 (full name) and nameID 6 (PostScript name) must be **unique per instance**, e.g. `Montserrat ExtraBold` / `Montserrat-ExtraBold`.
   - For the 400 and 700 instances, use the standard RIBBI naming (`Montserrat` Regular / Bold).
   - **Keep** nameIDs 0 (copyright), 13 (licence) and 14 (licence URL).
4. Subset to the needed scripts (Latin + Latin-Ext; add Arabic for Arabic fonts) with `fontTools.subset`, for families that allow modification. Keep the OpenType layout features (`--layout-features='*'`); **Arabic shaping depends on them**. Also pass `--name-IDs='*'` and `--name-legacy`. The subsetter's default keeps only nameIDs 0–6, which would **delete the licence records**. Subset by **script/Unicode range only, never by the characters a particular CV uses**.
4. Output:
   - `static/fonts/web/<slug>-<weight>.woff2`, used by the preview and PDF
   - `static/fonts/ttf/<slug>-<weight>.ttf`, used for DOCX embedding
   - Copy each family's `OFL.txt` to `static/fonts/licenses/`
5. Assert that every (font, weight) in the registry has both files, and that each file's `OS/2.usWeightClass` matches. Fail the build otherwise.
6. Check `OS/2.fsType` on every file and record it in the registry. It must permit embedding (0 or 8); OFL fonts normally have fsType 0. Fail the build on 2 or 4.
7. Record each TTF's nameID 1 in the registry as `word_family_name`. The DOCX run mapping (§6.2) and the embedding module (§6.3) must read this value, not rebuild the name themselves.

Then generate `static/css/fonts.css` from the registry: one `@font-face` per (family, weight) with `font-display: block`.

---

## 6. Rendering

### 6.1 HTML preview and PDF (Playwright)

- Templates use CSS variables only:
  `--font-heading`, `--font-heading-weight`, `--font-heading-size`, `--font-body`, `--font-body-weight`, `--font-body-size`, plus the derived sizes from §4.
- Flask builds these variables from validated values. It sets them on the CV root and applies `optical_scale` and `line_height`.
- In the PDF pipeline: load the page → `await page.evaluate("document.fonts.ready")` → explicitly `document.fonts.load()` each used family/weight → then `page.pdf(...)`. Assert with `document.fonts.check()` that each used face is loaded. If one isn't, log an error instead of silently producing a fallback PDF.
- Keep the existing RTL approach (`dir="rtl"` on `<html>`, `flex-direction: row`).

### 6.2 Word (.docx, python-docx)

Word only knows *Regular/Bold* per family name, so weights must be mapped to family names:

| Chosen weight | Word run font name | `bold` |
|---|---|---|
| 400 | `Family` | False |
| 700 | `Family` | True |
| any other (200, 300, 800, 900) | `Family WeightName` (e.g. `Cairo ExtraLight`, `Montserrat Black`) | False |

For **Arabic runs** you must set the complex-script attributes, not just `run.font.name`:

- `w:rFonts` with **`w:ascii`, `w:hAnsi`, `w:cs`, `w:eastAsia`** all set to the mapped name
- `w:bCs` alongside `w:b` when bold; `w:szCs` alongside `w:sz`
- Keep the existing `<w:rtl w:val="1"/>` + `<w:lang w:bidi="ar-SA"/>` per run

### 6.3 Embedding fonts in the Word file (REQUIRED)

**Every Word (.docx) download must embed the font files it uses.** The CV must then look the same on the recipient's computer even if they have never installed Cairo, Montserrat, and so on. This is part of the core feature, not an optional extra. A .docx download that references a registry font without embedding it counts as a bug.

**What to embed**

- Embed exactly the faces the document uses: the chosen heading face (family + weight), the chosen body face, and every derived face (e.g. a 700 subheading). Collect them while building the document, not by guessing afterwards.
- If a template default font is used and is in the registry with a TTF (e.g. Inter), embed it too. If a default font has no bundled TTF (e.g. Cormorant Garamond today), **add it to the build script and registry as a "template-default" font** so it can be embedded as well. Report any default font you could not add.
- Don't embed faces the document doesn't use. That only makes the file bigger.
- Embed the **full script-subset TTF** from `static/fonts/ttf/` (Latin + Arabic where relevant), **not** a subset of only the characters used. The recipient must be able to edit and add text in the same font.

**Refuse to embed a font that doesn't allow it.** Read `OS/2.fsType` for each face:
- `0` (installable) or `8` (editable): embed.
- `2` (restricted) or `4` (preview & print only): don't embed. Log an error and fail the test suite, because none of the chosen fonts should have these values.

**Put it in its own module:** `app/export/docx_font_embed.py`, with `embed_fonts(docx_path_or_bytes, faces) -> bytes`. Call it as a post-processing step after python-docx saves. Work on the ZIP package directly with `zipfile` + `lxml`, and write a fresh ZIP; don't modify the file in place.

**Package changes (ECMA-376 Part 1, §17.8 Fonts):**

1. **`word/settings.xml`**: add `<w:embedTrueTypeFonts/>`. Insert it at the **schema-correct position** inside `<w:settings>`: it comes after `w:view`, `w:zoom`, `w:removePersonalInformation`, `w:removeDateAndTime`, `w:doNotDisplayPageBoundaries`, `w:displayBackgroundShape`, `w:printPostScriptOverText`, `w:printFractionalCharacterWidth` and `w:printFormsData`, and before everything else. Word may call the file corrupt if the order is wrong. **Don't** add `<w:saveSubsetFonts/>`, because the full fonts must stay so the recipient can edit.
2. **Obfuscated font parts** `word/fonts/font1.odttf`, `font2.odttf`, … (one per embedded face):
   - Generate a new GUID per face (`uuid.uuid4()`), formatted in uppercase as `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`.
   - Key: remove the braces and dashes to get 32 hex characters. Split them into 16 byte pairs and **reverse the order** of the pairs: `key[i] = int(hex32[30-2*i : 32-2*i], 16)` for `i` in 0..15.
   - Obfuscate: for `i` in 0..31, `data[i] ^= key[i % 16]`. All other bytes stay unchanged.
3. **`word/fontTable.xml`** (create it if python-docx didn't): add one `<w:font w:name="…">` per Word family name from §6.2, containing:
   - `<w:embedRegular r:id="rIdN" w:fontKey="{GUID}"/>` for the regular face
   - `<w:embedBold r:id="rIdM" w:fontKey="{GUID}"/>` for the 700 face (RIBBI family, used with `bold=True`)
   - A non-RIBBI weight such as `Montserrat ExtraBold` is its **own** `<w:font>` entry with `w:embedRegular`.
   - Add a `w:charset`, `w:family` and `w:pitch` element, e.g. `w:charset w:val="00"` for Latin fonts and `w:val="B2"` (Arabic) for Arabic fonts. Also add `w:panose1` and `w:sig` if you can easily derive them from the OS/2 table. They help Word match fonts, but they are not required.
   - The `w:name` must **exactly equal** the font's legacy family name (nameID 1) **and** the names used in the runs' `w:rFonts`. Any mismatch means Word won't use the embedded font.
4. **`word/_rels/fontTable.xml.rels`** (create it if needed): one relationship per font part with
   `Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"` and `Target="fonts/fontN.odttf"`.
5. **`[Content_Types].xml`**: make sure it has
   `<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>`, and that the fontTable override exists if you created that part.

**Font-file requirements for embedding** (these are enforced in §5): the TTF's nameID 1 must be the exact Word family name, nameID 4/6 must be unique per face, and the licence/copyright names (IDs 0, 13, 14) must still be present.

**File size.** Embedding makes the file larger, and Arabic fonts are the biggest. Measure the added size per face during the build, store it in the registry, and log the final .docx size. Don't reduce size by trimming characters, since that breaks editing.

---

## 7. Tests and acceptance criteria

1. **Registry tests:** every (language, role, font) has ≥1 offered weight; the offered weights are a subset of the available weights; the size defaults are within range.
2. **Validation tests:** invalid font, weight or size → normalised to the default (or a 400 error for the API); a cross-language font (e.g. `Amiri` on an `en` CV) is rejected.
3. **Build test:** every registry face has woff2 and TTF files with a matching `usWeightClass`.
4. **Calibration page** (`/dev/typography`, debug only): renders every font × every offered weight × the default size in EN and AR sample text. Screenshot it via Playwright into `tests/artifacts/`.
5. **PDF test:** for 3 sample combinations per language, generate a PDF and use `pdffonts` (poppler) or `pypdf` font listing to assert that the **exact** font face names are embedded. No fallback font may be embedded.
6. **DOCX test:** parse `document.xml` and assert that the `w:rFonts` / `w:cs` / `w:bCs` values match the mapping table.
7. **DOCX embedding tests** (automated, one EN and one AR sample, plus one using a non-RIBBI weight such as 800):
   - `settings.xml` contains `w:embedTrueTypeFonts` at a schema-valid position.
   - Every face the document uses appears in `fontTable.xml`, with a matching relationship, an existing `.odttf` part and the `odttf` content type. There are no extra faces.
   - **Round-trip:** de-obfuscating each `.odttf` with its `w:fontKey` gives back **the exact bytes** of the source TTF. This proves the key derivation.
   - Each embedded font's nameID 1 equals its `<w:font w:name>` and the run `w:rFonts` names.
   - Opening the file with `python-docx` still works (the package is not corrupt).
8. **DOCX embedding manual check (required before this is called done):** on a **Windows PC where the chosen fonts are NOT installed** (uninstall them, or use a clean VM or another PC), open the downloaded .docx in Microsoft Word. There must be no repair prompt. The fonts must display correctly. File → Options → Save must show "Embed fonts in the file" as on. Editing and typing new text must keep the font. **Testing on the developer's own PC, where the fonts may be installed, proves nothing.** Record the Word version you tested.
9. **Regression:** existing CVs with no typography keys render pixel-identical (or visually identical) to before, for templates A, B and C.
10. **Manual check:** the switch from Montserrat 900 to Almarai keeps 800; Anton shows a disabled `400 — only weight`; changing language resets invalid choices with a notice.

---

## 8. Implementation order

1. Registry + validation + tests (§2, §3, §7.1–7.2)
2. `build_fonts.py` (including the Reserved Font Name report, fsType, `word_family_name`) + generated `fonts.css` + build test
3. Wizard UI (the 6 dropdowns, on the existing design/template step) + live preview via CSS variables
4. PDF pipeline changes + PDF font test
5. DOCX mapping (names, cs attributes) + DOCX test
6. **DOCX font embedding** (§6.3) + embedding tests (§7.7) + manual check on a PC without the fonts (§7.8)
7. Calibration script → fill in `optical_scale` / `line_height` → review the calibration page

Commit after each step. Report what was verified at each step and what wasn't.

---

## 9. Deployment (GitHub → Railway)

`DEPLOY.md` is the full runbook. These are the rules for this feature.

1. **Branch.** All work happens on `feature/typography-controls`. Never commit this feature directly to `main`.
2. **Ask before every push or merge.** Claude Code does not push, merge or deploy without an explicit go-ahead for that specific action. Approving one push does not approve the next.
3. **Merge gate.** Merge into `main` only when every §7 test passes, the §7.9 regression shows existing CVs unchanged, and the §7.8 manual Word check has been done and its Word version recorded. A step marked "not verified" blocks the merge.
4. **Audit before pushing.** Run `git ls-files` and confirm nothing from `.env`, `*.db`, `venv/`, `data/resume.json` or a hardcoded key is tracked. Font files under the font build output are expected; check their licences against the §5 Reserved Font Name report first.
5. **Push form.** Always use the non-interactive form, never a bare `git push`:
   `GIT_TERMINAL_PROMPT=0 git -c credential.interactive=never -c core.askPass= push origin <branch>`
   Confirm it landed with `git ls-remote origin refs/heads/<branch>`. The local `origin/*` ref can be stale.
6. **A push does not deploy.** Railway has no GitHub auto-deploy on this repo. The deploy path is `venv/Scripts/python tools/verify_deploy_target.py && railway up --detach`, run from an up-to-date `main` (`git status -sb` shows no "ahead"). Never run `railway up` without the guard.
7. **Fonts must ship in the image.** Before deploying, run `tools/verify_docker_context.py` and confirm `.dockerignore` does not exclude the font files. A missing font does not fail the build; Chromium silently falls back and the §7.5 guarantee breaks in production only.
8. **Verify after deploying.** Run `tools/smoke_deploy.py` against the Railway address, then export one EN and one AR PDF with a non-default font and confirm the embedded font names as in §7.5.
9. **Do not touch production settings** (env vars, the `/data` volume, DNS) as part of this feature.
