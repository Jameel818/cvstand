# RESUME HERE — paused 2026-09-20 (AUTO-DEPLOY WORKS · Arabic typography shipped · nothing blocked)

## ⏸ EXACTLY WHERE THIS STOPPED

**Nothing is blocked on the user and nothing is half-done.** Working tree clean,
17 commits pushed, `d2f8fcf` deployed and live, smoke test 25/25.

The whole pipeline now runs from here: commit → push → Railway builds on its
own. No `railway up` needed.

### The one optional item left

**Send `outreach/thmanyah-webfont-licence.md`** to `ask@thmanyah.com`. It buys
Thmanyah as LIVE text sitewide. Everything else about fonts is done; this is an
upgrade, not a gap. A Gmail draft could not be created — the connector lacks
the compose scope.

---

## ✅ AUTO-DEPLOY — fixed, and not where three attempts looked

A push to `main` now builds and deploys by itself. Verified from the API twice.

**The fix was one click on GITHUB, not Railway.** Railway had been correct the
whole time — Settings ▸ Source showed the repo, the branch, and "Auto deploys
when pushed to GitHub", no errors. What was missing was the Railway app's
**repository access** not including `cvstand`:
`github.com/settings/installations` ▸ Railway ▸ Configure ▸ **Only select
repositories** ▸ tick `cvstand` ▸ **Save**.

The connection was one-directional: Railway believed it was wired because that
setting lives in Railway's own database, while GitHub had no permission to
deliver the push event. **A settings pane showing a connection is not evidence
that events flow.** The measurable version: the repo had zero webhooks, and a
real push sat undeployed for minutes while everything "looked fine".

**The app slug is `railway-app`, not `railway`.** Two earlier attempts sent the
user to a 404 and to a page that does not serve this purpose.

### The duplicate project is deleted

`perfect-illumination` (`be278493-…`) is gone. It was NOT `railway up`
scaffolding against a missing link, as first recorded — its deployments were
all "via GitHub" while `cooperative-healing`'s were "via CLI". The GitHub app
had been wired to a NEW project instead of the existing service, so every push
auto-deployed to an unexposed twin with no domain, no volume, no variables.

`railway delete` marks `deletedAt` and **a plain `railway list` still prints
the project afterwards** — read `railway list --json`. Believing the plain
output, the delete was run twice and the second said "Project not found", which
reads like failure and was the opposite.

`tools/verify_deploy_target.py` now refuses to deploy when the CLI points
anywhere but `cooperative-healing`, checked by project **ID** (Railway's
generated names are indistinguishable at a glance). Mutation-tested against the
real duplicate before it was deleted.

---

## ✅ ARABIC TYPOGRAPHY — the user's font policy, applied

Adopted from the user's own written brief. **`FONTS.md` is the policy;
`tests/test_font_policy.py` (9 checks) is what makes it true.**

### The shell had no Arabic webfonts at all

`base.html` linked `fonts.css` (Latin) and nothing else, so the Arabic
INTERFACE fell back to whatever the OS supplied. The five OFL Arabic faces were
already vendored and correct; only the résumé previews ever asked for them.

    ar   hero Tajawal · headings Cairo · body IBM Plex Sans Arabic · CTA Tajawal
    en   Inter throughout, 1.6 leading — untouched

Scoped to `[dir="rtl"]`, which comes from the `ui_lang` cookie, so it is
unreachable on an English page. `fonts_ar_shell.css` is linked only when
`ui_lang == 'ar'`.

### Thmanyah IS on the site — as outlines

The licence forbids serving the font FILE, not using the DESIGN, and the user's
own brief names the route: *"export it as outlined vectors… not as extractable
font"*. `tools/outline_text.py --build-hero` shapes the fixed headlines with
HarfBuzz and writes SVG paths at build time.

**Live: the landing hero and all three gallery headings are Thmanyah Serif
Display, and the browser fetches no Thmanyah file** (measured: 26 font requests,
zero Thmanyah).

Build time, not request time: shaping costs ~200ms per cold page, and doing it
live would put fontTools, uharfbuzz AND the `.otf` inside the production image —
a font file on the server, which is the thing this avoids.

**FIXED text only.** Body copy, template names, blurbs and anything a user types
stay live text on the OFL faces. Outlines cannot be searched, selected,
translated or restyled.

### Two defects found by measuring, not looking

- **Cairo is a VARIABLE font (`wght 200-1000`) and the @font-face pinned it to
  900**, so `font-weight: 700` rendered Black and every heading looked
  oversized. Found because Google returns the IDENTICAL URL for weights 700 and
  800 — one file for the range. Fixed with `font-weight: 200 1000`.
  **`VARIABLE_RANGE` in `fetch_fonts_ar.py` records which families this applies
  to; Tajawal has no fvar table and is correctly per-weight. Check, do not
  assume, in either direction.**
- **`line-height: 1.9` was on `body`.** It is a body-copy value and the policy
  says so; on `body` it reached chips, buttons and card titles. The gallery's
  "أنظمة التوظيف" chip wrapped onto two lines. Now scoped to prose only.

### Also fixed: form controls were Arial, in BOTH languages

Browsers do not inherit `font-family` into `input`, `select`, `textarea` or
`button`. `.field input` had `font: inherit` so the builder was fine and the
account pages were not. One base rule; it corrects English too.

### The five faces now agree on optical size

Measured with canvas actualBoundingBox over five strings at font-size:100 —
Tajawal was 12% small and Amiri 9% large against the mean, so the same Arabic
résumé rendered at three different sizes depending on the template. `size-adjust`
corrects it with no template change.

**A claim made by eye was wrong twice:** Amiri "renders smaller" — it renders
9% LARGER; it is narrower with a lighter stroke.

---

## ✅ Earlier the same session

- **Gallery + builder in Arabic** — 104 catalogue rows, 49 names, 49 blurbs.
  Measured live: **49 cards, 0 Latin**.
- **Arabic sample names** — `ورين آشورث` IS "Wren Ashworth" in Arabic letters.
  Now `ليلى خليل` at `ديوان للتصميم · دبي`. Lengths held close (10→9, 20→19)
  so the RTL geometry suites over 49 templates passed untouched.
- **modern-t2's 270px void** — `justify-content:space-between` on a fixed
  column. 1 of 49. Gated by `tools/verify_voids.py` + `test_void_gate.py`.
- **Skill bars: words vs numbers was DATA** — the Arabic sample carried
  `percent` and the English one never did. 17 of 49 templates moved, exactly
  the bars and rings patterns.
- **The volume proof PASSES** — account created on live, `railway redeploy`,
  container cycled, signed back in: HTTP 302. `/data` genuinely persists.
- **Mobile: 18/18 clean** on live, 3 widths × 2 languages.

---

## Instrument errors — seven this session, and the pattern is the lesson

A new geometric or textual check is wrong until it has been pointed at
something whose answer is already known.

1. **Four servers on port 5000**, two started with system Python. Everything
   verified locally was true and said nothing about what the user saw.
2. **A screenshot "proving" the Arabic sample** rendered a fully ENGLISH page.
   `?lang=ar` is ignored — the interface language is the `ui_lang` COOKIE.
3. **The void detector's self-test failed against a working instrument.** The
   planted `height:600px` child was squashed to 44px because `.tpl` is itself a
   flex container. Without it, "0 of 49" would have been reported on a check
   that could see nothing.
4. **`size-adjust` went to the wrong fonts.** Splitting CSS on `@font-face {`
   left each rule holding the NEXT rule's comment, so Noto Kufi got Tajawal's
   correction — a wrong number in exactly the right shape.
5. **Two mutation tests of "English is untouched" PASSED against a broken
   stylesheet.** Both mutations were inert: the role variables are unread in
   English, and a `:root` declaration inserted above the original loses to it.
6. **The Thmanyah gate fired on the COMMENT explaining why Thmanyah is banned.**
   A check whose only failure is the note saying "we do not do this" teaches
   people to delete the note.
7. **The mobile check reported 6 failures, all false.** It excluded
   `position:fixed` elements but not their CHILDREN, so the closed drawer
   (`fixed`, `aria-hidden`, `translateX(379px)`) reported all its contents as
   overflow while `scrollWidth == viewport` throughout.

**And the flake fix that made things worse:** `test_shell_rtl_geometry` waited
`wait_for_timeout(3000)` for lazy iframes. Replacing it with a condition was
right, but the first version checked `contentDocument` on `#preview-stage`,
which is a DIV wrapping an iframe — an occasional flake became three consistent
failures. Caught only by running the combination THREE times; one green run
would have hidden it and one red would have looked like the original flake.
The suite is now 40% faster (~110s → ~63s).

---

## Untracked on purpose

- **`Fonts/`** — 27 MB. Holds the Thmanyah `.otf` files needed to regenerate
  the outlines (`--build-hero`), and `Nice fonts/`, which is fourteen
  commercial retail faces with **zero licence files**. **Not committed, and it
  must stay that way**: Thmanyah's licence forbids "redistribute, share,
  upload, host", and pushing to a git remote is uploading. A fresh clone
  therefore cannot rebuild the outlines without this folder — copy it by hand.
- `Arabic Fictitious names.txt`, `My recommedation.txt` — the user's inputs,
  now committed as `references/` so the policy's provenance is in the repo.

## Verification at the pause

    fast suite                     1775 passed, 583 skipped
    browser gates (roles/rtl/mobile)  55 passed ×3
    pixel + void gates                100 passed
    verify_overflow en / ar           49/49 clean both
    smoke_deploy (LIVE)               all 25 checks passed
    live                              d2f8fcf, auto-deployed from a push

---

# RESUME HERE — paused 2026-09-18 (LIVE AND CONFIGURED · 8 commits deployed · Arabic gallery shipped)

## ⏸ EXACTLY WHERE THIS STOPPED

**The deploy is no longer the dangerous thing here.** The five variables are
set, the volume is confirmed, the service passes 25/25, and every visitor now
owns their own résumé. Eight commits shipped and are live.

**Two capabilities were unblocked permanently and are worth knowing about
before anything else:**

- **`gh` is authenticated as `Jameel818`.** `git push` runs from inside Claude
  Code now. The claim in every previous entry that a push "can never run from
  here" is obsolete — it was the git credential manager hanging, and
  `gh auth login` displaces it. If a push ever hangs again, check
  `git config --get-all credential.helper` first.
- **The Railway CLI is installed and logged in** (`railway 5.57.9`, linked to
  `cooperative-healing` / `production` / `cvstand`). `railway up` deploys the
  working tree in ~135s.

### ✅ AUTO-DEPLOY WORKS — resolved 2026-09-19

A push to `main` now builds and deploys `cooperative-healing` on its own.
Verified from the API, not the dashboard: active deployment `8c7d2b4`,
`SUCCESS`, matching `origin/main` exactly, and 25/25 afterwards.

**The fix was one click and it was not the one three earlier attempts aimed
at.** Railway's side had been correct the whole time — Settings > Source showed
`Jameel818/cvstand`, branch `main`, "Auto deploys when pushed to GitHub". What
was missing was on GITHUB: the Railway app existed but its *repository access*
did not include `cvstand`. `github.com/settings/installations` > Railway >
Configure > **Only select repositories** > tick `cvstand` > **Save**.

So the connection was one-directional: Railway believed it was wired up because
that setting lives in Railway's own database, while GitHub had no permission to
deliver the push event. **A settings pane showing a connection is not evidence
that events flow.** The measurable version: the repo had zero webhooks, and a
real push (`8c7d2b4`) sat undeployed for minutes while everything "looked fine".

Diagnosing this took three wrong turns, all from reading UI state as truth:
`Auto deploy unavailable` in a settings pane, then a repo page saying no apps
were installed, then `perfect-illumination` deploying "via GitHub" anyway. The
thing that settled it each time was an observable fact — deployment history,
webhook count, a push that did or did not build.

### Nothing is blocked on the user any more

### Formerly blocking, now closed

