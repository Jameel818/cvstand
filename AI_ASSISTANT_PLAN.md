# AI writing assistant — plan and locked decisions

**Planned 2026-09-10/11. PHASE 1 BUILT 2026-09-11.** Phases 2-5 not started.
Decisions below were settled in discussion. §7's two open questions are both
ANSWERED — see §7. The next thing that happens is Phase 2, and Phase 2 is not
code: it is the user reading twenty Arabic samples.

Companion to `MONETIZATION.md` (what is sold, and for how much) and
`RESUME_HERE.md` item 5 (the payment track this belongs to).

---

## 1. What it is

An AI assistant inside the builder that helps the user WRITE their CV, not
lay it out. Five jobs, all through one endpoint and one model — the difference
between them is the prompt and the button, not the architecture:

1. **Rewrite a weak bullet** — "Managed social media accounts for 3 brands"
   becomes something with a verb and a number.
2. **EN ⟷ AR adaptation** — *the important one*. Not translation. Literal
   translation gives Arabic words in English sentence structure: grammatically
   fine, immediately reads as translated, job titles rendered literally instead
   of by the term Arabic speakers actually use. Adaptation rewrites it as an
   Arabic CV would be written in the first place.
3. **Draft the summary** from the rest of the document.
4. **Suggest bullets** from a job title, for the empty-box problem.
5. **Tailor to a pasted job ad.**

**Scope decided: all five (was "option 2").** The earlier argument for shipping
only the bilingual one was strategic, not technical, and it conflated two
separate things — which features EXIST versus which feature you LEAD WITH in
marketing. Having all five does not stop the landing page leading with the
bilingual one. Technically they are the same endpoint; the extra four are about
a day of prompt and UI work.

**The bar is good Arabic, not Gulf hiring conventions.** Settled by the user
2026-09-11, and it removes most of the risk this feature carried: "write
convincing Arabic" is something a native speaker can judge in twenty samples,
where "encode Gulf recruitment norms" would have needed a domain expert.

---

## 2. Why it is worth building

The reputable half of the market draws its paid line exactly here. From
`MONETIZATION.md` §3: FlowCV gates **AI** behind Pro; Teal's entire paywall
**is** AI credits; Kickresume paid is premium designs + AI. Templates and
exports are free everywhere. AI is what people actually pay for.

It also addresses the real user pain. People do not struggle with layout — 49
templates solve a problem users do not feel acutely. They struggle with **what
to write in the box**, and that is what stops a CV being finished.

**The trap to avoid:** "AI writes your CV" is the most commoditised feature in
the category, and recognisably-AI prose is now discounted by recruiters. A
generic assistant makes users' CVs worse at your expense. The prompts must
refuse to invent facts and must work from what the user actually wrote.

---

## 3. Privacy model — DECIDED

This is the first feature that sends the user's CV off their machine, and it
runs directly into the promise shipped in the footer on 2026-09-10:
*"Your résumé stays in your browser. It is never stored on our server."*

**The decision (the user's, and better than the alternative that was
recommended): AI is PAID-ONLY, OPT-IN, off by default, revocable.**

Why that shape wins:

- The **free tier keeps an absolute, unqualified privacy claim** — no AI at
  all, so nothing to qualify. That claim is an acquisition asset in this
  market, not boilerplate.
- The **paid user gets full document context**, so the assistant actually
  writes well. The rejected alternative (send only the field being worked on)
  protected the promise by crippling the feature for people who had already
  paid for it.
- The footer stays true as written. Free users never touch AI; paid users who
  decline never touch it; paid users who accept have text **processed**, not
  **stored**. The word carrying the claim is "stored" — which stays honest
  only as long as request bodies are never logged. **Test that.**

### The consent copy (drafted, ready to use)

Three surfaces, because one disclosure in one place is not enough — it belongs
at purchase AND at the moment of use.

**On the purchase page:**
> Includes AI writing help — optional, and off until you turn it on.

> يشمل مساعدة الكتابة بالذكاء الاصطناعي — اختيارية، ومعطّلة حتى تُفعّلها.

**First time they switch it on (once per user):**
> **Use AI to help write this?**
> Your résumé normally never leaves your browser. To rewrite text, we send the
> part you're working on to an AI service. We don't store it, and you can turn
> this off at any time.
> [Use AI] [Not now]

> **هل تريد استخدام الذكاء الاصطناعي للمساعدة في الكتابة؟**
> سيرتك الذاتية لا تغادر متصفحك عادةً. ولإعادة صياغة النص، نرسل الجزء الذي
> تعمل عليه إلى خدمة ذكاء اصطناعي. نحن لا نحفظه، ويمكنك إيقاف هذه الميزة في
> أي وقت.
> [استخدام الذكاء الاصطناعي] [ليس الآن]

