# CVStand — build status & guide

A single-user résumé builder web app. Enter your details once, switch between
designer layouts in two families (**Modern** and **ATS-Friendly**), preview
live, and export **PDF** and **Word (.docx)**.

## Run it

```
venv/Scripts/python -m pip install -r requirements.txt   # add --trusted-host flags if pip SSL-errors
venv/Scripts/python -m playwright install chromium        # for PDF export
venv/Scripts/python run.py                                # http://127.0.0.1:5000
venv/Scripts/python -m pytest -q                          # unit + contract, ~8s
venv/Scripts/python -m pytest --e2e -q                    # + the browser suite, ~158s
venv/Scripts/python -m pytest --e2e -q -m "e2e and not slow"   # browser, minus the 49-template gate (~85s)
venv/Scripts/python -m pytest --e2e -q --junitxml=junit.xml    # machine-readable report for CI
```

## Architecture

| Piece | File(s) | Notes |
|---|---|---|
| App factory / routes | `app/__init__.py`, `app/routes.py` | landing `/`, gallery `/templates`, builder `/builder`, `/api/*`, `/export/*` |
| Data contract | `app/schema.py` | JSON Schema for the resume dict + `normalize()` (fills optionals, caps stat chips at 4, drops blank chips, adds dot counts, derives `lang`/`dir`). `lang` is optional and absent-means-`en`, so pre-bilingual résumés need no migration |
| Template registry | `app/registry.py` | catalogue of all 49 layouts (24 modern + 25 ats); `_PORTED` set marks which are live |
| HTML rendering | `app/rendering.py`, `app/templates/resumes/<cat>/<block>.j2`, `_macros.j2` | each `.j2` emits only the 850×1100 `.tpl` canvas; `document_html()` wraps it with fonts + print CSS for preview & PDF |
| Auto-fit | `app/static/js/autofit.js`, `tools/verify_autofit.py` | compresses vertical rhythm (→0.85) then type (→0.90) until the résumé seats on one 1100px page. Inlined into every document by `document_html()`; self-starts after `fonts.ready`. Preview, PDF and the verify tool all await `window.ResumeAutofit.ready`, so all three paginate identically |
| PDF export | `app/exporters/pdf.py` | headless Chromium via Playwright, 850×1100 page, `printBackground`; renders `document_html(..., for_pdf=True)` so fonts are embedded; awaits the auto-fit before `page.pdf()` |
| Fonts (Latin) | `app/static/fonts/`, `tools/fetch_fonts.py` | 11 families self-hosted (34 `.woff2`, latin + latin-ext). `fonts.css` for the preview, `fonts_inline.css` (data: URIs) for PDF. No CDN. **Never re-run to add a script** — it would rebuild these files from what Google serves today. |
| Fonts (Arabic) | `tools/fetch_fonts_ar.py`, `fonts_ar*.css` | 5 Arabic families aliased **under the Latin family names**, confined by `unicode-range` to Arabic — so all 49 templates get Arabic glyphs with no edit, and no alias can claim a Latin codepoint. Loaded only for `lang="ar"`. |
| Labels (i18n) | `app/labels.py`, `tests/test_labels.py` | every fixed string the 49 templates print goes through the Jinja global `t()`. **The msgid IS the English string**, so `t()` is the identity in English and no English text can drift; Arabic lookup folds case and whitespace, collapsing ~40 casing variants onto ~55 rows. Language comes from a `ContextVar` set by `canvas_html()`, NOT `@pass_context` — templates import `_macros.j2` *without* context, so a context-based `t()` would silently return English inside any macro. `join_labels()` also translates the separator and conjunction, which Arabic needs as much as the words. |
| RTL typography | `app/rendering.py::RTL_TYPOGRAPHY`, `tests/test_rtl_typography.py` | one stylesheet, emitted by `document_html()` **only when `dir="rtl"`**. It does exactly one thing: gives `sec-head` size and weight back. In Arabic a heading loses its small-caps-and-tracking cue entirely (no case; Chromium applies tracking to zero gaps inside a joined run), and four templates — `ats-t13/19/21/23` — had nothing else. The other 45 carry hierarchy by size, weight or a rule and are untouched. The planned document-wide `letter-spacing`/`text-transform` purge was measured, found to fix nothing and to wrap a masthead, and dropped. |
| RTL mirroring | all `.j2` files, `tests/test_rtl_mirroring.py` | every directional CSS declaration is **logical** (`padding-inline-start`, `border-inline-start`, `inset-inline-start`, `text-align:end`, `padding-block`/`padding-inline` for the 4-value shorthand). In LTR each is its physical twin, so the pixel gate proves English did not move. Three static guards run in the fast loop; a `slow` browser test renders all 49 twice and checks each positioned element's centre lands at `width - centre_ltr`. `transform` has no logical form — `modern-t22`'s rotated rail is negated by a direction-scoped rule instead. |
| Mixed content (bidi) | `tests/test_bidi_mixed.py`, `tests/samples.py` | an Arabic résumé naming `Halden & Row`, and the mirror. **No isolation is applied and none is needed** — measured 0 findings across all 49 templates in Chromium (both mixtures) and per character in real Word, so the `<bdi>` / `unicode-bidi: isolate` pass the plan called for was dropped rather than shipped (session 23, the same shape as the phase-4 purge). The file gates what the bidi algorithm already gives us, on four properties that are unambiguous whichever way a reader scans the line: a field's glyphs stay contiguous, two inline elements do not overlap, a separator stays between the pair it separates, a Latin run reads LTR and an Arabic run RTL. **"The earlier field must be further right in RTL" is the wrong check** — it reports 33 of 49 templates broken, all false, because an LTR island inside an RTL line is read left-to-right. |
| Both directions | `tests/samples.py` | `ENGLISH` / `ARABIC` / `BOTH` / `MIXED` / `REVERSED`, imported as `from tests import samples`. The four catalogue suites that have historically found this project's real defects (`test_smoke`, `test_partial_entries`, `test_partial_contact`, `test_unrated_skill`) parametrise over `BOTH`, so every degrade contract is claimed in Arabic too. The English half of each pair carries **no `lang` key**, which keeps absent-means-English under test at the same time. Note the two shipped samples differ in one way that bites test authors: the Arabic one sets `percent` on every skill and the English one sets none, so Arabic renders `95%` where English renders `Expert`. |
| Interface language | `app/i18n.py`, `app/labels.py::ui_t`, `tests/test_ui_language.py` | the shell's language is a `ui_lang` **cookie**, deliberately independent of the résumé's own `lang`: editing an English résumé from an Arabic interface is an ordinary case. `ui_t()` falls through to the document catalogue so a form label and the heading it produces cannot disagree. The builder gets its strings as a table keyed by the FOLDED msgid (the two catalogues are cased differently). **Level words are the exception** — they are stored in the document, so they follow the résumé, not the reader. |
| Document language control | `app/static/js/builder.js` (`doclang` field, `levelRemapPlan`), `app/labels.py::all_levels`, `tests/test_document_language.py`, `tests/e2e/test_language_control.py` | the one control in Basics that writes `resume.lang`. Until it existed, `lang` was reachable **only by hand-editing `data/resume.json`** — it is in the schema and drives `dir`, the label catalogue, the Arabic font sheet and which Word master the export takes, and a bilingual user could type Arabic and had no way to say so. It reads the FILE, never the `ui_lang` cookie: the header switcher is the other language and stays unrelated (`app/i18n.py`). Changing it re-offers the other language's level words **without a reload** (the page ships both vocabularies) and *offers* to translate the ones already stored. The remap is POSITIONAL — index `i` is the same strength in both lists — so the fast loop gates that the two vocabularies stay the same length, aligned by dot count and ordered strongest-first. Declining is a valid answer: `LEVEL_DOTS` maps both vocabularies, so an English `Expert` in an Arabic résumé still draws five dots, it just reads in Latin. |
| Shell RTL geometry | `app/static/css/app.css`, `tests/e2e/test_shell_rtl_geometry.py` | `transform` has no logical form, and it slips a static guard by construction — it is not a directional *property*, it is a directional *value*. Three surfaces scale a full résumé iframe into a small box (landing hero, gallery thumbnail, drawer mini); `transform-origin: top left` is a PHYSICAL corner, so in RTL each render landed outside its `overflow:hidden` window and **every card a person picks a template from was blank in Arabic** — with all 49 iframes loaded and each `.tpl` present in the DOM. Fixed with a `[dir="rtl"]` origin override. The builder's `#preview-stage` was never affected: its origin is `top center`, which is direction-agnostic. The gate is geometric (horizontal overlap ≥ 90% in both directions, and the two directions within 2% of each other) because "did it load" was true throughout. Vertical overlap is reported but NOT asserted — these boxes clip vertically on purpose. |
| Showcase vs. own résumé | `app/routes.py::preview`, `app/store.py::load_showcase`, `tests/test_showcase_language.py` | `/preview` serves four surfaces and they do not want the same document. **With `showcase=1`** (landing hero, gallery cards) it renders the sample for the reader's INTERFACE language, because those cards demonstrate a layout — an Arabic visitor must not be shown English résumés. **Without it** (builder preview, drawer minis) it renders `load_resume()`, because there you are choosing a layout for your own content and stock text would be a lie. The showcase reads the `ui_lang` cookie and NEVER `resume["lang"]`: coupling them would look right whenever the two agree and would undo the independence `app/i18n.py` exists for — the sharp case is an Arabic document read through an English interface. The sample is cached as TEXT and re-parsed per call, so one of ~49 cards on a gallery load cannot poison the other 48. |
| Horizontal overflow | `tools/verify_overflow.py`, `tests/e2e/test_overflow_gate.py` | the OTHER axis. Auto-fit owns the vertical one and warns when it loses; too-WIDE content is silent — painted outside the 850px canvas, and the PDF page IS the canvas, so it is simply absent from the export. Measured across all 49 templates in both languages 2026-09-09. Three outcomes are separated and only two fail: **outside** the canvas and **clipped** with no ellipsis are silent loss; **ellipsised** is signalled loss and is allowed (`modern-t21`'s contact pill does it on purpose). Found and fixed one real defect — `modern-t12`'s `white-space:nowrap` headline, 39px off-canvas in English and 65px in Arabic. **Two instrument errors are documented in the tool and matter to anyone extending it**: a `Range`'s rects are NOT transform-aware in Chromium (`modern-t22`'s rotated rail reads as 20px of lost text on the shipped sample), and a Range reports the FULL run even where an ancestor clips it, so the rect must be intersected with intermediate clippers before it is compared with the canvas. The shipped sample is run as a control in both languages precisely to catch that class of error: a check that fails on the résumé this project ships is measuring the wrong thing. An unbroken 120-character token still overflows all 49 and is deliberately NOT fixed — see the gate's docstring for the two global rules that were tried and dropped. |
| Golden gates | `tests/golden/`, `tools/golden.py`, `tests/test_golden_{html,pixels}.py` | the regression net for the bilingual work: HTML fragment per template (fast, in the default loop) + rendered canvas (opt-in `--e2e`). Independent on purpose — see `tests/golden/README.md` for which change may move which. |
| DOCX export | `app/exporters/docx.py`, `word_masters/`, `tools/build_word_masters.py` | `docxtpl` fills a Word master per **(category, direction)** — 4 masters for all 49 layouts × 2 languages; masters are **generated by the builder script**, not hand-authored. RTL needs four things said in the XML (`w:bidi` on sectPr AND pPr, `w:rtl` on rPr, and the complex-script `w:rFonts/@w:cs`/`w:szCs`/`w:bCs`) plus `w:bidiVisual` on the chip table; `_apply_rtl()` applies them as a post-pass. A missing RTL master **raises** rather than falling back to English. |
| Browser suite | `tests/e2e/`, `tests/conftest.py` | the whole test session runs against a temp `CVSTAND_DATA_DIR`, never the real `data/`. Opt-in with `--e2e`: boots the real server on a throwaway `CVSTAND_DATA_DIR` and drives Chromium. Journey, offline, exports, content editing, the auto-fit bar's three states, and the 49-template auto-fit gate (marked `slow`). `test_journey_ar.py` is the ARABIC journey (13 tests): the shape differs, not just the strings — `dir` on the shell, `dir` inside the preview iframe, and the two languages proven independent through a browser. Note the builder overrides `{% block chrome %}` with an empty block, so there is **no language switcher on the builder page** — it is driven from the gallery. Any route-level test that writes the store must snapshot and restore it (`test_smoke.py::stored_resume`): the whole session shares one data dir, and `/export/*` reads the SAVED résumé. |
| Store | `app/store.py`, `app/static/js/builder.js`, `app/config.py::SERVER_STORE`, `tests/test_stateless.py`, `tests/e2e/test_browser_store.py` | **The BROWSER owns the résumé** (`localStorage`, keys `cvstand:resume` / `cvstand:template`); the server is a pure render-and-export service that keeps nothing. `data/resume.json` is ONE global file — right for a tool on your own machine, and the single thing that cannot survive a public URL, since two visitors read and overwrite each other with no bug anywhere in the code. It is not an authz gap accounts would close; it is one file where there needs to be one per person. `CVSTAND_SERVER_STORE=0` switches the old behaviour off: `PUT /api/resume` and `POST /api/template` answer 403, `GET /export/*` answers 405 + `Allow: POST`. **Set it for any deployment more than one person can reach** — and note WHY it is not optional: the browser store alone does not close the leak, because `/builder` seeds `#resume-data` from `load_resume()`, so with the mirror on, visitor A's autosave becomes visitor B's starting document. Measured through two browser contexts 2026-09-10. Exports take the résumé in a POST body (`routes._export_subject`), which also removes the window in which a save and a read could disagree. |
| Rate limits / admission | `app/limits.py`, `tests/test_limits.py` | Two guards answering two questions. **Rate limit** — per-client token buckets on `/api/render`, `/api/photo` and both exports, answering 429 + `Retry-After`. **Admission control** — a global bounded semaphore capping concurrent PDF renders, answering 503. The second is the one a rate limit cannot do: `app/exporters/pdf.py` launches a **whole Chromium per request**, and fifty clients making one request each are all inside any per-client limit while still putting fifty browsers on the box. Both in-memory and per-process; multi-worker means per worker, which is the moment to move the state out rather than raise the numbers. `ProxyFix` is opt-in via `CVSTAND_TRUSTED_PROXIES` — trusting `X-Forwarded-For` when nothing strips it is worse than ignoring it, since any client could then mint a fresh bucket per request. |
| Escaping | `app/rendering.py::_br_join`, `tests/test_escaping.py` | Thirteen templates joined user fields with a literal `<br>` and marked the result `| safe`, which cannot tell the separator from the values it separates. An email or skill name containing markup rendered live — in the preview, the drawer, and inside the headless Chromium the PDF exporter drives. `Markup.join` escapes each item and keeps the separator as markup. Harmless while single-user and local; stored XSS the moment it is not. Reverting all 13 fails exactly 20 tests (10 templates × 2 languages). |
| Accounts | `app/db.py`, `app/auth.py`, `/account/sign-{up,in,out}`, `app/templates/account.html`, `tests/test_auth.py` | **Stage 3 Phase 1. Anonymous use is unchanged and that is the point** — all 49 templates, unlimited PDF, both languages and the whole builder need no account, which `MONETIZATION.md` §6 calls an acquisition asset rather than a gap. An account is what you make when you BUY something. SQLite (`users`, with `pass_expires_at` already present for Phase 2), scrypt via `werkzeug.security`, session cookie carrying `uid` + `session_version`. That version is re-read from the database on every request, so a password change evicts sessions elsewhere — a cookie is a claim the user holds and only something they do not control can retire it. Sign-in failures say ONE thing for "no such account" and "wrong password", and `authenticate()` hashes a dummy when the account is missing so the TIMING does not leak what the message refuses to. Sign-out is POST (a GET that changes state is CSRF-able and gets link-prefetched); `next` is path-only (an open redirect on a sign-in page is the classic phishing setup). **The app refuses to BOOT** when `CVSTAND_SERVER_STORE=0` and `SECRET_KEY` is still the shipped default: the cookie now carries who you are, so a known signing key mints a session as any user. 10 mutations, 10 caught. |
| AI assistant | `app/assist.py`, `POST /api/assist`, `app/limits.py` (`assist` bucket), `tests/test_assist.py` | **Phase 1 of `AI_ASSISTANT_PLAN.md` — one job, EN ⟷ AR adaptation.** Streams SSE frames (`thinking` / `delta` / `done` / `error`); `claude-opus-5`, adaptive thinking at `effort: low`, system prompt and CV-context carrying cache breakpoints in that order (stable before volatile, or nothing caches). Three load-bearing properties. **(1) It proposes text and never touches the résumé** — no `save_resume`, no `normalize`; the user accepts a value and it takes the ordinary validated path, which is the whole defence against a model-written field reaching `StrictUndefined` as a 500 inside someone's PDF. **(2) Nothing logs the text** — `done` carries usage counters only and the mid-stream error frame does not echo the exception, because an exception can carry the request; that is what makes *"we don't store it"* true by construction. **(3) The route pulls the first chunk BEFORE building the Response** — a lazy generator would answer `200 text/event-stream` and only then discover the request was a 402, this project's signature failure where the status names the wrong layer. `has_ai_access()` returns True and is called on the real path; Stage 3 changes one return. The `anthropic` dependency is optional at runtime — no key means 503 and nothing else changes. Tests are offline via an injectable `client`; 10 mutations, 10 caught. |
| PWA | `/manifest.webmanifest` + `/sw.js` routes, `app/static/js/sw.js`, `app/static/icons/`, `tests/test_pwa.py` | Deferred 2026-08-30 for a correct reason — an offline shell could do nothing while the résumé, preview and exports all lived on the server. The browser store changed half of that, so the form now works offline with the document already in `localStorage`; only the preview render and the two exports need the network. **Navigations are network-first on purpose**: the shell's language comes from the `ui_lang` cookie, so one URL has two correct responses and a URL-keyed cache would serve the wrong language — the same shape as the gallery thumbnails that rendered the wrong résumé. The worker is served from the ROOT, not `/static/js/`, or its scope would be `/static/` and it would never see a page. `VERSION` in `sw.js` is bumped by hand because Flask serves `/static` with no content hash. |
| UI | `app/templates/{base,landing,gallery,builder}.html`, `app/static/css/app.css`, `app/static/js/builder.js` | design system + vanilla-JS builder (form generation, live preview, autosave, template drawer, download) |

