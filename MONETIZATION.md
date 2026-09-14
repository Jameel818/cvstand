# Monetization — what is sold per user

**Researched 2026-09-10. Market: MENA-first (Arabic + English), Gulf primary.**
Answers the open product question recorded in `RESUME_HERE.md` item 5, which
blocks the payment-gateway track. Every price below was fetched live, not
recalled — this file's claims expire. Re-verify before acting on the numbers.

Read §6 first. §1–5 are the evidence, §7–11 are what to build.

---

## 1. The answer

**None of the three, as posed.** "Templates, exports, or a subscription" was the
right question in 2020. In 2026 the reputable market gives templates and exports
away and sells **capacity and assistance** — how many résumés you may keep, and
whether a machine helps you write them. Selling templates or gating PDF puts
CVStand in the cohort the industry is actively turning against.

For a MENA-first product the answer narrows further: sell a **non-renewing,
time-boxed pass**, with the paid line drawn at the **bilingual Word export and
multi-résumé storage**, and all 49 templates plus unlimited PDF free forever.
The reasoning is §5–6.

---

## 2. How the four models were separated

Sorted this way because vendors deliberately blur them:

1. **One-time template unlock** — buy a design, keep it.
2. **Per-export / credits** — pay per download, or gate a format.
3. **Subscription** — recurring access, honestly presented.
4. **Trial-to-subscription** — a $2–3 "trial" that auto-converts at ~$25/4wks.
   Separated from (3) because the economics, the churn and the reputational
   cost are entirely different animals.

---

## 3. Evidence — the global market

| Product | Free tier | Paid | What the paywall actually gates |
|---|---|---|---|
| FlowCV | 1 résumé, **all templates**, unlimited PDF, **no watermark** | $19/mo, or $5/mo billed $60/yr | Résumé **count** + AI |
| Kickresume | Unlimited résumés **and downloads** on free customizations | $24/mo → $96/yr | Premium designs + AI |
| Teal | Unlimited résumés + job tracking, rationed AI credits | $19/mo, $7/mo annual | **AI credits** |
| Rezi | 1 résumé, 3 PDF downloads | $29/mo or **$149 lifetime** | Count + downloads |
| Jobscan | Free first draft → final PDF, no fee at download | — | Nothing at export |
| Zety | Build free; free download is **.txt only** | $1.95 trial → **$25.95/4wks** | **PDF + Word** |
| Resume.io | Build free | $2.95 trial → **$29.95/4wks** (~$389/yr) | **PDF** |
| Resume Genius | Build free | $2.95 → $23.95/4wks | **PDF** |
| MyPerfectResume | Build free | $2.95 → $23.95/4wks | **PDF** |

Three things to take from this table:

- **Templates are free everywhere that matters.** FlowCV ships every template on
  the free tier with no watermark. Gating design is not a business model any
  more; it is a reason to be reviewed badly.
- **Export-gating survives only inside the dark-pattern cohort.** Every product
  that gates PDF is also a trial-to-sub product, and all four appear on
  "avoid these traps" listicles that now rank for the category's own keywords.
- **The reputable paywall is quantity and AI.** FlowCV's 1-résumé line is the
  most-copied boundary in the category.

Note also that the trial cohort bills every 4 weeks — 13 charges a year, not 12.
Not a coincidence, and worth refusing on its own.

---

## 4. Evidence — MENA

**The Arabic consumer segment is saturated with free.** cv-in-arabic, cv-ar,
cv-gulf, write.cv (unlimited PDF, no watermark, no sign-up), FreeCV.org (22
templates, no card), StylingCV (50+ Arabic templates free, "premium templates"
paid), un-tool, saparabic. None of them found charging for a PDF.

**The incumbent monetizes the other side of the marketplace.** Bayt.com — the
region's default — makes CV building free and sells Premium/Elite to job seekers
as **visibility** (auto-sponsored Featured CV, priority ranking in employer
search), plus job postings and CV-search seats to employers. Bayt has never
tried to sell the document. That is the single most instructive data point in
this file.

**But the Gulf will pay for software.** Saudi indexes at **1.0x on app pricing —
the same as the US**. Apple Pay leads Saudi e-commerce preference at ~36%, mada
at ~22%, stc Pay ~12%; mada is used by **>70% of Saudi shoppers** and mada
e-commerce was **+28% YoY** in March 2026. Counter-signal: ~20% of UAE/KSA
streaming cancellations are price-driven, and 2026 consumer behaviour there is
described as sharply more value-sensitive.