**The toggle itself, with a permanent helper line:**
> AI writing help — off by default. The text you're working on is sent to an
> AI service to be rewritten.

> مساعدة الكتابة بالذكاء الاصطناعي — مُعطّلة افتراضياً. يُرسل النص الذي تعمل
> عليه إلى خدمة ذكاء اصطناعي لإعادة صياغته.

Tone is deliberate: state the mechanism in one sentence and move on.
Over-explaining privacy makes people suspicious — a long disclaimer reads as
something being hidden.

### ⚠ Do not ship without checking this

*"We don't store it"* is a claim about YOUR server and is true by construction
— don't log request bodies and it stays true.

Deliberately **NOT** written above: any claim about what the AI provider does
with the text — retention windows, training, processing location. Those are
real legal commitments. **Read Anthropic's current commercial terms and either
add a specific accurate sentence or stay silent.** A privacy statement that
turns out to be wrong is far worse than one that says less.

---

## 4. Technical decisions

Taken from the `claude-api` skill on 2026-09-11 — re-check before building, the
API drifts.

| | Decision | Why |
|---|---|---|
| Model | `claude-opus-5` | The default, and SETTLED 2026-09-11: Arabic adaptation stays on Opus 5 regardless of cost, because Arabic that reads as written rather than translated is the entire paid proposition. Sonnet 5 ($2/$10 per MTok) and Haiku 4.5 ($1/$5) are levers for the OTHER four jobs, to be measured in Phase 2 — not a default, and not a Phase 1 decision. Two cautions on that split: prompt caches are model-scoped, so a cascade forfeits cache reuse across its models, and current guidance is to measure the capable model at lower effort before building one at all. |
| Streaming | Yes | A writing assistant that pauses four seconds then dumps a paragraph feels broken. |
| Thinking | Leave adaptive (on by default on Opus 5) | Disabling it on Opus 5 has two documented failure modes. Lower the effort instead. |
| Thinking display | `display: "summarized"` | Default is `omitted` on Opus 5, which streams a long silence then text. |
| Effort | `output_config: {effort: "low"}` | These are short rewrites, not reasoning problems. Effort is the main spend lever. |
| Caching | Cache the system prompt + CV context | Stable across the 20–30 rewrites in one session. **Caveat:** the minimum cacheable prefix is 512–4096 tokens depending on model, so a short system prompt silently will not cache — verify with `usage.cache_read_input_tokens`, do not assume. |
| Key | Server-side only | Never in `builder.js`. |
| Route | `/api/assist`, own bucket in `app/limits.py` | Same pattern as `/api/render`, `/api/photo`, the exports. |

### Cost per call (measured against the price)

A bullet rewrite: ~1,400 input tokens (system + CV context + the bullet), ~150
output.

- **~1.1¢ per assist** uncached, before thinking tokens
- caching drops most of the input cost on repeat calls in a session
- a heavy session of ~30 assists: **~$0.30–0.50**

**⚠ That 1.1¢ EXCLUDES thinking tokens, and thinking is ON by default on Opus
5** (adaptive; disabling it has two documented failure modes, so effort is the
knob instead). Thinking is billed as output at $25/MTok. At `effort: low` the
real figure is plausibly **1.5-3¢**, not 1.1¢ — roughly double. It does not
change any decision in this file (AI is still 2-7% of a ~$7.30 net pass), but
it is the difference between a measured number and a remembered one.
**Phase 1 ships the instrument rather than the estimate:** every `done` frame
carries `usage`, so the first real session answers this by observation.
Counters only — never the text; see the privacy note in §3 and
`tests/test_assist.py::test_done_carries_counters_and_no_text`.

Against a **SAR 29 (~$7.70)** pass this is comfortable. Against the SAR 10 that
was first proposed it was most of the revenue — see `MONETIZATION.md` §8 for
that arithmetic, which is what moved the price.

### The schema boundary — non-negotiable

Model output goes through `validate()` **before** it can touch the résumé. The
templates run on `StrictUndefined`, and an AI-written field that skips
`normalize()` is a 500 in a user's PDF. The assistant **proposes**; the user
accepts; the accepted value takes the normal validated path.

---

## 5. Phases

**1 — Plumbing, and the hard job first. DONE 2026-09-11.** `anthropic` dependency, server-side
key, `/api/assist` with its own rate-limit bucket, streaming, caching. Ships
exactly ONE capability: **EN ⟷ AR adaptation**. First because it is the one
with real quality risk; everything else is a variation on plumbing that works.
*Built: `app/assist.py`, `POST /api/assist` (SSE), an `assist` bucket in
`app/limits.py`, `anthropic>=1.5` in requirements, 28 tests in
`tests/test_assist.py`. Fast loop 1609 -> 1637, 0 errors. 10 mutations applied,
10 caught.*

