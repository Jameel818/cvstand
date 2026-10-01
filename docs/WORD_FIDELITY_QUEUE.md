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
- [ ] 2. Demo CV one page in PDF + Word, EN + AR, every template (re-checked per template in 3)

## 3. Per-template Word designs (EN + AR: audit, demo + photo + refs 1 page, long CV, overlay, grade)
Already built last run - re-measure with the overlay, polish if > 10 %:
- [ ] modern-t8 (Band)
- [ ] modern-t10 (Sidebar)
- [ ] modern-t15 (Sidebar)
- [ ] modern-t20 (Sidebar)
- [ ] modern-t23 (Sidebar)
Sidebar:
- [ ] modern-t3
- [ ] modern-t5
- [ ] modern-t9
- [ ] modern-t16
- [ ] modern-t17
- [ ] modern-t24
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