**Egypt is not the same market.** Credit-card penetration is **under 10%**,
concentrated in the top income decile; **<8%** of online purchases use digital
wallets; COD still dominates. InstaPay (16M+ users, 0.1% fees) is the real rail
but is account-to-account and hostile to recurring card billing. Fawry reaches
250,000+ retail points for cash-in.

**The RTL gap is real, and it is the asset.** Novoresume: no Arabic, no RTL
templates, no Arabic fonts. LinkedIn Resume Builder: no Arabic. Enhancv,
Kickresume, Zety: no Arabic. Canva: accepts Arabic text into LTR templates and
requires manually repositioning every element — no automatic RTL layout, no
bilingual document. The category-wide failure is described exactly as this
project already understands it: RTL is not a CSS direction flip.

---

## 5. What the evidence means for CVStand

1. **Selling templates is off the table.** 49 designs are an acquisition asset,
   not inventory. Gating them competes with FlowCV's free tier and loses.
2. **Gating PDF is off the table.** It is the one move that reliably earns this
   category's worst reviews, and the free Arabic sites all give it away.
3. **A recurring subscription is a poor fit for the actual user.** Job seeking is
   bursty — a few weeks, then gone. Recurring billing against that lifecycle is
   how the industry ended up with a cancellation-complaint problem, and
   auto-renew distrust is higher, not lower, in this region.
4. **Gulf can pay; Egypt/Levant largely cannot, at any price.** With card
   penetration under 10%, Egypt is a free-tier growth market, not a revenue one.
   Price for the Gulf; serve Egypt free and count it as reach.
5. **The defensible thing is the bilingual Word export.** Every free Arabic tool
   produces a PDF. A genuinely RTL `.docx` — `w:bidi` on sectPr and pPr, `w:rtl`
   on rPr, complex-script `w:rFonts/@w:cs`, `w:bidiVisual` on the chip table,
   verified over COM to fit one page — is the scarce artifact, and Gulf
   employers routinely ask for an editable Word file. That is the paid line.

---

## 6. Recommendation — what is sold per user

> **A non-renewing, time-boxed access pass that unlocks the bilingual Word
> export and multi-résumé storage.** Not a template purchase. Not a per-download
> charge. Not an auto-renewing subscription.

"Non-renewing" is the whole point and is not a detail: the pass expires and the
user buys again if they still need it. That single property removes the
cancellation-complaint problem that defines this category, removes dunning,
removes chargeback exposure, removes involuntary churn, and — see §10 — collapses
the entitlement model to one timestamp column.

**Second revenue line, probably larger, deliberately deferred:** institutional
seats — universities, training centres, employability programmes, recruitment
agencies. Bayt's model is proof that in this region the money is on the
institution's side of the table, not the seeker's. Do not build it until the
consumer pass has run long enough to produce a real conversion number.

**Honest counter-argument, recorded rather than buried:** the current promise on
the landing page — *"No sign-up, no paywall"* — is itself a competitive asset in
a market this saturated with free. The recommendation above breaks it. It is
survivable only because the free tier stays genuinely free (all templates,
unlimited PDF, no watermark) and the copy can say so. If you would rather not
break it at all, the institutional line is reachable without ever charging a
job seeker — that is a legitimate alternative to this whole section.

---

## 7. The free/paid boundary, drawn on the real grid

| Capability | Free | Paid | Why |
|---|---|---|---|
| All 49 templates (24 modern / 25 ATS) | yes | — | FlowCV gives them away; gating loses |
| PDF export, unlimited, no watermark | yes | — | Table stakes; every free Arabic site does it |
| Arabic + English rendering, RTL layout, RTL typography | yes | — | Quality, not capacity — and it is the hook |
| Auto-fit, photo, live preview | yes | — | Quality |
| **Word (.docx) export** | no | yes | The scarce artifact (§5.5) |
| **Stored résumés** | 1 | unlimited | FlowCV's proven line |
| **AR ⟷ EN paired document** (same content, both languages, both formats) | no | yes | Nobody else can produce it |

The AR/EN pair is worth calling out as the headline paid feature rather than the
Word export alone: a Gulf applicant needs Arabic for a local or government
employer and English for a multinational, from one set of facts. That is a
specific, nameable job — and it is the one thing in this file that no competitor
in either market can do at all.