## Status

> Live progress is tracked in `RESUME_HERE.md` — that file is authoritative for
> what's ported. This section is the architectural summary.

**Done**
- Full app skeleton, data contract, registry, both export paths wired.
- Marketing landing, template gallery with category tabs, live builder
  (stepped form, live preview, zoom, autosave, template drawer, download menu).
- PDF export working (Chromium verified).
- **DOCX export working and verified in real Word** — both masters generated by
  `venv/Scripts/python tools/build_word_masters.py --verify`, which opens each
  over COM and checks it fits one page.
- Ported & compliance-checked — **all 49 live, porting COMPLETE** (all exact
  850×1100, no overflow, skill name+level as real text, chips hide when empty,
  no `::before`):
  - **Modern: 24/24 complete** (t1–t24).
  - **ATS: 25/25 complete** (t1–t25).
  - `_macros.j2`: `skill_dotrow` (+`name_css`/`level_css`), `skill_bar`
    (inline + `stacked`), `skill_ring` (conic dial, +`hole_bg` for dark cards),
    `skill_slider` (bar + knob), `rule_head`, `stat_band`, `experience_entry`,
    `education_entry`, `contact_lines`.
  - Divergences logged in each `.j2` header comment. Stale registry accents were
    corrected to the real template hex during the ring/slider batch.
