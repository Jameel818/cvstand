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
