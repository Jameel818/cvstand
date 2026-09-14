# Golden baselines

Two independent regression gates, built before the bilingual (AR/RTL) work so
that "English does not change" is something the suite **proves** rather than
something we assert.

| | `html/` | `pixels/` |
|---|---|---|
| What it captures | the exact canvas fragment a template emits | the rendered 850×1100 canvas |
| Checked by | `tests/test_golden_html.py` | `tests/test_golden_pixels.py` |
| Speed | ~1.6s, runs in the default loop | ~46s, opt-in via `--e2e` |
| Scenarios | `sample`, `sparse` (all sections empty), `gpa`, `partial` | `sample` |
| Regenerate | `python tools/golden.py --html` | `python tools/golden.py --pixels` |

## Why two

They break at different moments, and that difference is the point.

- Extracting a hardcoded `EXPERIENCE` into `t('experience')` **must** leave the
  HTML byte-identical. The HTML gate is the proof the label catalogue changed
  nothing for English.
- Converting `padding-left` → `padding-inline-start` **does** change the HTML,
  so the HTML gate is expected to move. But in an LTR document those are the
  same declaration, so the pixels **must not** move. The pixel gate is the
  proof the layout conversion was mechanical.

A change that needs *both* baselines regenerated has changed English output.
That is the thing we said we would not do — explain it, don't refresh it.

## Scenarios, and a blind spot they closed

The scenario list lives ONCE, in `tools/golden.py`; `tests/test_golden_html.py`
imports it. It used to be declared in both, which meant a scenario added to the
generator would never have been asserted.

`gpa` and `partial` were added during phase 3 (the label catalogue), because
byte-identity only proves what a baseline actually draws:

- **`gpa`** — neither `sample` nor `sparse` sets `education[].gpa`, so the
  `GPA <value>` prefix that 32 templates carry rendered in *neither*. The gate
  was byte-identical across a line it never drew.
- **`partial`** — three ATS templates compose a trailing heading from whichever
  optional sections exist ("Certifications, Tools & Languages"). `sample` has
  all three and `sparse` has none, so the separator and the conjunction — the
  parts that are language-dependent — never appeared in a baseline either. Two
  items is the case that draws exactly one conjunction.

Neither is in the pixel gate: it is `sample`-only and ~46s, and these branches
are about text that appears, not about layout.

## Tolerance

The pixel gate allows up to 50 pixels differing by more than 8/255 per channel.
Glyph rasterisation is not bit-deterministic between runs; a real layout shift
moves whole edges, not one channel by a hair. The injected-regression check
during Phase 0 (a 4px padding change in `modern-t2`) produced **40,043**
differing pixels, so the signal sits about three orders of magnitude clear of
the noise floor.

## On failure

The pixel gate writes `<key>-golden.png`, `<key>-actual.png` and an amplified
`<key>-diff.png` to `tests/e2e/artifacts/`. Look at them before regenerating.