- **The builder's first document follows the reader's language.** A résumé
  that does not exist yet has no language of its own to respect, so the seed —
  and only the seed — reads the `ui_lang` cookie: an Arabic visitor opens the
  builder onto `data/sample_resume_ar.json`, RTL, with `lang: "ar"` already
  set. Past that moment everything follows the DOCUMENT (`app/i18n.py`) and an
  edited résumé is never reseeded. At `SERVER_STORE=0` the seed is computed per
  request and never written, which is what stops the first visitor's language
  becoming the container's. `tests/test_builder_seed_language.py` +
  `tests/e2e/test_seed_language_journey.py`.
- **Auto-fit**: real user content is variable-length, so every document
  carries `app/static/js/autofit.js` and fits itself to the 1100px page before
  the preview settles or the PDF prints. Two stages — vertical rhythm to 0.85,
  then type scale to 0.90 — and no horizontal property is ever touched, which
  is what keeps full-bleed sidebars at the page edge and the absolutely
  positioned Modern layouts intact. Verified across all 49: a strict no-op on
  the shared sample, and 48/49 recover a +20% content overload. The one that
  cannot (`modern-t18`, a fixed-height card layout) reports `fitted: false` and
  the builder warns, as before. `tests/e2e/test_autofit_banner.py` covers the
  three things the builder says about that outcome.
