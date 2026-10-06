# Word fidelity queue (run of 2026-10-01, ~15 h, user away)

Branch `feature/word-fidelity`. Take the next unticked item. After each item
and each template: Word tests, tick here, update RESUME_HERE.md, commit, push
the branch (§9 form), `git ls-remote`. Decisions go to
`docs/WORD_FIDELITY_AUDIT.md` "Decisions made during the run".
If lost: re-read this file, RESUME_HERE.md and the audit, continue.

Fidelity measure: Word's own PDF (Microsoft Word on this PC) vs the app's PDF,
both rasterised at the same size; % of pixels that differ per page (target
< 5 %, acceptable < 10 % with the same elements in the same places). Tool:
scratchpad `ovl.py`.

## 0. Setup
- [x] 0a. Overlay/diff tool (`ovl.py`) + baseline % for the 7 existing designs

## 1. Polish modern-t2 and modern-t4 (EN + AR)
- [x] 1a. Arabic fonts: PDF's embedded faces vs Word styles/runs, role by role; before/after table
- [x] 1b. Vertical spacing: match the PDF's section positions (sidebar + main)
- [x] 1c. t4 ribbon folded tab
- [x] 1d. Details: bar ends, Arabic name size, gap before References, date dash style

## 2. Demo CV
- [x] 2. Demo CV one page in PDF + Word, EN + AR, every template (re-checked per template in 3)

