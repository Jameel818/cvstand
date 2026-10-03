# Merge plan — `feature/word-fidelity` → `main` (PREPARED, NOT EXECUTED)

Prepared 2026-10-03 (run 5). **Nothing below has been run.** Every step that
changes `main`, GitHub or production needs your explicit go-ahead, and the
push of `main` is a **deploy** (Railway auto-deploys `main`; spec §9.6).

Branch head at preparation: see `git ls-remote origin refs/heads/feature/word-fidelity`
(58 commits ahead of `main` e56240d; `main` has not moved since the branch
point, so the merge has no conflicts).

## 1. Merge gate (spec §9.3–9.7)

| Gate item | Status | Evidence |
|---|---|---|
| Full suite incl. browser tests, on the final commit | **NOT COMPLETE - re-run batches 4-5 first** | see §1a |
| `tools/verify_docker_context.py` | PASS | 447 required files survive `.dockerignore`, no local state ships. Run 5 added the files this branch needs to the required list (24 Word designs, `word_layouts.json`, `word_themes.json`, `calibration.json`, the two demo résumés the builder now seeds from), so the check now covers them |
| `tests/test_requirements_cover_imports.py` | PASS (3/3) | no new runtime package; the image installs only `requirements.txt` |
| Secrets audit (§9.4) | PASS | `git ls-files`: no `.env`, `*.db`, `venv/`, `data/resume.json`; `.env.example` holds placeholders only; no key patterns (sk-ant, AKIA, private keys) in tracked text |
| English output unchanged | PASS | pixel goldens green in the suite (all goldens are English); R4-3/R4-4 before/after: EN 0.00 % changed |
| Goldens updated? | **NO** | none changed, none need your approval |
| Typography step 7 (optical scale) | OFF | wired, only on with `CVSTAND_OPTICAL_SCALE=1`, which is NOT set and must not be set as part of this merge |
| §7.8 manual Word check | DONE earlier (Word 2013, 2026-09-28) for fonts; run 5 re-checked the Word designs in this PC's Word (Microsoft 365) | Desktop "CVStand Word fidelity review" |