- **Fonts self-hosted** — no `fonts.googleapis.com` anywhere; the app renders
  fully offline. Verified by loading each of the 11 families in Chromium with
  the network blocked. The **app shell** (`base.html`) was still linking the
  Google CDN until 2026-08-31 — a render-blocking stylesheet that cost ~21s per
  cold page load with no network. It now links the same self-hosted
  `fonts/fonts.css`; `tests/e2e/test_offline.py` fails on any off-machine
  request from any page.
- **Font licences vendored** — each family's full `OFL.txt` is in
  `app/static/fonts/licenses/` (`fetch_fonts.py --licences`), as OFL 1.1
  clause 2 requires for redistribution. `--check` and a unit test enforce it.
- **1741 tests passing** (24 skip as not-applicable) — 1412 in the fast loop
  (~18s) plus the browser journeys, the 50-image pixel gate, the RTL typography
  and mirroring gates, the shell RTL geometry gate and the mixed-content bidi
  gate behind `--e2e` (~600s).
  Chromium only; Firefox and WebKit are not installed and are not worth the
  download for a locally served single-user app.
  **The pixel gate only started running in that command in session 18** — it
  and `tests/e2e/` each opened their own `sync_playwright()`, and the second
  entry in a thread raises, so all 50 errored AT SETUP in every full run while
  passing when the file ran alone. Setup errors are not failures: pytest still
  printed "935 passed" and could still exit 0. There is now one session-scoped
  `_playwright` fixture in `tests/conftest.py` and a fast static guard
  (`tests/test_suite_invariants.py`) against a second one.
  **Note the fast loop has grown 3.5s → 18s** across sessions 13–23, because the
  half-filled-data contracts and the label/golden/mirroring sweeps each cover
  all 49 templates — and since phase 8 the content contracts cover them TWICE,
  once per language. Still fast enough to run on every edit, but if it keeps
  growing, give the catalogue sweeps their own marker rather than thinning
  them: they are what caught most of the defects found in those sessions.