~~**The Railway GitHub App is not installed on the repo**, so pushes do NOT
auto-deploy.~~ Confirmed from GitHub's own page: *"There aren't any GitHub Apps
installed on this repository."* Railway therefore shows `Auto deploy
unavailable` and `Could not load branches` while still displaying the repo
name, because it stores that in its own database.

    https://github.com/apps/railway-app/installations/new
    -> Only select repositories -> tick cvstand -> Install
    -> then Railway > Settings > Source > Retry

**The slug is `railway-app`, not `railway`.** Two earlier attempts sent the
user to `github.com/apps/railway` (404) and to the personal-account
installations page, neither of which exists for this purpose. Resolved via
`gh api apps/railway-app`; verify before quoting a URL.

Installing it is a consent action GitHub only accepts through its own UI —
there is no API, by design. A token with `repo` scope cannot do it. Until then,
`railway up` is the deploy path and nothing is blocked.

---

## ✅ SHIPPED — the user's four stated priorities

### 1. The gallery and builder are Arabic (`8c48bf3`)

`registry.py` held 49 names and 49 blurbs as English tuples that never passed
through `t()`, so an Arabic reader met 49 English cards under an Arabic
heading. 104 new `_UI_AR` rows: 48 names (Editorial Redline is shared by
`modern-t1` and `ats-t4`), 49 blurbs, 4 skill patterns, the category tabs and
the card chip. Measured on the live site: **49 cards, 0 Latin.**

**Six names are TYPEFACE proper nouns** (Fraunces Stack, Mono Tech, Wide Caps,
Accent Bar, Serif Executive, Centred Serif). None is transliterated — that is
the defect item 2 exists to fix. Each is translated by what the face DOES on
the page, which also clears the equal-strings gate.

Three existing rows lost their definite article (`Role`, `Qualification`,
`Language`) because they are composed into the add button, which read "add THE
job". The résumé HEADINGS keep theirs; they live in `_AR` and are untouched.

### 2. The Arabic sample has real Arabic names (`7491ec6`)

`ورين آشورث` IS "Wren Ashworth" in Arabic letters, and so were the employer,
the city and the school. Now `ليلى خليل` at `ديوان للتصميم · دبي`, from the
user's supplied name list where it had one.

**Lengths were held close on purpose** (10→9, 20→19). The RTL geometry suites
run over this sample across all 49 templates and were named as the likeliest
casualties; holding lengths is why all 322 passed untouched.

Emails, the site and `$3.2M` stay LATIN. A real Gulf CV mixes scripts and
`test_bidi_mixed` measured that the mixing needs no isolation (0/49) —
scrubbing every Latin character would delete that test's subject.

### 3. Template distortion: one defect, not a systemic one (`20ba360`, `bdc3c27`)

`modern-t2`'s main column was `justify-content:space-between` on a FIXED
1100px frame, which hands all leftover height to the gaps. Measured: a declared
**22px row-gap rendering as 157px, twice — 270px of void.** It matched the
reference image only because the reference's content filled the page.

**Only 1 of 49 templates did this** — checked before changing anything.

Now gated by `tools/verify_voids.py` + `tests/e2e/test_void_gate.py`. The
vertical axis had two gates and neither could see it: auto-fit fails when
content is too TALL, overflow when it is too WIDE, and **nothing watched for
content too SHORT.**

It measures a DISCREPANCY, not a property — `gap - (row-gap + larger adjoining
margin)`. Grepping for `space-between` finds this one instance and misses
`margin-top:auto`, stray margins, grid `align-content`. It also stays quiet
correctly: t2's SIDEBAR is still `space-between` and is not flagged, because
its content fills the height.

### 3b. Skill bars: the words-vs-numbers divergence was DATA (`a7834c2`)

The reference shows `90%`; the app showed `Expert`. It looked like a template
defect and was not: `sample_resume_ar.json` carried `percent` on every skill
and `sample_resume.json` never did. `_macros.j2:112` already does the right
thing — `label_txt = (_pc ~ '%') if _pc is not none else skill.level` — so the
English showcase fell back to the level word for want of a number.

Blast radius was exactly right: **17 of 49 templates moved, precisely the
`bars` and `rings` patterns.** dot-grid and inline never read `percent`.

The two showcase samples are now structural twins, so LANGUAGE is the only
variable between them. Comparing an English preview against an Arabic one was
previously comparing two different documents.

### 4. Fonts: the five Arabic faces now agree on size (`195c6a2`, `505c855`)

**Thmanyah cannot ship as a webfont, and the licence is explicit.** Read from
their live page, not only the bundled PDF. Commercial use in websites IS
permitted — the user was right about that — but embedding is permitted *"only
as part of a compiled, packaged, or obfuscated product"*, and it is prohibited
to *"make the Font Software available in any manner that allows end users to
extract, download, access... independently as font files, **including through
web embedding**."* A `@font-face` serving a `.woff2` is the named case.

`outreach/thmanyah-webfont-licence.md` is a ready-to-send request to
`ask@thmanyah.com`, which their licence invites in writing. **If the grant
arrives, keep it in `outreach/` and wire the face in — Cairo and thmanyah Sans
measured nearly metric-compatible (232.5 vs 230.4 wide, 94 vs 99 ink), so the
swap will barely move the layout.**

**"Nice fonts" has no licence files at all** — `sakkal-majalla`, `bahij-muna`,
`lyon-arabic-display` are commercial retail faces. Not shipped.

**What DID ship** is the real measured defect. Over five strings at
font-size:100px:

    Cairo                  103.6   100.1% of mean
    IBM Plex Sans Arabic   103.8   100.3%
    Tajawal                 90.6    87.6%   <- 12% smaller
    Amiri                  112.8   109.0%   <-  9% larger
    Noto Kufi Arabic       106.6   103.0%

Archivo layouts printed Arabic visibly small and Fraunces/Merriweather layouts
visibly large, beside the other 45. `size-adjust` corrects it with no template
change and no risk to English (`unicode-range` confines every alias to U+0600
and above; `--check` re-asserts it).

---

## Measured this session — DO NOT RE-DERIVE

- **The live service is correctly configured.** `SERVER_STORE=0`,
  `DATA_DIR=/data`, `TRUSTED_PROXIES=1`, `RENDER_CONCURRENCY=1`, a real
  `SECRET_KEY`. `RAILWAY_VOLUME_MOUNT_PATH` is **`/data`** and matches
  `CVSTAND_DATA_DIR` — the open question from 2026-09-15 is answered.
- **Chromium works in the container**: 147 KB PDF in 1.6s.
- **`tools/verify_voids.py` sweep: 0 of 49.** Reverting t2 makes it 1 of 49 at
  135px excess, so the sweep discriminates.
- **`.gitignore`'s `*.PNG` was swallowing all 49 pixel baselines** — 49 on
  disk, 0 tracked. Git's ignore matching is case-insensitive on Windows. A
  baseline that is not versioned cannot gate anything: a fresh clone has none,
  `golden.py --pixels` writes whatever the code currently renders, and the gate
  passes by having nothing to compare against. **That is the second silent
  pixel gate this repo has shipped.** Fixed with `!tests/golden/pixels/*.png`.
- **`test_no_label_is_still_hardcoded` had never scanned JS.** It walks
  `_template_files()`, which is Jinja only, while the builder's entire form is
  generated by `builder.js` — five English strings sat there for eight
  sessions. New gate: `test_no_label_is_hardcoded_in_the_generated_form`.
- **`_UI_AR` had duplicate keys.** `Modern` twice, `ATS-Friendly` three times,
  the last disagreeing with the other two. A dict literal keeps the LAST
  silently. New gate parses `labels.py` with `ast` — it must read the SOURCE,
  because by import time the duplicate has collapsed.
- **`test_ui_language.py::test_interface_language_does_not_touch_the_document`
  fails when run ALONE and passes in the full suite.** Pre-dates this session
  (confirmed by stashing). The seed fix means an Arabic cookie with no document
  seeds an Arabic résumé, so the level words come back Arabic where the test
  asserts English; in the full suite an earlier test writes a résumé first.
  **This is a genuine disagreement between that test and the seed rule**, still
  unresolved.
- **The builder's template chip never updated its text** — switching Modern for
  ATS swapped the colour and left the word. Fixed.

## Instrument errors this session — the recurring lesson, three more times

1. **Four servers on port 5000, two started with system Python.** `curl` and
   the user's browser could be served by different processes. Everything I
   verified locally was true and told the user nothing about what they saw.
2. **A screenshot "proving" the Arabic sample** rendered a fully ENGLISH page.
   `?lang=ar` is ignored — the interface language is the `ui_lang` COOKIE.
   Caught only because the text probes disagreed with the image.
3. **The void detector's self-test failed against a working instrument.** The
   planted `height:600px` child was squashed to 44px because `.tpl` is itself a
   flex container, so the fixture planted no void at all. Without the
   self-test, "0 of 49" would have been reported on the strength of a check
   that could see nothing.

Also: **a claim made by eye was wrong twice in the same direction.** Amiri
"renders noticeably smaller" — it renders 9% LARGER. It is narrower with a
lighter stroke. Measure before proposing a change, and again before believing
the first measurement (the first attempt reported all six faces at exactly
100px, having measured `getBoundingClientRect` on a span with `line-height:1`).

## Next actions (in order)

1. **Install the Railway GitHub App** (above). **The only item still blocked on
   the user.** Everything else below is now done.
2. **Send `outreach/thmanyah-webfont-licence.md`** to `ask@thmanyah.com`.
   Unblocks the one real remaining font improvement. A Gmail draft could not be
   created from here — the connector lacks the compose scope.

### Closed this session — do not redo

3. ~~The volume proof~~ — **DONE, and it passes.** Created an account on the
   live service, ran `railway redeploy`, watched the container cycle
   (`http=000` mid-flight), signed in again: **HTTP 302, the account survived.**
   `/data` is genuinely persistent. The account
   `volume-proof-53150f4a@example.com` is still there; delete it whenever.
4. ~~Open it on a phone~~ — **18/18 clean** on the LIVE site: `/`, `/templates`
   and `/builder` at 375, 393 and 412px, in both languages, `documentElement
   .scrollWidth` never exceeding the viewport. Not a real device, so iOS Safari
   is still untested, but the 2026-09-14 failure mode is gone.
   **The first run of that check reported 6 failures and every one was false.**
   It excluded `position:fixed` elements but not their CHILDREN, so the closed
   drawer — `fixed`, `aria-hidden="true"`, `translateX(379px)` — reported all of
   its contents as overflow while `scrollWidth == viewport` the whole time.
   Fixed by walking ancestors for `fixed` / `aria-hidden` / `transform` /
   `overflow-x`.
5. ~~The order-dependent `test_ui_language` failure~~ — **FIXED (`c0d326c`).**
   The test was under-specified, not in conflict with the seed rule: its name
   says "an Arabic interface must not relabel an ENGLISH resume" and it never
   wrote one, so it depended on an earlier test leaving a document behind. It
   now writes `samples.ENGLISH` itself. Passes alone, as a single test, and in
   the suite; mutation-tested with `samples.ARABIC`.
6. ~~`data/meta.json` tracked~~ — **untracked (`9e45cb5`).** `load_meta()`
   already guards on its absence. `data/resume.json` was never tracked. The two
   sample résumés stay tracked: they ship INSIDE the image and must survive an
   empty volume.

### The duplicate Railway project — deleted 2026-09-19

`perfect-illumination` (`be278493-a619-4e32-a320-309db2605052`) is deleted.
`railway delete --project <id> --yes` marks it `deletedAt` and a plain
`railway list` STILL PRINTS IT afterwards — read `railway list --json` and
check the field, or you will conclude the delete failed and run it again.

**The dashboard images corrected the theory about how it got there.** It was
not `railway up` scaffolding a project on a missing link. Its deployments were
all **"via GitHub"** and carried this session's commit messages, while
`cooperative-healing`'s were **"via CLI"** (`railway up`) with two GitHub ones
mixed in. So the Railway GitHub App IS installed and working — it was wired to
a NEW project instead of the existing service, and every push after
"Close modern-t2's 270px of void" auto-deployed to an unexposed twin with no
domain, no volume and no variables.

That is why deleting it was right regardless: its only asset was an auto-deploy
pointed at a dead end. But it means the GitHub integration is NOT simply
missing, as the 2026-09-18 entry above concluded from
`Auto deploy unavailable` / `Could not load branches`. Both readings were taken
from real evidence; the dashboard history is the one that settles it.

**Open question, testable in one push:** now that the twin is gone, does a push
deploy to `cooperative-healing`? Its history shows it HAS accepted GitHub
deploys. If yes, auto-deploy is solved and no GitHub App work remains.

### On using Thmanyah for the SITE but not the résumés

Asked 2026-09-18 and the answer is no, for a reason worth writing down: the
licence prohibition is about the FONT FILE being fetchable, not about what text
it renders. A `@font-face` in the app shell publishes the `.woff2` at a public
URL exactly as one in a résumé template does — same file, same download, same
clause. The only compliant route is outlining fixed text to SVG paths, which
ships no font file; but the wordmark is "CVStand" (Latin, so Thmanyah would not
touch it) and baking Arabic UI text into paths would break this project's own
rule that text stays real and selectable. The licence request is the unlock.

## Verification at the pause

    fast suite                    1747 passed, 575 skipped
    RTL typography/mirroring/bidi/journey_ar   238 passed
    pixel + void gates            100 passed
    golden html                   196 regenerated, only intended files differ
    verify_overflow en / ar       49/49 clean both
    verify_autofit                ALL PASS
    smoke_deploy (LIVE)           all 25 checks passed

---

# RESUME HERE — paused 2026-09-16 (SEED FIX SHIPPED · two plans written, NEITHER confirmed)

## ⏸ EXACTLY WHERE THIS STOPPED

One feature shipped and verified. Two plans are written and **waiting on the
user's answer** — no code was written for either. The deploy state is
**unchanged** from 2026-09-15 and is still the most dangerous thing here.

### 🔴 UNCHANGED AND STILL FIRST — the live service is misconfigured

Nothing in this session touched the deployment. Everything in the 2026-09-15
entry below still applies verbatim: the five environment variables, the volume
mount path, the public domain. **`CVSTAND_SERVER_STORE` unset still means every
visitor reads and overwrites one `data/resume.json`.**

**There are now 5 unpushed commits, not 4.** Railway builds what is on GitHub,
so the seed fix below is NOT live until `git push origin main` runs **from the
user's own terminal** (never from inside Claude Code — it hangs on the
credential prompt).

---

## ✅ SHIPPED — the builder's default document language follows the interface

**The problem.** An Arabic visitor switched the interface to Arabic, opened the
builder, and found an ENGLISH résumé. The fix was reachable only through
`Résumé language` in Basics — a control they may never notice, and whose
purpose is not obvious if they do.

**What was rejected, and why it matters.** The user first asked for the résumé
to follow the interface language everywhere. That was declined and the reason
given, because six passing tests assert the opposite
(`test_ui_language.py:123,135`, `test_journey_ar.py:211,254,350`, and all of
`test_showcase_language.py`). The sharp case: an Arabic CV opened by an English
reader must stay Arabic — the user changed the menu, not their CV. The user
agreed and chose the seed fix instead.

**THE RULE, and it is a narrow one:** the reader's language decides what a
**new** résumé starts as, and nothing more. A document that exists owns its own
language. Do not widen this.

- `app/store.py::load_resume(seed_lang="en")` — seeds from
  `SAMPLE_RESUME_PATHS[seed_lang]` on the FIRST read only. Unknown language
  falls back to English (the same degrade rule `load_showcase` uses; the value
  comes from a user-editable cookie).
- `app/routes.py` — **all four** call sites pass `i18n_mod.current_lang()`:
  `/builder`, `/api/resume`, `/preview`, and the export subject. All four, not
  just the builder, because whichever endpoint is hit first creates the file —
  seeding only in the builder leaves the language decided by the entry point.
- Covers the deployed config too: with `SERVER_STORE=0` the browser owns the
  document, but `builder.js` falls back to the server-injected `#resume-data`
  when localStorage is empty.

**Measured on a fresh data dir:** English UI → English sample, no `lang` key
(absent = English, unchanged). Arabic UI → Arabic sample with `lang: "ar"`.

**Session 24 declined this and was right at the time.** Its objection was that
stamping `lang:"ar"` on the ENGLISH sample's text renders worse than absent.
That was about the SAMPLE, not the principle — seeding from the Arabic sample
carries Arabic text and `lang:"ar"` together, so the pair stays consistent.

### Tests

`tests/e2e/test_language_consistency.py` — **9 tests**, plus a `no_document`
fixture in `tests/e2e/conftest.py` (the autouse `clean_state` writes a résumé
before every test, so the seed branch is otherwise unreachable from a browser).

- The interface language survives `/` → `/templates` → `/builder`, by `goto`
  AND by clicking, plus a back-navigation. Existing tests check each page in
  isolation, one request each; none walked a visitor THROUGH the journey, which
  is where a language actually gets lost.
- Showcase cards follow the reader **with the document seeded in the opposite
  language** — that is what makes the test able to fail.
- A new résumé opens in the chosen language, asserted on the PREVIEW iframe's
  `dir`, not the shell's: the shell has followed the cookie all along, so a
  shell assertion passes with the bug still present.
- The seed never overrides an existing document.

**Verification:** fast suite `1745 passed` (baseline unchanged; skips 516 → 525
= exactly the 9 new tests). Full browser suite `501 passed, 1769 deselected`
— read from the summary line, not the exit code. Run alone AND in the full
suite, per this file's order-dependence trap.

**Mutation-tested, 3 mutants, all caught, all reverted:** showcase coupled to
the document (`routes.py`), `dir="ltr"` hardcoded in `base.html`, seed forced
back to English-only (`store.py`).

---

## ⏳ TWO PLANS WRITTEN — BOTH WAITING ON THE USER, NO CODE WRITTEN

### Plan A — Arabic sample content (the user's live question)

**The user asked: "when the user changes the language to Arabic, will all the
English names change to Arabic names — is that applicable without problems?"**

**The answer is yes, and MOST OF IT ALREADY WORKS. Do not rebuild it.**
Switching the interface already swaps the whole showcase document, name
included — measured: `Wren Ashworth` → `ورين آشورث`.

**The real defect is content, in ONE file.** `data/sample_resume_ar.json` is
transliterated English, not Arabic: `ورين آشورث` IS "Wren Ashworth" in Arabic
letters. Likewise `هالدن آند رو` = "Halden & Row", `بورتسايد` = "Portside",
`كلية نورثفيلد` = "Northfield College". 61 of 67 string fields are already
Arabic script; only 6 carry Latin (3 emails, 1 site, `$3.2M`, the `lang` code).

Phases: (1) rewrite the proper nouns — **keep some Latin**, a real Gulf CV
mixes scripts and the bidi suite measured mixing needs no isolation (0/49);
scrubbing all Latin deletes that test's subject. (2) `tests/samples.py`
hardcodes `_ARABIC_COMPANY` / `_ARABIC_CITY` to mirror the sample and
`test_bidi_mixed.py:152-155` pairs `samples.MIXED` against `samples.ARABIC`
field by field — these break in lockstep. (3) add Arabic to
`test_autofit_gate.py`. (4) `test_rtl_typography.py` and
`test_rtl_mirroring.py` both load this sample and run geometry over 49
templates — most likely casualties of a text-length change.

**Estimated ~3-4h**, revised DOWN from 9-13h after measuring.

**The boundary to keep:** this is our DEMO content. The user's own typed name
must never change when they flip the interface. The seed fix already draws
that line.

### Plan B — template names and blurbs are untranslated (separate, not started)

`app/registry.py` holds 49 labels + 49 blurbs as hardcoded English tuples,
never routed through `t()`. Plus `tpl.skill_pattern` rendered raw
(`gallery.html:38`), the category tabs (`:15`), and a bare `'Modern' if ...
else 'ATS'` literal (`gallery.html:34`, `builder.html:12`). **≈106 msgids.**

**OPEN DECISION the user has not answered.** ~6 names are typeface proper nouns
("Fraunces Stack", "Mono Tech", Archivo/Anton). Translating a font name is
wrong, and transliterating it reproduces exactly the Plan A defect. But
`test_arabic_differs_from_english_for_every_msgid` **fails any msgid whose
Arabic equals its English**, so leaving one in Latin collides with a live gate.
Options given: (a) translate all 49; (b) translate descriptive + role names,
keep typeface names Latin with a narrow documented exemption — **recommended**;
(c) rename the ~6 in English first so every name becomes translatable.

---

## Measured this session — DO NOT RE-DERIVE

- **Arabic seats 49/49 with ZERO compression**, identical to English
  (`not fitted = []`, `compressed = 0`, via the real `ResumeAutofit` engine).
  There is genuine headroom for a content rewrite.
- **`test_overflow_gate.py:87` IS parametrized `["en","ar"]`** across all 49.
  The horizontal axis is already gated for Arabic. Only the **vertical**
  auto-fit gate (`test_autofit_gate.py:39`) and the **pixel** baselines
  (`test_golden_pixels.py:46`) are English-only. An earlier claim in this
  session that all four gates were English-only was wrong.
- **A naive height check is not the fit gate.** Setting `.tpl` height to `auto`
  and reading `scrollHeight` reported **16/49 English failures on the shipped
  sample** — content the real gate calls clean. The instrument was wrong, not
  the templates. Run a new geometric check against the SHIPPED sample first;
  this is the second time that rule has paid (see the `Range`-rects note).
- **No entry reordering exists anywhere in the builder** — `entryHTML()`
  (`builder.js:230`) emits only `Remove`; `add` always appends. **And
  `landing.html:85` advertises "Add and reorder entries as you go"**, shipped
  translated into Arabic via `labels.py:356`. We promise it in two languages
  and ship none. Section order is a different, far larger problem: it is
  hardcoded per template AND split across columns (`modern/t1.j2:65`).
- **Five hardcoded English strings in `builder.js`** — `Remove` (`:167`,
  `:231`), `Bullet points` (`:222`), `+ Add bullet` (`:227`), and
  `+ Add ${label.toLowerCase()}` (`:244`). `test_no_label_is_still_hardcoded`
  (`test_labels.py:325`) walks `_template_files()` — **Jinja only, it has never
  scanned JS** — and flags only literals already in the catalogue, which is why
  the bare `'Modern'` literal has always passed too.

---

# RESUME HERE — paused 2026-09-15 (RAILWAY IS PAID · THE IMAGE BUILT · config half-done)

## ⏸ EXACTLY WHERE THIS STOPPED

**The Docker image built successfully on Railway. That was the single biggest
unknown in the project and it is now resolved.** The user paid for Hobby, the
service deployed, and `Deployments` shows "deployment successful".

**But the service is running on DEFAULTS, which is the dangerous configuration.**

### 🔴 THE FIRST THING TO DO — the app is live and misconfigured

As of the pause the five environment variables had **not** been saved. With
`CVSTAND_SERVER_STORE` unset it defaults to `1`, which means the server keeps
ONE résumé at `data/resume.json` and **every visitor reads and overwrites the
same document**. Nothing is broken and nothing logs an error; it is simply one
file where there needs to be one per person.

**Nobody has the URL yet, so no harm has been done. Do not share the link or
sign up until the variables are in.**

Variables tab → **Raw Editor** → paste all five in ONE save:

```
SECRET_KEY=<generate a fresh one, see below>
CVSTAND_SERVER_STORE=0
CVSTAND_DATA_DIR=/data
CVSTAND_TRUSTED_PROXIES=1
CVSTAND_RENDER_CONCURRENCY=1
```

**All five together, not one at a time.** `app/__init__.py` raises
`InsecureDeployment` when `CVSTAND_SERVER_STORE=0` and `SECRET_KEY` is still
the shipped default, so saving the store flag without the key gives a
crash-looping container that reads like a broken deploy but is the guard
working correctly.

A key was generated in the previous session and exists **only in that chat
transcript** — deliberately never written to disk or to git. If it was already
pasted into Railway, Railway holds it and nothing more is needed. Otherwise
generate a fresh one; nothing has been signed with the old one, so there is no
cost to replacing it:

```
venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### State of the three deploy steps

| Step | State |
|---|---|
| **Build** | ✅ **SUCCEEDED** — first time ever, on the unpinned tree at `d1a9337` |
| **Volume at `/data`** | 🟡 **Probably attached** — the service shows a `Backups` tab, which Railway only renders for a service with a volume. **The mount path was never confirmed.** Check Settings; it must read exactly `/data`, not `/app/data` |
| **Variables** | ❌ **NOT SET** — see above |
| **Public domain** | ❓ Never confirmed. Railway does not expose a service by default: Settings → Networking → Public Networking → **Generate Domain**, port **8080** |

### Then, in order

1. Push. **4 commits are sitting unpushed** (see below). Railway builds what is
   on GitHub, so until this happens the running image is the unpinned one.
   `git push origin main` — **from the user's own terminal**, never from inside
   Claude Code, where it hangs on the credential prompt.
2. Smoke-test: `venv/Scripts/python tools/smoke_deploy.py https://<url>`
3. The four things the script cannot judge — live preview, Arabic reading
   correctly, a real phone, and the volume proof (sign up → redeploy → sign in).

---

## What this session added — 4 unpushed commits

All of it is pre-flight work done while waiting on the dashboard. The fast
suite is **1745 passed, 0 failed, 516 skipped**, unchanged throughout.

### `33875a2` — pinned dependencies, corrected two stale runbook claims

`requirements.txt` was all `>=`. The first-ever container build would therefore
also have been the first to use whatever PyPI served that morning — two
unknowns at once, and a failure nobody could attribute. Pinned to exactly what
the suite passes against.

**`gunicorn` most of all: `>=23.0` resolves to `26.2.0` today**, a major jump
past the version the Dockerfile's comments were written against. It is pinned
for reproducibility, **not** confidence — gunicorn is not installed on this
machine (nothing on Windows needs it) and the container is the first place it
has ever run. **If a deploy fails at process start rather than during the image
build, suspect that line first.**

Two things `DEPLOY.md` claimed that were no longer true:

- C4 said the store flag is checked with `!= "0"` so only `0` disables it. That
  was replaced the same day the rename landed — `app/config.py::_flag` accepts
  `0/false/no/off` and raises `AmbiguousFlag` on anything else. The runbook was
  warning the operator about the one input that is now safe. **A misspelled
  variable NAME is the only silent failure left**, because nothing can
  distinguish it from "unset".
- C1 still described a repo with one commit and no remote.

### `ed04fb7` — `tools/smoke_deploy.py`, and C6 stopped recommending a bad check

23 checks against a live URL, stdlib only, ~15s. In `tools/`, which
`.dockerignore` excludes, so it adds nothing to the image.

**The finding worth keeping: never smoke-test the PDF by opening `/export/pdf`
in a browser.** It misleads in both directions:

- Configured **correctly** (`SERVER_STORE=0`) a GET never launches Chromium —
  `_export_subject()` raises `_ExportNeedsPost` and the route answers 405. A
  tidy JSON refusal, no traceback, no information.
- Configured **wrongly** (`=1`) the same GET returns **200 and a real PDF** —
  it looks like a clean pass at the exact moment the deployment is serving one
  shared résumé to everyone.

Only a POST carrying the document in the body reaches `render_pdf`. The script
also asserts the `%PDF` magic **and** a size floor, because a Chromium that
fails to start can still render an error page into a structurally valid,
nearly empty PDF.

**The script was tested before being trusted, and both halves caught something:**

1. Run against a local instance configured like production, it reported 2
   failures that were bugs in **the script** — `urllib` follows redirects, so
   the `/lang/ar` check was reading the final `200` and the landing page's
   headers instead of the `302` and its `Set-Cookie`. Fixed with a
   non-following opener. Now 23/23, including a real 241 KB PDF in 2.9s.
2. Mutation-tested against a second instance with `CVSTAND_SERVER_STORE=1`,
   where the three store checks correctly fail. **A check that cannot fail is
   worthless** — this repo has already shipped a pixel gate that silently never
   ran.

### Verified this session, do not re-derive

- **The volume split is correct by construction.** `SAMPLE_RESUME_PATH` is
  anchored to `ROOT/data`, so the showcase samples ship *inside the image* and
  survive an empty volume, while `RESUME_PATH`, `UPLOADS_DIR` and `DB_PATH` all
  resolve under `CVSTAND_DATA_DIR` → `/data`. `create_app()` mkdirs both at
  boot. **Mounting `/data` will not hide the landing hero.**
- 49/49 templates are ported and render.
- The UI language cookie is `ui_lang`.

## Still open, unchanged

- **DNS at Hostinger — not started.** A/CNAME only. **Never MX or the SPF/DKIM
  TXT records**, or the mailbox breaks silently.
- **The mailbox `info@cvstand.com` does not exist.** The plan is bought; the
  address was never created. Every page footer already links to it.
- No CI (`.github/` does not exist). Chromium-only tests — iOS Safari untested.

---

# RESUME HERE — paused 2026-09-14c (CODE IS ON GITHUB · Railway blocked on a payment decision)

## ⏸ EXACTLY WHERE THIS STOPPED

**The code is pushed to GitHub and the deploy is one decision away.**

- **Repo: https://github.com/Jameel818/cvstand** — 7 commits, `main`, verified
  present on the remote (`Dockerfile`, `railway.json`, `requirements.txt`,
  `.dockerignore`, `run.py` all confirmed in `origin/main`).
- Local `main` is in sync with `origin/main`. Nothing uncommitted.
- **Railway is NOT free.** The user reached the plan wall — Hobby is ~$5/month.
  **They left before choosing.** Nothing is deployed. No Railway project was
  successfully created.

### THE ONE OPEN QUESTION — ask it first

**Pay ~$5/mo for Railway, or switch to Google Cloud Run (free at this
volume)?** The options were laid out and the user had to go. Do not re-derive
them:

| Option | Cost | Note |
|---|---|---|
| **Railway Hobby** | ~$5/mo | Already configured — `railway.json`, volume, vars |
| **Google Cloud Run** | Free at preview volume | Docker-native, ~30-45 min of setup, **no persistent disk** so accounts would not survive a redeploy (fine for a preview — the account features ship dark) |
| **Render free** | Free | **Rejected: 512 MB.** The PDF export launches a real Chromium and needs ~1 GB, so the one feature that matters would OOM |

Recommendation given: pay the $5, because the Docker image has never been
built anywhere and debugging it on the already-configured platform is faster
than debugging it while also configuring a new one.

### The GitHub push was the hard part, and it is DONE

Two hours went into it; do not repeat the dead ends:

- **Git Credential Manager's device-code flow is broken on this machine.** The
  browser shows "This site can't be reached" on the OAuth callback after the
  verification code is entered. GitHub authorises, Git never receives the
  token, nothing is stored.
- **A push CANNOT be run from inside Claude Code.** It needs an interactive
  credential prompt; every attempt hangs and has to be killed with TaskStop.
  `git -c credential.interactive=never push` fails fast and is the safe way to
  TEST whether a credential exists.
- What finally worked: the user ran `git push -u origin main` themselves from
  their own terminal.
- If a future push fails the same way, the reliable path is a Personal Access
  Token (`https://github.com/settings/tokens/new`, scope `repo`) used as
  `git push https://TOKEN@github.com/Jameel818/cvstand.git main`. **Never let
  a token into the repo, a file, or the transcript.**

### When deployment resumes

`DEPLOY.md` is the runbook and every claim in it was checked against the
running app. The checklist page for the user is
https://claude.ai/code/artifact/0f844ccb-0d8f-4b5c-87dc-186ef9c9be45

Three things that cause SILENT damage, in priority order:

1. **Mount the `/data` volume BEFORE the first signup.** Container disks are
   ephemeral; without it every deploy deletes every account.
2. **`CVSTAND_SERVER_STORE=0`** or two visitors overwrite each other's résumé.
3. **DNS later: A/CNAME only, never MX or the SPF/DKIM TXT records** — that
   breaks the mailbox. Not started; nothing has touched cvstand.com.

⚠ **The Docker image has still never been built.** No Docker on this machine.
Expect the first build to fail; the likely order is Chromium install, then
memory, then port binding.

---

# Previous entry — 2026-09-14b (rename SHIPPED · internal namespace SHIPPED · deploy prepped)

**This IS a git repo now.** Two commits on `main`, clean tree, **no remote** —
pushing to GitHub needs the user's account (there is no `gh` CLI here).

| | start of day | now |
|---|---|---|
| fast suite | 1692 passed, 0 errors | **1745 passed, 0 errors** |
| full `--e2e` | 2136 | **2237 passed, 0 errors** (11m48s, junit: 2261 cases) |

## 🔴 A LAUNCH-BLOCKING BUG WAS FOUND AND FIXED — the app did not work on phones

**28 of 32** page x width x language combinations overflowed horizontally below
900px. On a 390px screen the builder's **download button was off the edge of
the screen**. Nothing could have caught it: every browser context in the suite
was 1440x950 or 900x1200, so the narrowest thing ever rendered was a tablet.

Cause: two flex rows that could not shrink, plus `grid-template-columns: 1fr`
being `minmax(auto, 1fr)` — whose `auto` minimum is MIN-CONTENT, so the column
refused to shrink below its widest child. `minmax(0, 1fr)` is the fix.

Gated by `tests/e2e/test_mobile_layout.py` (35 tests, 4 widths x 4 pages x 2
languages). **That gate measures element rects, NOT `scrollWidth`**, and the
reason is written at the top of the file: the fix needs
`html { overflow-x: hidden }`, which collapses `scrollWidth` to the viewport
and would make the obvious test pass vacuously forever. It did exactly that
mid-fix — a scrollWidth probe reported 32/32 clean while the builder was still
140px too wide.

## Known gaps, NOT fixed

| Gap | Note |
|---|---|
| **Chromium only** | No WebKit/Firefox. iOS Safari is a large share of Gulf traffic and is entirely untested |
| **No CI** | `.github/` does not exist; tests run only when someone remembers |
| **Docker image never built** | Still the top deployment unknown |

**Three commits on `main`.** The third added `tests/e2e/test_brand_and_cache.py`
(13 browser tests): the brand VISIBLE rather than merely emitted, the footer
mailto as a real link, and the service-worker cache sweep across the rename —
the last being browser-only logic that nothing could previously reach.

⚠ **Two traps fired for real while writing those tests, both worth knowing:**

1. **pytest exited 0 with a failure present.** The summary line said
   `1 failed, 2201 passed`. This is the project's oldest trap and it has now
   burned four sessions. Read the summary line or the junit; never the exit code.
2. **A new test can be order-dependent and look fine.** The sweep test passed
   alone and failed in the full suite: a service worker's `activate` only fires
   for a worker not already running, and `test_offline.py` registers one
   earlier. `_cold_origin()` unregisters and clears caches first. **Run a new
   e2e test both alone AND in the full suite before believing it.**

## Read these first, in this order

1. **`DEPLOY.md`** — the Railway + Hostinger runbook. Every claim in it was
   checked against the running app, not the docs.
2. **`NAMING.md` §7a** — the seven things the rename plan got wrong once
   measured. §7 is kept verbatim as the record of the plan.
3. `.env.example` — the canonical list of every setting the code reads.

## What happened, in two parts

### Part 1 — the four rename phases (see the previous entry below)
`app/brand.py`, six surfaces, the three brand defects, the label gate widened,
the tagline, `MONETIZATION.md` §8a. Four dead catalogue rows deleted.

### Part 2 — internal namespace + deployment prep

- **`RESUMECRAFT_*` → `CVSTAND_*`** across 16 files, plus `data/cvstand.db`
  and the `cvstand:*` localStorage keys. **The old DO-NOT-TOUCH rule was
  inverted, deliberately** — it protected DEPLOYED users and there were none,
  so the rename was free exactly once and permanently expensive afterwards.
  **That window is now CLOSED**: `app/brand.py` says so, and after launch
  renaming those keys really would wipe documents.
- Three sites keep the old spelling ON PURPOSE (`app/brand.py:11`,
  `tests/test_brand.py:15`, `tests/test_labels.py:73`) — they are statements
  ABOUT the 2026-09-12 grep trap and stop being true if renamed.
- `sw.js` still sweeps the `resumecraft-` cache prefix. A cleanup filter only
  deletes keys it recognises, so dropping it strands old caches forever.
- **`Dockerfile`, `.dockerignore`, `.env.example`, `gunicorn`, git repo.**
- **`CVSTAND_SERVER_STORE` now refuses ambiguous values.** It was `!= "0"`, so
  `false` / `no` / `off` all meant TRUE — the operator typing the word they
  mean got the opposite, on the one setting that decides whether two visitors
  overwrite each other's résumé. Beyond the plan, added deliberately.

## ⚠ THE UNVERIFIED THING

**The Docker image has never been built.** There is no Docker on this machine.
`tools/verify_docker_context.py` statically checks `.dockerignore` against the
app's real runtime needs (and was mutation-tested by excluding `data/`
wholesale — the trap being that `data/` holds local state AND the shipped
showcase samples). **A static check is not a build.** The first real build on
Railway is the open risk; expect to iterate on the Dockerfile there.

## Blocked on the USER — all of it is clicking, none of it is code

| Blocked on | Note |
|---|---|
| **Create the mailbox** | The PLAN is bought; the ADDRESS `info@cvstand.com` does not exist yet. Every page footer already links to it. |
| **Push to GitHub** | Repo is committed, no remote, no `gh` CLI |
| **Railway** | Mount the `/data` volume BEFORE the first signup or every deploy deletes every account |
| **DNS at Hostinger** | A/CNAME only. **Never MX or the SPF/DKIM TXT records** — that breaks the mailbox |
| `ANTHROPIC_API_KEY` | AI Phase 2; app answers 503 without it, by design |
| Trademark cls. 9/42 KSA/UAE/UK | Does not block code |

## Verified facts a future session should not re-derive

- Hostinger holds exactly two subscriptions: `.COM Domain` (expires
  2027-09-13) and `Starter Business Email`. **No web hosting** — and shared
  hosting could not run this app anyway: the PDF export launches a real
  Chromium per request.
- `git config user.name` is set repo-locally to "Jamal Jameel" — a guess from
  the account email. Change it if wrong.
- The builder page renders NO wordmark, deliberately (`builder.html:4-5`
  empties the chrome and footer blocks). It carries the brand in `<title>`.

---

# Previous entry — 2026-09-14a (the CVStand rename SHIPPED — all 4 phases)

Everything is saved to disk (this is **not a git repo** — no commit needed).
No dev server or background process is running. This file + BUILD.md +
NAMING.md + auto-memory are the whole handoff.

## State at the pause (2026-09-14) — the rename is DONE

**All four phases of `NAMING.md` §7 ran in one session.** The app is CVStand
everywhere a reader can see, in both interface languages.

| | before | after |
|---|---|---|
| fast suite | 1692 passed, 0 errors | **1728 passed, 0 errors** |
| full `--e2e` | 2136, 0 errors (carried) | **2172 passed, 0 errors (junit: 2196 cases, 0 failures)** |

**Read `NAMING.md` §7a first.** §7 is kept verbatim as the record of the plan;
§7a is the list of seven things the plan got wrong once measured against the
tree. Do not re-run the rename.

### What shipped

- **`app/brand.py` is new and is the single source of truth** — `NAME`,
  `HEAD`/`TAIL`, `SUPPORT_EMAIL`, `DOMAIN`, `TAGLINE`, reaching every template
  through a context processor. A fourth rename is one line.
- **Six surfaces renamed** plus the manifest (`routes.py:385-386` now read
  `brand.NAME` and dropped the `ui_t()` wrapper, which was always a no-op).
- **`info@cvstand.com` is wired in** — footer of every page, and the sign-in
  page, which previously said "get in touch" while the app contained **no
  address of any kind**. It is NOT inside a msgid, on purpose: `t()`'s key IS
  its English string, so an address in the sentence re-keys the catalogue and
  drops the Arabic whenever the mailbox changes.
- **The tagline**: "Make your CV stand out." / "اجعل سيرتك الذاتية تلفت
  الأنظار." It exists to resolve the booth-vs-stand-out ambiguity and a test
  asserts the disambiguating verb survives any future rewrite.
- **`tests/test_brand.py` is new** (32 tests) — brand in header, footer and
  `<title>` on every page in both languages, byte-identical in Arabic.
- **The label gate now covers the app shell**, has **attribute coverage**, an
  **accent-aware** word pattern, and a **reverse (dead-row) assertion**.
- **`MONETIZATION.md` §8a no longer promises storage that has no table.**
- **`sw.js` VERSION v1 → v2.** Required, and it was in none of the four phases.

### Defects found and fixed that were NOT in the plan

1. **Four dead catalogue rows, not one.** `"Résumé Builder"` plus
   `"Templates back"`, `"qualifications"`, and two template-switch errors
   orphaned when the switch moved to localStorage — which `labels.py`'s own
   comment already said had happened. All 49 Arabic renders verified clean
   after deletion.
2. **The label gate could not see attributes at all**, which is the real reason
   `base.html`'s meta description survived — not the glob. Widening the glob
   alone does NOT catch it.
3. **`WORDY` was ASCII-only**, so any string containing "résumé" was invisible
   to the miss detector — the accent trap from `NAMING.md` §3, living inside
   the test written to catch that class of miss.
4. **`t` is two different functions** (`labels.t` in résumé templates, `ui_t`
   in the shell) reading two differently-cased catalogues. One flat msgid list
   is wrong; widening the glob failed two tests for this reason alone.

### The method note worth keeping

**Five successive attempts to measure dead catalogue rows were each wrong in a
different way** — wrong catalogue (`_AR` vs `_UI_AR`); a self-referential blob
that included `labels.py` and made the test pass vacuously; folded-vs-raw key
casing; a double-quote pattern that swallows single-quoted literals inside
attributes; and naive quote pairing shifted by a single apostrophe in prose.

**Every new gate was mutation-tested before being believed.** The vacuous one
was caught that way and by nothing else — it passed a fabricated
`"Zombie Row Nothing Renders"` entry. This is the fourth time in this project
that a green gate turned out not to be running.

### Still blocked on the USER, unchanged

| Blocked on | What it unblocks |
|---|---|
| **Hosting** | The whole `outreach/` kit — every email links to the site |
| **Buying `info@cvstand.com`** (decided, not yet purchased) | The From line for that kit |
| `ANTHROPIC_API_KEY` | AI Phase 2 — `tools/assist_samples.py` does the rest |
| A native Arabic read of 20 samples | Whether the AI ships at all |
| Trademark cls. 9/42 in KSA/UAE/UK | Printing outreach at volume — does not block code |

⚠ The mailbox is **decided but not bought**. Everything in code points at
`info@cvstand.com` already, so the address must exist before the site is
deployed or the footer links to nothing.

---

# Previous pause — 2026-09-13 (domain bought + email decision · NO code changes)

Everything is saved to disk (this is **not a git repo** — no commit needed).
No dev server or background process is running. Nothing here is lost between
sessions — this file + BUILD.md + NAMING.md + auto-memory are the whole handoff.

## State at the pause (2026-09-13) — two decisions, no code touched

**No application code, test or template was modified this session.** Test counts
carried over from 2026-09-11 (1692 fast / 2136 full, 0 errors) and were NOT
re-run; nothing happened that could change them. Only `NAMING.md` and this file
were edited.

### 1. The domain is bought: **`cvstand.com`** — the brand is **CVStand**

`cvcraft.com` was taken, as `resumecraft.com` already was. **Siyar is dead** —
`NAMING.md` §5 is marked superseded in place but kept as the record of how the
namespace was searched. **`NAMING.md` is rewritten: read its header block and
§7-§9, not §5.**

What the new name settles, and what it does not (`NAMING.md` header block has
the full version):

- **FIXED** — the noun. MENA says *CV*, and `outreach/` already says "CV
  builder" in every subject line, EN and AR. Name now matches the kit.
- **NOT FIXED** — "Stand" has no Arabic morpheme, same as "Craft". **Costs
  nothing in code**: `labels.py:229` already ruled the brand is never
  translated, so that policy carries over untouched. Paid in positioning; the
  remedy is a tagline, not a third name.
- **OPEN** — "stand" reads as a booth (جناح) *or* "stand out". The tagline has
  to disambiguate. Phase 4, not a blocker.

### 2. Domain alone is NOT enough — buy a mailbox on it

Asked and answered this session; the reasoning is in `NAMING.md`'s header block
so it does not have to be re-derived. Short form: Stage 2 revenue is entirely
hand-sent cold email to Saudi/UAE career centres, and a `@gmail.com` From line
reads as a student, not a vendor; SPF/DKIM/DMARC only exist on a domain you
send from; and **`account.html:82` already tells locked-out users to "get in
touch" at an address that does not exist** — verified this session that there is
NO mail code anywhere (`smtplib` / `flask_mail` / reset-token: zero hits under
`app/`). Cost is ~$1-6/month against four-figure institutional quotes.

Human mailbox (`hello@cvstand.com`) now; transactional `noreply@` only when
password reset ships. Buy it early — a new domain has no sending reputation and
age is free.

### The rename plan is written and NOT confirmed

`NAMING.md` §7 has four phases, fully specified with line numbers. **The user
paused before answering the one open question: all four phases, or Phases 1+2
now and Phase 3 in its own session?** Ask that first, then start.

Headlines, so a future session knows the shape without re-reading:

- **Phase 1 (~1h)** — put the brand in a new `app/brand.py` constant FIRST, then
  rename 6 surfaces. ⚠ The constant is not optional polish: after the rename
  `grep -i cvstand` will STILL miss the wordmark (`CV<b>Stand</b>`), which is
  the exact trap that produced a confidently wrong answer on 2026-09-12.
- **Phase 2 (~45 min)** — the three brand defects found 2026-09-12, same files.
  Includes deleting the then-dead `"Résumé Builder"` msgid at `labels.py:231`.
- **Phase 3 (MEDIUM)** — widen `tests/test_labels.py:60`'s glob. The only phase
  that can overrun; commit the widening separately from the fixes.
- **Phase 4 (~30 min)** — tagline, plus `MONETIZATION.md` §8a's storage claim
  that has no table behind it (name-independent, can land first).

**DO NOT TOUCH in any phase:** `RESUMECRAFT_*` env vars, `data/resumecraft.db`,
`resumecraft:resume` / `resumecraft:template`. The browser owns the résumé;
renaming those keys wipes every existing document for zero visible gain.

### Still blocked on the USER, unchanged

| Blocked on | What it unblocks |
|---|---|
| **Hosting** (the domain is now owned) | The whole `outreach/` kit — every email links to the site |
| A mailbox on `cvstand.com` | The From line for that same kit |
| `ANTHROPIC_API_KEY` | AI Phase 2 — `tools/assist_samples.py` does the rest |
| A native Arabic read of 20 samples | Whether the AI ships at all |
| Trademark cls. 9/42 in KSA/UAE/UK | Printing outreach at volume — **does not block code** |

## Previous pause — 2026-09-12 (naming decision · NO code changes · previous: 1692 fast / 2136 full, 0 errors)

Everything is saved to disk (this is **not a git repo** — no commit needed).
No dev server or background process is running. Nothing here is lost between
sessions — this file + BUILD.md + NAMING.md + auto-memory are the whole handoff.

## State at the pause (2026-09-12) — naming only, no code touched

**No application code, test or template was modified this session.** The test
counts in the heading are carried over from 2026-09-11 and were not re-run;
nothing happened that could change them.

**The whole session is written up in `NAMING.md`.** Read that file, not this
summary, before touching the brand.

### The decision
**Siyar — سِيَر** (the plural of سيرة, literally "CVs"), on **`siyar.co`** or
**`siyarcv.com`**. Gated on Phase 0: the user must verify both at a registrar
plus trademark classes in KSA / UAE / UK. Nothing is renamed yet.

`resumecraft.com` is taken (user verified on Hostinger).

### Three things a future session must not repeat

1. **`grep -i resumecraft` does NOT find the wordmark.** It is split across tags
   as `Résumé<b>Craft</b>` (`base.html:30,71`) and the accented `Résumé` misses
   an ASCII pattern. **Grep for `Craft`.** This produced one confidently wrong
   answer this session ("the brand slot is empty" — the brand was already
   shipped on every page).
2. **"Does a company own this?" is not "is the domain free?"** Five names were
   proposed and five were taken because only the first question was asked. Check
   DNS / a registrar FIRST. Every short real word in `.com` is gone, in Arabic
   and English alike — stop looking for one.
3. **`MONETIZATION.md` §8a promises a feature with no table behind it** —
   "Keep as many CVs as you need" / "احتفظ بما تشاء من السير الذاتية". There is
   no résumés table: `app/db.py:53` has `users` and nothing else, and the
   localStorage key `resumecraft:resume` (`builder.js:28`) is singular. **An
   account stores zero résumés today.** Do not put saved versions in a slogan.
   `NAMING.md` §6 has the full evidence.

### Three real defects found, all unfixed (`NAMING.md` §7, Phase 3)
- The brand does not reach every page: `base.html:10` default title and
  `account.html:15` both say `t('Résumé Builder')`, so sign-up/sign-in are
  branded generically — and in Arabic a translated title sits beside a Latin
  wordmark.
- `base.html:11`'s `<meta name="description">` is hardcoded English, never
  routed through `t()`, while the manifest's description IS translated
  (`routes.py:387`). **The label gate cannot see it:**
  `tests/test_labels.py::_template_files` globs `*/*.j2` + `_macros.j2` only, so
  the entire app shell is outside the gate.
- Zero brand coverage in tests: `grep -rn "Craft" tests/` returns nothing and no
  test asserts on any `<title>`.

### Agent Reach — installed, never run
Unrelated to the résumé app; asked for mid-session.

- Installed **agent-reach 1.5.0** into a dedicated venv at
  `C:\Users\User\.agent-reach-venv` (entry point
  `...\Scripts\agent-reach.exe`). **Deliberately not the project venv** — bare
  `python` on this machine resolves to
  `Resumes builder project-1\venv\Scripts\python.exe`, so a naive `pip install`
  would have put 23 packages into the résumé builder.
- Use `py -3` on this machine (Python 3.14.6). `python3` is the Microsoft Store
  alias and is not a usable install.
- **It was never executed.** `agent-reach install --env=auto` was denied twice by
  the auto-mode classifier (Untrusted Code Integration), and adding a permission
  rule was denied as Self-Modification. Nothing was written to `~/.agent-reach/`
  — no config, no tokens, nothing in this project directory.
- To run it, the user does it themselves:
  `! C:\Users\User\.agent-reach-venv\Scripts\agent-reach.exe install --env=auto`
  (read-only; verified in source at `cli.py:261,299,370` that without `--system`
  it writes nothing), or grants a permission rule via `/permissions`.
- Missing deps found by direct probe: `gh` (GitHub channel), `uv`/`uvx`
  (LinkedIn only). `node`/`npm` present. `yt-dlp` bundled with the install.
- `--system` has never been passed. The optional channels (Twitter, Reddit,
  Facebook, Instagram, XiaoHongShu, Xueqiu) all authenticate with exported
  browser cookies or a logged-in Chrome session — the upstream doc's own advice
  is to use a secondary account.

## Restart the app
```
cd "C:\Users\User\Downloads\Resumes builder project-1"
venv/Scripts/python run.py            # -> http://127.0.0.1:5000
venv/Scripts/python -m pytest -q      # 1425 fast tests, ~17s (461 opt-in tests skipped)
venv/Scripts/python -m pytest --e2e -q  # 1862 tests incl. browser + pixel gates, ~670s
venv/Scripts/python -m pytest --e2e -q -m "e2e and not slow"  # skip the 49-template gates
venv/Scripts/python tools/fetch_fonts.py --check   # Latin fonts present + consistent
venv/Scripts/python tools/fetch_fonts_ar.py --check # Arabic aliases claim no Latin codepoint
venv/Scripts/python tools/build_word_masters.py --verify   # rebuild all 4 + open in Word
venv/Scripts/python tools/verify_autofit.py        # all 49: no-op on sample, recovers overload
venv/Scripts/python tools/verify_overflow.py --plain  # CONTROL: the shipped sample must be 49/49 clean
venv/Scripts/python tools/verify_overflow.py [--extreme] [--lang ar]  # horizontal overflow, all 49
venv/Scripts/python tools/golden.py --html         # regenerate HTML baselines (deliberately!)
venv/Scripts/python -m pytest tests/test_assist.py -q  # AI assistant, 34 tests, offline
venv/Scripts/python -m pytest tests/test_auth.py -q    # accounts + sessions, 48 tests
venv/Scripts/python tools/assist_samples.py --preview   # Phase 2 review page, no API calls
venv/Scripts/python tools/assist_samples.py             # Phase 2 FOR REAL — needs a key, costs money
```

**The AI assistant makes no live call in any test.** `app.assist.adapt` takes an
injectable `client` and the suite passes a fake, so the loop stays free and
works offline. `ANTHROPIC_API_KEY` is NOT set in this environment; without it
`/api/assist` answers 503 and nothing else changes.

⚠ **Read `N passed` together with the summary line, not alone.** pytest exits 0
with SETUP ERRORS present; that is how the pixel gate went 30+ runs without
running at all (session 18). Grep the output for `error` / `FAILED`, or use the
`junit.xml` the `--junitxml` flow writes.

**Bilingual quick checks** (phases 3-7 all ship a gate in the fast loop):
`tests/test_labels.py` (labels routed + no `t` shadowing), `test_rtl_typography.py`,
`test_rtl_mirroring.py` (no physical directional CSS; the geometric mirror test
is `slow`), `test_ui_language.py` (UI vs document language), `test_docx_rtl.py`.
Height check for a ported template (renders the shared sample, measures `.tpl`
scrollHeight/width, checks no `::before`, skill text, writes `tools/<key>.png`):
`venv/Scripts/python tools/verify_height.py <cat>-tN [<cat>-tN ...]`
`verify_height.py` now also reports auto-fit's `natural` height, which is the
number a port should be judged on — auto-fit is a safety net for variable user
content, not a licence to ship an overflowing port. That number comes from a
text-range scan, so unlike `.tpl` scrollHeight it sees through `overflow:hidden`
and absolute placement and needs no per-panel measuring.
Note: pip in this env needs `--trusted-host pypi.org --trusted-host files.pythonhosted.org`.
Playwright + Chromium are already installed (PDF export works).

## State at the pause (2026-09-11, 19:05)

**Nothing is running.** No dev server, no background process, no stray
Chromium. This is not a git repo — everything is on disk and there is nothing
to commit.

**Verified on the final tree, from `junit.xml` and not from the summary line:**
`errors="0" failures="0" skipped="24" tests="2160"` — **2136 passed** in 11m11s.
Fast loop **1692**.

Three tracks landed this session; each is written up in full below.

1. **AI assistant Phase 1** — `app/assist.py`, `/api/assist`, entitlement gate
   live and returning True. Phase 2 (the Arabic quality gate) is the next step
   and needs an API key plus the user's own reading.
2. **The outreach kit** — `outreach/`, no code. Blocked on one thing: there is
   no deployed URL.
3. **Stage 3 Phase 1** — accounts and sessions, plus a `SECRET_KEY` boot guard.

**Three things are blocked on the USER, not on code:**

| Blocked on | What it unblocks |
|---|---|
| A deployed URL (hosting + domain) | The whole outreach kit; also a sane place for an API key |
| `ANTHROPIC_API_KEY` | AI Phase 2 — `tools/assist_samples.py` then does the rest |
| A native Arabic read of 20 samples | Whether the AI ships at all |

**Deliberately NOT left behind:** `tools/assist_review.html` was deleted. It
held the source text echoed back as if it were model output, and a future
session could have mistaken it for a real Phase 2 run. Regenerate the layout
any time with `tools/assist_samples.py --preview`.

**Next code step, if you want one:** Stage 3 Phase 2 — `pass_expires_at`,
`has_active_pass()`, and wiring `assist.has_ai_access()` to it. About half a
session, no external dependency. Phases 3-6 of the Stage 3 plan follow.

## Earlier state (2026-09-09, 23:50)

Nothing is running — the dev server was started to preview the app and has been
stopped. Everything is on disk; this is not a git repo, so there is nothing to
commit. Fast loop **1425 passed**, full `--e2e` **1862 passed, 24 skipped, 0
errors, 0 failures** on the final tree.

**The user's own résumé changed during the preview, by them, and is theirs.**
`data/resume.json` is now `lang: "ar"` with Arabic level words, on
`modern-t2` — i.e. **they used session 24's new control for its actual purpose**
and the last English-only assumption is closed in practice, not just in test.
Do not overwrite it or "restore" it to the sample. Verified after the change:
0px silent horizontal loss and auto-fit natural 1100.0px (`fitted: true`, no
compression), so their document is clean on both axes.

Screenshots of the running app and of the language control are in
`screenshots/session-2026-09-09/` — landing, gallery, builder, and the Arabic
switch with its translated level words.

Two sessions landed here (24 and 25); both are written up below in full.

## Where things stand

Full app built and working: landing (`/`), gallery with Modern/ATS tabs
(`/templates`), live builder (`/builder`) with stepped form, live preview, zoom,
autosave, template drawer, download menu. **Both exports work — PDF and DOCX.**

**49 templates live** in `registry._PORTED` — **porting is COMPLETE**. Every one
compliance-checked + screenshot-verified at 850×1100:

- **Modern (24/24)**: COMPLETE — every block ported.
- **ATS (25/25)**: COMPLETE — every block ported.

`_PORTED` now equals the full catalogue, so there is no longer a live
"catalogued but not ported" key. The two tests covering that branch
(`test_unported_template_key_is_rejected`, `test_set_template_rejects_unported`)
synthesise one via a `unported_key` fixture that monkeypatches
`registry.TEMPLATES` — keep that fixture if the branch stays.

### `_macros.j2` state
`skill_ring(skill, opts)` — conic-gradient ring. opts: `size` `hole` `ring`
`track` `ink` `hole_bg` `name_css` `level_css` `pct_size`. `hole_bg` (default
`#ffffff`) sets the disc colour behind the ring for dark/tinted cards.
`skill_dotrow(skill, opts)` — also takes `name_css` / `level_css`.
`skill_slider(skill, opts)` — NEW: bar + a decorative knob at the fill %; value
shown as real text. opts: `track` `fill` `track_h` `knob` `name_css`
`label_css` `row_min` (label-row min-height for wrap alignment). Used by t10.
All additions are backward-compatible — prior callers (t1/t13/t17) unchanged.

