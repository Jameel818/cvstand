# Merge plan — `feature/word-fidelity` → `main` (PREPARED, NOT EXECUTED)

Prepared 2026-10-03 (run 5), updated 2026-10-04 (run 6) and 2026-10-07
(run 8). **Nothing below has been run.**

## Verdict (run 8): READY for step A - on your go-ahead

Every gate passes on the final commit (table below). Two things are yours to
decide and do NOT block the merge: item 3 of run 8 (English t7/t9/t12 at
12pt run to 2 pages - options in the queue/review page, recommendation O1),
and the user-settings results (large chosen sizes can give a 2-page Word
file where the PDF stays on one - the spec's "Page flow" decision accepts a
second page; details in §1b). Not merged, not pushed to `main`. Every step that changes `main`, GitHub or production needs your
explicit go-ahead, and the push of `main` is a **deploy** (Railway
auto-deploys `main`; spec §9.6).

Branch head: see `git ls-remote origin refs/heads/feature/word-fidelity`.
`main` is still e56240d, the branch point, so the merge has no conflicts.

## 1. Merge gate (spec §9.3–9.7) — run 8 results

| Gate item | Status | Evidence |
|---|---|---|
| Full suite incl. browser tests, on the final commit | **PASS** (run 8) | 4035 outside e2e + 1339 browser = 5374 passed, 0 failed (2 tests updated for run 7/8 behaviour; 1 intermittent passed on re-run) - see §1a |
| `tools/verify_docker_context.py` | PASS | 450 required files survive `.dockerignore`, no local state ships. Required now also: the 24 Word designs, `word_layouts.json`, `word_themes.json`, `calibration.json`, the two demo résumés, the t22 rail pictures (`app/static/rails/*.png`). Forbidden now also: `docs/review/` (excluded from the image in run 6) |
| `tests/test_requirements_cover_imports.py` | PASS | no new runtime package (the rail pictures are pre-rendered; Word export still needs no browser) |
| Secrets audit (§9.4) | PASS | `git ls-files`: no `.env`, `*.db`, `venv/`, `data/resume.json`; `.env.example` placeholders only; no key patterns in tracked text |
| English output unchanged | PASS | HTML + pixel goldens 247/247 green after the t22 rail change (the rail's immunity to the Fonts panel changes nothing without choices) |
| Goldens updated? | **NO** | none changed, none need your approval |
| Typography step 7 (optical scale) | OFF | only on with `CVSTAND_OPTICAL_SCALE=1` — not set, must not be set |
| Word check | DONE | run 8: 40 changed demos re-measured in Microsoft Word (Microsoft 365, this PC): **46/48 ≤ 10 % strict**, all 48 one page (exceptions t9 EN 15.2 / AR 12.6, as run 6). Sidebars checked on Word's SCREEN (window captures, 19 templates EN+AR) and in its PDF |
| Sidebars solid on screen | PASS | run 8: page shapes copied into the body (`docx_design.body_page_shapes`); tests/test_docx_run8_sidebars.py fails if page 1's colour is header-only or a gap opens |
| Other programs | DONE | LibreOffice 26.8: t2/t22 EN+AR shapes now drawn (bars, rings, rail) — review page "Portability" |

### 1a. Full suite on the final commit
Run 6, five batches (Word closed), at `0e5f6e8` and fixed up to `6eef4c4`:
- Batch 1 (everything outside tests/e2e): 4005 passed / 47 skipped / 2
  failed - both from the t22 rail change (the RTL mirroring guard: the rail
  box no longer mirrored -> the word now moves inside a mirrored box; the
  policy-faces test now excludes the rail's fixed face). Both files re-run:
  pass (212 incl. HTML goldens).
- Batch 2: 70 passed.
- Batch 3: 409 passed / 1 failed - the PDF font test counted the rail's fixed
  Cairo Black as an unchosen font; it now allows AND requires it in t22 AR.
  Re-run: 8/8.
- Batch 4: stopped by Claude Code for LOW SYSTEM MEMORY at ~95 %, 3 failures
  before that point - the t22 cases of test_typography_apply (the rail no
  longer follows the Fonts panel, as required); the test now leaves the rail
  to test_t22_rail.py. Re-run: t22 cases 24/24; the rest of batch 4 (Word
  builder, Word layout/theme gates, calibration page, the rail) 17/17.
- **Batch 5 (autofit / overflow / void gates, 247 tests) did not run on this
  commit** - the low-memory stop came first and, per Claude Code's rule, it
  was not restarted. It passed in run 5 at e52b464; since then the PDF side
  changed only for the t22 rail (and the rail's checks pass). **Run it before
  step A** (close Word/LibreOffice and other heavy apps; ~5 min):
  `venv/Scripts/python -m pytest --e2e -q tests/e2e/test_autofit_gate.py tests/e2e/test_overflow_gate.py tests/e2e/test_void_gate.py`
  and, for a clean record, the non-t22 part of batch 4:
  `venv/Scripts/python -m pytest --e2e -q tests/e2e/test_typography_apply.py`
- Known intermittent: test_form_feedback::test_adding_a_role_and_naming_it_works_end_to_end.

Run 8 (2026-10-07), on the final code, foreground, Word closed, small batches:
- Outside e2e: 4035 passed / 0 failed (one run-7 test now allows t1 Arabic's
  mild fit - run 8 item 4).
- Batch 5: void 50, overflow 99, autofit 98 = **247 passed**.
- typography_apply 595 passed; the other 27 e2e files 497 passed after one
  test (Word builder, t22 at 11pt) learnt that the type fit may scale the
  chosen size down to 0.90; test_shell_rtl_geometry's gallery-thumbnail case
  failed once and passed alone (12/12) - timing.

### 1b. User settings in Word (run 8) - page counts, Word vs PDF
- (a) Details Markazi Text 12pt (the user's downloads), all 24: Arabic 23/24
  one page (t24 two); English (Markazi is not offered in English, so 12pt in
  the template face) 13/24 one page - t5 t6 t7 t9 t12 t13 t14 t17 t18 t21
  t24 two pages; the PDF keeps all of these on one.
- (b) Source Serif 4, largest sizes (EN), t2 t7 t9 t12 t15 t21: t9 t12 t21
  two pages (PDF: one).
- (c) Noto Naskh Arabic, largest sizes (AR), same six: all two pages (PDF:
  one, except t9).
- Why: the PDF's autofit also compresses line height; Word's lines stay
  natural (your rule). Accepted by the "Page flow" decision; the open option
  is run 8 item 3 (type floor 0.88).

## 2. What goes live

**Word (.docx) export — the main change.**
- All 24 Modern templates export their own DESIGN to Word
  (`app/exporters/word_designs/t1…t24.py`, `docx_design.py`), EN and AR
  (Arabic right to left, mirrored). **46 of 48 demo CVs are within 10 % of
  the PDF** (≥ 90 % similar) in Microsoft Word; exceptions modern-t9 EN
  (14.6 %, font design: Archivo 900 vs Word's Archivo Black) and AR (12.7 %,
  content taller in Word). Every demo is one page.
- **Design shapes are portable** (`docx_dml.py`): DrawingML that LibreOffice,
  Google Docs and WPS draw, with the old VML kept as the fallback for older
  Word. Layout proven identical to before.
- **modern-t22's rail word** is fixed artwork in every program: a 300 dpi
  picture in the page header (never editable, never follows the Fonts panel);
  Arabic in Cairo Black, filling the rail.
- Run 7/8: Word takes the PDF's autofit steps (block gaps to 0.85, type to
  0.90, line spacing natural) when a page would spill; sidebars are solid
  on Word's screen (page shapes in the body, not only the header); rounded
  corners without hairlines; t23 pill/dots, t21 header, photo rings, t20,
  t10 sliders + rounded card, t1 side spacing.
- Fixes found while polishing: Arabic pages no longer get an invisible
  default header (t13 band was 23 px low), rounded cards no longer show a
  square strip under their corners, t21's name column, t19's contact line,
  t15's photo, Word line spacing rules for caps names and tight lines.
- Generic layout masters as the fallback (`docx_layout.py`,
  `app/word_layouts.json`, 4 new `word_masters/modern_*`); a one-page fit
  estimator (`docx_measure.py`); Word follows the builder's chosen fonts and
  sizes; Arabic joined lines keep phones left to right.

**PDF / preview.**
- English: pixel-identical (goldens).
- Arabic: the policy faces really load (Tajawal, Cairo, IBM Plex Sans
  Arabic); phone numbers isolated (t4 `555-0100-22`); a chosen font no longer
  downloads unused policy faces; **modern-t22's Arabic rail word is now Cairo
  Black filling the rail** (was IBM Plex at 140 px, ~2/3 of the rail).
- Both languages: modern-t22's rail word no longer follows the Fonts panel.

**Builder.** New visitors start from the one-page DEMO résumé.

**Not user-visible.** `/dev/typography` (404 unless debug), step-7 data (OFF),
`run.py` (dev only), tools (`build_t22_rail.py`, …), tests, `docs/review/`
(repo only — **no longer copied into the image**).

## 3. Merge (step A — needs your approval)

```
git checkout main
git pull --ff-only origin main            # main must still be e56240d
git merge --no-ff feature/word-fidelity -m "Merge feature/word-fidelity: Word designs for all 24 Modern templates (portable shapes, t22 rail, solid sidebars, Word autofit), Arabic policy faces and phone isolates"
venv/Scripts/python tools/verify_docker_context.py
venv/Scripts/python -m pytest -q tests/test_requirements_cover_imports.py
venv/Scripts/python -m pytest -q          # fast loop on the merge commit
```
Stop here and report. Nothing has reached GitHub or production yet.

## 4. Deploy (step B — needs your separate approval AS A DEPLOY)

1. Note the CURRENT live deployment ID in the Railway dashboard (rollback target).
2. Push (§9.5 form only):
   `GIT_TERMINAL_PROMPT=0 git -c credential.interactive=never -c core.askPass= push origin main`
   then `git ls-remote origin refs/heads/main` must equal the merge commit.
3. Railway builds and deploys `main` (≈1–3 min; installs only `requirements.txt`).

## 5. Live checks (step C — right after the deploy)

On `https://cvstand-production.up.railway.app` and `https://cvstand.com`:
1. `venv/Scripts/python tools/smoke_deploy.py <url>` — all checks pass.
2. Builder, fresh private window, English: modern-t2 → Word + PDF; Word shows
   the design; PDF one page.
3. Arabic (`/lang/ar`): modern-t2, t11, t22 → Word right to left with the
   design; t22's rail word is the red picture down the right edge; t11's
   contact phone reads `555-0138-64`; Arabic PDF fonts are Tajawal / Cairo /
   IBM Plex Sans Arabic only.
4. modern-t22 with a font chosen in the Fonts panel (EN and AR): the rail word
   is unchanged in the preview, the PDF and Word.
5. Open one t2 AR and one t22 AR download in LibreOffice or Google Docs: bars,
   rings and the rail appear.
6. modern-t4 Arabic: reference phones `555-0100-22`, `555-0177-31`.
7. Railway logs: no 500s on `/export/docx` or `/export/pdf`.
8. Open a modern-t2 and a modern-t3 Word download (EN + AR) in Word, Print
   Layout, cursor in the body: the sidebar is one solid colour from the page
   top to the foot, no pale band, no light line at its inner edge.
9. Arabic, Fonts panel Details = Markazi Text 12pt: modern-t7 and t15 Word
   downloads are one page.

## 6. Rollback

Any check in §5 fails → redeploy the deployment ID noted in §4.1 from the
Railway dashboard. Then `git revert -m 1 <merge commit>` on `main` and push it
— ANOTHER deploy, needs approval — so `main` matches what runs.

## 7. Not part of this merge

No env vars, no `/data` volume, no DNS. Step 7's optical scale stays OFF.
