# Merge plan — `feature/word-fidelity` → `main` (PREPARED, NOT EXECUTED)

Prepared 2026-10-03 (run 5), updated 2026-10-04 (run 6). **Nothing below has
been run.** Every step that changes `main`, GitHub or production needs your
explicit go-ahead, and the push of `main` is a **deploy** (Railway
auto-deploys `main`; spec §9.6).

Branch head: see `git ls-remote origin refs/heads/feature/word-fidelity`.
`main` is still e56240d, the branch point, so the merge has no conflicts.

## 1. Merge gate (spec §9.3–9.7) — run 6 results

| Gate item | Status | Evidence |
|---|---|---|
| Full suite incl. browser tests, on the final commit | SUITE_STATUS | see §1a |
| `tools/verify_docker_context.py` | PASS | 450 required files survive `.dockerignore`, no local state ships. Required now also: the 24 Word designs, `word_layouts.json`, `word_themes.json`, `calibration.json`, the two demo résumés, the t22 rail pictures (`app/static/rails/*.png`). Forbidden now also: `docs/review/` (excluded from the image in run 6) |
| `tests/test_requirements_cover_imports.py` | PASS | no new runtime package (the rail pictures are pre-rendered; Word export still needs no browser) |
| Secrets audit (§9.4) | PASS | `git ls-files`: no `.env`, `*.db`, `venv/`, `data/resume.json`; `.env.example` placeholders only; no key patterns in tracked text |
| English output unchanged | PASS | HTML + pixel goldens 247/247 green after the t22 rail change (the rail's immunity to the Fonts panel changes nothing without choices) |
| Goldens updated? | **NO** | none changed, none need your approval |
| Typography step 7 (optical scale) | OFF | only on with `CVSTAND_OPTICAL_SCALE=1` — not set, must not be set |
| Word check | DONE | run 6: all 96 demo/long files opened and exported by Microsoft Word (this PC, Microsoft 365) with no prompt; 46/48 demos ≤ 10 % strict difference from the PDF, all one page |
| Other programs | DONE | LibreOffice 26.8: t2/t22 EN+AR shapes now drawn (bars, rings, rail) — review page "Portability" |

### 1a. Full suite on the final commit
SUITE_DETAIL

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
git merge --no-ff feature/word-fidelity -m "Merge feature/word-fidelity: Word designs for all 24 Modern templates (portable shapes, t22 rail), Arabic policy faces and phone isolates"
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

## 6. Rollback

Any check in §5 fails → redeploy the deployment ID noted in §4.1 from the
Railway dashboard. Then `git revert -m 1 <merge commit>` on `main` and push it
— ANOTHER deploy, needs approval — so `main` matches what runs.

## 7. Not part of this merge

No env vars, no `/data` volume, no DNS. Step 7's optical scale stays OFF.