### DONE — session 1: `modern-t17`–`t21`
- **t17** "Two-Tone Ribbon" — compression to scrollHeight 1101 (`skill_ring` 68→54).
- **t18** "Interlocking Block" — absolute two-tone + flex columns; navy #002B66 /
  brass #C08A2E; hand-rolled flex-track bars; kicker → #C9973A, level words navy.
- **t19** "Label Gutter" — single-column gutter stack; `skill_bar` stacked.
- **t20** "Cotton & Cherry" — flex two-column, right-hand cotton rail + cherry dots.
- **t21** "Rounded Card Shell" — three absolute rounded cards; `skill_dotrow` on
  the dark green card.

### DONE — session 2: `modern-t12` `t16` `t22` `t24` (ring set)
- **t16** "Charcoal Rings" — charcoal rail + white body; `skill_ring` with
  `hole_bg:#1C1C20` on the dark rail; bespoke "Selected Launches" dropped,
  "Platforms" → Tools.
- **t24** "Hard-Edged Sidebar" — squared replica of t5; slate/amber block
  headers; `skill_ring` (slate dial on amber track) in a #d9d9d9 cell-rule grid.
- **t22** "Vertical Rail Rings" — rotated "RESUME" rail (decorative DOM text);
  body + inner split; `skill_ring` 66px 2-up; name 76→56 so it holds one line.