---

## 8. Price ladder — SETTLED 2026-09-11

**One SKU at launch: SAR 29, once, 30 days, non-renewing.** Do not offer
7/30/90 tiers — choice here reads as a pricing trick, and there is no data to
price tiers with anyway.

| | Gulf (SAR/AED) | Egypt / Levant |
|---|---|---|
| Free | 0 | 0 |
| **30-day pass, non-renewing** | **SAR 29** | price at PPP, ~50–60% of Gulf |
| Institutional seats | quote | quote |

Expect Egypt to underperform any price because of the card-penetration ceiling
(§4), not because of the number. Do not read a weak Egypt result as a pricing
failure.

### Why 30 days, not 1 or 2 weeks

**Calibrate to the job-application cycle, not to how long writing a CV takes.**
Writing takes one evening. The cycle is: apply → recruiter asks for it in Word
→ interview → they ask for an Arabic version → a second role appears. That runs
for weeks, and it is exactly when the paid features get used.

- **1 week** — it is precisely the resume.io/Zety trial length, so it carries
  the association the whole positioning exists to escape; and a real search
  does not resolve in seven days, so the pass dies right when the recruiter
  asks for the Word file.
- **2 weeks** — no natural anchor; nobody makes purchase decisions in
  fortnights.
- **30 days** — matches the search burst and how people already think. Say
  "30 days", not "1 month": unambiguous, and it reads as a window rather than
  a billing period.

**The asymmetry is the real argument.** Too long costs almost nothing — files
have near-zero marginal cost, so a few users getting extra value is noise. Too
short costs refund requests, angry users and bad reviews, and in this category
reviews ARE the battlefield. When the risk is that lopsided, err long.

**Start the clock on first USE of a paid feature, not at purchase.** Someone
who buys at 11pm Thursday and does not sit down with it until Sunday has not
silently burned three days. Cheap to implement, and it removes the single most
common complaint about time-boxed products.

### Why 29 and not 10

SAR 10 was the first proposal. Two costs eat it, and the first is the one
nobody expects:

**The gateway's FLAT fee.** Moyasar is ~2.2% **+ 1 SAR per transaction** (§9).
The 1 SAR does not scale:

| Price | Gateway takes | You keep |
|---|---|---|
| SAR 10 | 1.22 (**12%**) | 8.78 ≈ $2.34 |
| SAR 29 | 1.64 (**5.7%**) | 27.36 ≈ $7.30 |

**AI cost.** ~1.1¢ per assist, ~$0.30–0.50 for a heavy session, and a pass runs
30 days — an enthusiastic user can burn $1–2 (`AI_ASSISTANT_PLAN.md` §4).
Against $2.34 net that is most of the revenue. Against $7.30 it is comfortable.

**And cheap reads as suspicious.** SAR 10 beside "49 designs + AI + Word
export" invites *"what's the catch?"* — the exact question the positioning
exists to pre-empt. The comparison that sells is not a low absolute number, it
is the contrast: **SAR 29 once, versus resume.io at ~$389/year.**

---

## 8a. The offer — launch copy

Price as the hook is the right call: the category's reputation problem IS
auto-renewal, so being loudly the opposite of it is the strongest positioning
available. Two rules that produced this wording:

- **Never put "subscription" and "one time" in the same sentence.**
  "Subscription" is the word people fear. It is a *pass*, an *unlock*, or
  "30 days of full access".
- **Do not sell PDF — it is free.** Listing "PDF & Word" as a paid benefit
  undercuts the honesty that makes everything else credible. Word is the paid
  one. And the actual differentiator — the CV in **both languages** — belongs
  in the offer, because nobody else can do it.

> # SAR 29. Once.
> ### 30 days of everything. Then it just ends.
>
> - All 49 designs — **in Arabic and English**
> - Download as **Word**, as well as PDF
> - **AI writing help** — rewrite a weak line, draft your summary, or turn your
>   English CV into proper Arabic
> - Switch between all 49 designs without retyping anything
> - **No renewal. No card kept on file. No second charge, ever.**
>
> **Free, no sign-up:** every design, unlimited PDF downloads, no watermark,
> both languages. Word and AI are the paid part.

