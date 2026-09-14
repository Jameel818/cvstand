# Naming — the app's public brand

**Status: DECIDED AND BOUGHT — 2026-09-13.**

The brand is **CVStand**, on **`cvstand.com`**, which the user has registered.
`cvcraft.com` was taken; so was `resumecraft.com`.

**Nothing has been renamed in the code yet.** The rename plan is §7 below and is
no longer gated on anything — the domain is owned. §1-§6 are the 2026-09-12
research that led here and are kept as the record of *how* the namespace was
searched, not as a live recommendation. **Siyar is superseded.** Do not act on
§5.

### What changed, and what that costs

§2 gave two reasons to drop RésuméCraft. CVStand settles one and not the other:

- **FIXED — the noun.** MENA says *CV*, not *résumé*, and the outreach kit
  already says "CV builder" in every subject line, EN and AR
  (`outreach/01-email-en.md`, `02-email-ar.md`). The name now matches both the
  market's word and the kit's own copy.
- **NOT FIXED — no Arabic form.** "Stand" has no Arabic morpheme, exactly like
  "Craft". **This costs nothing in code**: `app/labels.py:229` already decided
  the brand is never translated ("a brand does not change script when the
  interface does"), and that policy carries over untouched — no Arabic wordmark
  to design, no bidi question in the header, no new catalogue entry. It is paid
  in positioning, and the remedy is a tagline, not another name.
- **OPEN — "stand" reads two ways.** A booth/stall (جناح) or *stand out*. The
  wordmark alone does not disambiguate. If the intended reading is "stand out",
  the tagline has to carry it. A copy decision (Phase 4), not a blocker.

### `.com` also settles the email question (asked 2026-09-13)

§5 had left `.co` vs `siyarcv.com` open, with the tiebreaker stated as "if `.co`
feels thin for institutional email to a Saudi university career centre."
`cvstand.com` is a `.com`, so that reservation is gone.

**A domain alone is NOT enough — buy the mailbox with it.** Four reasons, in
weight order:

1. **Stage 2 revenue is entirely cold email.** `outreach/` is seven files of
   hand-sent B2B email to Saudi/UAE university career centres. A `@gmail.com`
   From line to an institutional career office reads as a student asking for
   something, not a vendor offering something. `outreach/03-objections.md`
   exists because you expect scrutiny — the From line is the first objection,
   and it is answered or failed before the mail is opened.
2. **Deliverability is a property of the sending domain.** SPF/DKIM/DMARC are
   DNS records on `cvstand.com`; sending from a free mailbox inherits Gmail's
   reputation and builds none of your own. Note that the kit's own rule —
   5-10/day, by hand, follow up twice — happens to be exactly the warm-up
   regime a new sending domain needs. It was written for CITC anti-spam
   reasons; keep it for both.
3. **The app already has a dead end only a mailbox closes.**
   `app/templates/account.html:82` tells a locked-out user "Password reset is
   not available yet — get in touch and we will sort it out." There is no
   address anywhere to get in touch at, and **no mail code exists at all** —
   `smtplib` / `flask_mail` / reset-token: zero hits under `app/`, verified
   2026-09-13. A mailbox is the cheap fix; the alternative is building password
   reset, which is a whole feature.
4. **Cost is not a real input.** Zoho ~$1/user/mo (free tier for one user on one
   domain), Google Workspace ~$6. `MONETIZATION.md` §8 prices institutions at
   "quote", i.e. four figures.

Keep the two roles separate: a **human mailbox** — **DECIDED 2026-09-14: it is
`info@cvstand.com`** (not the `hello@` this file first proposed) — for the
outreach From, replies and quotes; and a **transactional sender** (`noreply@`
via Resend/Postmark) only when password reset actually ships.

`info@cvstand.com` now lives in `app/brand.py` as `SUPPORT_EMAIL` and renders
in the footer of every page and on the sign-in page, where the "get in touch"
sentence previously named no address at all. It is deliberately NOT inside a
msgid: `t()`'s key IS its English string, so an address written into the
sentence would re-key the catalogue and silently drop the Arabic every time the
mailbox changed. Do not route the outreach through a bulk ESP; hand-sent
from a real mailbox is the entire point of the approach.

**Buy the mailbox early even if launch is far off** — a brand-new domain has no
sending history, and weeks of age before the first cold send is free reputation.

---

## 1. What the brand is TODAY

The app already has a user-facing brand: **RésuméCraft**. It is not a plan, it
is shipped:

| Surface | File |
|---|---|
| Header + footer wordmark `Résumé<b>Craft</b>` | `app/templates/base.html:30,71` |
| Page titles | `landing.html:2`, `builder.html:2`, `gallery.html:2` |
| PWA manifest `name` + `short_name` | `app/routes.py:385-386` |
| Design-system / source banners | `app/static/css/app.css:2`, `js/builder.js:1`, `js/sw.js:1` |
| Deliberately NOT translated to Arabic | documented at `app/labels.py:229` and `:483` |

⚠ A naive `grep -i "resumecraft"` MISSES the wordmark: the markup splits it
across tags (`Résumé<b>Craft</b>`) and the accented `Résumé` does not match an
ASCII pattern. Grep for `Craft` instead. This cost one wrong conclusion in
session 2026-09-12 ("the brand slot is empty" — it was not).

The internal namespace is separate and stays: `RESUMECRAFT_*` env vars,
`data/resumecraft.db`, and the localStorage keys `resumecraft:resume` /
`resumecraft:template`.

## 2. Why the name is changing

`resumecraft.com` is taken (user verified on Hostinger, 2026-09-12).

Two further objections, independent of availability:

1. **Wrong noun for the market.** MENA says *CV*, not *résumé*. The project's
   own outreach kit says "CV builder" in every subject line, EN and AR
   (`outreach/01-email-en.md`, `02-email-ar.md`).
2. **"RésuméCraft" has no Arabic form.** "Craft" has no Arabic morpheme; it can
   only be transliterated into meaningless noise. For a product whose one
   defensible asset is real RTL plus the bilingual `.docx` (`MONETIZATION.md`
   §5), a name that fails in Arabic undercuts the pitch.

## 3. THE METHOD ERROR — read this before proposing any name

Five candidates were proposed and five were taken. The cause was asking the
wrong question: **"does a company own this?" is not "is the domain free?"**

Search engines find companies. They do not find registered-but-parked domains,
which is most of the namespace. Check DNS (or a registrar) FIRST, then search
for trademark and category conflicts on whatever survives.

**The structural finding: every short real word in `.com` is gone — in Arabic
and English alike.** Four-to-six-letter dictionary words were exhausted a decade
ago. There is no name that both means something and has a free `.com`. Do not
spend another session looking for one. The real choice is:

1. a coined word (no meaning to collide with), or
2. a real word on a non-`.com` TLD, or
3. a real word plus a modifier (`getX.com`, `Xcv.com`).

## 4. Candidates checked, with evidence

| Name | Verdict | Evidence |
|---|---|---|
| **ResumeCraft** | taken | `resumecraft.com` — Hostinger, user-verified |
| **Careerly** | taken, badly | 5+ companies. careerly.tech **sells to university career centres** — literally the `outreach/04-targets.md` audience. Also usecareerly.com, careerlynetworks.com |
| **Masar** | taken | Masar Destination — a $26.6bn Makkah development, Vision 2030 flagship, IPO'ing. Owns the word in the primary market |
| **Seera** | taken | Seera Group Holding, Tadawul 1810 (ex-Al Tayyar) |
| **Sanad** | taken twice | Sanad / Mubadala aerospace; Saudi Aramco Nabors Drilling |
| **Milaf** | taken | PIF-owned premium dates brand |
| **Sirati** (سيرتي) | taken, same category | sirati.bh — AI hiring-tech, Manama, founded 2024 |
| **Numu** | taken | MENA AI growth platform built on the same "Arabic word" logic; NUMU Ventures, Riyadh |
| **Nawa / Nawah** | taken | NAWA Technologies (FR nanotech); Nawah Energy (UAE nuclear operator) |
| **Malaf** (ملف) | REJECTED on merit | Domain registered. And `mal-` is the negative prefix in English and every Romance language — malware, malfunction, malpractice, *mal* = bad. Also bureaucratic in Arabic: ملف is the file a ministry keeps on you |

### DNS sweep, 2026-09-12

All registered: `siyar.com` (giantpanda NS, in use), `malaf.com`, `nabda.com`.

Registered but on registrar-default nameservers, i.e. **parked / likely for
sale**: `safha.com` (Namecheap), `wajha.com` (NameBright), `lamha.com` (GoDaddy).

No NS record, so **likely available**: `siyar.co`, `siyar.io`, `siyar.sa`,
`siyarcv.com`, `getsiyar.com`, `trysiyar.com`, `usesiyar.com`.

Registered: `siyar.me`, `siyar.app` (Cloudflare).

⚠ "No NS" means *probably unregistered*, NOT confirmed — a registered domain
with no nameservers looks identical. A registrar is the only authority.

## 5. The decision: Siyar — سِيَر

> ⛔ **SUPERSEDED 2026-09-13 — the brand is CVStand on `cvstand.com`, bought.**
> Kept only as the record of how the namespace was searched. Do not act on it.

- **Arabic.** سِيَر is the plural of سيرة — literally *"CVs / life-stories."* Not
  coined, not transliterated, and pluralised, which suits a product meant to
  hold several. It carries the classical biographical tradition (the genre of
  *Siyar* works), so it reads cultured rather than administrative — the exact
  failing of Malaf.
- **English.** "SEE-yar." Two syllables, no negative prefix, no phoneme English
  lacks, no Romance-language landmine.
- **Availability.** The only candidate with no competitor anywhere in
  CV / career / HR. Nearest: Siyaram Silk Mills (different string, Indian
  textiles), a real-estate Instagram account, and a dormant-looking SIYAR
  LIMITED on UK Companies House.
- **It sidesteps the résumé-vs-CV noun problem** entirely, which was the
  original objection to ResumeCraft.

**Domain: `siyar.co` preferred** — short, reads as a product. **`siyarcv.com`**
is the fallback if `.co` feels thin for institutional email to a Saudi
university career centre: it keeps `.com` credibility and the "cv" says what
the bare name deliberately does not.

Residual risks: some English speakers try "SIGH-yar" once. The plural subtlety
only registers consciously with educated Arabic readers (everyone else reads
"biographies", still correct). UK trademark classes need checking because of
SIYAR LIMITED.

## 6. What the hook slogan may NOT claim

Asked this session: *how many résumé versions can a user save on his account?*

**Today: zero.** Verified in code, not in the plan docs:

- `app/db.py:53` — `users` is the ONLY table (id, email, password_hash,
  created_at, session_version, pass_expires_at). **There is no résumés table.**
- `app/static/js/builder.js:28` — the localStorage key is `resumecraft:resume`,
  **singular**. One document, per browser.
- `data/resume.json` is one global file (which is why
  `RESUMECRAFT_SERVER_STORE=0` exists).

An account currently stores nothing but a login. `MONETIZATION.md` §7 *plans*
1 free / unlimited paid, but §8a's launch copy ALREADY promises "**Keep as many
CVs as you need**" / "احتفظ بما تشاء من السير الذاتية" — a feature with no table
behind it. **That copy is unshippable as written.**

**So do not build the hook on saved versions.** The honest hook is what is both
true now and unique (§5, §7): *the same CV in Arabic and English, with a Word
file that actually opens.* Storage is a capacity line for the pricing table,
not a slogan.

## 7. Plan — **ALL FOUR PHASES EXECUTED 2026-09-14**

Confirmed and run in one session. Test count went 1692 -> 1728 fast, 0 errors.
What follows is the plan as written on 2026-09-13, kept verbatim as the record;
**where the tree disagreed with it, the correction is marked inline.** Read
§7a for what actually happened.

### 7a. What the plan got wrong, measured rather than assumed

1. **Phase 3 was not the risk it was billed as.** It predicted "a batch of
   genuinely untranslated shell strings". The shell has 117 msgids and **zero**
   were missing Arabic. The phase was exclusions and plumbing, not translation.
2. **The glob miss was a wrong DIRECTORY, not "wrong extension and wrong
   depth".** `TPL_DIR` is `templates/resumes`; the shell is its PARENT.
3. **Widening the glob does not catch defect 2.** A `<meta>` description is an
   attribute, and the scan only ever read text nodes and Jinja literals.
   Attribute coverage was never in the plan and is what actually closed it.
4. **`t` is two different functions** — `labels.t` (reads `_AR`, follows the
   document) in the résumé templates, `ui_t` (reads `_UI_AR`, follows the
   reader's cookie) in the shell — so one flat msgid list is wrong. Widening
   the glob failed two tests for this reason alone, neither a real defect.
5. **`WORDY` was ASCII-only**, so every string containing "résumé" was
   invisible to the miss detector — the §3 accent trap living inside the test
   written to catch that class of miss.
6. **`sw.js`'s `VERSION` had to be bumped** and was in no phase. The shell is
   cached under a manual key; without the bump every returning visitor keeps
   the old wordmark, and nothing in the suite can see it.
7. **Four dead catalogue rows, not one.** `"Résumé Builder"` was joined by
   `"Templates back"`, `"qualifications"` and two template-switch errors
   orphaned when the switch moved to localStorage — which labels.py's own
   comment already said had happened.

**The method note worth keeping.** Five successive attempts to measure dead
catalogue rows were each wrong in a different way: scanning `_AR` when the
shell reads `_UI_AR`; a self-referential blob that included `labels.py` and
made the test vacuous (caught only by mutation); folded-vs-raw key casing; a
double-quote pattern that swallows single-quoted literals inside attributes;
and naive quote pairing shifted by one apostrophe in prose. **Every new gate
here was mutation-tested before being believed**, and the vacuous one was
caught that way and no other.

### Phase 0 — USER, and it no longer blocks code

Trademark classes 9 and 42 for "CVStand" / "CV Stand" in KSA, UAE and UK. Lower
risk than the Siyar check would have been — the domain is already owned and
nothing is deployed — so **run Phases 1-4 in parallel with it**, not behind it.
The exposure is outreach material printed at volume before it clears.

Also: buy the mailbox (see the header block above). It unblocks nothing in code,
but it is a gating item for the whole `outreach/` kit, alongside hosting.

### Phase 1 — single source of truth, THEN rename (LOW, ~1h)

This is the SECOND rename, which is evidence the string moves. Define it once:

- New `app/brand.py` — `NAME = "CVStand"`, `HEAD = "CV"`, `TAIL = "Stand"`,
  exposed through a context processor.
- `base.html:30,71` — `Résumé<b>Craft</b>` becomes
  `{{ brand_head }}<b>{{ brand_tail }}</b>`.
- `landing.html:2`, `builder.html:2`, `gallery.html:2` — three page titles.
- `routes.py:385-386` — manifest `name` / `short_name` read `brand.NAME`,
  dropping the `ui_t()` wrapper, which was always a no-op for an untranslated
  brand.
- `app.css:2`, `builder.js:1`, `sw.js:1` — three comment banners.
- `labels.py:229,483` — the two comments that name the old brand.

⚠ **Why the constant, and not just six edits.** After the rename
`grep -i cvstand` will STILL miss the wordmark, because it will be
`CV<b>Stand</b>` — the identical trap that produced one confidently wrong answer
on 2026-09-12 (§3). A constant in one `.py` file makes the ASCII string
greppable and makes the third rename a one-liner.

**DO NOT TOUCH** — unchanged from the 2026-09-12 plan: `RESUMECRAFT_*` env vars,
`data/resumecraft.db`, and the `resumecraft:resume` / `resumecraft:template`
localStorage keys. The BROWSER owns the résumé; renaming those keys silently
wipes every existing user's document for zero user-visible gain. The internal
namespace and the public brand do not have to match.

### Phase 2 — the three brand defects (LOW, ~45 min)

Same files as Phase 1, so the same pass.

1. **The brand does not reach every page.** `base.html:10`'s default title is
   `t('Résumé Builder')` and `account.html:15` is
   `{{ heading }} · {{ t('Résumé Builder') }}` — so sign-up/sign-in are branded
   generically, and in Arabic the title reads منشئ السيرة الذاتية beside a Latin
   wordmark. Point both at the brand. Then **delete the now-dead
   `"Résumé Builder"` entry at `labels.py:231`** —
   `test_every_msgid_has_an_arabic_translation` only checks the other
   direction, so dead catalogue entries are invisible to it. Add the reverse
   assertion while you are in there.
2. **`base.html:11`'s `<meta name="description">` is hardcoded English**, never
   routed through `t()`, while the manifest's description IS translated
   (`routes.py:387`). Route it. Phase 3 says why no test caught this.
3. **Zero brand coverage in tests.** Add one: brand present in header, footer
   and `<title>` across landing / gallery / builder / account, in both UI
   languages, byte-identical in Arabic. **This is what makes the grep trap
   harmless** — the test becomes the guard instead of anyone's memory.
   (Changing titles breaks no existing test — verified: `grep -rn "Craft"
   tests/` is empty and nothing asserts on any `<title>`.)

### Phase 3 — widen the label gate (MEDIUM — the only phase that can overrun)

`tests/test_labels.py:60` is
`sorted(TPL_DIR.glob("*/*.j2")) + [TPL_DIR / "_macros.j2"]`. The app shell is
`.html` **and** sits at the top level of `TPL_DIR`, so it misses on *both*
counts — wrong extension and wrong depth. That is precisely why defect 2 above
survived. Widening the glob is three lines and will likely surface a batch of
genuinely untranslated shell strings.

**Commit the widening and the string fixes separately**, or this phase eats the
session.

### Phase 4 — copy, name-dependent (LOW, ~30 min)

- A tagline that resolves the "stand" ambiguity, EN + AR.
- **`MONETIZATION.md` §8a is unshippable as written**, and is name-independent,
  so it can land first and probably should: it promises "Keep as many CVs as
  you need" / "احتفظ بما تشاء من السير الذاتية" against a schema with no
  résumés table (`app/db.py:53` has `users` and nothing else). See §6.

## 8. Verified as needing NO work (2026-09-13)

Checked in the tree, not assumed:

- **`outreach/` needs no rename.** All seven files use `[LINK]` / `[YOUR NAME]`
  placeholders; the only brand-ish hit is `README.md:27`, an env-var reference.
  Fill in the deployed URL and the kit is live.
- **The logo mark carries no text** — `app.css:121` is a pure CSS gradient
  square. The favicon at `base.html:19` is an inline SVG document glyph, no
  lettering.
- **PWA icons: verify visually once.** `app/static/icons/` holds four PNGs
  (655B-1.9KB) — almost certainly the same glyph, but nobody has looked.
- **Docs carry the old name in prose** — `BUILD.md:1`, `MONETIZATION.md:18,106`.
  Cosmetic; batch at the end.

## 9. Risks

| Risk | Level | Mitigation |
|---|---|---|
| Phase 3 scope explosion | MEDIUM | Split the glob widening from the string fixes |
| pytest `N passed` trap — **third occurrence in this project** | LOW | Read the summary line, grep for `error` / `FAILED`, or use `junit.xml` |
| Trademark comes back dirty | LOW | Domain is owned either way; only printed outreach is exposed |
| Existing tests break | NONE | Verified — no test touches the brand or any `<title>` |

**Complexity: LOW overall.** Phases 1+2 together ≈2h and that is the entire
visible rename. Phase 4 is writing, not code.