- **Every template must render an incomplete résumé** (`tests/test_partial_entries.py`,
  49 × 2 in the fast loop — the same parametrise-the-catalogue shape the other
  contract tests use). The Jinja env is `StrictUndefined`, so a field the
  templates read but `normalize()` did not default is a 500, not a blank. Both
  the half-filled entry the builder's "+ Add" leaves behind and a name-and-title
  -only résumé used to 500 all 49; the per-entry blanks are now derived from
  `RESUME_SCHEMA` so a new optional field cannot reintroduce it.
- **An unrated skill degrades to text, never to a graphic**
  (`tests/test_unrated_skill.py`). A skill with no level word and no explicit
  percent has nothing to draw, but every graphic drew something anyway, and
  what it drew was a claim the user never made: an empty dot row reading "0 of
  5", a 0%-filled bar or slider, a ring printing a literal **"0%"**, and
  `"Ceramics —    "` in Word. Fixed in the 4 shared macros AND the 15 templates
  that inline their own skill markup; the 9 ATS layouts that print only
  name-and-level text were already correct. The test counts graphic markers
  with and without an unrated skill, so it states the property directly
  ("adding an unrated skill adds no graphic") rather than pattern-matching
  markup.
- **An upload is judged by its bytes, not its file name**
  (`tests/test_photo_upload.py`, 10 fast). `/api/photo` gated on
  `file.mimetype`, which is the **browser's guess from the extension** — so the
  gate only caught a user who picked a file with an honest one. Renaming a
  document to `.png` sends `image/png` and reached Pillow unguarded
  (`UnidentifiedImageError`), and a truncated photo has a valid header, so it
  survived `Image.open()` and blew up later inside `crop()`. Both escaped as an
  unhandled **500** that the builder printed as "error 500" — the app blaming
  its own server for the user's file, this project's recurring wrong-layer
  message. `img.load()` now forces the decode, the two cases get **different**
  advice ("not a photo" vs "damaged"), and the reason travels as JSON so the
  client shows what the server actually found instead of mapping a status code.