**2 — Arabic quality gate. STOP/GO. ← YOU ARE HERE.** Twenty real before/after
pairs, reviewed by a native speaker (the user). If the Arabic is not
convincingly native, the prompt is reworked before anything is built on top of
it. Cheap now, expensive after four features depend on it. *User's review time.*

**The harness is BUILT (2026-09-11): `tools/assist_samples.py`.** It does not
grade anything — no test distinguishes "correct Arabic" from "Arabic a native
speaker would write on a CV", and that judgement is the entire gate. It runs
the twenty cases through the REAL `app.assist.adapt` (not a copy, so the gate
cannot drift from the app) and writes `tools/assist_review.html`: source and
result side by side, each cell carrying its own `dir` and an Arabic face, with
the four failure modes as checkboxes.

    venv/Scripts/python tools/assist_samples.py --dry-run  # list, no calls
    venv/Scripts/python tools/assist_samples.py --preview  # layout, no calls
    venv/Scripts/python tools/assist_samples.py            # the real run

Cases are drawn from the SHIPPED samples wherever possible. Six are deliberate
traps, because the shipped samples are too well written to test the promises
the prompt actually makes:

| | Trap | The failure it catches |
|---|---|---|
| 9, 10 | A weak, vague line | Coming back *stronger* — an invented fact, which is the one unrecoverable failure |
| 11, 12 | Already in the target language | A silent paraphrase of text nobody asked it to touch |
| 17 | Mixed script in one line | Latin tool and company names dragged into Arabic script |
| 18 | A date range and a percentage | Numbers altered, or Arabic-Indic digits |

**It also answers the two things §4 marks as estimated rather than observed**:
the real cost per assist including thinking tokens, and whether caching
engaged at all. Both printed, and both on the review page. Reading order and
what to look for are in the module docstring — read that before the results.

**It needs `ANTHROPIC_API_KEY`, which does not exist in the dev environment.**
No live call has been made from any of this code. `--preview` was used to
verify the page's layout, `dir` and font on known input before a run costs
anything.

**3 — The other four jobs.** Same endpoint, different prompts and buttons.
*~half a day.*

**4 — Consent and gating.** The toggle, the first-use dialog, the five Arabic
catalogue rows, the entitlement check, the daily fair-use ceiling. *~half a day.*

**5 — Tests.** The schema boundary; the consent toggle genuinely stopping calls
(not just hiding the button); the rate limit; the label gate on the new
strings. *~half a day.*

**Complexity: MEDIUM.** ~2–2.5 days of build, plus the user's review in Phase 2.

---

## 6. Risks

| | Risk | Mitigation |
|---|---|---|
| **HIGH** | Arabic reads as translated rather than written | Phase 2 is a gate, not a checkbox |
| **MEDIUM** | Five entry points means more calls per user inside a FIXED-price pass. "Paste a job ad" is the expensive one — large input every time | The daily fair-use ceiling matters more with five jobs than it would with one |
| **MEDIUM** | Generic AI prose that makes CVs worse | Prompts must refuse to invent facts and work only from what the user wrote |
| **LOW** | AI output bypassing `normalize()` breaks the templates | §4, and Phase 5 gates it |
| **LOW** | API key exposure | Server-side only |

---

## 7. ANSWERED 2026-09-11 — both, by the user

1. ~~**Go-ahead for Phase 1?**~~ **GIVEN.** Phase 1 is built.

2. ~~**Is it acceptable that this ships dark?**~~ **YES**, and the proposed
   handling is what shipped: `assist.has_ai_access()` returns `True` today and
   is CALLED on the real path, so Stage 3 changes one return value rather than
   going looking for where the gate should have been. It is gated by a test
   that asserts a `False` answer stops the request **before** the provider is
   billed — the property that actually matters — rather than asserting the
   constant.

   The argument that settled it: a working bilingual demo is ammunition for the
   Stage 2 institutional conversations, which are the part that produces
   revenue. Shipping dark is not idle inventory here; it is the demo.

**Note the tension worth re-reading before starting:** the user wants price to
be the marketing hook (`MONETIZATION.md` §8a), which argues for building the
paid features. The standing strategic advice is that price is a CONVERSION
tool, not an ACQUISITION one — it works on someone who already found the site,
and does nothing to get them there. Stage 2 (institutional outreach) is still
what produces revenue. Do not let a good offer feel like a growth plan.