> # ٢٩ ريالاً. مرّة واحدة.
> ### ٣٠ يوماً بكل المزايا. ثم تنتهي من تلقاء نفسها.
>
> - جميع التصاميم الـ٤٩ — **بالعربية والإنجليزية**
> - تنزيل بصيغة **Word**، إضافةً إلى PDF
> - **مساعدة الكتابة بالذكاء الاصطناعي** — أعد صياغة سطر ضعيف، أو اكتب نبذتك،
>   أو حوّل سيرتك الإنجليزية إلى عربية سليمة
> - بدّل بين التصاميم الـ٤٩ دون إعادة كتابة شيء
> - **بلا تجديد. بلا حفظ لبطاقتك. وبلا أي رسوم أخرى — إطلاقاً.**
>
> مجاناً وبلا تسجيل: كل التصاميم، وتنزيل PDF بلا حدود، وبلا علامة مائية،
> وباللغتين.

**Corrected 2026-09-14 — the storage claim had no schema behind it.** This
block used to promise "Keep as many CVs as you need" / "احتفظ بما تشاء من السير
الذاتية". There is no résumés table: `app/db.py:53` creates `users` and nothing
else, and `app/store.py:41`'s `save_resume` writes ONE file at a single
`RESUME_PATH` — not one per account, not one per anything. An account stores
zero résumés today, so the bullet was selling a feature that does not exist, in
the same list as "No card kept on file", which is the line the whole offer's
credibility rests on. One false bullet is enough to cost the rest of them.

The replacement is true now and needs no table: one set of details already
feeds all 49 layouts. **If saved versions are ever built, the bullet can come
back — with the table, not before it.**

Two notes on the copy. **"No card kept on file" is the line that makes "no
renewal" believable** — anyone can claim no auto-renew; not storing the card
proves it, so the implementation must actually match the claim. And
Arabic-Indic numerals (٢٩) versus Western (29) is a genuine choice in Gulf
digital products — both are common. Test it; it is not settled here.

**The standing caution.** Price is a CONVERSION tool, not an ACQUISITION one.
This offer works on someone who has already landed on the page and does nothing
to get them there. Stage 2 (institutional outreach, §6) is still what produces
revenue. Do not let a good offer feel like a growth plan.

### 8b. What that caution does and does not say — asked and answered 2026-09-11

Asked directly: *does this mean I must talk to institutions — isn't social media
enough?* Recorded because the sentence above reads as anti-marketing and is not.

**It is not a claim about social media.** Social media IS acquisition. The
caution is about PRICE: nobody has ever bought something because of a number
they never saw. Both are needed; only one of them is written down so far.

**The split that follows from §8's arithmetic:**

- **Organic social — do it.** Free, and Arabic CV content is underserved (§4).
  This is the realistic consumer channel. Slow and unforecastable, which is
  exactly why it cannot be the only one.
- **Paid social — hold.** You keep **~$7.30 once**, with no renewal by design,
  so every acquisition riyal comes out of $7.30 and never gets a second chance.
  Paid clicks against a one-time sale that small do not obviously pay back, and
  §12 is explicit that **no credible conversion data was found** for this
  category — so the funnel cannot be modelled, only measured. Do not buy
  traffic for a checkout that does not exist yet.
- **Institutional — this is the one.** One career-services office is 500-5,000
  people in a single conversation, at a quoted price, against an annual budget
  that can repeat. §4's Bayt finding is the regional proof.

**The operationally useful half is "it isn't code".** Institutional outreach
needs no accounts, no payment, and not the AI. The bilingual RTL `.docx` — the
scarce artifact of §5.5 — already exists and already opens in Word. Those
conversations can start on the app as it stands, which makes them the one
revenue-producing action available before Stage 3.

**The unbudgeted line.** Customer acquisition cost is the only number in this
file that can sink the plan. Gateway fees and AI are pennies by comparison
(§8c). Nothing here estimates CAC, and nothing should until there is a real
number to divide by.

### 8c. Unit economics, corrected 2026-09-11

Recorded because a plausible back-of-envelope — *$10 price, $3 AI, $3 gateway,
$4 profit* — was wrong on all three inputs, and wrong in the optimistic
direction on two of them.

| Line | Plausible guess | Actual, per §8/§9 and `AI_ASSISTANT_PLAN.md` §4 |
|---|---|---|
| Price | $10/month, recurring | **SAR 29 ≈ $7.73**, once per 30 days, non-renewing |
| Gateway | $3 | **SAR 1.64 ≈ $0.44** (2.2% + 1 SAR) — **5.7%**, not 30% |
| AI | $3/user/month | **~$0.05–0.55** typical; ~$1–2 heavy, capped by fair use |
| **Net per pass** | **$4** | **~$6.70–7.25** |

