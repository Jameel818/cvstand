# RESUME HERE — paused 2026-09-22 (ARABIC BUILDER SEED FIXED · SHIPPED & VERIFIED LIVE · nothing blocked)

## ⏸ EXACTLY WHERE THIS STOPPED

**Reported from production:** choosing العربية and then opening `/builder`
gave an Arabic *interface* around an *English* CV. Confirmed on the live site
before touching anything — `curl -b "ui_lang=ar" .../builder` returned
`<html lang="ar" dir="rtl">` wrapped around a seed of `"name": "Wren
Ashworth"`.

**Cause, and it was not the language code.** Seeding by interface language was
already wired (`load_resume(seed_lang)`, `data/sample_resume_ar.json`). It
also WROTE the seed to `data/resume.json` — one file for the whole server,
which nothing rewrites at `CVSTAND_SERVER_STORE=0`. So the language of the
first request to reach the container became everyone's, permanently.

**Fixed** in `app/store.py`: with the store off, `load_resume()` neither reads
nor writes that path — it is `seed_resume(lang)` and nothing else. Not reading
it is the half that makes the fix arrive on its own: `/data` is a PERSISTENT
volume, so the stale file outlives every deploy, and a version that only
stopped writing would have shipped green and changed nothing on the live site.

`data/sample_resume_ar.json` also came up to parity with the English sample
(3 posts, 2 degrees, 6 tools — it was 2/1/4, so the Arabic default rendered
visibly sparser). **The three added Arabic strings are awaiting the user's
wording review** — دار الرواق للنشر / مصممة أولى, ماجستير الاتصال البصري, and
نوشن + كي نوت.

**Gates:** `tests/test_builder_seed_language.py` (13) and
`tests/e2e/test_seed_language_journey.py` (3). Both mutation-tested: restore
either the write or the read and the two-visitor tests fail. One visitor
passes either way, which is how this shipped.

**Then the claim was widened to the whole site**, because selecting a language
reaching every surface was true and asserted nowhere:
`tests/e2e/test_selected_language_everywhere.py` (6) picks العربية ONCE on the
landing page and checks what the app decides on its own — the shells, the
builder's browser-generated form labels, the hero and gallery cards, a
template opened with "Use this", and the drawer minis across a template
switch. `test_every_live_template_opens_in_the_selected_language` makes the
same claim over all 49 at request level. No app change was needed: the seed
fix was the missing piece.

**SHIPPED.** `d125c58` (the fix) and `c947ac1` (the whole-site gates), both
pushed and confirmed with `git ls-remote` — the local ref lies after a push.

**VERIFIED ON THE LIVE SITE** after deploy, both languages in one container:

    [ar] seed lang='ar'  name='ليلى خليل'     preview <html lang="ar" dir="rtl">
    [en] seed lang=None  name='Wren Ashworth' preview <html lang="en" dir="ltr">

Full suite **2526 passed / 24 skipped / 0 failed** (`--e2e`, 12m44s).

### Still open

- **A visitor who has selected NOTHING gets English**, even with an Arabic
  browser: `app/i18n.py::current_lang` reads the cookie and nothing else, so
  `Accept-Language: ar` is ignored. Measured on production. This is what an
  incognito window shows, and it reads exactly like the bug that was fixed —
  it is not one. A plan exists (cookie → `best_match` → English, plus
  `Vary: Accept-Language, Cookie`); the user has not asked for it.
- **The three added Arabic strings still await a wording review** (see above).
  They are live.
- **`/builder` has no language switcher at all** — it blanks the site header
  (`{% block chrome %}{% endblock %}`). The language is chosen on the landing
  or gallery page and carried in by the cookie. That is the reported journey
  and it now works, but a visitor already sitting on the builder cannot switch
  from there. Not changed: it is new UI, not a bug fix.
- **`cvstand.com` is still a Hostinger PARKED DOMAIN** and has never served
  this app (see below) — unchanged from 2026-09-20.

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

## ✅ TWO DEAD UI BUGS, both only on a DEPLOYMENT

Found because the user previewed the real site. Neither could reproduce
locally, and that is the whole lesson: **`CVSTAND_SERVER_STORE=0` is a
different application**, and the default test fixture runs with it ON.

### 1. The gallery's "Use this" button did nothing, on every deployment

`POST /api/template` answers **403** when the server holds nothing, and the
gallery's script navigated only on `res.ok` — its entire failure path was
`else { b.disabled = false; }`. So all 49 buttons re-enabled themselves and
stayed put, silently.

`builder.js` already had the right order: write `localStorage` FIRST, mirror
to the server only `if (S.serverStore)`. The gallery did the opposite. It now
stores under `cvstand:template`, the key `builder.js` already reads on boot —
**the POST never carried the choice on a deployment; the localStorage write
is what does.**

**Why no test caught it:** `test_the_deployed_server_refuses_to_hold_a_resume`
asserts the server correctly says no. Nothing asserted the USER CAN STILL
PROCEED after it says no. Those are different claims and only one was tested.

### 2. The builder's bar named the wrong template

Found while verifying fix 1 on production: localStorage held `ats-t8` ("Big
Type"), the canvas rendered ats-t8, the exports used ats-t8 — and the bar read
"Editorial Redline", the deployed default. `#tpl-label` is Jinja-rendered from
`load_meta()` and was only ever repainted inside the drawer's switch handler,
never on boot. **The bar was the single surface lying, which is why it
survived: everything else agreed with itself.**

Both are covered against the `deployed_server` fixture and mutation-tested.

---

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

    fast suite                     1941 passed, 586 skipped
    full suite (--e2e)             2504 passed, 24 skipped, 0 failed
    pixel goldens                  50/50 unchanged (English did not move)
    verify_overflow en / ar        49/49 clean both
    smoke_deploy (LIVE)            all 25 checks passed
    live em/size, ar / and /templates   1.000 and 1.000 (was 0.800)