- **t12** "Typographic Mono" — full-bleed Anton; paired heading rows
  (WORK EXPERIENCE | CONTACT, EDUCATIONAL HISTORY | SKILLS); `skill_ring` with
  `hole_bg:#f7f7f5`. NOTE: built for dense content — with the shared sample the
  short education column leaves whitespace beside the 5-ring grid. Ties into the
  open per-template-sample question (Next action #3).
- All: stale registry accents fixed to the real template hex; divergences logged
  in each `.j2` header.

### DONE — session 3: `modern-t10` (closes Modern 24/24)
- **t10** "FinTech Elite" — burnt-orange #A93005 sidebar + white body. New
  `skill_slider` macro (bar + knob, value as real text). The reference's double
  skill list (sidebar "Key Skills" + body sliders) renders once as the body
  sliders; sidebar slot carries Tools. The 3 bordered skill cards become one
  bordered card with an internal 3-col slider grid (robust to any skill count).
  Registry accent `#1F3A5F`→`#A93005`.

### DONE — session 4: `ats-t23` + `ats-t8` (closes ATS 25/25 and all 49)
- **`ats-t23`** "Open Air" — new port. Teal #0F6E63 / ink #13201E / tint #57635F,
  Poppins throughout, no rules or fills anywhere. Vertical padding 62→46 and
  section gap 22→14 to seat the shared sample once Tools + Languages are added;
  the 72px side padding is held so the open feel survives. scrollHeight 1100.
- **`ats-t8`** "Big Type" — released from hold. Condensed pass took it 1316→1100:
  section gap 24→12, padding 60/52→42/32, Anton name 66→54, leading 1.85/1.8/1.7
  →1.55–1.6, experience gap 14→11, role 17→16. The oversized Anton masthead —
  the template's whole identity — survives at 54px. Also swapped the en-dash date
  separator for a plain hyphen (ATS parse safety).
- Two stale registry accents fixed: `ats-t23` #0D9488→**#0F6E63**,
  `ats-t8` #111111→**#C0392B**.

### DONE — session 5: Word masters (DOCX unblocked)
Both masters exist and `/export/docx` returns a real `.docx` for all 49 layouts.

- **Generated, not hand-authored.** `tools/build_word_masters.py` builds both
  files with `python-docx`. Edit the script and re-run — **never edit the
  `.docx`**, the next build overwrites it. This supersedes the old
  `word_masters/README.md` instruction to author them in Word; rationale in the
  script header (reviewable source, one-command rebuild, and python-docx writes
  each tag as a single run so Word can't split `{{ r.name }}` mid-tag).
- **Two bugs found and fixed while verifying** — both would have shipped:
  1. `render_docx()` needed `autoescape=True`. Without it "Halden & Row"
     rendered as "Halden  Row"; a `<` could corrupt the package.
  2. `_dot_glyphs()` returned `○○○○○` for any level off the `LEVEL_DOTS` scale,
     so languages read "English — Native ○○○○○" — a graphic contradicting the
     text. Unmapped levels now render text only, per `dots_for()`'s docstring.
- `docxtpl`'s `{%tc %}` horizontal cell loop **does not work here** — it emits an
  empty `<w:tr/>`. Chip row is a fixed 4-cell borderless table with inline
  conditionals (a `{%p if %}` can strip a cell to zero paragraphs → invalid
  OOXML). `normalize()` already caps at 4 and drops blank metrics.
- New context field `r.contact_line` (in `docx.py::_contact_line`) — Word has no
  sidebar, so contacts collapse to one pipe-separated line.
- 8 DOCX tests added; the old "501 until authored" test became a 200-plus-MIME
  assertion.

### DONE — session 6: the masters would not open (fixed)
The first cut of both masters **Word refused to open**, and every structural
test was green on them. Three OOXML schema-order violations:

| Element | Emitted | Schema requires |
|---|---|---|
| `w:pPr` | `spacing` then `pBdr` | `pBdr` **before** `spacing` |
| `w:rPr` | `sz` then `spacing` | `spacing` **before** `sz` |
| `w:tblPr` | `tblLook` then `tblBorders` | `tblBorders` **before** `tblLook` |

`w:pPr`/`w:rPr`/`w:tblPr` are ordered *sequences*; appending to the end is
well-formed but invalid, and Word rejects the whole document. **python-docx and
lxml parse such a file happily**, so reopening it and reading the text back —
which is what the tests did — passes on a document nobody can open. Fixed with
`insert_element_before(el, *successors)`; `tests/test_docx_validity.py` now
asserts child order in both the masters and the rendered export.

Then, with the files finally opening, real Word showed a second defect: content
spilled 2–3 lines onto page 2, stranding the `LANGUAGES` heading alone on
Modern. Fixed by `keep_with_next` on every heading + job role/meta line (the
structural fix — user content is variable-length so it *will* repaginate) and
margins 0.75→0.62 / 0.8→0.66.

`tools/build_word_masters.py --verify` now drives Word over COM and reports
open-failures and page-2 spill. Both masters: **opens, fits one page.**

**⚠ Protected View gotcha.** This project lives under `C:\Users\User\Downloads\`,
which is on Word's default "unsafe locations" list, so **double-clicking any
`.docx` inside the project fails to open** ("Office has detected a problem with
this file"). The file is fine — COM `Documents.Open` bypasses Protected View,
which is why `--verify` passes on a file Explorer refuses. To open one by hand,
copy it outside `Downloads` first, or use Word's File → Open → Browse. Confirmed
2026-08-30: same file failed from the project dir, opened from the Desktop.
Note this also means `--verify` cannot detect a Protected View rejection.
Appearance eyeballed via Word's HTML export — both read well and Modern is
properly differentiated (Georgia navy heads, italic title, heavier header rule).

### DONE — session 7: fonts self-hosted (no CDN, renders offline)
11 families, 34 `.woff2` (latin + latin-ext, 995 KB) now in
`app/static/fonts/`, fetched by `tools/fetch_fonts.py`. No render path touches
`fonts.googleapis.com` any more.

**Two stylesheets, because the two render paths resolve URLs differently:**
- `fonts.css` — `<link>`ed by the preview, which is served over HTTP
  (`/preview`, and an iframe `srcdoc` inheriting the page's base URL). Browser
  caches it; the preview document stays ~12 KB.
- `fonts_inline.css` — same rules with the bytes as `data:` URIs, injected into
  the document for PDF. **Required**: `pdf.py` renders via `set_content()`,
  whose base URL is `about:blank`, so `/static/fonts/...` resolves to nothing
  and Chromium silently substitutes a fallback face — no error, no log line.
  ~1.35 MB per export, but an export is a one-off action.
  `document_html(..., for_pdf=True)` selects it.

Gotchas hit:
- Naive inlining base64'd a shared file once per subset rule → **4.2 MB**. Now
  grouped by file with merged `unicode-range`s → **1.35 MB**, each file once.
- **`tools/verify_height.py` also uses `set_content`** and had to switch to
  `for_pdf=True`, or every template height would be measured in a fallback face.
  Heights re-verified identical (1100) after the switch.
- Windows has no `.woff2` MIME entry, so Flask served fonts as
  `application/octet-stream`; `create_app()` now registers `font/woff2`.
- `@font-face` blocks are copied verbatim from Google with only `url()`
  rewritten — hand-writing them breaks the variable-font weight axes that
  Fraunces (`opsz,wght`), Inter and Archivo rely on.

Verified by loading all 11 families in Chromium **with the network blocked**:
each renders at a distinct width vs the fallback. The linked variant under
`set_content` fails all 11 — which is exactly the silent bug this design avoids.

`app/static/fonts/LICENSES.md` records the OFL-1.1 licence + source per family.
**If you publish this project, ship each family's `OFL.txt`** — a link is not
sufficient under the licence.

### DONE — session 8: photo in DOCX (closes the last real gap)
A photo appeared in PDF but vanished in Word. Now: `modern_editorial.docx`
embeds it as a 22 mm `InlineImage`; **`ats_standard.docx` deliberately has no
photo slot**, mirroring the HTML family exactly (16/24 Modern templates have a
photo slot; **0/25 ATS** do, because images defeat résumé parsers).

- `_context(data, doc)` now takes the `DocxTemplate` — an `InlineImage` must be
  bound to the document it is embedded in, so context is built after the
  template is opened.
- The master guards `{%p if photo %}`, not `r.photo_url`: a dangling URL (upload
  deleted) yields a falsy `photo` and the paragraph disappears rather than
  leaving a gap or a broken image. A bad image file can never fail the export.
- **The photo cost ~79pt and pushed 5 paragraphs to page 2.** Modern master
  re-tuned to fit *with* a photo — margins 0.66→0.5, heading lead 7→4pt, list
  `space_after` 1→0, photo 28→22 mm. A photo-less résumé now just has more
  bottom margin. Verified in Word: photo **and** no-photo both spill 0.
- 4 tests cover it: embeds in Modern, never in ATS, and absent/dangling URLs
  produce no image.

### DONE — session 9: auto-fit (Next action #1 resolved, the other way)
Next action #1 offered per-template samples vs auto-fit. **Per-template samples
were dropped, not deferred**: `/preview` — the builder *and* all 49 gallery card
iframes (`gallery.html:26`) — renders `load_resume()`, the user's live data,
never `sample_resume.json`. So 49 calibrated samples would have changed only the
first-run seed and my own screenshots. The bottom whitespace on t10/t12/t16/t21
is a verification-harness artifact. The *product* defect was the opposite one —
heavy content overflowing, warned about but never fixed.

`app/static/js/autofit.js` fits any content to the 1100px page in two stages:
rhythm (line-height, block margins/padding, row-gap) 1.00→0.85, then type scale
1.00→0.92 only if rhythm bottoms out. **No horizontal property is ever touched.**
That is the whole safety argument: a `transform: scale(k)` would shrink the box
to 850k wide and pull every full-bleed sidebar off the page edge, and widening
the logical canvas to 850/k instead would break the absolute layouts (t7/t8/t11/
t14/t15/t18/t21) whose px offsets are keyed to 850. Vertical-only leaves both
untouched by construction; font-size is horizontally safe for the same reason —
text re-wraps inside boxes that have not moved.

Inlined into every document by `document_html()`, not `<script src>`'d — the
same about:blank lesson as the fonts. It self-starts after `fonts.ready`;
preview, `pdf.py` and `verify_autofit.py` all await `window.ResumeAutofit.ready`,
so **the fit the user approves on screen is the fit that prints**. Without that
await in `pdf.py`, `page.pdf()` races the fit.

**Two bugs found while verifying, both mine, both silent:**
1. First measurement used `.tpl.scrollHeight` plus a `scrollHeight > clientHeight`
   check for clipped boxes. That branch counted a fixed-height box's trailing
   padding as overflow, so `ats-t7` (1113) and `modern-t22` (1112) compressed
   themselves on the shared sample they fit perfectly well. Replaced with a
   **text-range scan**: walk the text nodes, take the lowest Range rect. A Range
   rect is pure layout geometry — an ancestor's `overflow:hidden` clips what is
   painted but never moves it — so it sees through clipping and absolute
   placement alike and counts only ink a reader would lose.
2. `line-height` and `font-size` both inherit, so writing a parent before
   capturing its children made each child cache an already-scaled value and
   compound the compression. Fixed by capturing every element before writing any.

**Results (`tools/verify_autofit.py`, all 49):** strict no-op on the shared
sample everywhere (d=1, t=1). 47/49 recover a +20% overload (one extra role, two
extra bullets per role). `modern-t17` (1286→1104) and `modern-t18` (1300→1133)
cannot — both are the fixed-height card layouts already flagged as clip-prone —
and correctly report `fitted:false` so the builder warns. Real PDFs exported at
full compression come out **one page**; screenshots at d=0.85/t=0.92 read
cleanly, hierarchy intact.

Builder now distinguishes three states: silent when it fits unaided, a green
info bar ("Auto-fitted to one page — spacing tightened N%"), or the amber
warning when it is still over at the floors. It reads the engine's result rather
than `.tpl.scrollHeight`, which under-reported on 7 Modern layouts.

11 wiring tests in `tests/test_autofit.py` (browser-free, so `pytest -q` stays
~3s); behaviour lives in `tools/verify_autofit.py` per the project's convention
that browser verification is a tool, not a test.

### DONE — session 10: the browser suite (`tests/e2e/`, opt-in via `--e2e`)
All 99 previous tests ran through the Flask test client or read files. Nothing
exercised a browser, so autosave, the preview iframe, the drawer, the blob
downloads and auto-fit were only ever checked by hand or by `tools/` scripts.
121 browser tests now cover them; `pytest -q` is unchanged at ~3.5s because the
suite is skipped unless `--e2e` is passed (`tests/conftest.py`). Chromium only —
Firefox and WebKit are not installed, and a locally served single-user app does
not earn the download. Run 3× back to back: 23/23 non-`slow` tests every time,
no flakes. `--junitxml=junit.xml` gives CI a machine-readable report.

- `tests/e2e/conftest.py` boots the **real server in a subprocess** on a free
  port against a throwaway data dir. That needed one app change:
  `config.DATA_DIR` now honours `RESUMECRAFT_DATA_DIR`. Without it the suite
  would autosave over the user's own `data/resume.json` on every keystroke.
  `SAMPLE_RESUME_PATH` was re-pinned to `ROOT/data/` so seeding still works.
  Failures leave a screenshot + Playwright trace in `tests/e2e/artifacts/`.
- `test_journey.py` (9) — landing → gallery → tabs → "Use this" → builder →
  edit → preview → autosave → reload; add-a-bullet; drawer switch (persisted);
  a rejected render surfacing in the form; zoom.
- `test_offline.py` (6) — every page with all off-machine requests aborted.
- `test_exports.py` (4) — PDF and DOCX pulled through the real download menu:
  filename, magic bytes, **PDF is one page**, DOCX contains the edit and no
  unrendered `{{ tag }}`, ATS master embeds no image.
- **The unit suite was writing into `data/` too** — `tests/test_smoke.py`'s
  `uploaded_photo` fixture POSTs a real upload, so every `pytest -q` since it
  was written left a stray .jpg in `data/uploads/` (three are still there,
  none referenced — `photo_url` is empty — delete them whenever). `tests/conftest.py`
  now points the whole session at a temp `RESUMECRAFT_DATA_DIR` at import time,
  before `app.config` reads it. Verified: a full `--e2e` run leaves
  `data/resume.json` and `data/meta.json` byte-identical.
- `test_content_editing.py` (4) — add/remove a tool (rows re-index), a stat
  chip vanishing when its metric is cleared (a standing rule in CLAUDE.md), and
  photo upload → form thumbnail → canvas → **an image inside the PDF** → Remove
  clears it everywhere. The upload is a real non-square PNG, so the server's
  centre-crop and 512px downscale are asserted on the served bytes.
- `test_autofit_gate.py` (98, marked `slow`) — `tools/verify_autofit.py`'s two
  properties as tests, reusing its `heavy_sample()` so the fixture has one
  definition.

**Two real defects found, both fixed:**
1. **The app shell still linked `fonts.googleapis.com`.** Session 7 delinted the
   *résumé document* render paths and stopped there; `base.html` kept the CDN
   `<link>`. A render-blocking stylesheet on an unreachable host does not fail
   fast — every cold page load sat ~21s waiting (measured: `/templates`
   DOMContentLoaded 21.2s, `/builder` 15.7s) before Chromium gave up, in a
   product whose selling point is that it runs locally. Now links the
   self-hosted `fonts/fonts.css`; Inter and Fraunces were already among the 11
   families. Fraunces 600 (one hero word) falls back to the vendored 700 —
   500 and 700 are the only weights fetched.
2. **`TYPE_FLOOR` drift.** `tests/test_autofit.py::test_floors_match_the_documented_contract`
   was **already failing** at the start of this session: the engine had been
   lowered to `0.90` while that test, `verify_autofit.py`, BUILD.md,
   RESUME_HERE.md and autofit.js's own header all still said `0.92`. The lower
   floor is what seats `modern-t17`'s heavy sample (1285.7 → 1092.5), so
   recovery is **48/49, not 47/49** — `modern-t18` alone still cannot
   (1299.9 → 1120.4) and correctly reports `fitted:false`. The engine was left
   alone and the five stale mentions updated to 0.90. **If 0.90 was accidental,
   put the constant back and revert those five.**

Also: each family's full `OFL.txt` is now vendored in
`app/static/fonts/licenses/` by `tools/fetch_fonts.py --licences`, which closes
the "before publishing" caveat. `--check` and a unit test fail if one is missing.


### DONE — session 11: the auto-fit bar, and #4 decided
Two things, both in the reporting layer rather than the engine.

**`tests/e2e/test_autofit_banner.py` (4 tests, ~6s).** Session 10 covered the
auto-fit *engine* across all 49 layouts (`test_autofit_gate.py`) but nothing
covered what the builder then **says** about the result — which is the only part
of auto-fit a user ever sees. `builder.js::checkOverflow` reads
`ResumeAutofit.ready` inside the preview iframe, across a document boundary, so
`tests/test_autofit.py` (deliberately browser-free) cannot reach it. It is also
the exact path that was silently wrong before session 9. All three states now
have a test: hidden when it fits unaided, the green info note with a real
percentage when it seats after a squeeze (`modern-t1` heavy, 1252.0 → 1100.0 @
d=0.85 → "tightened 15%"), the amber warning when it cannot (`modern-t18`
heavy, 1299.9 → 1120.4), and the note clearing again when the overflow is
trimmed. Run 3× back to back: 4/4 every time, no flakes.

**Measurement gotcha found while writing it.** The obvious trim/overflow lever —
adding or removing *bullets* — does not move the number on `modern-t1`. `.tpl`
is a fixed 1100px flex column, so `measure()` floors at `.tpl.scrollHeight` =
1100 whenever `.tpl` does not clip, and the experience column absorbs bullets
into the slack the sidebar leaves it: **eight extra bullets on one role still
report natural 1100.0.** Only adding or removing a whole entry moves it. So
`natural` below 1100 is not meaningful on a non-clipping fixed-height template
— worth knowing before trusting a `verify_height.py` reading.

**Decision #4 resolved: `TYPE_FLOOR = 0.90` is intentional and stays.** Stage 2
only runs once stage 1 has bottomed out at 0.85, so it is the last thing tried
before the builder gives up and warns; recovery stays 48/49. Session 10 said it
had updated the five stale 0.92 mentions — **it missed BUILD.md entirely**.
Corrected now: BUILD.md's architecture row (→0.92 → →0.90), its auto-fit prose
(0.92, and "47/49 … the two that cannot") and `test_autofit_gate.py`'s docstring
("47/49 … the two fixed-height card layouts"). `tests/test_autofit.py`'s pin
docstring now records the decision instead of posing the question.

### DONE — session 11b: a latent Windows flake in the browser suite
A full `--e2e` run came back **`224 passed, 1 error`** — and pytest still
**exited 0**, which is why a run like it could have been reported as green:

    PermissionError: [Errno 13] Permission denied: '...\e2e-data0\resume.json'
    ERROR tests/e2e/test_journey.py::test_zoom_controls_scale_the_stage

Not the app — the fixture. `clean_state` rewrites `resume.json` before every
test, and the builder autosaves on a **900ms debounce**, so a test that edits a
field and then ends can leave a `PUT /api/resume` in flight that lands inside
the *next* test's reset. On POSIX that is harmless. **On Windows it is not**:
opening a file for writing while another process holds it open fails outright,
and `store.py::_write_json` ends in `tmp.replace(path)` — atomic on POSIX, but
**also denied on Windows** when the destination is open. There is no
last-writer-wins to fall back on.

It is load-dependent, not deterministic: the same suite ran 225-green three
times before and after. It surfaced when three pytest sessions overlapped.

Fixed in `tests/e2e/conftest.py` with `_despite_the_server(op)` — a bounded
retry (40 × 50ms) around the reset's write and unlink. Retrying is the right
shape: the server's write is legitimate and short-lived, and the fixture only
needs to land last. A permanent lock still fails loudly, with a diagnosis
instead of a bare Errno 13; a non-`PermissionError` propagates untouched.

Also exposed as a **`seed_resume` fixture**, because `test_autofit_banner.py`'s
`_load` had the identical unguarded `write_text` and would have flaked next.
Any future test that seeds a different résumé should use `seed_resume`, never a
raw `write_text` into `live_server.data_dir`.

**Verified under the conditions that broke it**: two full `--e2e` suites run
concurrently, both 225 passed, zero `PermissionError`. Plus a direct check of
the helper's three behaviours (transient lock recovers, permanent lock raises a
diagnosed `AssertionError`, unrelated exceptions propagate).

⚠ **Do not read `N passed` alone as a green run.** pytest exits 0 with setup
errors present. Check for `error` in the summary line, or use the `junit.xml`
the documented `--junitxml` flow already writes (now gitignored).

### DONE — session 12: entry removal covered (`tests/e2e/test_entry_removal.py`)
A coverage audit against the builder's interactive surface found one whole
branch of `builder.js`'s click handler untested in a browser. `rm` was
exercised only on **tools** — a list of plain strings, one input per index,
nothing nested. The lists that actually carry risk are the object lists with
bullets: their inputs are named by position (`experience.1.bullets.0`), so
deleting entry 0 has to re-bind every input after it. `onChange(true)` does
that by rebuilding the form from `data`, and nothing checked it.

**Why the canvas alone could not catch it.** The preview renders from `data`
either way, so a patch-in-place regression would leave the résumé looking
perfectly correct while the form's inputs stayed bound to the old indices —
the next keystroke lands in the wrong role. The new tests therefore assert on
the **form**: entry count, the entry-head title, and the *values* sitting in
`experience.0.company` / `experience.0.bullets.0` after a delete.

4 tests, ~10s: removing a role with bullets (re-index), removing one bullet
(siblings keep their bindings), emptying a section (`education` → the heading
must go with it, the same no-stranded-label rule the stat chips follow), and a
removal surviving the autosave round trip on reload.

**Each one was mutation-checked rather than trusted for passing first time**,
which all four did:

| Mutation | Caught by |
|---|---|
| `onChange(true)` → `onChange(false)` on the structural branch (no form rebuild) | role re-index, bullet re-index |
| `{% if r.education %}` → `{% if True %}` in `modern/t1.j2` | empty-section heading |
| `rm` updates the UI but never persists | reload-survives, empty-section |

All three sources were restored and `diff`-verified identical afterwards.
Suite is **229** (was 225); the 31 non-`slow` browser tests ran 3× back to
back, 31/31 each time, no flakes. `data/resume.json` and `data/meta.json` still
carry their 2026-08-28/30 timestamps.

Also corrected **BUILD.md's test paragraph, which was stale at 221** — it had
missed session 11's 4 auto-fit-banner tests. Now 229 with the per-file
breakdown.

### DONE — session 13: two real defects behind the last coverage gaps
Working the three gaps session 12 left listed. One turned out to be nothing;
the other two were live bugs, and the second is the worst one found in the
project so far.

**Not a bug: the download menu.** It opens, closes on an outside click and
re-opens correctly. Session 12's suspicion came from a probe that never
actually clicked (`page.locator("h1").count()` is 0 on `/builder`, so the
conditional short-circuited). Pinned by a test now — `#dl-toggle` relies on
`e.stopPropagation()` so the document-level close handler does not eat its own
opening click, and dropping that one call makes the menu impossible to open.

**Bug 1 — a rejected photo upload was completely silent.** `/api/photo`
refuses a non-image with `abort(415)`, which answers with an **HTML** error
page, so the handler's `res.json()` threw and its `catch (_) { /* ignore */ }`
swallowed the throw. The `setSaveState("saving")` set just before the upload
was never handed back: the indicator read **"Saving…" for ever** and nothing
said why no photo appeared. Now the status is checked before parsing, the
reason is shown in `#form-errors`, and the file input is cleared so the same
file can be retried. Handing the indicator back needed a `savePending` flag —
saying "Saved" while an edit is still on the 900ms debounce would just be a
different lie.

**Bug 2 — `normalize()` did not honour its own contract, and every template
500'd on ordinary content.** `schema.py`'s docstring promises "every optional
field has a defined empty-value degrade path … so a missing field never 500s a
render", and the Jinja env runs `StrictUndefined`, which makes any gap fatal
rather than blank. It defaulted **only `bullets`**. Two consequences, both
reachable by a normal user:

- The builder's "+ Add role" pushes `{bullets: []}`. Only `role` is required,
  so the moment the user **typed the job title** the entry became schema-valid
  and reached `_macros.j2`'s `{% if job.start or job.end %}` → `/api/render`
  **500 on all 49 templates**. Adding a role and naming it is the most ordinary
  edit in the app.
- A résumé holding only `name` and `title` — the emptiest the schema allows —
  **500'd all 49** on `contact.email`.

Measured: **98/98 renders failed before the fix, 0/98 after** (49 templates ×
{half-filled entry, name-and-title-only}). The per-entry blanks are now derived
from `RESUME_SCHEMA` itself rather than hand-listed, so adding an optional
field cannot leave `normalize()` behind. `percent` is deliberately excluded —
the macros read it as `skill.get('percent')` so that "unset" and "0%" stay
distinguishable, and defaulting it would erase that.

**Bug 2 hid behind a misleading message.** `doRender` treated every non-422 as
a parse failure and its catch reported *"Could not reach the preview service"*
— so a 500 pointed at the network. That is why this survived eleven sessions
of hand-testing. It now distinguishes a server error from an unreachable one.

**New tests.** `tests/test_partial_entries.py` (100, fast loop, no browser —
`document_html()` is plain Python): 49 × half-filled entry, 49 × name-and-title
only, plus one test asserting the blanks really are schema-derived and one that
defaulting never clobbers a supplied value (an explicit `percent: 0` included).
`tests/e2e/test_form_feedback.py` (4): the rejected photo, a good photo after a
rejected one, the full add-a-role journey, and the download menu.

All four e2e tests mutation-checked, all four load-bearing:

| Mutation | Caught by |
|---|---|
| `normalize()` reverted | 100 fast tests + the add-a-role journey |
| photo handler back to catch-and-ignore | rejected-photo, good-photo-after |
| `e.stopPropagation()` dropped from `#dl-toggle` | download menu |

Suite is **333** (200 fast + 133 browser). The 35 non-`slow` browser tests ran
3× back to back, 35/35 each time, no flakes. Sources restored and `diff`-verified
after every mutation; `data/resume.json` / `data/meta.json` still 2026-08-28/30.

### DONE — session 14: the same bug class, chased through both exporters
Session 13's defects shared a shape: **data a user can really produce, rendered
into a claim they never made.** Rather than stop at the HTML preview, this
session followed that shape into the DOCX exporter and the skill graphics.

**Defect 3 — a stray blank line in Word.** The Word masters guarded every
*separator* in the company/location/dates line but not the line itself, so the
role-only entry from session 13 rendered an **empty paragraph** — a blank line
in Word where the HTML drops the row outright, wasting vertical space in a
master tuned to fit exactly one page. Fixed with a `{%p if %}` around the whole
meta paragraph. That is safe *here* specifically: the zero-paragraph trap
recorded in session 5 applies to **table cells**, which must keep at least one
paragraph; this one is in the document body.

**Defect 4 — every skill graphic asserted "zero" for an unrated skill.** A
skill with no level word and no explicit percent has nothing to draw. Each
renderer drew something anyway:

| Renderer | What it drew for an unrated skill |
|---|---|
| `skill_dotrow` + 8 inline copies | five empty circles — "0 of 5" |
| `skill_bar` / `skill_slider` + inline copies | a 0%-filled track, knob pinned left |
| `skill_ring` | a literal **"0%"** printed inside the ring |
| Word masters | `"Ceramics —    "` — a dangling em-dash |

All of it colour and shape making a claim with no text beside it, which is
precisely what CLAUDE.md's standing rule forbids. `dots_for()` already had the
right answer (session 5: an unmapped level renders text only); the rest of the
renderers now follow it — unrated ⇒ **name as text, no graphic**.

**The fix is wider than it first looked.** 15 of the 49 templates inline their
own skill markup instead of calling the shared macros, so fixing the 4 macros
left 15 still violating. All 15 are fixed (8 dot-grid, 7 bar/ring). The 9 ATS
layouts that print only name-and-level **text** were already correct — an empty
text span asserts nothing, and treating that as a fail was an error in the
first cut of the test.

**Proof the 19 edited files changed nothing else:** all 49 templates were
rendered with the standard sample before and after and compared
whitespace-normalised — **identical, every one**. So the change is provably
confined to the unrated case. The 98-test auto-fit height gate agrees.

**Brief-compliance pass** (CLAUDE.md requires one after any template edit) —
only the deltas:
- Gate 2 "every skill's level is real selectable text, not only a bar/ring/dot
  fill" — **was FAIL, now pass**.
- Gate 2 "no information conveyed by colour alone" — **was FAIL, now pass**.
- Gate 3 "empty-value degrade path defined for each optional field" — **was
  FAIL for `skills.level`, now pass**.
- Gate 1 "keep everything else as it is" — pass, evidenced by the 49-template
  normalised diff above.
- Gate 3 "repeating units are true siblings" — pass, and worth stating since it
  is a judgement call: an unrated skill renders a *different* structure to a
  rated one. That is a **data-driven degrade path**, the same shape as the
  `{%p if photo %}` guard and the stat-chip rule, not a specially-styled entry.

Suite is **445** (312 fast + 133 browser); 35 non-`slow` browser tests 3× green.
Both Word masters re-verified over COM: **open, fit one page.**

### DONE — session 15: the last two candidates, one real
Session 14 left two named candidates. Both were checked; one was already
correct, the other was the same defect in a third place.

**`summary_highlight` — already correct, now pinned.** All three templates that
draw the marker swipe (`ats-t4`, `ats-t10`, `modern-t2`) already guard with
`r.summary_highlight in r.summary`. Without that guard
`r.summary.split(highlight, 1)[1]` raises IndexError — a 500 — the moment the
user edits the summary and leaves the phrase behind. It never regressed, but
nothing held it: a test now does, and dropping the guard on `ats-t4` fails it.
The other 46 templates ignore `summary_highlight` entirely, so a phrase that no
longer matches is a silent no-op there by design.

**Defect 5 — a half-filled social link.** `label` and `url` are both
schema-required, so a *fresh* entry is invalid until the user types in both
fields — but **clearing one afterwards is valid** and reaches the renderers.
Nothing guarded it, in two shapes:

| Shape | Layouts | What an empty label produced |
|---|---|---|
| `bits.append(s.label)` into a joined list | 29 | `"… \| wrenashworth.example.com \| "` — a dangling separator |
| caption + value divs | 8 | a bold **blank caption** floating above the URL |

The first is the `"Ceramics —"` bug again; the second is the stat-chip rule
inverted. Every other contact field was already guarded (`{% if c.phone %}`);
the social loop was the one that was not. Fixed in 37 templates plus
`_macros.j2::contact_lines`, both halves guarded so a label-without-URL cannot
leave a caption over nothing either. `docx.py::_contact_line` was **already
correct** — it filters blanks before joining.

Two layouts are right for their own reasons and were left alone: `ats-t3` shows
`s.url or s.label`, and `modern-t21` slices `bits[:4]`, so the fifth entry never
renders.

**Proof the 37 edited templates changed nothing else:** all 49 rendered with two
*complete* social links before and after, whitespace-normalised — **identical,
every one**.

**The detector was wrong twice before it was right**, which is worth recording:
1. First cut subtracted the supplied value from the rendered text and compared.
   Reads well, but a separator legitimately belongs to a value that IS present,
   so it failed 25 correct templates.
2. Second cut looked for `[|·•]` before a closing tag — and missed the 6
   layouts that join with `"<br>"`, where the artefact is a trailing line break
   rather than a stray pipe. The mutation check is what exposed that: reverting
   the guards failed 21 of 29, not 28.
   Both artefacts are now measured as a **delta** against a résumé with no
   social link, so a layout is never blamed for markup it already had.

Suite is **641** (508 fast + 133 browser); 35 non-`slow` browser tests 3× green.
Templates restored and `diff -r`-verified identical after the mutation.

**⚠ The fast loop is now ~8.8s, up from 3.5s in session 12.** Each half-filled-
data contract sweeps all 49 templates, and there are now four of them. It is
still fast enough to run on every edit; if it keeps growing, give the catalogue
sweeps their own marker rather than thinning them — they caught four of the six
defects found in sessions 13–15.

### DONE — session 16: the upload gate trusted the file name
A `/e2e` continuation pass. The baseline suite was re-run and confirmed green
the documented way — **629 passed, 12 skipped, and the summary line checked for
`error`**, per session 11b's warning that pytest exits 0 with setup errors
present. Then the interactive surface was audited against the browser suite,
which turned up one live defect.

**Defect 6 — `/api/photo` 500'd on files a user really picks.** The handler
gated on `file.mimetype`, and **that is the browser's guess from the file
extension, not a reading of the bytes**. So the gate only ever caught someone
who picked a file with an honest extension. Two ordinary shapes walked through:

| What the user did | What reached Pillow | What they saw |
|---|---|---|
| renamed a document to `.png` (browser sends `image/png`) | `UnidentifiedImageError` | **500** |
| picked a half-copied photo (valid header) | `open()` succeeds, `crop()` raises "image file is truncated" | **500** |

Measured before the fix: text-as-png, empty file, 2-byte jpeg, pdf-as-png and a
truncated PNG — **all five 500**. The builder rendered that as "error 500",
which is this project's signature failure: **an error message naming the wrong
layer**, the same shape as `doRender`'s "Could not reach the preview service"
that hid a 500 on all 49 templates for eleven sessions.

- `img.load()` forces the decode inside the handler, so the failure happens
  where it can still be explained. Opening without decoding is *not* enough —
  the truncated case is exactly the one that survives `Image.open()`.
- The two cases get **different advice**: "not a photo — use a PNG, JPEG or
  WebP" is useless to someone whose file already *is* a PNG, just an incomplete
  one, so that one says "damaged or incomplete". A test pins that they differ.
- The reason travels as **JSON** (`_reject_photo`), because only the server read
  the bytes. `builder.js` shows it verbatim and keeps the status-code wording
  only as a fallback for a failure upstream of the handler. The old client
  hard-coded 415 → "not a photo", which is why it could not have told the two
  apart even with the server fixed.
- The mimetype gate stays — it rejects without reading the file at all.

**Why the existing test could not catch it.** `test_a_rejected_photo_says_why`
(session 13) sends `mimeType: "text/plain"` — which is what makes it stop at
the mimetype gate. A real browser never sends that for a file named `.png`. The
new browser tests send it the way the browser really does: image extension,
image mimetype, non-image bytes.

**Mutation-checked, both halves separately** — the fixes are a matched pair, so
each was reverted alone:

| Mutation | Caught by |
|---|---|
| server fix reverted | 9 of 10 fast tests; all 4 photo browser tests |
| client fix reverted (server fix in place) | the damaged-photo test alone — it was told "not a photo", the wrong advice |

Both sources `diff`-verified identical to their backups afterwards.

**A line-ending trap worth recording.** `app/routes.py` is **LF** while
`app/schema.py`, `builder.js` and most of `tests/` are **CRLF** — this repo is
genuinely mixed, per file. `pathlib.write_text()` on Windows translates `\n` to `\r\n`,
so rewriting an LF file through Python flips **every line** and buries a
6-line change in a 500-line diff. Check `count(b"\r\n")` before and after
any scripted edit here, and match the file's own ending rather than the repo's.

10 fast tests (`tests/test_photo_upload.py`) + 2 browser
(`tests/e2e/test_form_feedback.py`). Suite is **653** (518 fast + 135 browser);
the 37 non-`slow` browser tests ran 3× back to back, 37/37 each time, no flakes.
`data/resume.json` and `data/meta.json` still carry their 2026-08-28/30 stamps.
No template was edited, so CLAUDE.md's brief-compliance pass is not triggered.

### DONE — session 16b: the drawer's silent switch (the last named candidate)
Session 16 left two candidates listed. Both were worked; **one was a real bug,
the other was already correct and is now proven so rather than assumed.**

**Defect 7 — a failed template switch said nothing at all.** `buildDrawer`'s
click handler ended a failure with a bare `if (!res.ok) return;`, and had **no
catch around the `await fetch` at all**. So:

| What went wrong | What the user saw |
|---|---|
| server answers non-OK | drawer stays open, layout unchanged, **no message** |
| connection dropped (the local Flask server is one Ctrl-C away) | same, plus an unhandled rejection in the console |

A failed switch was indistinguishable from clicking the template already
selected. This is the one builder action with **no feedback path of its own** —
the form has `#form-errors`, exports alert, saving has the indicator — and it
is worse than it looks, because `.drawer-scrim` covers `#form-errors` while the
drawer is open, so the obvious place to report it is not even visible from
there. The drawer now carries its own `#drawer-error` line
(`builder.html`, `.drawer .drawer-error` in `app.css`), cleared on reopen and
on a successful switch. The drawer deliberately **stays open** on failure so
the click can be retried.

**Written test-first**, and the three tests failed the right way before the fix.
One detail worth keeping: the `page` fixture's own "no uncaught JS errors"
assertion independently caught the missing catch as
`AssertionError: uncaught JS error(s): Failed to fetch` — a *teardown error*
rather than a test failure, which is exactly the shape session 11b warned reads
as green if you only look at the `N passed` count.

Mutation-checked as two separable halves, since the fix has two branches:

| Mutation | Caught by |
|---|---|
| `catch` made silent (fetch rejects) | the unreachable-server test alone |
| `!ok` branch back to a bare `return` | the failed-switch and error-clears tests |

**Not a bug: the export failure path.** `download()`'s `alert()` on a non-OK
export was the second candidate, and it turned out to be correctly implemented
*and* already covered by `test_a_failing_export_surfaces_instead_of_silently_
doing_nothing` (session 13). Rather than take the passing test at face value it
was mutation-checked too — silencing the `!ok` branch fails it — so the
coverage is real, not incidental. Nothing was changed there.

Suite is **656** (518 fast + 138 browser); the 40 non-`slow` browser tests ran
3× back to back, 40/40 each time, no flakes. `builder.js` is +49 lines across
sessions 16 and 16b and nothing else in it changed; line endings verified
unchanged on all four edited files (`builder.js` CRLF, `builder.html`,
`app.css`, `routes.py` LF). No template was edited, so CLAUDE.md's
brief-compliance pass is not triggered.

## Porting notes that recur (apply to every template)

- **ATS-safe invariants for `t16`–`t25`** (from the source file comment):
  single linear column; **canonical single-word headings only** — no
  combined/invented labels like "Tools & Languages"; label tracking ≤ 1.2px;
  every skill row `name — Level` with a real em-dash as selectable text;
  plain-hyphen date ranges. So Tools and Languages each get their own
  single-word section, pushing section count to ~8 and forcing tighter section
  spacing (gaps ~10–15, occasional leading trims) to fit the shared sample.
  Earlier ATS ports (`t1`–`t15`) were freer — several fold the trailing
  optional data into one combined-label block instead.
- **The shared sample forces compression.** One `data/sample_resume.json`
  (creative lead, 3 roles, 5 skills, + tools/langs/2 certs) is tuned to
  `modern-t1`. Low-density Modern layouts overflow it, so nearly every Modern
  port tightens section/column gaps from the reference values (logged per file
  header). Unresolved: per-template calibrated samples, or auto-fit scaling.
- **Absolute-positioned references** (`modern-t7`, `t8`, `t11`, `t14`, `t15`,
  `t18`, `t21`): `t8` needed a full re-flow into flex columns (its px offsets
  can't hold variable content); the others keep the absolute frame but compress
  the panel gaps and are verified by panel-measurement + screenshot, not `.tpl`
  scrollHeight. `t18`/`t21` fixed-height cards can clip trailing content under
  much heavier user data.
- Optional data with no home in a reference: fold into an existing section, add
  a small trailing block, or (ATS `t16`+) give it its own canonical section.
  `r.references` renders only when non-empty. `r.photo_url` wired on every
  template that has a photo slot.

### DONE — session 17: bilingual AR/EN, phases 0-2 (English proven unchanged)

New requirement, arriving after feature-complete: the app must serve Arabic and
English users, RTL and LTR, without breaking anything already working. An
8-phase plan is in play; **phases 0, 1 and 2 are done, phases 3-8 are not
started.**

**What the audit found** (before any code was written):

- **Zero Arabic glyph coverage.** All 11 self-hosted families are Latin-only,
  and the PDF path inlines only those — so Arabic would have fallen back to
  whatever the host machine had, or tofu on a clean container.
- **218 `letter-spacing` + 143 `text-transform:uppercase`, across all 50 files.**
  Letter-spacing breaks Arabic's cursive joining; uppercase is a no-op in a
  script with no case. Between them they carry most of the heading hierarchy,
  so Arabic headings would go flat, not merely different.
- **~350 hardcoded English labels** in ~40 spellings (`Experience` /
  `EXPERIENCE` / `Work Experience` / `PROFESSIONAL EXPERIENCE` / `ABOUT ME`).
- **Physical CSS throughout** — 68 `padding-left`, ~52 absolutely-positioned
  `left:`, 19 `text-align:right`, 15 `border-left`.
- **`skills[].level` is both display text and the `LEVEL_DOTS` key**, so an
  Arabic level word would have scored 0 dots and silently dropped the graphic.

**Phase 0 — the regression harness** (`tests/golden/`, `tools/golden.py`).
Two deliberately independent gates, because the later phases break them at
different moments:

- `tests/test_golden_html.py` — the exact canvas fragment per template, over
  two scenarios (`sample`, and a `sparse` one with every optional section
  empty). 99 tests, ~1.6s, runs in the default loop.
- `tests/test_golden_pixels.py` — the rendered 850x1100 canvas. 50 tests, ~46s,
  opt-in via `--e2e`. Deliberately NOT under `tests/e2e/`, whose autouse
  `clean_state` fixture boots a Flask server this gate does not need.

Both were **mutation-checked, not trusted**: a 4px padding change injected into
`modern-t2` produced a precise one-line HTML diff and 40,043 differing pixels
with a bounding box on the experience timeline, then was reverted. That is ~3
orders of magnitude above the 50-pixel tolerance, so the gate is not marginal.

**Phase 1 — `lang`, additive.** `lang` is an OPTIONAL schema enum (`en`/`ar`);
absent means English, so every résumé written before this still validates and
renders identically — **no migration of any stored file.** `normalize()` derives
`r.lang` / `r.dir`; `document_html()` emits `<html lang dir>`. Arabic level words
were ADDED to `LEVEL_DOTS` alongside the English ones rather than replacing
them, which is the other half of why no stored data has to move.

**Phase 2 — Arabic fonts, via aliasing** (`tools/fetch_fonts_ar.py`).
`tools/fetch_fonts.py` is deliberately UNTOUCHED and never re-run: rebuilding
`fonts.css` from what Google serves today could silently re-hint the Latin faces
under every existing résumé. The new tool only reads it.

The mechanism that avoids editing 49 templates: each Arabic `@font-face` is
declared under the **Latin family's own name**, confined by `unicode-range` to
Arabic codepoints. Browsers resolve `font-family` per GLYPH, so
`font-family: Archivo` — already in every template — keeps taking Latin from
Archivo and starts taking Arabic from Tajawal. Pairing preserves register
(geometric->geometric, serif->naskh, display->Kufi), with a weight override for
Anton, whose nominal 400 reads black and so maps to Noto Kufi 900.

40 alias rules over 13 files (573 KB), 5 sources (Cairo, Tajawal, Amiri, Noto
Kufi Arabic, IBM Plex Sans Arabic), all 5 OFL texts vendored. Loaded only for
`lang="ar"`: an English PDF document stays 1368 KB, Arabic is 3521 KB.

**The safety property, asserted rather than assumed**: no alias may declare a
`unicode-range` below U+0600. If one did, it could outrank the real Latin face
and change English. Enforced in both `tools/fetch_fonts_ar.py --check` and
`tests/test_fonts_ar.py::test_no_alias_claims_a_latin_codepoint`.

**One pre-existing test was fixed, not worked around.**
`test_inline_css_embeds_each_file_exactly_once` counted every `.woff2` in the
fonts directory, so it failed the moment 13 Arabic files landed beside the
Latin ones. It now counts the files `fonts.css` actually references — which is
the contract its name claims. The Latin inline copy still embeds each Latin
file exactly once; that was never violated.

**Gate results after every phase: English is byte-identical and pixel-identical.**
All 50 pixel goldens passed unchanged after Phase 1 and again after Phase 2.

**A pre-existing defect found and deliberately NOT fixed** (fixing it would
change English output, which phases 0-2 promised not to do): `builder.js` offers
`Native / Fluent / Conversational / Basic` in the SAME `LEVELS` list used for
skills, but `LEVEL_DOTS` maps none of them. A skill set to "Fluent" is not
"unrated" by the macros' test (`{% if not skill.level %}`), so it renders a dot
row with **zero of five filled** — a graphic asserting "none" beside the word
"Fluent". This is the exact failure `exporters/docx.py::_dot_glyphs` already
guards against in Word ("a graphic flatly contradicting the text beside it"), so
the HTML path contradicts the DOCX path today. No template routes `r.languages`
into a graphic macro, so it is reachable only via a skill — but it IS reachable
from the UI. **Fix it as its own change, with its own golden regeneration**,
not folded into a phase.

### DONE — session 18: bilingual phase 3 (labels), and the pixel gate that was never running

**Phase 3 is complete: every fixed label in the 49 templates now goes through
`t()`, and English is byte-identical.** Phases 4-8 remain, in the same order.

**The design, and why English cannot drift.** `app/labels.py` keys the
catalogue by the ENGLISH STRING ITSELF — `t('Work Experience')` returns
`'Work Experience'` verbatim when the document is English. There is no English
table that could be wrong, so the "character-identical" requirement is a
property of the design rather than of 80 hand-checked mappings. Arabic lookup
folds case and whitespace, which collapses the templates' ~40 casing variants
(`SKILLS` / `Skills` / `skills`) onto ~55 Arabic rows. An untranslated msgid
renders English and never raises — coverage is a TEST failure, not a render
failure, per the same rule that produced `normalize()`'s degrade paths.

**A ContextVar, not `@pass_context`.** `t()` reads the language from a
ContextVar set by `canvas_html()`. The obvious alternative — reading `r.lang`
out of the Jinja context — works in a template and NOT in a macro: every
template does `{% import "_macros.j2" as m %}` *without* `with context`, so an
imported macro gets a fresh context where `r` does not exist. That version
would have returned English inside any macro, silently. The binding is released
in a `finally`, or one template raising would leave every later render in that
thread Arabic.

**Four passes, because labels are written four different ways.** A single scan
would have missed three-quarters of them:

| Pass | Shape | Sites |
|---|---|---|
| 1 | plain text nodes — `<div>Experience</div>` | 262 |
| 2 | macro ARGUMENTS — `{{ dh("Experience") }}`, how 15 ATS templates write theirs | 116 |
| 3 | COMPOSED headings — a list joined at render time | 13 |
| 4 | value prefixes, photo placeholders, `ribbon()`, conditionals | 20 |

Pass 1 alone left 15 ATS templates completely untouched and looked finished.

**`join_labels()`, because the punctuation is language-dependent too.** Three
ATS templates build a trailing heading from whichever optional sections exist
("Certifications, Tools & Languages"). Translating only the WORDS leaves
`الشهادات, الأدوات & اللغات` — half in the wrong script. The conjunction is
passed in because the templates genuinely differ: `ats/t4` writes "and" where
`ats/t12` and `ats/t14` write "&", and both had to survive verbatim.

**A landmine found on the way: 15 sites shadowed the new `t`.** Five macro
parameters (`{% macro head(t) %}`) and seven `{% for t in r.tools %}` loops
rebind `t` to a string, so `t('Tools')` in that scope raises "str object is not
callable". `ats/t5.j2` already had a label and a shadowing loop **on the same
line** and survived only because the label happened to sit before the loop
opened — any later edit would have tripped it. All renamed to `label` / `tool`;
a test now forbids the pattern.

**One thing deliberately NOT done.** `modern/t22.j2` spells "RESUME" as six
separately-kerned `<span>` letters on a rotated rail. Arabic is cursive, so six
isolated glyphs are not a word: this needs a layout change, which is phase 5,
not a string swap. It is the ONLY exclusion in the miss-detector, so anything
else that scan finds is a real miss.

**Proof, in three layers.** The golden HTML gate stayed byte-identical
throughout (99 tests). But byte-identity only proves what a baseline actually
draws, and **neither golden scenario sets `education[].gpa`** — so the
`GPA <value>` prefix in 32 templates rendered in NEITHER, and the gate was
identical across a line it never drew. Same blind spot for the composed
headings: `sample` has all three optional sections and `sparse` has none, so
the separator and conjunction never appeared. So:

1. a one-off differential — all 49 templates × 12 scenarios rendered with the
   pre-edit templates and the current ones: **588 renders, byte-for-byte
   identical**;
2. `gpa` and `partial` added to `tools/golden.py` as permanent scenarios.
   Regeneration was checked to have ADDED two directories and changed nothing
   in `sample` or `sparse` — a regeneration that quietly launders a change is
   the trap `tests/golden/README.md` warns about;
3. the scenario list, which was declared in BOTH `tools/golden.py` and
   `tests/test_golden_html.py`, now lives once and is imported — a scenario
   added to the generator would previously never have been asserted.

**`tests/test_labels.py` (62 tests), all ten mutations caught:**

| Mutation | Caught by |
|---|---|
| a routed label put back as hardcoded text | the miss detector |
| a helper-argument label put back as a bare literal | the miss detector |
| an Arabic catalogue row deleted | coverage |
| a row holding the English string as its "Arabic" | the differs-from-English test |
| `t` shadowed again by a tools loop | the shadow guard |
| `t()` translating in English too | 159 golden tests + the identity test |
| `canvas_html()` no longer resetting the language | the reset test |
| `join_labels()` using English punctuation in Arabic | the punctuation test |
| `t()` no longer returning Markup for the `<br>` labels | the markup test |
| the GPA prefix put back as hardcoded text | the GPA test + goldens |

The reset test **was wrong first and passed vacuously**: it used an unknown
template key, and `_template_path()` raises BEFORE `set_lang()` is called, so
it never entered the `try` at all — it passed with the `finally` deleted. It
now makes `normalize()` raise, which happens inside it.

**Defect 8 — the pixel gate has never run in the documented command.** Found by
running `pytest --e2e` the documented way. `tests/e2e/conftest.py` holds a
session-scoped `sync_playwright()` open for the whole run, and
`tests/test_golden_pixels.py` opened its own; the second entry in one thread
raises "Playwright Sync API inside the asyncio loop". So:

- `pytest --e2e tests/test_golden_pixels.py` → **50 passed**
- `pytest --e2e` (the documented full command) → **all 50 error at setup**

and because setup errors are not failures, the summary read `935 passed, 12
skipped, 49 errors` and pytest **exited 0** — the exact trap session 11b
recorded. The pixel gate is the only proof that English APPEARANCE does not
move, and phases 4-5 (RTL typography, layout mirroring) rest entirely on it.
It has been absent from that command since it was written in session 17, which
is why "all 50 pixel goldens passed" in that session's notes: the file was run
alone.

Fixed with ONE session-scoped `_playwright` fixture in `tests/conftest.py`,
shared by both gates. `tests/test_suite_invariants.py` guards it **in the fast
loop** — a gate that stops running is a failure that shows up as green, so the
slow opt-in suite is the wrong place to catch it. The guard parses with `ast`
rather than grepping: three files discuss `sync_playwright` in prose, and the
regex version flagged its own docstring.

**Numbers.** Fast loop **798** (was 636; +98 golden, +62 labels, +2
invariants), ~9s. Full `--e2e`: **986 passed, 12 skipped, 0 errors, 0 failures**
— against 935 passed + 49 errors before the fixture fix. The browser-affected
tests (`tests/e2e/` + the pixel gate) were run 3× back to back with no flakes.
Line endings verified unchanged on all 50 templates (45 CRLF / 7 LF, per-file).
`data/resume.json` and `data/meta.json` untouched (2026-09-06).

**Brief-compliance pass** (CLAUDE.md requires one after any template edit) —
only the deltas: **no delta.** All 49 templates were edited, and the 588-render
differential plus the 99 golden HTML tests show every rendered byte unchanged
for English, so no checklist row can have moved. The Arabic side is not yet a
deliverable — labels are translated but layout is not mirrored (phase 5), so
the templates are not yet claimed to comply in Arabic.

**Not done, and out of phase 3 by the plan:** the app shell (`base/landing/
gallery/builder.html`, `builder.js`'s `SPEC`) is phase 6, and the Word masters'
English headings are phase 7. Both still print English regardless of `lang`.

### DONE — session 19: bilingual phase 4 (RTL typography) — and the plan's premise was wrong

**Phase 4 is complete, and it is a fraction of what the plan described.** The
plan called for a `[dir="rtl"]` stylesheet killing `letter-spacing` and
`text-transform` document-wide, then rebuilding Arabic heading hierarchy across
the catalogue. **Both purges were measured, found to fix nothing and to cause
harm, and were dropped.** What shipped is a targeted heading rescue for four
templates.

**Measurement 1 — `letter-spacing` does not damage Arabic in Chromium.** The
audit's premise was that it "breaks Arabic's cursive joining". Rendering the
same string at several tracking values and reading back the width says
otherwise. At `letter-spacing:2.5px`, across Archivo, Montserrat, Poppins,
Anton and Merriweather:

| text | length | gaps that got spaced |
|---|---|---|
| Arabic, one word (`المهارات`) | 8 | **0.00** |
| Arabic, two words | 14 | **1.00** (the word space only) |
| Latin (`WORK EXPERIENCE`) | 15 | **15.0** (every gap) |

Blink applies tracking to **zero** gaps inside a joined Arabic run — including
across the non-joining letters within a word. So the purge could not have
improved a single Arabic glyph.

**Measurement 2 — the purge actively breaks a masthead.** Neutralising tracking
makes text *wider*, and **all 42 negative-tracking declarations in the catalogue
are display type, 23px–64px**. Removing `-1px` from `modern-t10`'s name widened
it just enough to wrap onto a second line: **+38.7px**, traced to that exact
element by diffing every bounding box with the rule on and off. There is no CSS
discriminator between label tracking and display tracking — 23 of those 42 also
carry `text-transform:uppercase`, so "reset tracking on uppercase elements"
targets precisely the mastheads that wrap. `text-transform` is likewise a no-op
on a script with no case, and those same mastheads carry it deliberately.

A rule that fixes nothing measurable and breaks a masthead should not ship.

**The real defect, which the plan under-described.** An English heading carries
three cues — size, weight, and small-caps-with-tracking. In Arabic the third is
worth nothing (no case, and no tracking per above), so a heading that leant on
it flattens into body text. Nothing raises; the résumé just stops being
scannable.

**Phase 3 is what made this measurable.** A section heading is now exactly the
output of `t()`, so it can be identified by its catalogue string. Every heading
in all 49 templates was measured against its own body text:

- **45 templates** carry hierarchy anyway — by size (up to 2.6× body), by weight
  700–900, or by a rule/fill behind the heading. **Left alone.**
- **`ats-t13`, `ats-t19`, `ats-t21`, `ats-t23`** — heading size ≈ body
  (ratio 1.00–1.04), weight 600, no rule, no fill. Only colour survived.

**The first probe was wrong, and a render caught it.** Its first cut took the
median over every element carrying `text-transform:uppercase` — a set dominated
by small tracked *captions* (stat-chip labels, date kickers) that are supposed
to be small. It reported 34 templates "at risk" and rated `modern-t17` 0.72
"FLAT" when the render shows its headings reading perfectly. **Two static
diagnostics in this session were overturned by looking at the actual output.**

**The fix.** A `sec-head` class on the heading element of those four, and an
RTL-only stylesheet:

```css
[dir="rtl"] .tpl .sec-head { font-size: 14px !important; font-weight: 700 !important; }
```

- Emitted by `document_html()` **only when `dir="rtl"`**, the same shape as the
  Arabic font sheet — an English document never carries the rules at all, which
  is belt to the selector's braces.
- `14px`, not the 14.5px first tried: both read as headings (ratio 1.17 vs 1.21,
  and 1.17 is what `ats-t1` already uses), but 14.5px left `ats-t23` — the
  tightest of the four — with **10px** of the page to spare against **18px** at
  14px.
- `ats-t13` was the odd one: it has no `text-transform:uppercase` anywhere, its
  headings being a mono blue `{{ ML }}` label used for headings and nothing
  else, so all 7 were marked directly.

**Result: all four go from ratio 1.00–1.04 / weight 600 to 1.17 / weight 700,
and no template in the catalogue now lacks a heading cue in Arabic.** Confirmed
on the render, not only in the numbers.

**English is provably untouched.**
- The **pixel gate stayed at 50/50** — the class is inert in LTR and the
  stylesheet is not emitted for LTR, which is the whole safety argument.
- The **HTML gate moved for exactly 12 files** — 4 templates × the 3 scenarios
  that render headings — and every added line differs only by
  `class="sec-head"`. Regenerated deliberately; `diff -rq` confirms nothing else
  in the 196 baselines moved.
- This is the split `tests/golden/README.md` describes: an HTML-only move is a
  markup change, and only a change to BOTH baselines would mean English output
  had moved.

**A number worth carrying forward: the Arabic page is tighter than the English
one.** Ink-bottom across all 49 with the Arabic sample — `natural` is useless
here, it floors at 1100 on a non-clipping fixed-height `.tpl` — gives a median
headroom of **75px**, but `modern-t7` has **7.1px** and 12 templates sit under
40px. Phase 5's mirroring has very little vertical room to spend on those.

**8 tests (`tests/test_rtl_typography.py`), 7/7 mutations caught:**

| Mutation | Caught by |
|---|---|
| stylesheet emitted for every document, not just rtl | the dir-scoping test |
| stylesheet never emitted | 5 of the 8 |
| a selector no longer `[dir="rtl"]`-scoped | the scoping test |
| rescue size dropped to 12px | the browser ratio test (all 4) |
| rescue weight dropped to 600 | the browser ratio test (all 4) |
| one heading loses its marker class | the browser test's unmarked-heading check |
| `sec-head` added to an unmeasured template | the only-the-four test |

The browser test asserts on the **rendered page**, not on the CSS text, because
the rule only works if `!important` really beats the template's inline
`font-size` — that is the entire mechanism, and it would fail silently if the
selector or the injection stopped matching. It also asserts that *no* section
heading in those four renders without the class, since three of them emit the
heading from a macro (the class appears once in the file and eight times in the
output, so counting source occurrences proves nothing).

**Numbers.** Fast loop **802** (was 798), ~9s. Full `--e2e`: **994 passed, 12
skipped, 0 errors, 0 failures**. Line endings unchanged on all 50 templates and
`rendering.py`. `data/resume.json` / `data/meta.json` untouched.

**Brief-compliance pass** (CLAUDE.md, template edits) — deltas only: four
templates gained a `class` attribute and nothing else; the 12-file golden diff
is the evidence. No palette, type pairing, skill pattern or section order
changed, and the pixel gate proves the English render is identical. The Arabic
render is still not a finished deliverable — layout is not mirrored (phase 5).

**Still English regardless of `lang`, by plan:** the app shell (phase 6) and the
Word masters (phase 7).

### DONE — session 20: bilingual phase 5 (layout mirroring)

**All 49 templates now mirror. Zero unmirrored decorations, and the pixel gate
never moved.** Phase 5 was billed as "the only real template work"; almost all
of it turned out to be mechanical, and the hand-work reduced to one element.

**The audit, which set the scope precisely.** `dir="rtl"` already mirrors normal
inline flow and flex row order. What it cannot touch is anything named
left/right:

| category | count | files | treatment |
|---|---|---|---|
| `padding-left` / `margin-*` / `border-*` / `text-align:right` | 116 | 49 | direct logical rename |
| asymmetric 4-value `padding:` | 25 | 11 | split to `padding-block` + `padding-inline` |
| `left:` / `right:` on positioned decorations | 66 | 15 (all `modern/`) | `inset-inline-*` |
| `transform`, gradients, shadows | 2 | 2 | no logical form; by hand |
| symmetric 2/3-value `padding:`/`margin:` | 196 | — | already mirror; untouched |

The ATS family has **no** absolute positioning at all, which is why those
templates already read correctly before this phase.

**Stage A and most of stage B were both mechanical, and the pixel gate is why
that is safe.** In an LTR document `padding-inline-start` *is* `padding-left` —
the same used value, not an approximation — so 202 conversions across all 50
files must be invisible to English. **The pixel gate stayed at 50/50 through
every step.** The HTML gate moved for 164 of 197 baselines, which is the
expected half of the split `tests/golden/README.md` describes: a move in BOTH
would have meant English output changed.

**The plan expected the absolute offsets to be hand-work. They were not.**
`inset-inline-start` handles a negative offset correctly by construction: in
RTL it maps to `right`, so `inset-inline-start:-31px` puts a timeline dot 31px
beyond the right edge exactly as it sat 31px beyond the left edge in English.
That one rename fixed 65 of the 66.

**Verification was geometric, not visual.** Rendering the same résumé LTR and
RTL and comparing where each positioned element landed — a mirrored element's
centre must sit at `canvasWidth - centre_ltr` — found **71 unmirrored elements
across 16 templates** after stage A, and **0** after the inset conversion plus
the one hand fix. Eyeballing 15 templates would not have been trustworthy;
`modern-t2`'s stranded timeline dots were 545px out, but several panels were
subtler.

**The one real hand fix: `modern-t22`'s rotated rail.** Its box mirrored, and it
still landed at x=-388, because **`transform` has no logical form** —
`translate(-50%)` still moves left and `rotate(-90deg)` still turns the same
way. Mirroring a transform means negating it, which only a direction-scoped
rule can do, so it went into the phase-4 RTL stylesheet as `.vrail`.

The rail also had to stop being **six separately-kerned Latin letters**
(`R`,`E`,`S`,`U`,`M`,`E`) — the one exclusion recorded in phase 3, because
Arabic is cursive and six isolated glyphs are not a word. The template now emits
a single span carrying `t('RESUME')` for RTL and the untouched Latin branch
otherwise, so **English HTML for this template changed only by the class
attribute**. Two further tunings, both measured rather than guessed: 214px suits
six Latin caps but the Arabic term is two words whose ascenders overflow the
215px rail (140px fits), and `justify-content:flex-start` suits a word that
nearly fills the 1043.5px track while the Arabic runs ~700px, so it is centred.

**Every HTML baseline change was accounted for before regenerating.** Rather
than regenerate and hope, each new render was normalised back to the old
spelling and compared: **192 of 196 matched byte-for-byte**, and the only four
that did not were `modern-t22`, differing solely by `class="vrail"`. That is the
discipline `tests/golden/README.md` asks for — a regeneration that quietly
launders an unrelated change is the trap.

**4 tests (`tests/test_rtl_mirroring.py`), 5/5 mutations caught:**

| Mutation | Caught by |
|---|---|
| a `padding-left` comes back | the physical-property guard |
| an absolute offset reverts to `left:` | the guard **and** the geometric test |
| `text-align:end` reverts to `right` | the text-align guard |
| a 4-value shorthand comes back | the shorthand guard |
| the rail's RTL transform override removed | the geometric test |

Three guards are static and run in the **fast loop**, because a physical
property added later mirrors wrongly and nothing raises — the page just renders
with a panel on the wrong side. The geometric test is `slow`-marked (~79s: it
renders 49 templates twice).

**Centres, not left edges.** The geometric test compares centres because one
decoration legitimately changes width between languages — the rail is six Latin
letters at 214px in English and one Arabic word at 140px in Arabic. Its centre
still mirrors exactly, and a stranded element moves a centre just as far as an
edge.

**Numbers.** Fast loop **805** (was 802), ~10s. Full `--e2e`: **998 passed, 12
skipped, 0 errors, 0 failures**. Line endings unchanged on all 50 templates.
`data/resume.json` / `data/meta.json` untouched.

**Brief-compliance pass** (CLAUDE.md, template edits — all 50 files touched):
deltas only. No palette, type pairing, skill pattern or section order changed;
the pixel gate proves the English render is byte-identical in appearance, and
the normalised-diff check proves every markup change is a property rename plus
one class attribute. Skill graphics still carry name and level as real text
(the dot rows fill from the right in RTL, which is correct reading order).

**Still English regardless of `lang`:** the app shell (phase 6) and the Word
masters (phase 7). Phase 8 is the cross-cutting test pass, including the
mixed-content bidi case.

### DONE — session 21: bilingual phase 6 (app shell)

**The interface is now bilingual too.** Landing, gallery and builder all render
in Arabic, mirrored, with a language switcher in the header.

**Two languages, deliberately independent** (`app/i18n.py`):

| | source | question it answers |
|---|---|---|
| document | `resume["lang"]` | what language is the RÉSUMÉ written in? |
| interface | the `ui_lang` cookie | what language does this PERSON read? |

Editing an English résumé from an Arabic interface is an ordinary case — a
bilingual user applying to an English-speaking employer — so tying them
together would be wrong. That independence was one of the four assumptions
recorded when the plan was written, and it is now enforced by a test rather
than by intention: the builder page carries an Arabic UI and English level
words at the same time.

**Where that distinction actually bites: the level dropdown.** Whatever the
user picks is STORED in `skills[].level` and printed on the résumé, so those
lists follow the DOCUMENT's language. Had they followed the reader's, an Arabic
UI would have dropped an Arabic level word into an English résumé.

**A defect closed on the way** (recorded in session 17, left open then):
`builder.js` offered skill and LANGUAGE levels as one list of eight, so a skill
could be set to "Fluent" — a word `LEVEL_DOTS` does not map, and which is not
"unrated" either, so the macros drew a five-dot row with **zero filled** beside
it. `SKILL_LEVELS` and `LANGUAGE_LEVELS` are now separate lists, per language,
and a test asserts every offered skill word maps to a dot count. This makes the
defect **unreachable from the UI**; a résumé already stored that way is
untouched, and the renderer half of that note remains open.

**The catalogue is shared, on purpose.** `ui_t()` falls through to the document
catalogue, because the builder's section headings ARE the résumé's section
headings — a person should not see one word in the form and a different one on
the page. 143 shell-only strings plus the 70 document ones.

**English is character-identical**, by the same property phase 3 used: the msgid
IS the English string. Verified by rendering all three pages with the pre-phase
templates and diffing — landing and gallery came back **byte-identical**, and
the builder differs only by the four deliberate additions (`dir` on `<html>`,
the switcher, the i18n payload, and the back-arrow span).

**Two escaping bugs found by that diff, both mine:**
1. `&amp;` came out **double-escaped** — the msgid must be the UNESCAPED text so
   autoescape restores the entity. Exactly the lesson phase 3 recorded, which I
   applied there and not here.
2. Apostrophes became `&#39;`. `ui_t` now returns Markup carrying **text-node
   escaping only** — `&`, `<`, `>` and `"`, leaving the apostrophe alone. Safe
   because it is only ever applied to a string that IS in the catalogue, i.e.
   one this project wrote.

**A bug that only a screenshot caught.** The builder's *Basics* section
translated while *Contact* stayed English. `ui_catalogue()` was keyed by each
source's own casing — `_UI_AR` holds `"Full name"` as written, `_AR` holds
`"contact"` folded — so a table built from either alone silently missed half its
entries. The table is now keyed by the folded msgid and `T()` folds before
looking up. **Three of the six defects in this session were invisible in the
tests and obvious in the render.**

**Mirroring the shell** cost 18 declarations in `app.css` (all logical now) plus
three things a logical property cannot express:
- the drawer slides with `translateX(100%)`, which does not mirror — it is
  pinned with `inset-inline-end`, so in RTL it sits on the LEFT and needed
  `translateX(-100%)`;
- the back arrow `←`, now its own element flipped with `scaleX(-1)`;
- `.sr-only`, which **did not exist** — the switcher's label would have been
  visible in the header. Caught by reading the render, not the tests.

**Also renamed: `{% for t in ... %}`** in gallery.html and landing.html. `t` is
now the translate function in the shell environment, so those loops would have
shadowed it — the same landmine phase 3 found in 15 résumé templates.

**Security note.** `/lang/<code>` accepts a `next` target and only follows it if
it is a path on this app. An open redirect is worth refusing even in a local
single-user tool, because the habit is what carries into a deployed one — and a
payment page is on the roadmap.

**17 tests (`tests/test_ui_language.py`), 8/8 mutations caught:**

| Mutation | Caught by |
|---|---|
| level list follows the reader instead of the résumé | the independence test |
| a language level leaks back into the skill list | the dot-count test |
| the shipped table reverts to exact-cased keys | the client-fold test |
| an unknown cookie value is trusted | the fallback test |
| the open-redirect guard removed | both redirect tests |
| `dir` no longer emitted on `<html>` | all three page tests |
| a physical `margin-left` returns to app.css | the logical-CSS guard |
| an Arabic catalogue row deleted | the coverage test |

**A line-ending slip, caught and fixed.** `read_text` + `write_text(newline="")`
flipped base.html from CRLF to LF — session 16's trap, in the shape it warns
about. Restored; all four shell templates verified against their originals
(base CRLF, the other three LF).

**Numbers.** Fast loop **822** (was 805), ~11s. Full `--e2e`: **1015 passed, 12
skipped, 0 errors, 0 failures**. No template or résumé rendering changed, so
neither golden gate moved. `data/resume.json` / `data/meta.json` untouched.

**Left for phase 7:** the Word masters still print English headings whatever
`lang` says. Phase 8 is the cross-cutting test pass, including the mixed-content
bidi case.

### DONE — session 22: bilingual phase 7 (DOCX RTL)

**The Word export is bilingual. Four masters now: one per (category,
direction).** With this, nothing in the app is English-only regardless of
`lang`.

**`dir="rtl"` buys nothing in Word.** A .docx is right-to-left only if the XML
says so, in FOUR separate places — and saying only the obvious one produces a
document that opens, fits one page, passes a structural test, and still lays
its Arabic out left-to-right:

| element | where | what it does |
|---|---|---|
| `w:bidi` | `w:sectPr` | the section reads right-to-left |
| `w:bidi` | `w:pPr` | the paragraph does, so its default alignment flips |
| `w:rtl` | `w:rPr` | the RUN does — without it glyphs still run left-to-right inside a right-aligned paragraph |
| `w:rFonts/@w:cs`, `w:szCs`, `w:bCs` | `w:rPr` | Arabic is a COMPLEX SCRIPT: Word takes face, size and weight from the `cs` attributes, not `ascii`/`hAnsi` |

Plus `w:bidiVisual` on the stat-chip table. **Each of the five was
mutation-checked separately and each is load-bearing.**

**Applied as a POST-PASS** (`_apply_rtl`), not a flag threaded through twenty
primitives: it touches every paragraph, run and table by construction, so a
component added later cannot be left half-mirrored — which would be one
English-aligned paragraph nobody notices.

**Schema order, again.** Every new element had to be inserted before its
successors, the trap session 6 spent itself on. `tests/test_docx_validity.py`
already globs the masters directory and its `SEQUENCES` table already knew
where `bidi`, `rtl`, `bCs`, `szCs` and `bidiVisual` belong, so the 18 existing
order tests validated the new masters the moment they existed. **One gap closed
while here: `w:sectPr` was not in that table**, and it is now — that is exactly
where the section-level `w:bidi` goes.

**Georgia has no Arabic glyphs at all**, so the Arabic Modern master takes Times
New Roman — the serif Word guarantees. Left alone, Word would substitute a face
of its own choosing: the same silent substitution the HTML side solved by
self-hosting fonts.

**Headings come from the shared catalogue.** The builder imports `app.labels`
and calls `t()` under `set_lang(lang)`, so a Word heading and its on-screen
counterpart cannot drift apart. 13 heading literals routed.

**English is provably untouched.** The two English masters rebuild
**byte-identical inside the package** (all 17 parts compared, not the zip
bytes, which carry timestamps). A test also asserts they contain none of
`w:bidi`, `w:rtl` or `w:bidiVisual`.

**A missing RTL master RAISES rather than falling back.** The fallback would
hand an Arabic résumé a left-to-right Word file with English headings — output
that is wrong rather than absent, which is the failure shape this project keeps
finding. The route turns it into a 501 that says what is missing.

**Verified in real Word, twice over.** `--verify` opens all four masters: open,
fit one page. But the masters carry Jinja tags and almost no content, and
docxtpl rewrites that XML at request time — **the file a user downloads is not
the file that was verified**. So the rendered exports were opened too (English
and Arabic × both masters): all four open, spill 0 pages, correct reading order.

**The probe was wrong before the document was.** The first check read
`Section.PageSetup.Bidi` and reported every Arabic export as left-to-right.
**`PageSetup` has no `Bidi` property** — reading it over COM yields `$null`, so
the check could only ever say "LTR". `Paragraph.Format.ReadingOrder` is the real
signal, and its constants are inverted from the obvious guess:
**wdReadingOrderRtl = 0, wdReadingOrderLtr = 1**. Recorded in
`word_masters/README.md`; a future session will otherwise re-derive it.

**17 tests (`tests/test_docx_rtl.py`), 8/8 mutations caught:**

| Mutation | Caught by |
|---|---|
| `w:rtl` dropped from every run | 4 tests |
| `w:bidi` dropped from every paragraph | the per-paragraph marking test |
| complex-script font not set | the four-places test |
| table `bidiVisual` dropped | the four-places test |
| `w:bidi` appended to `sectPr` instead of ordered | the schema-order gate |
| Georgia left in the Arabic master | the font test |
| headings not translated | the Arabic-headings test |
| an Arabic résumé falls back to the English master | 7 tests |

Because the masters are BUILT rather than stored as source, each mutation had to
edit the builder, rebuild, run, then restore and rebuild again — the English
masters were confirmed byte-identical afterwards.

**Numbers.** Fast loop **851** (was 822), ~11s. Full `--e2e`: **1044 passed, 12
skipped, 0 errors, 0 failures**. No HTML template or résumé rendering changed,
so neither golden gate moved. `data/resume.json` / `data/meta.json` untouched.

**Left for phase 8** — the last one: both directions through the existing
suites, an Arabic e2e journey, and the MIXED-content case (Arabic prose carrying
English company names) for the bidi-isolation trap. Worth noting the Arabic
sample already exercises a little of this — its contact line renders
`wren.ashworth@examplemail.com | 555-0138-64 | بورتسايد` — and nothing yet
asserts how those neutrals order.

### DONE — session 23: bilingual phase 8 (tests) — the plan's premise was wrong again

**The bilingual feature is COMPLETE. All 8 phases done.** Phase 8 was the
cross-cutting test pass: both directions through the existing suites, an Arabic
browser journey, and the mixed-content bidi case.

**The mixed-content trap is NOT sprung, and no isolation was added.** The plan
assumed an Arabic résumé naming `Halden & Row` would need `<bdi>` (or
`unicode-bidi: isolate`) around every user field, and that the fix would be
markup in all 50 files. Measured, it is not needed:

| what was measured | result |
|---|---|
| Chromium, all 49 templates, Arabic doc + Latin employers | **0 findings** |
| Chromium, all 49, English doc + Arabic employers | **0 findings** |
| Chromium, all 49, plain Arabic (the probe's own baseline) | **0 findings** |
| real Word, `ats-t1`, per character via `Information(5)` | `Halden & Row,` advances **152.65 → 204.70pt** — a clean left-to-right island inside a right-to-left paragraph |

Same shape as session 19: the phase's premise did not survive measurement, so
the fix was dropped rather than shipped. Isolation is not free — `<bdi>` pins a
field to its own first strong character, which changes how an all-neutral field
(a bare phone number, a date range) resolves. `tests/test_bidi_mixed.py` is
therefore a **gate on the behaviour the algorithm already gives us**, not a fix.

**Three wrong measurements were made before the right one.** Worth recording,
because each looked convincing and each would have produced a "fix" for nothing:

1. **"In RTL the earlier field must be drawn further right."** Reports **33 of
   49** templates broken. All false: an LTR island inside an RTL line is READ
   left-to-right, so two fields that both resolve LTR are correctly drawn
   earlier-on-the-left. This is the check that makes the contact line look
   scrambled when it is not.
2. **"A field drawn in more than one rect is torn."** Reports **49 of 49**. A
   mixed-direction string legitimately produces one rect per directional run.
3. **`Word.Range.Information(5)` on the FIRST word or character of a
   paragraph** returns the PARAGRAPH's start position, not the word's — in an
   RTL paragraph that is the right margin, so `H` in `Halden` reported 203.85pt
   while `a` reported 152.65. Read alone it says the run is reversed. Skip the
   first character. (Cousin of the session-22 finding that `PageSetup.Bidi`
   does not exist.)

What survived is only what is unambiguous whichever way a reader scans the
line: a field's glyphs stay **contiguous**, two inline elements do not
**overlap**, a separator stays **between** the pair it separates, and a Latin
run reads left-to-right while an Arabic run reads right-to-left.

**Both directions through the existing suites** — `tests/samples.py` is the new
shared vocabulary (`ENGLISH`, `ARABIC`, `BOTH`, `MIXED`, `REVERSED`). The
suites that have historically found this project's real defects now sweep the
catalogue twice:

| suite | was | now |
|---|---|---|
| `test_smoke.py` | 49 | 49 × 2 |
| `test_partial_entries.py` | ~160 | 310 |
| `test_partial_contact.py` | 98 | 270 |
| `test_unrated_skill.py` | ~151 | 208 |

The English half of every pair carries **no `lang` key**, so the
absent-means-English promise is now under test in four more places.

**One assertion was narrower than its contract, and Arabic found it.**
`test_a_rated_skill_is_untouched_everywhere` asserted the level WORD appears;
that failed 12 templates in Arabic. Not a defect: the skill macros print
`percent` INSTEAD of the word, and **the two shipped samples differ** —
`data/sample_resume.json` sets no `percent` at all, `data/sample_resume_ar.json`
sets one on every skill. The assertion now accepts either, in
`test_unrated_skill.py` and in `test_smoke.py`, which had the same gap.

**A route-level Arabic export test leaked into the shared store.**
`/export/*` reads the SAVED résumé — there is no way to hand it data — so
testing the Arabic master through the route means writing one, and the whole
session shares one `RESUMECRAFT_DATA_DIR`. Without a restore it left an Arabic
résumé behind and `test_ui_language.py::test_interface_language_does_not_touch_the_document`
failed in the full run while passing alone. `test_smoke.py::stored_resume`
snapshots and restores the file. **Any future route-level test that writes the
store needs the same fixture.**

**`tests/e2e/test_journey_ar.py`, 13 tests** — the Arabic journey. A separate
file rather than a `lang` parameter on `test_journey.py`: what differs is not
the strings but the SHAPE — `dir` on the shell, `dir` inside the preview
iframe, and a language switcher that must move one without the other. It covers
the round trip (including an `&` through JSON → autosave → schema → autoescape
→ form value), the drawer, both downloads from the real menu, and the level
dropdown in both pairings.

**The builder has NO language switcher.** `builder.html` overrides
`{% block chrome %}` with an empty block, so the header — and the switcher with
it — does not exist on the page where a person actually spends their time; the
interface language can only be changed from the landing page or the gallery.
Found while writing the journey. Not fixed (it is a design question, not a
defect), but the test now asserts the switcher is absent there, so the day it
appears the test says so rather than silently passing.

**Numbers.** Fast loop **1396** (was 851), ~18s. Full `--e2e`: **1712 passed,
24 skipped, 0 errors, 0 failures**, 8m43s (was 1044 / ~290s). No app, template
or exporter code changed in this session — only tests — so neither golden gate
moved: `test_golden_html` 197/197 and `test_golden_pixels` **50/50**, the
latter confirmed present in the junit output rather than assumed (session 18's
lesson).

### DONE — session 23b: the Arabic gallery was blank, and looking at it is what found that

**Found by RUNNING the app in Arabic, minutes after declaring the bilingual
feature complete and gated.** 1712 tests were green. None of them looked at
where a pixel landed in the app SHELL.

**Every surface where a person chooses a template was empty in Arabic.** The
landing hero, all 49 gallery cards, and the drawer minis. Measured:

| surface | LTR visible | RTL visible |
|---|---|---|
| landing hero card | 100% | **0%** |
| gallery thumbnail | 98% | **0%** |
| drawer mini | 98% | **0%** |
| builder preview stage | 99% | 99% ✅ |

**The cause is the session-20 lesson, one layer up.** Those three surfaces
shrink a full 850×1100 résumé iframe with `transform: scale()`, and
`transform-origin: top left` is a PHYSICAL corner. In RTL the iframe's layout
box hangs leftward from the right edge of its clipping box, so scaling toward
the iframe's own top-left parks the render hundreds of pixels outside the
`overflow: hidden` window — gallery thumbnail: box `[959,1225]`, drawn at
`[375,647]`.

`transform` has no logical form. `app.css` already KNEW that — it carries a
`[dir="rtl"]` override for the drawer's `translateX` under a comment reading
"the two things a logical property cannot express". There were four. Fixed with
the same shape:

```css
[dir="rtl"] .hero-card iframe,
[dir="rtl"] .tpl-thumb iframe,
[dir="rtl"] .drawer-item .mini iframe { transform-origin: top right; }
```

**The builder's own `#preview-stage` was never affected** — its origin is
`top center`, and a centred origin is direction-agnostic. That is why the
preview rendered perfectly in the Arabic builder while the gallery did not, and
it is why the fix is the ORIGIN and not the scale.

**Why 1712 tests missed it.** Each gate stops one step short:

- `test_rtl_mirroring.py` scans the résumé `.j2` files and renders `.tpl`
  canvases. `app.css` is not a résumé template and the shell is not an
  850×1100 canvas.
- the golden HTML and pixel gates only cover the résumé canvas.
- `test_journey_ar.py::test_the_gallery_previews_an_arabic_resume` asserts on
  the `/preview` RESPONSE BODY — which was correct all along. All 49 iframes
  loaded, each with its `.tpl` in the DOM. Nothing raised, nothing 500'd,
  nothing was missing. **The pixels were simply somewhere else.**

The signature failure shape again, so the new gate is deliberately geometric:
not "did it load" but "is it ON SCREEN".

**`tests/e2e/test_shell_rtl_geometry.py`, 12 tests, mutation-checked.** With the
CSS fix removed it fails 6/12 — exactly the three broken surfaces × both tests
— while the never-broken preview stage stays green. It asserts the horizontal
overlap only: every one of these surfaces clips VERTICALLY on purpose (a 1100px
page at .32 is 352px in a 340px box, and the preview pane scrolls, which sat at
82% in English and Arabic alike). The first cut asserted vertical too and
flagged a scrollbar as a bidi defect.

**The lesson to carry:** the bilingual gates were all built around the résumé
document, because that is where the hard problems were. The SHELL got static
guards (no physical properties in `app.css`) and string coverage, but nothing
geometric. `transform` slips through a static guard by construction — it is not
a directional property, it is a directional *value*.

**Still open, found in the same look and NOT fixed:** the builder's form fields
inherit the interface direction, so an English résumé edited in an Arabic UI
shows its sentences right-aligned with the full stop at the wrong end
(`.designers, four launches, one set of rules everyone can follow`). The fix is
`dir="auto"` on the generated inputs and textareas in `builder.js`, so each
field takes direction from its own content — which is what a bilingual builder
wants regardless of the interface. Left as a decision rather than done.

**A note on driving the real app:** `run.py` serves the REAL `data/` dir, so
clicking a template in the drawer rewrites the user's `data/meta.json`. It did
(ats-t1 → modern-t11) and was restored from the screenshots taken beforehand.
`data/resume.json` was never touched. Drive the real server read-only, or point
it at a throwaway `RESUMECRAFT_DATA_DIR`.

### DONE — session 23c: the showcase previews follow the reader

**Asked for as "duplicate all 49 templates in Arabic". That was not needed and
was not done.** The templates have not been English-only since phase 3 —
`ats-t1` and `modern-t11` were rendered with `data/sample_resume_ar.json` and
came out fully Arabic: translated headings, mirrored layout, sidebar on the
right, Arabic level words. What was English was the RÉSUMÉ being previewed.

`/preview` rendered `load_resume()` — the user's own document — and **four
surfaces share that one route**. So an Arabic visitor on the landing page saw
English résumés in every card: the app advertising a product it does not sell.

**The split, which is the whole change:**

| surface | renders | why |
|---|---|---|
| landing hero cards | the SHOWCASE sample, in the **interface** language | it demonstrates a layout |
| gallery résumé cards | the SHOWCASE sample, in the **interface** language | same |
| builder live preview | `load_resume()` | you are editing YOUR document |
| template drawer minis | `load_resume()` | you are picking a layout for YOUR content |

`/preview?showcase=1` is the switch; `store.load_showcase(lang)` is the loader;
`config.SAMPLE_RESUME_PATHS` maps `en`/`ar` to the two samples. `landing.html`
and `gallery.html` pass the flag, the builder never does.

**The coupling to avoid, and the test that forbids it.** The showcase reads
`i18n.current_lang()` — the cookie — never `resume["lang"]`. Reading the
document's language would look correct in every case where the two agree and
would undo the independence `app/i18n.py` exists for. The sharp case is an
**Arabic document read through an English interface**: the cards must be
English. That is its own test.

**The sample is cached as TEXT, not as a parsed dict.** A gallery page issues
one `/preview` per card — ~49 reads per load — and handing every caller the
same dict would let one mutate the copy the next 48 receive. Re-parsing 3KB is
cheaper than that class of bug.

**`tests/test_showcase_language.py`, 16 tests, 4/4 mutations caught** — and the
fourth caught a vacuous test of my own first:

| mutation | caught |
|---|---|
| cache hands out a shared dict | ✅ |
| showcase reads `resume["lang"]` instead of the cookie | ✅ |
| the gallery stops passing `showcase=1` | ✅ |
| the BUILDER starts passing it | ❌ first cut → ✅ after fix |

**The builder guard was scanning a file that could not fail.** It looked for
`url_for('main.preview', …)` in `builder.html`, but the builder does not write
its preview URLs in Jinja: it ships a bare `previewBase` and **builder.js**
appends the query string (`${EP.previewBase}?template_key=${t.key}` for the
drawer minis). The guard now asserts the word `showcase` appears in neither
`builder.html` nor `builder.js`, and the mutation on the line that can actually
change is caught.

**One existing test was rewritten, not repaired.**
`test_journey_ar.py::test_the_gallery_previews_an_arabic_resume` asserted the
old contract — that the cards show the USER's résumé. That contract was
deliberately inverted, so the test now asserts the new one, and a second test
was added for the English-interface/Arabic-document case.

**Numbers.** Fast loop **1412** (was 1396), ~18s. Full `--e2e` on the final
tree: **1741 passed, 24 skipped, 0 errors, 0 failures**, 10m02s — junit
confirms `test_golden_pixels` **50** and `test_golden_html` **197** actually
ran, so English output did not move. That also closes the verification left
open by 23b's CSS fix.

**Left alone deliberately:** the drawer minis inside the builder. They are the
same "pick a template" job as the gallery, so there is an argument for making
them follow the interface too — but they sit in the builder, where every other
pixel is the user's own document, and stock content there would be a lie about
whose CV you are looking at. Say so if that judgement should go the other way.

### DONE — session 24: the builder can set the document's language (Next action #6)

**The last English-only assumption in the product, and it was a UI gap, not an
engine gap.** `resume["lang"]` drives `dir`, the label catalogue, the Arabic
font sheet and which of the four Word masters the export takes. Every layer
beneath it has been bilingual since phase 7. It was reachable **only by
hand-editing `data/resume.json`** — so the user who typed `احمد صالح` into the
builder on 2026-09-08 got a résumé that rendered `dir="ltr"` with English
section headings under Arabic content, and had no way to say otherwise.

**What shipped:** one control in Basics — `Résumé language`, a two-option
select (`English` / `العربية`, autonyms, so they are not in the catalogue) —
writing `resume.lang` through the same autosave every other field uses.

**It reads the FILE, never the cookie.** That is the whole risk in this change.
Wiring it to `ui_lang` would look correct in every case where the two agree,
which is most of them, and would undo the independence `app/i18n.py` exists
for. The sharp case is the one the app is for: a bilingual user applying to an
English-speaking employer from an Arabic interface. Both directions are tested,
and `ui_lang` / `document.cookie` are now forbidden in builder.js by a static
guard that strips comments first — the file discusses `ui_lang` in prose four
times, so a naive `not in` guard could never have failed.

**The level words are re-offered without a reload.** The dropdowns are built in
the browser from a table the page ships, so `/builder` now sends
`levels_by_lang` (both vocabularies) alongside `levels` (the document's).
`SKILL_LEVELS` / `LANGUAGE_LEVELS` in builder.js became mutable **copies** that
`applyLevelVocab()` swaps in place — SPEC holds a live reference to them, so
swapping the contents updates every dropdown on the next re-render, and copying
keeps the payload's own arrays intact for the switch back.

**The remap is OFFERED, not applied.** Changing the language asks once —
`Translate the level words already chosen? 7 (Expert → خبير)` — and rewrites
only on OK. Declining leaves a working résumé: `LEVEL_DOTS` maps both
vocabularies, so an English `Expert` in an Arabic document still draws five
dots, it just reads in Latin. That is a legible state for a bilingual user to
choose, and rewriting user content that gets PRINTED is not something to do on
their behalf.

**The remap is positional, and nothing in the data structure enforced that.**
`Expert` is `SKILL_LEVELS["en"][0]`, so it becomes `SKILL_LEVELS["ar"][0]`.
Reordering either list would silently regrade every stored level with no error
anywhere. Three fast tests now pin it: same length, index-aligned **by dot
count** (not by position alone), and ordered strongest-first in both languages.

**The two decisions the last session left open, both settled:**

- *Re-map stored level words?* Yes, but as an offer — above.
- *Default `lang` from the interface language on a new résumé?* **No.** A "new"
  résumé here is `store.load_resume()` seeding from `data/sample_resume.json`,
  whose content is English. Stamping `lang: "ar"` on English sample text would
  produce a worse first render than the current absent-means-English degrade.
  Making it coherent would mean seeding from `sample_resume_ar.json` instead —
  a different, larger change that would move what every existing test starts
  from. Absent-means-English stays; the control makes it explicit.

**Numbers.** Fast loop **1425** (was 1412), ~17s. Full `--e2e`: **1763 passed,
24 skipped, 0 errors, 0 failures**, 9m58s — junit confirms `test_golden_pixels`
**50** and `test_golden_html` **197** actually ran, so English output did not
move. (Read `N passed` with the summary line, not alone: pytest exits 0 with
setup errors present.)

**Tests: 22 new, 5/5 mutations caught.**

| mutation | caught by |
|---|---|
| the control reads `ui_lang` instead of the file | 3 tests, both layers |
| the remap is applied whatever the user answers | `test_declining_the_offer_leaves_the_words_alone` |
| the dropdowns never re-offer the new vocabulary | `test_the_dropdowns_re_offer_the_new_language_without_a_reload` |
| the Arabic skill vocabulary is reordered | the two alignment tests, in the fast loop |
| `docLang` is never advanced (2nd switch remaps from the wrong source) | `test_the_switch_is_reversible` |

`tests/test_document_language.py` (13, fast) is the payload, the vocabularies
and the static guards. `tests/e2e/test_language_control.py` (9, `--e2e`) is the
half only a browser can answer — the form is generated by builder.js, the remap
happens in memory and reaches disk only through autosave, which is exactly how
`lang` came to be unsettable in a schema-valid, fully-tested app.

⚠ **Basename collision.** The e2e file is `test_language_control.py`, not
`test_document_language.py`, because `tests/` has no `__init__.py`: two test
modules with the same basename abort collection with an import-mismatch error
the moment both are collected. It passed when each ran alone.

**Eyeballed, not just asserted.** Switched a live builder to Arabic and looked
at it: headings translate (التواصل / القدرات / الخبرة / التقدير), the canvas
mirrors, the level words sit beside their dots in Arabic. One thing to expect
rather than fix — a document marked Arabic whose CONTENT is still English
renders its English lines right-aligned with trailing punctuation on the left.
That is the bidi algorithm doing its job, and it resolves as the user types
Arabic; `tests/test_bidi_mixed.py` gates the drawn behaviour.

### DONE — session 25: the horizontal axis (the untried angle, and it paid)

RESUME_HERE named this as the one angle never looked at: **auto-fit handles
vertical overflow; nothing has ever tested horizontal behaviour, and several
layouts use fixed px column widths.** It was worth asking.

**Why the two axes are not the same problem.** Too-tall content is *loud* —
auto-fit compresses, reports `fitted: false` when it cannot, and the builder
raises a banner the user can act on. Too-wide content is *silent*: it is
painted outside the 850px canvas, and the PDF page IS the canvas, so it is
simply absent from the export. Nothing throws. The résumé looks right on screen
while the email address on it has lost its last nine characters. Same shape as
every other defect this project has found — see the "silent failures all have
the same shape" note from session 13.

**`tools/verify_overflow.py`** renders all 49 in Chromium and reports three
outcomes, not one:

| outcome | meaning | verdict |
|---|---|---|
| `outside` | painted beyond the canvas → absent from the PDF | **fails** |
| `clipped` | cut by an ancestor's overflow, no ellipsis | **fails** |
| `ellipsised` | cut with a `…` the reader can see | **allowed** |

That third row is the distinction the whole audit turns on. `modern-t21`'s
contact pill ellipsises a long email deliberately; a reader who can SEE text
was cut can go and shorten it. Counting it as a defect pushes you to break a
46px fixed-height pill to seat a 74-character address.

**One real defect, fixed: `modern-t12`.** `white-space: nowrap` on the headline
meant it could never wrap, so an ordinary 50-character job title ran **39px
off the canvas in English and 65px in Arabic**, and the canvas is
`overflow:hidden`. Replaced with `text-align:end` and allowed to wrap. The four
HTML goldens moved; **all 50 pixel goldens held** — markup changed, appearance
did not, which is exactly the case `tests/golden/README.md` says may be
refreshed rather than explained.

#### Two instrument errors, both caught by running the SHIPPED sample as a control

This is the part worth carrying forward. The first two versions of the scan
reported the résumé this project ships as broken.

1. **`Range.getClientRects()` is not transform-aware in Chromium.**
   `modern-t22`'s rotated "RESUME" rail: the element's own box is 153px wide
   (67..220), a Range over the same glyph returns 233px (27..260) — the
   UNROTATED run, in a frame nothing is painted in. Inside a transformed
   subtree the scan now uses the parent element's rect instead.
2. **A Range reports the full run even where an ancestor clips it.**
   `modern-t21`'s pill ellipsises the email at 670px and the Range still
   returned 869px — "19px outside an 850px canvas" where the glyphs stop well
   inside it. The rect is now intersected with every clipping ancestor
   *between* the text and the canvas (the canvas itself excluded, or the check
   could never fire, since most templates set `overflow:hidden` on `.tpl`).

**I chased error 2 into a fix before catching it**, adding `min-width:0` to
t21's contact spans with a comment claiming it made the ellipsis work. It did
nothing: `min-width:auto` already resolves to 0 for a flex item whose overflow
is not `visible`. Measured identical both ways (`span_client` 294,
`span_scroll` 492, ellipsis rendering) and reverted. **`modern-t21` was never
broken.**

#### The global fix that was tried, measured, and dropped

An unbroken 120-character token overflows **all 49** templates. The obvious fix
is one inherited rule on the canvas. Both halves were tried and both were
dropped, for reasons the pixel gate supplied rather than reasons I assumed:

- `overflow-wrap: break-word` — 49 → 22 still losing text, and it **moved
  `modern-t2`**: the narrow sidebar level column began breaking `Expert` into
  `Expe`/`rt`, `Advanced` into `Adva`/`nced`. It turned invisible spill into
  visibly broken words on a résumé that was fine.
- `+ min-width: 0` — 22 → 9, and moved `modern-t2`'s sidebar by **31,148
  pixels**.

Changing how 49 shipped layouts render is not a fair price for an input nobody
types. The behaviour is pinned by `test_the_scan_can_fail` instead, which
asserts the token still overflows — so the gate cannot go vacuously green, and
if a future change ever does absorb an unbreakable token the test says so.

**A third finding, measured and deliberately left alone.** `modern-t2`'s level
words (`Advanced`, `Proficient`) spill their own element box by ~19px on the
SHIPPED sample. Not loss: the navy panel behind them runs to 298 and the text
stops at 289, so it stays on its own background, legible. Fixing it would move
English pixels to correct something no one can see. It is also the reason
`break-word` was harmful — that column is where the breaking happened.

**The gate.** `tests/e2e/test_overflow_gate.py` — 99 tests (49 templates × 2
languages on the `wide` sample, plus the can-fail control), `slow` + `e2e`,
~80s. Mutation-checked: restoring t12's `nowrap` fails it in **both**
languages.

**Numbers.** Fast loop unchanged at **1425** (the gate is opt-in; skips 362 ->
461). Full `--e2e` **1862 passed, 24 skipped, 0 errors, 0 failures**, 11m09s —
junit confirms `test_golden_pixels` **50**, `test_golden_html` **197**,
`test_overflow_gate` **99** and `test_autofit_gate` **98** all actually ran.

## Next actions (in order)

1. ~~Shared-sample strategy~~ — **resolved in session 9** (auto-fit; per-template
   samples dropped for the reason above). Nothing outstanding.
2. **PWA** — manifest + service worker. Unblocked (fonts are local now), but
   **low value while the app is single-user and server-rendered**: previews and
   both exports need the Flask server running, so an offline shell could not do
   anything. Worth building only if this gets deployed publicly for phone
   install. Deliberately deferred 2026-08-30.
3. ~~Photo~~ — **fully done** (session 8).
4. ~~`TYPE_FLOOR` decision~~ — **resolved in session 11**: 0.90 is intentional
   and stays; the docs were corrected to it (BUILD.md had been missed in session
   10). Recovery is 48/49, `modern-t17` seats at 1092.5, `modern-t18` warns.
   **There are no open decisions left in the project.**

5. **Payment gateway page** — raised by the user 2026-09-07, for "later", no
   scope given yet. **Not started, and nothing has been designed for it.**
   Recording it here because it invalidates a standing assumption rather than
   just adding a screen: this app is single-user, local-only, HTTP on
   127.0.0.1, with `data/resume.json` as the whole store and **no accounts and
   no auth anywhere**. A payment page needs, at minimum, deployment, accounts,
   HTTPS, and a decision about what is actually being sold per user (templates?
   exports? a subscription?) — that last one is a product question that has to
   be answered before any of the technical work means anything.
   **STAGE 1 BUILT 2026-09-10** — the app is now deployable to more than one
   person. Browser-owned résumé (`localStorage`) with the server as a pure
   render-and-export service; `RESUMECRAFT_SERVER_STORE=0` for deployment;
   exports POST the document; rate limiting + a cap on concurrent Chromium
   renders; the 13 `| safe` sites fixed; PWA. Full suite green. Four new test
   files: `test_escaping`, `test_limits`, `test_stateless`, `test_pwa`, plus
   `e2e/test_browser_store`. See BUILD.md's Store, Rate limits, Escaping and
   PWA rows. **Still open before a public URL: accounts do not exist**, which
   is fine until something is sold and is the first item of Stage 3.

   **Answered 2026-09-10 — see `MONETIZATION.md`.** Researched MENA-first:
   templates and PDF stay free, the paid line is the bilingual `.docx` export
   plus multi-résumé storage, sold as a **non-renewing time-boxed pass** rather
   than an auto-renewing subscription. That file also carries the free/paid
   boundary, the rails decision (it branches on where you incorporate), and the
   security gate below — including a verified stored-XSS finding.
   Two knock-ons worth knowing now:
   - it **revives the PWA** (item 2 above), which was deferred *because* the
     app is local-only and single-user;
   - it makes `/api/*` and `/export/*` a public surface. They have never been
     threat-modelled — there is no authz, no rate limiting, and `/api/photo`
     accepts uploads. Do that review before anything is exposed, not after.
   Do NOT interleave this with the bilingual phases: phases 4-5 rewrite layout
   in all 49 templates and the pixel gate is the only thing holding English
   still. Land bilingual, then start payments as its own track.

6. ~~**The builder cannot set the document's language**~~ — **DONE, session
   24.** One control in Basics (`Résumé language`) now writes `resume.lang`,
   reading the FILE and never the `ui_lang` cookie. Both open decisions were
   settled: the level-word remap is OFFERED on the switch (declining leaves a
   working résumé — `LEVEL_DOTS` maps both vocabularies), and `lang` is NOT
   defaulted from the interface language, because a new résumé seeds from the
   ENGLISH sample and stamping `lang: "ar"` on English text would render worse
   than absent-means-English does. 22 tests, 5/5 mutations caught.
   **There are no open decisions left in the project.**

**The app is feature complete and browser-tested.** The only remaining build
item (PWA) is deferred by choice. The OFL caveat is closed — every family's
`OFL.txt` ships in `app/static/fonts/licenses/`.

If a future port cannot be made to fit the shared sample, note that auto-fit is
NOT the fix: the sample row is a regression gate — `verify_autofit.py` and now
`tests/e2e/test_autofit_gate.py` both fail the moment a port needs compression
to seat the standard content.

### DONE — session 26: AI assistant Phase 1 (`app/assist.py`, `/api/assist`)

Phase 1 of `AI_ASSISTANT_PLAN.md` §5. **Ships one job — EN ⟷ AR adaptation —
because that one carries all the quality risk**; the other four are the same
endpoint with a different prompt and are Phase 3.

- `app/assist.py` — model/effort/caching per §4, streaming, the injectable
  `client` the tests use, and the entitlement gate.
- `POST /api/assist` — SSE (`thinking` / `delta` / `done` / `error` frames),
  its own `assist` bucket in `app/limits.py` (15/min, the only endpoint here
  that costs MONEY rather than CPU).
- `anthropic>=1.5` in requirements. **Optional at runtime** — with no key the
  route answers 503 and nothing else in the app changes. That is how it ships
  until Stage 3.
- 28 tests, all offline. Fast loop **1609 -> 1637**, 0 errors.

**Three design decisions worth not re-litigating:**

1. **The route pulls the FIRST chunk before building the Response.** A
   generator is lazy, so handing Flask the raw one would answer `200
   text/event-stream` and only then discover the request was a 402 — this
   project's signature failure, where the status names one layer and the truth
   is another. Mutation-checked: the naive version fails 2 tests.
2. **`done` carries usage counters and never text.** The privacy claim in
   `AI_ASSISTANT_PLAN.md` §3 is true by construction and stays true only while
   nothing logs the body. The mid-stream error frame deliberately does NOT
   echo the exception, because an exception can carry the request.
3. **`has_ai_access()` returns True and is CALLED.** Stage 3 changes one
   return. The test asserts a `False` answer stops the request *before* the
   provider is billed, not that the constant is `True`.

**10 mutations applied, 10 caught** — and two of them initially reported
MISSED for instrument reasons, not test reasons: one pattern half-applied
(silently a no-op) and one produced a SyntaxError that pytest reported as `10
errors` alongside `18 passed`. **Both looked like a passing mutant.** The
mutation loop now proves the mutant IMPORTS before believing any result from
it. This is the same lesson as session 25's `verify_overflow` instrument
errors, in a new tool — see the closing note of this file.

**Not done, deliberately:** no UI. There is no button, no consent dialog and no
toggle — those are Phase 4, and the consent copy must not ship before the
Phase 2 Arabic gate says the feature is worth consenting to.

### DONE — session 26: Stage 3 Phase 1 — accounts and sessions

`app/db.py` (SQLite), `app/auth.py`, three `/account/*` routes, one template,
44 tests. **Anonymous use is unchanged**, which is the property most easily
lost here and the one `test_anonymous_*` exists to hold: no account is needed
for any template, any PDF, either language or the builder.

- **Schema**: `users` with `session_version` and `pass_expires_at`. That last
  column is unused until Phase 2 and is there on purpose — a column that
  arrives with the feature needing it is a migration; one already there is an
  UPDATE.
- **Sessions**: cookie carries `uid` + `session_version`; the version is
  re-read from the database every request, so a password change evicts
  sessions elsewhere.
- **Sign-in failures say one thing** for "no such account" and "wrong
  password", and `authenticate()` hashes a dummy when the account is missing
  so the timing does not leak what the message refuses to.
- **Sign-out is POST.** A GET that changes state is CSRF-able from any `<img>`
  and gets link-prefetched — a sign-out link logs people out as they read.
- **10 mutations, 10 caught** (the first attempt at the enumeration mutation
  changed one shared line and so changed BOTH messages — it proved nothing
  until rebuilt as a real branch).

**A security hole was closed in the same pass.** `SECRET_KEY` defaulted to
`"dev-only-not-secret"`. That was harmless while the session cookie carried
nothing; it now carries WHO YOU ARE, so a known signing key mints a session as
any user — including one holding a paid pass — without touching the database.
`create_app()` now REFUSES TO BOOT when `RESUMECRAFT_SERVER_STORE=0` (the
existing "this is a real deployment" switch) and the key is still the default.
Failing at startup is deliberate; a warning in a log nobody reads ships anyway.

**One real bug shipped and was caught by looking at the page, not by a test.**
The route pre-translated the heading and button with `ui_t(...)`, whose
signature is `ui_t(text, lang="en")` — so with no language argument the Arabic
sign-up page rendered a fully mirrored, fully Arabic form under an English
heading with an English button. **`tests/test_labels.py` passed throughout**,
because the catalogue rows existed and nothing was reading them. Translation
now happens in the template where `t()` knows the reader's language, every
`AuthError` message is a catalogue msgid, and
`test_auth_messages_are_all_translated` reads the raise sites out of the AST so
a new untranslated message fails rather than silently rendering English.
**The generalisable bit: a label gate proves the catalogue has a row, not that
anything looks it up.** Same family as the golden-gate blind spot.

**The guard broke two tests, and the full run reported `2 errors` alongside
`2134 passed` — with EXIT CODE 0.** `tests/e2e/test_browser_store.py` starts a
real server with `RESUMECRAFT_SERVER_STORE=0`, which is exactly the condition
the new boot guard fires on, so both tests errored at setup. The guard was
right; the fixture now sets a `SECRET_KEY`, which is what a real deployment
has to do anyway. This is the third time this project's `N passed` trap has
bitten — read the summary line, grep for `error`, or use `junit.xml`.

**Fast-loop cost, watched deliberately.** The autouse DB-reset fixture took the
fast loop 22s → 70s on the first cut (two fresh connections per call, twice per
test, ~1650 tests). One cached connection brought it to 30s; skipping the wipe
when nothing was written brought it to **25s**. The fast loop is what runs on
every edit — tripling it is the difference between a suite you run and one you
skip.

**Next in Stage 3: Phase 2** — `pass_expires_at`, `has_active_pass()`, and
wiring `assist.has_ai_access()` to it. That is the one-line change the AI's
Phase 1 was built to make possible.

### DONE — session 26: the outreach kit (`outreach/`, no code)

Stage 2 of [[commercial-stage-ladder]] — the part `MONETIZATION.md` §8b says
actually produces revenue, and the part that needs no accounts, no payment and
not the AI. Seven files: cold email + two follow-ups in **both** languages, an
objection sheet answering the ten questions an institution will ask, a target
list, a tracker and its guide, plus two ready-to-send `.docx` attachments in
`outreach/samples/` (generated, and verified as valid OOXML with real RTL
markup in the Arabic one — 42 `w:bidi`, 40 `w:rtl`).

**⛔ It cannot be used yet: there is no deployed URL.** Every email links to
the site and the whole approach is the product demonstrating itself. That is a
hosting task, not a development one — the app has been deployable since Stage 1.

Three deliberate constraints, all recorded in the kit itself:

- **No email addresses were invented.** `04-targets.md` names institutions and
  says how to find the right person; a fabricated address either bounces or
  reaches the wrong human and burns the institution.
- **The emails claim nothing unverifiable.** No AI (unshipped, Arabic
  unreviewed), no user numbers, no institutional price (`MONETIZATION.md` §8
  says "quote"), no competitor named as bad. Every line survives being checked,
  which is the only reason a cold email from an unknown person works.
- **Send by hand, 5-10/day, follow up twice then stop.** A blast burns the
  sending domain, and Saudi anti-spam rules (CITC) are flagged as worth
  checking before any volume.

Targets are grounded in live search, not memory, and labelled `[verified]` vs
`[known]` so the unchecked ones are obvious. The buying signal found: Saudi
career centres already run CV-writing workshops, so this is a better tool for
something they do every term rather than a new idea to sell.

### Next: Phase 2, and it is NOT code

**Phase 2 is a STOP/GO gate and it needs the user, not the agent.** Twenty real
before/after pairs, read by a native speaker. If the Arabic reads as translated
rather than written, the prompt in `app/assist.py::_SYSTEM` is reworked before
anything is built on it. Cheap now, expensive after four features depend on it.

**The harness is built — `tools/assist_samples.py`.** Twenty cases through the
real `app.assist.adapt`, writing `tools/assist_review.html` (side by side,
correct `dir` per cell, four failure-mode checkboxes, measured cost and cache
behaviour). Six of the twenty are deliberate traps; the table in
`AI_ASSISTANT_PLAN.md` §5 says what each one catches. `--dry-run` lists the
cases and `--preview` renders the page, both without calling anything.

Two defects were found in the harness itself and fixed before it ever ran:
source language was DERIVED as "the opposite of the target", which is wrong for
the two cases whose line is already in the target language and put Arabic in an
LTR cell with a Latin font; and the empty run reported "caching never engaged"
from zero calls. Both are the same shape as sessions 25-26 — **a measuring tool
announcing a finding it never measured.** Both are now gated.

**It needs one thing that does not exist yet: an API key.** `ANTHROPIC_API_KEY`
is not set in this environment and the `ant` CLI is not installed, so no live
call has ever been made from this code. Everything above is verified against a
fake client. **The first real call is unproven** — expect to fix something
small on it, and check `usage` in the `done` frame while you are there, because
whether caching actually engaged is an open question (short prefixes silently
do not cache) and the ~1.1¢/assist estimate excludes thinking tokens.

### Where to pick up — SESSION END 2026-09-11

**Read these three, in this order:** `MONETIZATION.md` (what is sold, for how
much, and the evidence), `AI_ASSISTANT_PLAN.md` (the next feature, fully
planned, not started), then BUILD.md's Store / Rate limits / Escaping / PWA
rows for what shipped on 2026-09-10.

**Code state: Stage 1 done, full suite green** — 2053 passed, 24 skipped, 0
failures, exit 0 (11m00s). Fast loop 1609. The app is deployable to more than
one person. Nothing is half-finished; no work in progress was left uncommitted
to disk.

**Settled in discussion, written down, no code yet:**
- **What is sold:** not a subscription and not "the export" generically — the
  **Word (.docx) file**, multi-résumé storage and the AR/EN pair, unlocked by a
  **non-renewing 30-day pass at SAR 29**, clock starting on first USE of a paid
  feature. PDF and all 49 templates stay free forever. `MONETIZATION.md` §6–§8.
- **The launch offer copy**, English and Arabic, and the two rules that
  produced it. `MONETIZATION.md` §8a.
- **The AI assistant**: five jobs, paid-only, opt-in, off by default; consent
  copy drafted in both languages; model/streaming/caching/effort decided; cost
  measured at ~1.1¢ per assist. `AI_ASSISTANT_PLAN.md`.

~~**Two questions were open when the session ended**~~ — **BOTH ANSWERED by
the user 2026-09-11**, and Phase 1 is built. Go-ahead given; shipping dark is
acceptable, on the argument that a working bilingual demo is ammunition for the
Stage 2 institutional conversations rather than idle inventory.
**There are no open decisions left in the project.**

**Also settled in discussion and written into `MONETIZATION.md` §8b/§8c:** what
the "price is a conversion tool" caution does and does not say (it is not
anti-social-media — organic yes, paid hold, institutional is the one that
pays), and a correction to the unit economics — gateway is **$0.44 not $3**, AI
is **$0.05-0.55 not $3/month**, net is **~$7 not $4**. The conclusion that
matters: AI is 2-7% of revenue, so switching to a cheaper or self-hosted model
saves ~$0.30 and risks the only feature nobody else has. **Customer acquisition
cost is the one unbudgeted line and the only one that can sink the plan.**

**One thing that must not be skipped before any of this goes public:** the
privacy copy contains *"We don't store it"*, which is true by construction only
as long as request bodies are never logged. And **no claim about what the AI
provider does with the text has been written** — read Anthropic's current
commercial terms before adding one. See `AI_ASSISTANT_PLAN.md` §3.

### Where to pick up

**Bilingual work: ALL 8 PHASES DONE. The feature is complete and gated.**
Arabic glyphs, `dir="rtl"`, headings that read as headings, a mirrored layout
on all 49 templates, a mirrored translated app shell with a language switcher,
a right-to-left Word export, and — as of session 23 — both directions through
the content suites, an Arabic browser journey, and the mixed-content case.
**Nothing in the app is English-only regardless of `lang`.**

As of session 24 the user can also SET `lang` — one control in Basics, reading
the file and not the cookie. That was the last English-only assumption left in
the product: the engine had been bilingual since phase 7, but the only way to
tell it a résumé was Arabic was to hand-edit `data/resume.json`.

Two premises recorded in the plan turned out to be false, and BOTH were
dropped rather than shipped. Do not re-open either from the older notes:

- the caps / letter-spacing worry (session 17's audit) — see session 19;
- the bidi-isolation trap (`<bdi>` around every user field) — see session 23.
  Measured 0 findings across 49 templates in Chromium and per character in real
  Word. `tests/test_bidi_mixed.py` gates the behaviour instead.

Phases, all closed:

3. ~~**Labels**~~ — **DONE, session 18.** ~55 catalogue rows behind a Jinja
   `t()` global, ~400 sites across all 50 template files. English stayed
   byte-identical (99 golden tests), and a 588-render differential covers the
   branches the goldens never drew. Casing and phrasing preserved per template
   as required — `Work Experience` is still `Work Experience`.
4. ~~**RTL typography**~~ — **DONE, session 19, and much smaller than this
   said.** The `letter-spacing` / `text-transform` purge was measured, found to
   fix nothing (Chromium applies tracking to ZERO gaps inside a joined Arabic
   run) and to break a masthead (+38.7px wrap on `modern-t10`), so it was
   dropped. What shipped is a heading rescue for the four templates that
   genuinely lose every cue: `ats-t13/19/21/23`. Pixel gate held at 50/50.
5. ~~**Layout mirroring**~~ — **DONE, session 20.** 202 declarations converted
   to logical properties across all 50 files; pixel gate held at 50/50
   throughout, HTML gate moved for 164/197 as expected. The absolute
   decorations did NOT need hand-work: `inset-inline-start` mirrors a negative
   offset correctly by construction, which fixed 65 of 66. Only
   `modern-t22`'s rotated rail needed a hand fix (`transform` has no logical
   form). Verified geometrically — 71 unmirrored elements found after the
   first pass, 0 after.
6. ~~**App shell**~~ — **DONE, session 21.** 143 shell strings behind a
   cookie-driven `t()`, `app.css` fully logical, a header language switcher.
   The interface language is INDEPENDENT of the résumé's `lang` (app/i18n.py),
   which matters most for the level dropdown: those words are stored in the
   document, so they follow the résumé, not the reader. Also split
   SKILL_LEVELS from LANGUAGE_LEVELS, closing the session-17 "Fluent scores
   zero dots" defect at the UI end.
7. ~~**DOCX RTL**~~ — **DONE, session 22.** Four masters now, one per
   (category, direction). RTL needs FOUR things said in the XML, not one —
   `w:bidi` on sectPr AND pPr, `w:rtl` on rPr, and the complex-script
   `w:rFonts/@w:cs`/`w:szCs`/`w:bCs` — plus `w:bidiVisual` on the chip table.
   Each mutation-checked separately. English masters rebuild byte-identical.
8. ~~**Tests**~~ — **DONE, session 23.** `tests/samples.py` (`ENGLISH`,
   `ARABIC`, `BOTH`, `MIXED`, `REVERSED`) is the shared vocabulary; four
   catalogue suites now sweep both directions, `tests/e2e/test_journey_ar.py`
   is the Arabic journey (13 tests), `tests/test_bidi_mixed.py` is the
   mixed-content gate. The isolation fix the plan called for was measured and
   is not needed.

`data/sample_resume_ar.json` has now been rendered, measured and reviewed in
all 49 templates, in both single-script and mixed form. Note it differs from
the English sample in one way that matters when writing tests: **it sets
`percent` on every skill, and the English one sets none**, so Arabic renders
`95%` where English renders `Expert`.

Three assumptions were stated and have now been exercised rather than merely
held: `lang` on the document plus a separate UI-locale cookie (proven
independent through a browser), Western digits, and user content never
machine-translated. The fourth — pilot-4-then-45 — is spent. Any of them can
still be overridden.

**Next: Phase 2 of the AI assistant (a human reading Arabic), then the payment
gateway page (item 5 above).** The
instruction not to interleave it with the bilingual phases no longer applies —
bilingual has landed. Nothing else is outstanding, and there are no open
decisions in the project.

The pre-bilingual position, for reference: nothing was half-finished and nothing
was waiting on a decision. `pytest --e2e -q`
is green at **653** (also green as two concurrent runs, which is what exposed
the session-11b flake); `data/resume.json` and `data/meta.json` are the user's own
and were verified untouched by a full run (dated 2026-08-28/30, not today). The
next piece of work is a choice: build the PWA if this ever gets deployed
publicly, or start a new feature.

Both candidates session 16 named are now resolved (session 16b): the drawer was
a real bug and is fixed; the export path was already correct and its existing
test was mutation-checked rather than trusted. **Every swallow-shaped branch
found so far has been worked.**

No candidate is currently outstanding, so the next audit needs a fresh angle
rather than a list to work through. Two that have never been looked at: the
autosave failure path (`doSave`'s `catch` leaves "Unsaved changes" standing with
no reason given, which is honest but mute if the server is gone), and the fact
that removing a photo never deletes the uploaded file, so `data/uploads/` grows
without bound. Neither is known to misbehave — they are starting points, not
findings.

All three coverage gaps session 12 listed are closed (session 13) — two of
them were hiding live bugs. **The lesson worth carrying forward: this project's
silent failures all have the same shape** — a `catch` that swallows, or an
error message that names the wrong layer. `doRender`'s "Could not reach the
preview service" masked a 500 on all 49 templates for eleven sessions. When
adding a fetch path here, make the failure branch say which layer failed.

No known coverage gaps remain. Untested surface that is genuinely low-risk:
the zoom control's exact scale maths (its wiring is covered), and drawer
scroll position.

**If you keep pulling this thread**, the productive question has been "what
else can a user produce that a renderer will misrepresent?" — not "what else
can crash". Five defects in three sessions came from it, and not one threw an
exception in the preview. Every candidate named so far is now closed:
half-filled entries (13), the Word meta line and unrated skills (14), the
stale highlight and the half-filled social link (15).

~~The untried angle is the **other direction** — a field made absurdly long.~~
**Done, session 25**, and it found one real defect (`modern-t12`'s `nowrap`
headline, 39px off-canvas) plus two instrument errors in my own measurement.
`tools/verify_overflow.py` + `tests/e2e/test_overflow_gate.py` now cover the
horizontal axis for all 49 in both languages.

The lesson that generalises beyond this project: **run the shipped, known-good
input through a new check before believing any finding it reports.** Both
instrument errors announced themselves as "the résumé we ship loses text", and
both would otherwise have been fixed as if they were bugs — one of them nearly
was (see the `modern-t21` reversal above).

If the question is worth asking again, what is still untried is the
**interaction** of the two axes: a value long enough to wrap changes the
height, and auto-fit then rescales the type, which changes every width again.
Nothing has measured whether that loop settles or oscillates.

See `BUILD.md` for architecture. Memory: `resume-builder-webapp`,
`resume-template-porting`, `e2e-browser-suite`, `pdf-render-base-url`,
`docx-export-gotchas`.