So AI is **2-7% of revenue**, not 30%. Two consequences:

**Switching to a cheaper or self-hosted model to save money solves a problem
that does not exist.** The saving is ~$0.30 per customer; the risk is the
Arabic, which is the only thing in §7's table no competitor can produce at all.
"Free" models are also mostly not free — open weights are free to download and
not to serve, and an always-on GPU is a fixed monthly cost that beats per-token
billing only at volumes far above launch. There is a separate and real
question about **cross-border data transfer under Saudi PDPL** for any provider
outside the region — unverified here, and it must be checked before a provider
is named in the privacy copy (`AI_ASSISTANT_PLAN.md` §3 deliberately names
none). Model choice is a Phase 2 quality decision, not a cost one.

**Margin per sale was never the risk; number of sales is.** A 90% margin on
zero sales is zero — which is §8b, arrived at from the cost side.

---

## 9. Payment rails and compliance

**The single most decision-relevant fact found:** the SAR 375,000 VAT
registration threshold **does not apply to foreign sellers** of digital services
into Saudi Arabia. One Saudi customer creates a registration obligation. This,
not gateway fees, should drive the decision.

**If incorporated inside KSA → Moyasar.** ~2.2–2.5% + 1 SAR, no setup, no
monthly fee, fastest mada onboarding, T+1 settlement. (Tap ~2.9–3.94% + 1–2 SAR;
HyperPay 1,500 SAR setup + 250 SAR/mo, priced for scale.) Then ZATCA applies
directly: Phase 1 QR-coded structured invoices since 2021, and Phase 2 Fatoora
portal integration — Wave 24 covered >SAR 375k turnover with a **30 June 2026**
deadline that has already passed. Budget for it as real work, not a checkbox.

**If incorporated outside KSA → Paddle as merchant of record.** It becomes the
seller of record and absorbs VAT/GST registration and remittance worldwide,
which is the only clean answer to the no-threshold rule above. Its MENA
jurisdiction coverage could **not** be confirmed from public sources — verify
with Paddle directly before committing.

**Non-negotiable regardless of gateway:** Apple Pay (highest-preference method in
KSA at ~36%) and mada (>70% of Saudi shoppers). An international-Visa-only
checkout silently fails a large share of real Saudi users — it will read as a
conversion problem, not a payments problem.

**Egypt:** Fawry and InstaPay, and accept that card-based recurring billing is
not viable. A non-renewing pass happens to fit A2A rails far better than a
subscription would — another argument for §6.

---

## 10. Build spec

Written against the recommendation in §6. Items 1, 2 and 6 are model-independent
and would be needed whatever you sell; 3 and 4 are where a different answer would
change the work.

**1. Accounts and auth — does not exist at all today.** `app/store.py` is one
`data/resume.json` + `data/meta.json`, no DB, no users, no sessions. Needs a real
user store (SQLite → Postgres) and session auth. Largest single item.

**2. Multi-tenancy — the biggest structural change.** `load_resume()` /
`save_resume()` and the selected-template meta become per-user. Ripples into the
test suite: the whole session shares one `CVSTAND_DATA_DIR`
(`tests/conftest.py`), and every route-level test that writes the store snapshots
and restores it (`test_smoke.py::stored_resume`). That contract has to be
re-expressed per-tenant or the suite starts lying.

**3. Entitlement — one column.** A non-renewing pass is a single
`pass_expires_at` timestamp per user. Payment succeeded → extend. No plan state
machine, no dunning, no proration, no grace periods, no cancellation flow. If you
choose a recurring subscription instead, this item alone grows by an order of
magnitude — that is a genuine engineering argument for §6, not just a
reputational one.

**4. Gate placement.** `/export/docx` checks entitlement; `/export/pdf` does not.
`app/registry.py` and the gallery are untouched — all 49 stay free. The
1-résumé free limit lives in the store layer, not the routes.

**5. Landing copy, and a trap in it.** `app/templates/landing.html:13`
("Start building — it's free") and `:104` ("No sign-up, no paywall") both become
false. **The msgid IS the English string**, so editing either creates a *new*
msgid that silently falls back to English for Arabic readers until a catalogue
row is added in `app/labels.py`. Confirm `tests/test_labels.py` fails on the edit
before making it — if it doesn't, that gap is worth closing first.

