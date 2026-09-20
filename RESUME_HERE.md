# RESUME HERE — paused 2026-09-20 (FONT POLICY APPLIED · DEPLOYED · nothing blocked)

## ⏸ EXACTLY WHERE THIS STOPPED

Working tree clean, 3 commits pushed, `66e86b5` deployed and LIVE, smoke test
25/25, full suite 2501 passed / 24 skipped / 0 failed.

**The live URL is `https://cvstand-production.up.railway.app`.** Write that
down — it was in no file in this repo before today.

### The one thing still open

**`cvstand.com` is a Hostinger PARKED DOMAIN and has never served this app.**
Confirmed twice: fetching its `/static/css/app.css` returns Hostinger's parked
page as HTML, and Railway reports `customDomains: []`. DEPLOY.md §D is the
procedure and §D0 now records that it has not been done. Until it is, every
deploy is invisible at that address — which reads exactly like a broken deploy
and is not one. **This is what "nothing changed when I previewed" was.**

---

## ✅ THE FONT POLICY, PAST THE HEADLINES

It was reaching about six selectors and the outlined hero. It now reaches
every shell surface and the CV documents themselves — **in Arabic only**.

### The headlines were 20% small, by construction

Each outlined run's viewBox is the face's ascent+descent, 1.25x the em for
Thmanyah Serif Display, and `app.css` set `height: 1em`. Measured: the landing
h1 asked for 57.6px and painted a **46.1px** em; the gallery asked 41.6 and
painted 33.3. Both exactly 0.80. Now `--outline-box` is written per run and
the em equals the font-size — verified on production at 1.000.

**No optical correction on top, and that is measured.** Thmanyah's Arabic
x-height (medial heh) is 0.695em against Cairo 0.770 and Tajawal 0.560, and
against Inter's 0.730 CAP height. A display headline reads by its caps, so the
Arabic h1 wanted the clamp() it already had. It was wrong by 0.80, not by scale.

**Runs are one per WORD.** A phrase is one box with a fixed aspect ratio and
cannot break; the ATS gallery heading was a single 1374-unit run that would
have overflowed a phone the moment the size was corrected.

### The shell: six role gaps, found by auditing computed style

`h4`, `.eyebrow`, `.stat-strip b`, `.num`, `.faq summary` inherited body copy
where the policy asks for Cairo. `.tab` sat on body copy beside CTA buttons.
`.btn` shipped at 700 where the policy says ExtraBold. Added `--font-nav`.

And a real bug: `[dir=rtl] button` set the CTA family on every DESCENDANT, so
the same `.chip-modern` rendered in Tajawal inside a button and in Plex on a
card. **A component's face must not depend on what contains it.**

### The CV documents: roles, in all 49

Name Tajawal ExtraBold, body IBM Plex Sans Arabic, section titles split
**27 Tajawal / 22 Cairo** — the policy assigns section titles twice and
contradicts itself, and the answer to that was "50% Cairo, 50% Tajawal". The
split follows each template's own Latin register (grotesque → Tajawal,
geometric/serif/humanist → Cairo), because two templates that look alike in
English must not diverge in Arabic for no reason.

**The alias layer could not do this.** `fonts_ar.css` keys on (family, weight),
so it can say "Archivo becomes Tajawal" but never "the name becomes Tajawal".
Weight is not a proxy for role either: Archivo 900 is used at 25px AND at 12px,
Open Sans 700 is 12px in 42 of its uses. Hence markup hooks + an RTL-only sheet.

### ENGLISH DID NOT MOVE — and that is the load-bearing claim

- **0 of 3722** English elements changed computed font, across 6 pages.
- **50/50 pixel goldens pass unchanged.**
- The HTML goldens moved and **only** by the class attributes: strip
  `cv-name`/`cv-section`/`cv-sections-taj` back out and they are byte-identical.
- Arabic overflow stays **49/49 clean** after the face swap.

---

## Two near-misses worth keeping

1. **`cv-section` was very nearly called `sec-head`.** That class already
   exists on four templates, and `RTL_TYPOGRAPHY` forces it to
   `font-size: 14px !important` to rescue headings that read as body text.
   Mass-applying the name would have crushed every Arabic section heading in
   all 49, including 24px mastheads, **and no gate would have caught it.**
   Found by reading the stylesheet the class already lived in.

2. **`modern/t10` declares `'DM Sans'`**, vendored nowhere — so it renders in
   a system fallback in Latin and the OS default in Arabic, the one template of
   49 the Arabic work never reached, **and the pixel golden was captured WITH
   the fallback, so the baseline agreed with the bug.** Changed to Inter, then
   changed BACK: fixing it moves that template's English pixels, and the
   standing instruction is that the Arabic policy must not alter English CV
   templates. No Arabic-only fix exists — the alias generator only emits rules
   for families present in `fonts.css`. Named exemption in
   `tests/test_template_fonts.py`, with a staleness guard.

## Instrument errors — three, and none of them reported a number

A new measurement is wrong until it has been pointed at something whose answer
is already known. All three were caught by their own self-tests:

1. **fontTools vs canvas** — fed Cairo-900 and Kufi-900 against 400-weight
   files for the others, then called the difference "optical size". Self-test
   missed the recorded values by -18.3 and +17.2.
2. **Raster + background reference** — probes bled glyph overflow into each
   other's boxes, and `px[0,0]` is meaningless on the gradient hero.
3. **The wrapping probe** — `سيرتك الذاتية` contains a space and wrapped to two
   lines at 200px, while `Handgloves` is one unbreakable word and never did.
   So Latin linearity read a perfect 2.000 while Arabic read 6.349.

The instrument that worked photographs the element twice, once with the text
hidden, and diffs. Gradients, neighbours and antialiasing all cancel.

**And the same brittleness four times in the test suite:** `test_smoke`,
`test_autofit`, `e2e/test_journey` and `test_rtl_typography` each matched an
exact class ATTRIBUTE string. Adding a second class to the same element made
them report a missing canvas, and zero marked headings on a template with
eight. They match the class token now.

## Verification at the pause

    fast suite                     1939 passed, 584 skipped
    full suite (--e2e)             2501 passed, 24 skipped, 0 failed
    pixel goldens                  50/50 unchanged (English did not move)
    verify_overflow en / ar        49/49 clean both
    smoke_deploy (LIVE)            all 25 checks passed
    live em/size, ar / and /templates   1.000 and 1.000 (was 0.800)
