# AI assistant in the builder — plan (Claude Haiku 5.5)

**Written 2026-10-18. PLAN ONLY — nothing in this document is built, no API
call has been made, and no environment variable was added or changed.**

This supersedes the model choice in the older root `AI_ASSISTANT_PLAN.md`
(2026-09-11, which picked Claude Opus 5 and built a dark `POST /api/assist`
with no buttons). Its product decisions still stand: the assistant works from
what the user wrote and never invents facts; it PROPOSES text and the user
accepts it; nothing logs the user's text; Arabic is judged as Arabic, not as
translated English. What changes here: the model (Claude Haiku 5.5, the
user's choice), the three phases below, and the money controls.

**The September assistant has its own switch, OFF** (run 11, 2026-10-19):
`app/assist.py` `ENABLED = False`, a code constant, not an environment
variable. Adding ANTHROPIC_API_KEY turns on Import my CV and nothing else;
`/api/assist` answers 404 and builds no client while the switch is off
(tests/test_assist.py). Its model is now Claude Haiku 5.5. Switching it on is
a reviewed commit, made only after the owner approves this plan.

Related, built in the same run: **Import my CV** (`app/importer.py`), which
uses the same key, the same model, the same daily-limit store and the same
spending cap described here. It is the first thing that will spend money once
the key exists.

---

## 1. The three phases

| Phase | What the user sees | What is sent to Claude | What comes back |
|---|---|---|---|
| **1. Improve** | An **Improve** / **حسّن** button beside the Summary box and beside every bullet | the one text, the CV's name, title and that role (context), the document language | 1 rewritten version (plus 1 alternative for the Summary), shown under the box with **Use this** / **Keep mine** |
| **2. Tailor to this job ad** | A **Tailor to a job ad** / **خصّص لإعلان وظيفة** button above the form; the user pastes the ad | the whole CV (text fields only, no photo), the pasted ad | a review screen like Import's: a new Summary, rewritten bullets that match the ad, skills worth listing that the CV already proves — each item accepted or rejected on its own |
| **3. Write my cover letter** | A **Write it for me** / **اكتبه لي** button in the Cover letter section (built this run, item 3) | the whole CV + the job ad if the user pasted one + recipient / company / subject from the letter form | greeting, 3–4 paragraphs and closing, filled into the letter form for the user to edit; never sent anywhere else |

Rules that hold in every phase:
- **Same language as the document** (`resume.lang`): an Arabic CV gets Arabic
  back, an English CV English. EN ⟷ AR adaptation stays a separate, explicit
  action (the old plan's job 2), never a side effect.
- **No invention.** The system prompt forbids new employers, dates, numbers,
  degrees or skills; a number may only be reused if it is in the user's text.
  Tailoring may reorder and reword, never add experience.
- **Nothing is written to the CV until the user accepts it**, and acceptance
  goes through the normal form path, so it is validated, saved per language
  and undoable like typing.
- **Structured output** (`output_config.format`, a JSON schema per job) so
  the reply is parsed, not scraped — Haiku 5.5 rejects assistant prefill, so
  the old "start the reply with `{`" trick is not available.

## 2. Model and settings

- **Model:** `claude-haiku-5-5` (Claude API, first party).
- **Thinking:** Haiku 5.5 thinks by default at effort `medium`, and thinking
  is billed as output. Rewriting one bullet needs none: send
  `thinking: {"type": "disabled"}` (accepted at effort `high` or below) for
  Phase 1; `effort: "low"` with thinking on for Phases 2–3, where planning a
  letter around a job ad earns a little reasoning. Measure on 20 samples
  before changing either.
- **No sampling parameters** (`temperature`, `top_p`, `top_k`): Haiku 5.5
  answers 400 to non-default values; vary wording through the prompt.
- **Prompt caching:** the system prompt (rules + the JSON schema + 2–3 short
  examples, ~1,200 tokens) is identical for every user, so it is cached;
  Haiku 5.5 caches prefixes from 512 tokens. Order stays stable-before-volatile
  (system → CV → the one text), as `app/assist.py` already does.
- **Refusals:** a `stop_reason: "refusal"` is shown as "This text could not
  be processed" and costs the user one use; Haiku 5.5 has no server-side
  fallback, and none is added.
- **The old `MODEL = "claude-opus-5"` in `app/assist.py` changes to Haiku 5.5
  in Phase 1** — that file is the endpoint Phase 1 reuses.

## 3. Where the API key lives

- **Railway → the CVStand service → Variables → `ANTHROPIC_API_KEY`.** Added
  by the user, never by Claude Code, never committed (`.gitignore` already
  excludes `.env*`; the secrets audit greps for `sk-ant-`).
- The app reads it at request time (`os.environ`), so adding it needs a
  redeploy/restart of the service, nothing else. Without it every AI button
  shows **Coming soon / قريباً** and every AI route answers 503 before any
  work is done (already true of `/api/assist` and of Import).
- Use a **separate Anthropic workspace** for CVStand (Claude Console →
  Workspaces), so its key, usage and spend limit are its own.

## 4. What it costs (current list prices)

Claude Haiku 5.5, prompts of 100K tokens or fewer: **$0.10 per million input
tokens, $0.50 per million output tokens**; cached input read at 0.1x
($0.01/M), 5-minute cache write at 1.25x ($0.125/M). (Prompts over 100K
tokens cost $0.50 / $2.50 — no CVStand request comes near that.) The
tokenizer counts about 30% more tokens than Haiku 4.5 did; the estimates
below already use the larger count, and Arabic text is counted at ~1.5x the
English for the same content.

| Use | Input tokens | Output tokens (incl. thinking) | Cost per use (EN) | (AR) |
|---|---|---|---|---|
| Improve one bullet | ~2,000 (1,200 cached) | ~250 | **$0.0002** | $0.0003 |
| Improve the Summary (2 versions) | ~2,300 (1,200 cached) | ~500 | **$0.0004** | $0.0005 |
| Tailor to a job ad | ~5,500 | ~2,200 | **$0.0016** | $0.0022 |
| Write my cover letter | ~5,000 | ~2,000 | **$0.0015** | $0.0021 |
| Import my CV (built) | ~5,500 | ~3,500 | **$0.0023** | $0.0030 |

So **one dollar buys roughly 4,000 bullet Improves, 600 tailorings, 650
letters or 430 imports** (English; about a third fewer in Arabic). These are estimates from the prompt sizes in this plan, not
measurements: the first real calls should log `usage` (counts only, never
text) and this table gets corrected from them.

## 5. Limits: per user per day, and a monthly cap

**Per user per day** (resets at midnight UTC):

| Action | Limit |
|---|---|
| Improve (bullets + Summary together) | 40 |
| Tailor to a job ad | 5 |
| Write my cover letter | 5 |
| Import my CV | 10 (built this run) |

Worst case, one user maxing every limit in Arabic: 40×$0.0005 + 5×$0.0022 +
5×$0.0021 + 10×$0.003 = **≈ $0.07 a day**.

"User" = the signed-in account when there is one, otherwise the visitor's
client key (IP-based, `app/limits.client_key`). Counts live in the SQLite
database already on the Railway volume (`/data/cvstand.db`, table
`ai_usage(day, who, action, count)`), so they survive a restart; nothing else
about the request is stored. The in-memory per-minute rate limit
(`CVSTAND_LIMIT_ASSIST`) stays as a burst guard on top.

**Monthly spending cap, in two layers:**
1. **Anthropic's own limit** — set a monthly spend limit on the CVStand
   workspace in the Claude Console (suggest **$20/month** to start). This is
   the hard stop that holds even if the app's own count is wrong.
2. **The app's own budget** — every response's `usage` × the prices above is
   added to `ai_spend(month, usd)` in the same database. At **$15** (75% of
   the Console limit) every AI button switches to "The AI assistant is
   resting until next month" / "المساعد متوقف حتى الشهر القادم", before
   Anthropic starts refusing. Both numbers are settings
   (`CVSTAND_AI_MONTHLY_USD`), set on Railway by the user.

## 6. Privacy notice (shown before the first use, and under every AI button)

> **EN** — When you use the AI assistant, the text you ask it to work on and
> the CV it needs for context are sent to Anthropic, the company that makes
> Claude, to process your request. CVStand does not store that text, and
> Anthropic does not use it to train its models. Nothing is changed in your
> CV until you accept a suggestion.

> **AR** — عند استخدامك للمساعد الذكي، يُرسَل النص الذي تطلب العمل عليه
> والسيرة الذاتية اللازمة للسياق إلى شركة Anthropic، صانعة Claude، لمعالجة
> طلبك. لا يحتفظ CVStand بهذا النص، ولا تستخدمه Anthropic لتدريب نماذجها.
> لا يتغيّر شيء في سيرتك الذاتية حتى توافق على الاقتراح.

The same wording goes into the privacy section of the site. (Anthropic's
commercial terms: API inputs and outputs are not used for training; standard
retention applies on Anthropic's side — link their policy, do not paraphrase
it further.)

## 7. Error handling

| What happens | What the user sees | What the server does |
|---|---|---|
| No `ANTHROPIC_API_KEY` | buttons read **Coming soon / قريباً**, disabled | 503 before any work |
| Daily limit reached | "You've used today's N. More tomorrow." | 429, counted per action |
| Monthly budget reached | "The AI assistant is resting until next month." | 503, no call made |
| 429 / 529 from Anthropic (busy) | "Busy right now — try again in a minute." | the SDK's 2 retries with backoff first; the use is NOT counted |
| 5xx / timeout / network | "The assistant didn't answer. Your CV is unchanged." | logged with the request id only; use not counted |
| `refusal` | "This text could not be processed." | counted (Anthropic billed it) |
| Reply fails the JSON schema | "That didn't come back right — try again." | one silent retry, then this message |
| Text too long | the button is disabled with the reason | checked before sending |

Never logged: the user's text, the CV, the job ad, the reply. Logged: action,
token counts, cost, status, Anthropic request id.

## 8. Time estimate

| Phase | Work | Estimate |
|---|---|---|
| Shared groundwork | `ai_usage` / `ai_spend` tables, daily + monthly gates, privacy notice EN/AR, Coming-soon states, model switch in `app/assist.py`, error mapping (most of this is shared with Import, built this run) | 0.5 day |
| 1. Improve | 2 prompts + schemas, buttons on Summary and bullets, suggestion UI with Use / Keep, undo, tests with a mocked client, 20-sample Arabic review by the user | 1.5–2 days |
| 2. Tailor to a job ad | prompt + schema, paste box, per-item review screen (reuses Import's), tests | 2 days |
| 3. Write my cover letter | prompt + schema, button in the letter section, fill + undo, tests | 1 day |
| First real calls | measure cost and quality on 20 EN + 20 AR samples, correct §4 | 0.5 day + the user's review |

Total ≈ **6 working days** of build, plus the user's sample reviews between
phases. Each phase ships on its own and stays dark until the key exists.