**6. Checkout in RTL.** Prices, currency and any hosted-gateway iframe inside a
`dir="rtl"` shell. This project's own precedent is exact: `transform` has no
logical form, `transform-origin: top left` is a physical corner, and it blanked
**every** card in the Arabic gallery while all 49 iframes were present in the
DOM. A hosted checkout iframe is that same shape. Gate it geometrically, the way
`tests/e2e/test_shell_rtl_geometry.py` does — "did it load" was true throughout
last time.

**7. PWA.** Revived by deployment, per `RESUME_HERE.md` item 2 — it was deferred
*because* the app was local-only.

---

## 11. Security — a gate on shipping, not a follow-up ticket

`RESUME_HERE.md` already says to threat-model `/api/*` and `/export/*` before
exposure. One concrete finding, verified in the code today:

**Stored XSS via `| safe` on user input — 13 sites.** Autoescape is on globally
(`app/rendering.py:28`), but thirteen templates defeat it to join fields with
`<br>`. `_macros.j2:206` (`contact_lines`) builds `parts` from raw
`contact.email`, `.phone`, `.address`, `.site` and `social[].label`, joins, and
marks the result safe. `modern/t3.j2:54` does the same with skill names;
`modern/t3.j2:61` and `t5.j2:66` with `r.tools`. Also `ats/t19.j2:35`,
`modern/t13.j2:26`, `t16.j2:42`, `t23.j2:29`, `t24.j2:42`, `t3.j2:47`,
`t5.j2:44`, `t7.j2:147`, `t9.j2:52`.

Today this is harmless — single-user, local, you could only attack yourself. On a
public multi-tenant deployment an email field containing markup renders as live
HTML in the builder preview and the template drawer, **and is fed to headless
Chromium by the PDF exporter**. Fix is mechanical: escape each part and join with
a `Markup("<br>")` separator, rather than marking the joined string safe.
`app/labels.py:460 _as_html` shows the project already reasons about this
distinction correctly for its own strings.

**DONE 2026-09-10** — fixed via `app/rendering.py::_br_join`, all 13 sites
converted, gated by `tests/test_escaping.py` (140 tests, both languages).
Reverting all 13 fails exactly 20 of them. The golden HTML and pixel gates both
pass unchanged, so nothing moved visually.

**Also DONE 2026-09-10 — rate limiting and admission control** (`app/limits.py`,
`tests/test_limits.py`). Per-client token buckets on `/api/render`, `/api/photo`
and both exports, and a global bounded semaphore capping concurrent PDF renders.
The semaphore is the one that matters: **every `/export/pdf` launches its own
Chromium** (`app/exporters/pdf.py:35`), and fifty clients making one request
each are all inside any per-client limit while still putting fifty browsers on
the box. Answers 429 and 503 respectively, both as JSON. `ProxyFix` is opt-in
via `CVSTAND_TRUSTED_PROXIES` — trusting `X-Forwarded-For` when nothing
strips it is worse than ignoring it, since any client could then mint a fresh
bucket per request.

**Correction to an earlier draft of this section:** `/api/photo` was listed as
needing content-type validation and EXIF stripping. It already does both. It
checks the mimetype, forces a full decode with `img.load()` so a renamed
non-image and a truncated file fail where they can still be explained, handles
`DecompressionBombError`, re-encodes to JPEG (which drops EXIF), and names the
file by SHA-1 of its own bytes rather than anything the user supplied. The only
real gap was the missing rate limit, now closed.

**The shared `data/resume.json` — CLOSED 2026-09-10.** The browser owns the
résumé now (`localStorage`), and the server is a pure render-and-export
service: POST it a document, get a PDF or `.docx` back, nothing kept. Exports
carry the document in the body. `CVSTAND_SERVER_STORE=0` turns the
shared-file routes off for deployment.

One finding from building it, because it would have shipped as a silent leak:
**the browser store alone does not close the hole.** `/builder` seeds the page
from `load_resume()`, so with the server mirror still on, visitor A's autosave
becomes visitor B's starting document — the leak moves from the store to the
SEED and looks fixed from every angle except two browsers side by side.
`tests/e2e/test_browser_store.py` runs exactly that, against a server started
with the flag off. It is why the flag is a deployment requirement and not a
preference.

That also makes §5.5's privacy line literally true rather than a slogan: on a
deployment the CV never touches the server's disk. The footer says so.