### 1a. Full suite on the final commit
- At `e52b464` (after run 5's suite fixes): **5278 passed / 47 skipped / 0
  failed**, all 5 batches (3945 outside e2e + 1333 browser).
- After R4-8c's Word fix (`8115ced`, docx_design joined runs + 5 tests):
  batch 1 (everything outside tests/e2e) **3950 passed / 47 skipped / 0
  failed**; batch 2 **70 passed**; batch 3 **410 passed**; all 748 Word +
  Arabic-builder tests (test_docx_*, word e2e, arabic builder) **passed**.
- **Batches 4 (test_typography_apply, calibration page, word layouts/themes
  gates) and 5 (autofit/overflow/void gates) were stopped by Claude Code for
  LOW SYSTEM MEMORY** and, per its rule, not restarted. They passed at
  `e52b464`; the only code change since is Word-only (docx_design.run), which
  none of them exercise except the word gates (passed in the 748). Still: the
  gate says "full suite on the final commit", so **re-run them before step A**:
  `venv/Scripts/python -m pytest --e2e -q tests/e2e/test_typography_apply.py tests/e2e/test_typography_calibration_page.py tests/e2e/test_word_layouts_current.py tests/e2e/test_word_themes_current.py`
  then `... tests/e2e/test_autofit_gate.py tests/e2e/test_overflow_gate.py tests/e2e/test_void_gate.py`
  (close Word and other heavy apps first; ~5 + ~5 min).
- Known intermittent: test_form_feedback::test_adding_a_role_and_naming_it_works_end_to_end
  (timing under load; passed 5/5 alone and in the latest batch 2).

## 2. What goes live

**Word (.docx) export — the main change.**
- All 24 Modern templates export their own DESIGN to Word
  (`app/exporters/word_designs/t1…t24.py`, `docx_design.py`): sidebars,
  bands, rings, dot rows, bars, timelines, photo frames, in EN and AR
  (Arabic: right-to-left, mirrored columns). Measured against the app's PDF
  in real Word: demo CV one page in Word for 48/48; strict difference EN
  median 9.0 %, AR median 8.9 %; grades 2 MATCHES, 5 near MATCHES, 17 CLOSE.
- Generic layout masters as the fallback (`docx_layout.py`,
  `app/word_layouts.json`, 4 new `word_masters/modern_layout*/gutter*.docx`).
- A one-page fit estimator for Word (`docx_measure.py`).
- Word follows the builder: chosen fonts and sizes (Name/Headings/Details).
- Arabic joined lines (t6/t11/t19 contact line) keep phones left to right.

**PDF / preview — Arabic only (English pixel-identical).**
- Arabic documents now really draw the policy faces (Tajawal, Cairo, IBM
  Plex Sans Arabic) — before, preview and PDF fell back to system fonts
  (live: Liberation Sans / FreeSerif). Arabic PDFs stay small (46–77 KB).
- Phone numbers in Arabic documents are isolated (t4 references read
  `555-0100-22`, were `22-0100-555`) — all templates.
- An Arabic résumé with a chosen font no longer downloads the unused policy
  faces in the preview.

**Builder.** New visitors start from the one-page DEMO résumé
(`data/demo_resume*.json`) instead of the longer showcase sample.

**Not user-visible.** `/dev/typography` (404 unless debug mode — production
runs gunicorn, never debug), `app/typography/calibration.json` + registry
accessors (step 7, OFF), `run.py` (dev only; live-like by default), tools,
tests, `docs/review/` (423 files from this branch; the folder is ≈16 MB —
NOT used by the app, but `.dockerignore` excludes only `*.md` under docs/, so
they ARE copied into the image: harmless, just weight; see §7).

## 3. Merge (step A — needs your approval)

```
git checkout main
git pull --ff-only origin main            # main must still be e56240d
git merge --no-ff feature/word-fidelity -m "Merge feature/word-fidelity: Word designs for all 24 Modern templates; Arabic policy faces and phone isolates"
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
3. Railway builds and deploys `main` (≈1–3 min; the image build installs only
   `requirements.txt`).

## 5. Live checks (step C — right after the deploy, before announcing anything)

On `https://cvstand-production.up.railway.app` and `https://cvstand.com`:
1. `venv/Scripts/python tools/smoke_deploy.py <url>` — all checks pass.
2. Builder, fresh private window, English: modern-t2 → Download Word + PDF;
   Word opens with the design (yellow band, navy sidebar, bars); PDF one page.
3. Builder in Arabic (`/lang/ar`): modern-t2, t11, t22 → Word is right to
   left with the design; t11's contact line phone reads `555-0138-64`;
   Arabic PDF embedded fonts are Tajawal + IBM Plex Sans Arabic only
   (`pdffonts` or Acrobat → Properties → Fonts) — NOT Liberation/FreeSerif.
4. modern-t4 Arabic PDF and Word: reference phones `555-0100-22`, `555-0177-31`.
5. One EN and one AR PDF with a NON-default font chosen in the Fonts panel:
   the embedded font names match the choice (§7.5).
6. Railway logs: no 500s on `/export/docx` or `/export/pdf` during the checks.

## 6. Rollback

Any check in §5 fails → redeploy the deployment ID noted in §4.1 from the
Railway dashboard (dashboard only; the CLI cannot redeploy by ID). Then
`git revert -m 1 <merge commit>` on `main` and push it — that push is
ANOTHER deploy and needs approval — so `main` matches what runs.

## 7. Not part of this merge

No env vars, no `/data` volume, no DNS. Step 7's optical scale stays OFF.
Open decision for you: `docs/review/` (≈16 MB, 423 files from this branch)
goes into `main`'s history AND into the Docker image (docs/ is not excluded).
Options: keep as is; or add `docs/review/` to `.dockerignore` before merging
(one line, image only, re-run verify_docker_context.py). I have not changed
it - your call.