- **A failed template switch reports itself** (`tests/e2e/test_form_feedback.py`,
  3 browser). `buildDrawer`'s click handler ended a failure with a bare
  `if (!res.ok) return;` and had **no catch around the fetch at all**. A failed
  switch was therefore indistinguishable from clicking the template already
  selected, and a dropped connection became an unhandled rejection in the
  console. It is the one builder action with no feedback path of its own — the
  form has `#form-errors`, exports alert, saving has the indicator — and the
  scrim covers `#form-errors` while the drawer is open, so the drawer now
  carries its own `#drawer-error` line, cleared on reopen and on success.
- **A half-filled contact leaves no artefact** (`tests/test_partial_contact.py`).
  Both `label` and `url` are schema-required for a social link, so a fresh one
  is invalid until both fields are typed — but clearing one afterwards is
  valid and reaches the renderers. 29 layouts appended the label into a joined
  list (an empty one left `"… | wrenashworth.example.com | "`, a dangling
  separator); 8 rendered it as caption + value (an empty label left a bold
  blank caption above the URL). All guarded, plus `contact_lines`. The test
  measures the two artefacts as a **delta** against a résumé with no social
  link, so a layout is never blamed for markup it already had.
  The fast loop is unchanged in character — smoke/contract only (template test auto-covers every `_PORTED`
  key; 8 cover DOCX content, 11 OOXML schema validity, 9 fonts, 11 auto-fit
  wiring). Auto-fit *behaviour* needs a real layout engine and is checked by
  `tools/verify_autofit.py`, keeping `pytest -q` at ~3s.

