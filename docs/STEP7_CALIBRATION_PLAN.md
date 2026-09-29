# Typography step 7 — calibration: PLAN ONLY (not approved, no code)

Written 2026-09-30 overnight, per the user's work order (item 8). Spec:
`docs/CVSTAND_FONT_CONTROLS.md` §4.1 (optical size), §7.4 (calibration
page), §8 step 7. The user decided (2026-09-28) that step 7 follows the
merge, and (2026-09-29) that it follows the Word layouts. Nothing here is
built. Every **DECIDE** needs the user's answer.

## 1. What step 7 must deliver (from the spec)

1. `tools/calibrate_fonts.py`: Playwright renders a reference string per
   script (EN `Hxpg`, AR `محمد`) in every offered face at 100 px, measures
   the rendered **ink height**, and writes `optical_scale = reference /
   face` (reference Inter for EN, Cairo for AR), clamped to 0.85–1.8.
2. A per-font `line_height`, from `hhea`/`OS/2` ascender + descender AND the
   rendered result. The Naskh faces (Amiri, Scheherazade New, Lateef, Noto
   Naskh Arabic, Markazi Text) need more than the Kufi/sans faces.
3. The chosen pt is what is stored and shown; the scale only changes the
   rendering.
4. `/dev/typography` (debug only): every font × every offered weight × the
   default size, EN and AR sample text, screenshotted by Playwright into
   `tests/artifacts/` (§7.4).

## 2. What already exists and must be reused

- **`tools/fetch_fonts_ar.py` `SIZE_ADJUST`** (the user's instruction for
  step 7): canvas `actualBoundingBox` over five strings the templates really
  print, at 100 px, for the five Arabic faces of the older alias layer.
  Tajawal 114.2 %, Amiri 91.7 %; faces within 5 % of the mean are left alone
  ("a correction smaller than the measurement's own spread is noise").
  Step 7 turns that measurement into a function
  (`tools/_ink.py::ink_height(page, family, weight, text)`) that both tools
  call. `fetch_fonts_ar.py --check` then proves the refactor moved nothing.
- **The measurement-instrument rule** (memory "measurement instrument
  errors"): point a new instrument at something whose answer is known first.
  Here that is SIZE_ADJUST itself: the new tool must reproduce Tajawal and
  Amiri within ±1 % before any number it prints is trusted.
- **Size plumbing:** `app/typography/render.py::config()` hands sizes to
  `typography.js`, and autofit multiplies a per-role factor. `optical_scale`
  enters as one more multiplier in that config, never in the stored value.

## 3. Proposed design

**Registry.** `optical_scale` and `line_height` per (language, family) go in
`app/typography/build.json` next to the existing measured data (generated,
never hand-edited). `registry.py` exposes them; the whitelist and the UI
never see them.

**Measuring ink.**
- Canvas `measureText().actualBoundingBoxAscent + Descent`, not DOM rects,
  because DOM rects measure the line box, not the ink.
- Each face at its **default offered weight** for the role (Details 400,
  Headings 700).
- Several strings, not one: `Hxpg` alone is dominated by `H` and `p`. The
  spec's string is kept as the headline number, and the other strings the
  templates print give the spread.
- **DECIDE (1):** the clamp. The spec says 0.85–1.8. Jomhuria needs about
  1.7, which is the reason for the upper bound. A face beyond it is listed,
  not silently clamped.

**Line height.** `max(hhea ascender − descender + lineGap, OS/2 winAscent +
winDescent) / unitsPerEm`, checked against the rendered line box. Written as
a CSS `line-height` multiplier for the preview/PDF.

**Where they apply.**
- Preview + PDF: `typography.js` multiplies the chosen size by
  `optical_scale` and sets `line-height` for the chosen face's role.
  Templates keep their own line-height when no font is chosen, so English
  CVs with no typography keys stay pixel-identical: the 50 pixel goldens are
  the proof.
- **Word — DECIDE (2):** today the Word export applies the chosen FONTS but
  never the chosen SIZES (`docx_theme` writes faces and colours only; found
  while writing this plan). Step 7 is the natural place to add both the
  chosen size and the optical scale to the Word role styles (`w:sz` +
  `w:szCs`). It changes Word page flow, so the real-Word check
  (`tools/verify_word_embedding.py`, 98 files) must run again. The
  alternative is to leave Word sizes as they are and record the gap.

**The calibration page** `/dev/typography`: registered only when
`app.debug` (a test asserts 404 otherwise). One row per (font, weight):
the sample name, a heading, and a body paragraph at the default size, EN and
AR, each labelled with its scale. `tests/e2e/test_typography_calibration.py`
screenshots it into `tests/artifacts/` and asserts every face `loaded`.

## 4. Risks

- **Moving what the user already approved.** A scale of 0.9 on a chosen font
  changes the preview the user has been looking at since step 3. Only
  documents WITH a chosen font move. The EN goldens have no typography keys,
  so they cannot catch this either way; a before/after review page (as in
  step 4) is needed.
- **Autofit interplay:** a larger optical scale means more text, so autofit
  compresses more. The open "Arabic autofit first-pass compression"
  follow-up (RESUME_HERE) sits exactly here and should be probed first.
- **Latin-Ext fallback faces** (8 Arabic families stop at Latin-1
  upstream): the scale must apply to the chosen face only, not to the
  fallback that draws "Ł".

## 5. Test plan

1. The instrument check: the new ink function reproduces SIZE_ADJUST (Tajawal,
   Amiri) within ±1 %.
2. `build.json`: every offered (language, family) has `optical_scale` in the
   clamp range and a `line_height` ≥ 1.0. The five Naskh faces have a larger
   `line_height` than Cairo.
3. `--check` mode on the calibration tool (the numbers are current).
4. Preview/PDF: a chosen face renders at `size × scale` (computed style);
   the stored value is unchanged; no-key documents are pixel-identical (50
   goldens).
5. `/dev/typography`: 404 unless debug; the e2e screenshot; every face
   loaded.
6. If DECIDE (2) = yes: Word role styles carry the chosen size × scale in
   `w:sz`/`w:szCs`, and the 98-file real-Word flow check passes.

## 6. Estimate

About 2 sessions: (1) the tool, the instrument check, build.json and the
page; (2) applying the scale in preview/PDF (+ Word if chosen), the
before/after review, the golden and flow checks.