## 3. Per-template Word designs (EN + AR: audit, demo + photo + refs 1 page, long CV, overlay, grade)
Already built last run - re-measure with the overlay, polish if > 10 %:
- [x] modern-t8 (Band) - CLOSE, EN 7.0 % (tol 3.7) / AR 6.8 % (4.9), demo 1/1 page
- [x] modern-t10 (Sidebar) - CLOSE, EN 9.3 % (5.2) / AR 7.5 % (5.1), demo 1/1
- [x] modern-t15 (Sidebar) - CLOSE, EN 10.5 % (5.7) / AR 12.3 % (10.4, fallback faces), demo 1/1
- [x] modern-t20 (Sidebar) - CLOSE, EN 9.3 % (6.0) / AR 7.9 % (6.5), demo 1/1
- [x] modern-t23 (Sidebar) - CLOSE, EN 7.3 % (4.2) / AR 6.4 % (5.3), demo 1/1
Sidebar:
- [x] modern-t3 - CLOSE, EN 13.5 % (tol 6.5) / AR 10.7 % (7.9), demo 1/1, long 2 clean
- [x] modern-t5 - CLOSE, EN 11.2 % (tol 7.1) / AR 22.7 % (21.1; Arabic column ~50px longer: Word's Arabic faces vs the PDF's fallback), demo 1/1, long 2 clean
- [x] modern-t9 - CLOSE, EN 14.8 % (tol 8.1) / AR 13.4 % (9.3), demo 1/1, long 2 clean
- [x] modern-t16 - CLOSE (near MATCHES), EN 7.1 % (tol 2.4) / AR 7.9 % (6.6), demo 1/1, long 2 clean; rings = editable stroke shapes, % as text
- [x] modern-t17 - CLOSE, EN 8.1 % (tol 4.0) / AR 17.2 % (16.1; name block taller with Word's Arabic face), demo 1/1, long 2 clean
- [x] modern-t24 - CLOSE, EN 14.7 % (tol 11.1) / AR 23.7 % (21.9; Arabic faces vs the PDF's fallback), demo 1/1, long 2 clean
Band:
- [x] modern-t7 - CLOSE (near MATCHES), EN 8.3 % (tol 3.0) / AR 8.2 % (5.5), demo 1/1, long 2 clean
- [x] modern-t11 - MATCHES, EN 6.5 % (tol 1.8) / AR 6.0 % (4.2), demo 1/1, long 2 clean
- [x] modern-t13 - CLOSE, EN 8.9 % (tol 6.8) / AR 11.1 % (10.3), demo 1/1, long 2 clean
- [x] modern-t14 - CLOSE, EN 14.0 % (tol 11.5) / AR 17.0 % (15.5); overlapping panel/photo simplified (photo shows its uncovered 483-761px), demo 1/1, long 2 clean
- [x] modern-t18 - CLOSE, EN 8.7 % (tol 5.1) / AR 8.3 % (6.4), demo 1/1, long 2 clean; rail navy begins under the photo frame
- [x] modern-t21 - CLOSE, EN 14.1 % (tol 10.5) / AR 15.8 % (13.8); rounded cards via corner masks (side card's foot square), demo 1/1, long 2 clean
Open:
- [x] modern-t1 - MATCHES, EN 6.4 % (tol 2.5) / AR 6.5 % (5.7), demo 1/1, long 2 clean
- [x] modern-t6 - CLOSE (near MATCHES), EN 7.7 % (tol 3.3) / AR 8.6 % (7.0), demo 1/1, long 2 clean
- [x] modern-t12 - CLOSE, EN 9.1 % (tol 5.2) / AR 9.4 % (8.1), demo 1/1, long 2 clean; empty SKILLS/EDUCATION heads hidden
- [x] modern-t22 - CLOSE, EN 21.0 % (tol 17.2; the giant rail letters sit ~20px off) / AR 10.8 % (8.8), demo 1/1; RESUME rail = page-anchored vertical text box; long CV: the two-column block starts on page 2 (AR 3 pages)
Gutter:
- [x] modern-t19 - CLOSE, EN 9.9 % (tol 8.1) / AR 6.2 % (3.8), demo 1/1, long 2 clean

## 4. Font sizes
- [x] 4. Word applies the chosen SIZES (Name, Headings, Details), EN + AR, tests + real-Word check - DONE: factor per role as typography.js (designs + ATS/editorial masters), tests/test_docx_sizes.py, real Word t2/t11/ats-t1 EN+AR (all 1 page except ats-t1 AR = 2 at the larger sizes)

## 5. Review
- [x] 5. docs/review/word_fidelity_review.html + Desktop "CVStand Word fidelity review" (pdf / word-demo / word-long-p1 / word-long-p2 / overlay, grade, %, differences, .docx)

## 6. Full suite
- [x] 6. Close Word; full suite incl. browser tests; fix without weakening - 5232 passed / 47 skipped / 0 failed (25 min); one e2e test made design-aware (name on two lines)

## Follow-ups (NOT this run: the PDF/HTML templates stay unchanged)
- [ ] Arabic PDF shows reference phone numbers reversed; fix later in the HTML/PDF templates.
- [ ] Arabic PDF/preview draw system fallback faces (the policy families are never declared in the document); see the audit FINDING.

## Final
- [x] Final report, RESUME_HERE, commit, push, ls-remote, clean status

## Run 4 (2026-10-02, ~7 h, user away) — builder path NOT verified until item 1 says so
- [x] R4-1a. Which process serves :5000 (folder, branch, commit); stop any old server - port 5000 = this folder's run.py (feature/word-fidelity a602f8a = 775963 + a note); no other server
- [x] R4-1b. Real builder (Playwright, fresh context): t2 t4 t8 t11 t22 "Use this" + Word EN/AR vs Desktop files; export endpoint reaches docx_design - real builder (fresh context): t2 t4 t8 t11 t22 EN/AR all carry their design drawings; the endpoint calls render_docx -> docx_design
- [x] R4-1c. Builder with user-like data: no photo, empty sections, a chosen font, a changed size - user-like data (no photo, level words, chosen fonts/size): designs hold (EN 7-8 %); fixed level words breaking in t2/t5/t18 value cells, t11 AR spill (spread reserve), a NameError (t2) only with level words
- [x] R4-1d. Fix the cause + e2e test on the real builder path (template, language, Fonts panel, Download Word) - cause = local single-user mode (one stored data/resume.json, mixed language) -> run.py now live-like; tests/e2e/test_word_design_builder.py (6 cases)
- [x] R4-2a. Arabic: local builder vs live site (labels, sample, direction, previews, downloads) - live = Arabic demo; local = the stored English-bodied document; main locally identical (not a branch regression)
- [x] R4-2b. Fix what this branch broke (Arabic demo sample?), one-page Arabic demo - run.py live-like by default (browser store, throwaway key); --server-store keeps the old mode; Arabic demo is one page (run 1)
- [x] R4-2c. e2e: switch to Arabic -> preview Arabic + RTL, PDF and Word Arabic - tests/e2e/test_arabic_builder.py on the live-configured server
- [x] R4-3a. Arabic PDF/preview fonts actually used (3 Modern + 2 ATS, with/without a chosen font), local + live - no font chosen: local PDF = Segoe UI/Times/Tahoma, LIVE PDF = Liberation Sans/FreeSerif, previews local+live = Segoe UI/Times; chosen font: correct faces (local + live)
- [x] R4-3b. Why the policy faces aren't loaded; prepare the fix - cause: policy CSS named families no document declares; fix: 'CVT ' families + typography.css link (preview) / inlined faces (PDF) - APPLIED on the branch (affects RTL only)
- [x] R4-3c. Before/after images (EN unchanged + AR), list of goldens that would change (not updated) - before/after 5 templates: EN 0.00 % changed (pixel-identical), AR 4.7-6.9 % (fonts); goldens that would change: NONE (all goldens are English); images in scratch ba/ -> Desktop 'CVStand PDF font fix review' (8b)
- [x] R4-4. Arabic PDF reference phones reversed: fix in HTML/PDF templates, before/after, goldens listed - cause bidi W2 (digits after Arabic become Arabic numbers); every phone in an RTL document wrapped in LRI..PDI in canvas_html (all 50 templates); t4 AR now 555-0100-22 (was 22-0100-555), t2/t20 AR unchanged (0.00 %), EN 0.00 %; goldens that would change: NONE; tests/test_rtl_phone_isolates.py
- [x] R4-5. Seven fonts drawn as Calibri in Word: cause + fix, real Word check for each, tests - cause: all 7 are Microsoft 365 cloud fonts; Word prefers its cloud copy and shows Calibri on a PC's FIRST open while it downloads (cache dirs dated the minute of run 2's check); real Word now 7/7 exact (ats-t1, t2, t11, EN+AR, offered roles); no code change (renaming the faces would change the user's font names - decision 47); tests/test_docx_cloud_fonts.py (19)
- [x] R4-6. Polish weakest: t22, t14, t21, t3, t9, t24 (EN + AR, demo + long, re-grade)
  - [x] t22 - long CV fixed: columns now break across pages as stacks of unbreakable units (entry; heading + first entry; contact item; heading + first ring pair; ring pair) - EN long 2 pages with page 1 full (was: page 1 header only), AR 3 -> 2 pages, no orphaned heading/ring label; demo EN 20.9 % (tol 16.9) / AR 11.3 % (9.6), 1/1; grade CLOSE (rail letters still ~20 px off in EN)
  - [x] t14 - EN 14.0 -> 10.7 % (tol 7.8), AR 17.0 -> 9.7 % (6.6), demo 1/1, long 2 clean; grade CLOSE (near MATCHES). Causes: the estimator read the header (photo merged over 3 rows) as 415pt not 249pt, so the near-one-page fit squeezed the column (docx_measure: merged cells span their rows); the photo's 30px drop was re-tinied away (python-docx returns the merge's top cell); flags 2-3 lost their 13px gap; Arabic rail on the wrong side (bidiVisual borders are logical - fixed for all designs: t2 AR 9.1 -> 8.6, t4 AR 11.2 -> 7.9)
  - [x] t21 - EN 14.1 -> 12.2 % (tol 8.7), AR 18.3 -> 12.4 % (9.8), demo 1/1 (a fuller AR CV too), long 2 clean; grade CLOSE. Causes: bottom margin 24px larger than the PDF's (cards stopped short); the foot push was computed BEFORE the near-one-page fit shrank the column, so the stats card stopped ~55px short in Arabic - pushes now run after the fit (SidebarPage/ColumnPage; t4/t18 re-measured unchanged)
  - [x] t3 - no change kept (a row-gap calibration measured no gain, reverted); AR 10.7 -> 9.3 % (5.4) from the RTL border fix; EN 13.5 % (tol 6.5); demo 1/1, long 2; grade CLOSE (near MATCHES)
  - [x] t9 - EN 14.8 -> 14.6 % (tol 8.1 -> 7.6), AR 13.9 % (10.4); education lines keep the PDF's 16px strut (no font-size on .tpl), the drift at TECHNICAL halved (-17.8 -> -9.3 px); demo 1/1, long 2; grade CLOSE
  - [x] t24 - AR 23.7 -> 10.1 % (tol 6.3; the Arabic PDF now draws the policy faces, item 3), EN 15.0 % (10.9); education date column sized to its text (degree was ~6px late); demo 1/1, long 2; grade CLOSE. EN's rest: Word draws Microsoft's cloud Open Sans (heavier, ~2px taller lines)
- [x] R4-7. (time permitting) typography step 7 calibration, before/after, no goldens - tools/_ink.py + tools/calibrate_fonts.py (--instrument reproduces SIZE_ADJUST: Tajawal -0.7 %, Amiri +0.7 %; --check), app/typography/calibration.json (35 families EN+AR), registry optical_scale()/line_height(), /dev/typography (debug only) + e2e screenshot; the scale is wired into typography.js but OFF (CVSTAND_OPTICAL_SCALE=1) pending your review: 13 before/after images; goldens that would change: NONE (no typography keys in any golden)
- [x] R4-8a. Close Word; full suite incl. browser tests - run 5 (2026-10-03), in 5 batches (low-memory rules): 5278 passed / 47 skipped / 0 failed (3945 outside e2e + 1333 browser). Fixed: item 3's CVT faces broke 2 e2e tests (updated, stricter) + a real defect (Arabic with a chosen font downloaded the unused policy faces: rendering.rtl_typography) + 2 stale-gate tools (themes tool would have written "CVT Tajawal" into Word - prefix stripped, json unchanged; layouts sort read t13's side-by-side row by sub-pixel y - now row + reading order, t13 EN+AR Education first as its Word design). 1 timing flake (test_form_feedback, 5/5 alone). Decisions 57-59
- [x] R4-8b. Review page + Desktop folders (fidelity review; "CVStand PDF font fix review") - run 5: all 24 x EN/AR re-measured in real Word (4 batches, own Word instance only; the user's open Word untouched): demo 1 page in Word for 48/48; strict % EN 5.8-21.0 (median 9.0), AR 5.0-19.3 (median 8.9); run-2 numbers shown beside for comparison; no grade changed (2 MATCHES, t3/t6/t7/t14/t16 near MATCHES, rest CLOSE); weakest t22 EN (rail letters offset) and t5 AR (main column ~25px lower), designs intact. docs/review/word_fidelity_review.html + Desktop "CVStand Word fidelity review" (96 .docx) refreshed; "CVStand PDF font fix review" unchanged since run 4 item 8
- [x] R4-8c. Restart local server from feature/word-fidelity; real builder download uses the designs EN + AR - run 5: run.py live-like on :5000 (left RUNNING); real builder t2 t4 t11 t22 EN+AR: Word draws every design, Arabic RTL, Arabic PDF = Tajawal + IBM Plex Sans Arabic only, t4 AR phones 555-0100-22 (PDF + Word). Found + fixed: t11 (and t6, t19) Arabic contact line phone reversed in Word - joined runs split per item (decision 60, tests/test_docx_joined_rtl.py); re-checked in Word
- [x] R4-9 (run 5). Merge prepared, NOT executed: docs/MERGE_PLAN_WORD_FIDELITY.md (gate table, what goes live, merge / deploy / live-check / rollback). verify_docker_context.py PASS (now also requires the 24 Word designs, word_layouts/themes.json, calibration.json, demo resumes: 447 files); requirements test PASS; secrets audit PASS. OPEN: suite batches 4-5 on the final commit were stopped by low memory - re-run before merging
- [x] R4-final. Report, RESUME_HERE, commit, push, ls-remote, clean status

## Run 6 (2026-10-03/04) - portability, the t22 rail, the 90% target
- [x] R6-1. docs/review/ excluded from the Docker image; verify_docker_context.py forbids it (proved: removing the line fails the check)
- [x] R6-2a. Real Word first: t2/t22 EN+AR render (run 5 images); the user's LibreOffice defects reproduced (t2 AR bars missing; t22 AR rail horizontal/broken, rings grey only)
- [x] R6-2b. Shapes as DrawingML + VML fallback (app/exporters/docx_dml.py): bars, dots, sliders, rects, roundrects, custom paths, rings, nodes, page ovals, page-height fills; layout byte-identical to before (unwrapped), estimator reads the fallback; Word stacking range fixed; LibreOffice 26.8: bars, rings, rail now appear
- [x] R6-2c. tests/test_docx_portable.py (every shape DrawingML + VML fallback, docPr ids unique, ring angles, estimator equivalence); Word opened all 96 run-6 files with no prompt
- [x] R6-3. t22 rail word fixed artwork: never follows the Fonts panel (CSS/typography.js/autofit skip .vrail); Arabic Cairo Black 900 (96.8% of the rail; Alexandria too thick for the rail); Word = 300 dpi header picture (tools/build_t22_rail.py); tests/e2e/test_t22_rail.py + portability tests; English goldens unchanged (247/247)
- [x] R6-4. 90% target: 46/48 demo files <= 10% strict (all 1 page); exceptions t9 EN (Archivo 900 vs Word's Archivo Black + a URL wrap) and t9 AR (content taller in Word, fit needed) - decisions 61-68
- [x] R6-5. Full suite on the final commit, in batches - batches 1-3 run (4 failures, all from the fixed t22 rail, fixed and re-run green); batch 4 stopped by LOW MEMORY at ~95% (its 3 t22 failures fixed, the rest re-run green); batch 5 NOT run (stopped before it; not restarted per Claude Code's rule) - see the merge plan §1a
- [x] R6-6. Review page + Desktop folder (48-file table, LibreOffice column, rail before/after); merge plan gate results
- [x] R6-7. Local server running (live-site mode, :5000; GET /export/pdf -> 405)

## Run 7 (2026-10-06) - the user's review of the 24 Arabic downloads (decisions 69-73)
- [x] R7-1. Confirm every finding in Microsoft Word on the user's own files (one AR batch). The files carried Details 12pt Markazi Text (t1-t4, t6-t16), reproduced exactly. Real in Word: overflow (t3 t4 t7 t9 t12 t15 t16), t23 pill + half dots, t21 header fragments, t18 frame, t20 block, t10 sliders, t1 side spacing, sidebar hairlines. The rest is LibreOffice only (LibreOffice 26.8 draws the fills on the user's own files)
- [x] R7-2. Overflow: Word takes the PDF's autofit steps (gaps to 0.85, type to 0.90, never the line spacing). Your 7 AR overflows are now 1 page in Word. EN at the same settings: t7 t9 t12 still 2 pages at the floor
- [x] R7-3. Sidebar lines = corner-mask hairlines in print (not gridlines) -> masks overlap by 0.75pt; every other border scanned (48 designs) is in the PDF
- [x] R7-4. t23 dots + pill, t21 header masks, photo ring outer edge (t18 + all ringed photos), t20 photo strip, t10 sliders; EN gets the same code
- [ ] R7-5. Not fixed: t1 sidebar spacing (estimator ~60pt long on t1's side column), t10 card's rounded border, t21 side card's bottom corners, t4 AR blank p2 at 12pt with the default face
- [x] R7-6. Word re-measure of the 14 changed templates: all 56 Word PDFs made, demo 28/28 1 page. The strict-% compare was KILLED for low memory (not restarted)
- [x] R7-7. Tests: Word batch 854 passed / 23 skipped (incl. tests/test_docx_run7_fixes.py, 63). Browser batch 5 NOT run (low memory)
- [x] R7-8. Review page: "Run 7" section + docs/review/run7 before/after (44 images)
- [ ] R7-9. Open: the strict-% re-measure of the 14 changed templates (scratch ovl.py r7 ... - Word PDFs exist; only the compare remains); suite batch 5; then the merge decision

## Run 8 (2026-10-07) - sidebars on Word's screen, open items, merge gate (decisions 74-78)
- [x] R8-0. Sidebars: cause = Word dims the header layer (the colour lived only there). The fix copies the page shapes into the body (page 1 + last page). Verified on Word's screen (19 templates EN+AR, before/after window captures) and in Word's PDF; tests/test_docx_run8_sidebars.py. Page-2 options: A (page 1 only) vs B (page 1 + last page, applied)
- [x] R7-5/R8-4. t1 Arabic side spacing like the PDF (estimate bias + squeeze counted as overflow), 1 page
- [x] R7-5/R8-5. t10 skills card rounded (outline shape)
- [x] R7-9/R8-1. Strict-% re-measure of the 20 changed templates (5 Word batches of 8): 46/48 <= 10% (t9 EN/AR as run 6), all 1 page
- [x] R8-2. User-settings gate in Word: (a) Markazi 12pt all 24 EN+AR, (b) Source Serif 4 max (6 EN), (c) Noto Naskh Arabic max (6 AR) - every 2-page file listed in the merge plan §1b, with the PDF's page count
- [ ] R8-3. English t7/t9/t12 at 12pt: options O1 (type 0.88: all 1 page), O2 (gaps 0.80: t7 still 2), O3 (gaps 0.80 + type 0.86: all 1 page), or accept 2 pages - recommendation O1; WAITING for the user's approval (not applied)
- [x] R8-6. Stale t7/t15 images regenerated; review page Run 8 section (sidebar screen strips, page-2 options, item-3 options)
- [x] R8-7. Batch 5: 247 passed; full suite 5374 passed / 0 failed on the final code
- [x] R8-8. Merge plan: gate results, verdict READY for step A on the user's go
- [x] R8-9. Local server restarted (live-site mode)