**Not done yet**
- Per-template calibrated sample data — **dropped, not deferred**. `/preview`
  (the builder *and* all 49 gallery iframes) renders `load_resume()`, the
  user's live data, never `sample_resume.json`, so per-template samples would
  only have changed the first-run seed and the verification screenshots. The
  real defect was the opposite one — heavy content overflowing — and auto-fit
  closes it.
- ~~ship each font family's OFL.txt~~ — **done** 2026-08-31.
- ~~photo upload~~ — **done** (was mis-recorded as TBD): `POST /api/photo`
  square-crops and stores, `GET /uploads/<name>` serves, and the builder has the
  file input / preview / Remove control. Verified end to end.
- PWA manifest + service worker.

## Porting a template — the loop (per CLAUDE.md)

1. Extract the `<!-- N -->` / `id="tN"` block from the source `.dc.html`.
2. Create `app/templates/resumes/<cat>/tN.j2` emitting only the `.tpl` div,
   replacing placeholder content with `{{ r.* }}` holes and `{% for %}` loops
   over true siblings. Reuse `_macros.j2`.
3. Add `"<cat>-tN"` to `registry._PORTED`.
4. Restate the locked spec; walk `references/brief-compliance-checklist.md`
   against the rendered output; fix every fail; re-check.
5. Report deltas only.