Still open before exposure:
- **No authz** on `/api/*` or `/export/*` — arrives with accounts. Moot while
  nothing is stored server-side and nothing is sold; the first item of the
  build spec above.

---

## 12. What could not be evidenced

State these as unknown rather than guessing:

- **No conversion-rate or revenue data** for any resume builder at this scale.
  Nothing public and credible was found. The price ladder in §8 is a hypothesis.
- **Arabic-builder pricing is largely invisible** — the Arabic segment's paid
  tiers (StylingCV "premium templates", Tadween's credits) do not publish
  numbers. §4's "saturated with free" claim is well supported; "and nobody
  successfully charges" is *not* proven, only unobserved.
- **Paddle/Lemon Squeezy MENA coverage** — not confirmable from public sources.
- **Stripe's current KSA/UAE/Egypt merchant status** — sources conflict (UAE
  described as limited support, KSA as supported, Egypt unclear). Check
  stripe.com/global directly.
- **Where you are incorporated** is an input I do not have, and §9 branches
  entirely on it. That is the first thing to settle.
- Search tooling is US-region, which under-samples Arabic-language and
  Gulf-local results. The MENA half of §4 is thinner than the global half and
  should be treated as directional.

---

## Sources

Global pricing: [FlowCV pricing](https://flowcv.com/pricing) ·
[Kickresume comparison](https://www.kickresume.com/en/help-center/10-best-resume-builders/) ·
[Zety review/pricing](https://resufit.com/blog/zety-review-pricing-is-it-worth-it/) ·
[Resume.io review](https://resufit.com/blog/resumeio-review-pricing-templates-worth-it/) ·
[Paywall/trap survey](https://resufit.com/blog/the-ultimate-guide-to-truly-free-resume-builders-no-hidden-costs-or-paywalls/) ·
[Spotting paywalls](https://www.jobshinobi.com/blog/how-to-spot-paywalls-in-free-resume-builders) ·
[Zety download paywall](https://pitchmeai.com/blog/zety-resume-builder-download-paywall) ·
[Cost survey](https://www.resumetemplates.com/career-advice/how-much-does-a-resume-builder-cost/)

MENA market: [Bayt Premium](https://www.bayt.com/en/premium/) ·
[Bayt employer pricing](https://business.bayt.com/pricing/) ·
[StylingCV Arabic templates](https://stylingcv.com/arabic-resume-templates/) ·
[CV-In-Arabic](https://cv-in-arabic.com/) · [CV Gulf](https://cv-gulf.com/) ·
[Arabic RTL gap](https://tadween.me/blog/best-resume-builder-arabic) ·
[Canva ATS/Arabic](https://stylingcv.com/compare/canva-resume-alternative/)

Willingness to pay: [Fastest-growing app markets 2026](https://adapty.io/blog/fastest-growing-app-markets-2026/) ·
[UAE/KSA consumer behaviour 2026](https://www.biobrain.io/blog/consumer-behavior-trends-in-uae-and-saudi-arabia-for-2026) ·
[Deloitte digital consumer KSA/UAE](https://www.digitalretailnews.com/en/articles/deloitte-digital-consumer-trends-2025-uae-ksa)

Rails and compliance: [mada conversion 2026](https://voxire.com/blog/mada-payment-conversion-saudi-2026/) ·
[Saudi gateway integration guide](https://logiolegion.com/blogs/payment-gateway-integration-saudi-arabia-developer-guide) ·
[Gateway fee comparison](https://gulfsaasreview.com/article/payment-gateway-fees-saudi-arabia-2026) ·
[Tap vs HyperPay vs Moyasar](https://logiolegion.com/blogs/tap-payments-vs-hyperpay-vs-moyasar-saudi-arabia-2026) ·
[ZATCA compliance 2026](https://synergystrat.com/zatca-vat-compliance-guide-2026/) ·
[KSA VAT registration](https://noblecoreksa.com/vat-registration-saudi-arabia/) ·
[MoR for MENA SaaS](https://readcrucible.com/articles/stripe-vs-paddle-vs-lemon-squeezy-for-mena-saas) ·
[Stripe global](https://stripe.com/global) ·
[Egypt payment methods](https://xpay.app/blog/payment-methods-egyptian-customers-prefer) ·
[Egypt payments transformation](https://www.thunes.com/insights/trends/egypts-payments-transformation-a-regional-hub-in-the-making/)
