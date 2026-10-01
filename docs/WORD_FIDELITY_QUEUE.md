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
- [ ] modern-t7
- [ ] modern-t11
- [ ] modern-t13
- [ ] modern-t14
- [ ] modern-t18
- [ ] modern-t21
Open:
- [ ] modern-t1
- [ ] modern-t6
- [ ] modern-t12
- [ ] modern-t22
Gutter:
- [ ] modern-t19

## 4. Font sizes
- [ ] 4. Word applies the chosen SIZES (Name, Headings, Details), EN + AR, tests + real-Word check

## 5. Review
- [ ] 5. docs/review/word_fidelity_review.html + Desktop "CVStand Word fidelity review" (pdf / word-demo / word-long-p1 / word-long-p2 / overlay, grade, %, differences, .docx)

## 6. Full suite
- [ ] 6. Close Word; full suite incl. browser tests; fix without weakening

## Follow-ups (NOT this run: the PDF/HTML templates stay unchanged)
- [ ] Arabic PDF shows reference phone numbers reversed; fix later in the HTML/PDF templates.
- [ ] Arabic PDF/preview draw system fallback faces (the policy families are never declared in the document); see the audit FINDING.

## Final
- [ ] Final report, RESUME_HERE, commit, push, ls-remote, clean status
