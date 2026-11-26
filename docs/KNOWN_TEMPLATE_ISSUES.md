# Known template issues (locked as they are)

The download lock (`tests/golden/downloads/`, `tools/lock_downloads.py`) freezes every PDF and Word download
**as it is now**. That is the approved current state, not a perfect one. The issues below are inside the lock.

**Fixing one of them later:**
1. The task names the template.
2. The fix changes only that template. The download-lock test proves it: only that template's downloads differ.
3. The owner looks at the new look (`tools/lock_downloads.py sheets --keys <template>`) and approves it.
4. Only that template's lock is updated:
   `python tools/lock_downloads.py update <template> --approved "<who approved what, when>"`
5. Its row here moves to "Fixed" with the date and branch.

Sources: RESUME_HERE.md (feature/word-audit, word-pages and defects entries) and
`Desktop\review-word-audit-2026-11-25\STATUS.md` ("Not changed"). Collected 2026-11-25 on feature/download-lock.

## Open

| # | Template | Language | Paper | PDF / Word | What is wrong | Source |
|---|---|---|---|---|---|---|
| 1 | modern-t5, modern-t8 | EN + AR | both | PDF letter vs Word letter | The PDF cover letter drops the side "Contact" heading that the CV shows. The Word letter keeps it, matching the CV header. **The owner must decide which is right**; then the other one is changed. | word-audit STATUS.md |
| 2 | modern-t20 | AR | Letter | PDF vs Word (CV, photo CV) | The PDF squeezes the flex photo to a 6px strip. Word stops at 22px: a thinner picture saves no height, because its paragraph keeps a text line. | word-audit |
| 3 | modern-t14 | EN + AR | both | Word | The photo is partly under the orange panel in the PDF. Word shows the visible part beside the panel (a documented simplification in `t14.py`). The panel edge differs by a few px in the Arabic letter. | word-audit |
| 4 | modern-t18 | EN + AR | both | Word | The navy rail starts under the photo's white frame (334px), not beside it at 312px (a documented simplification in `t18.py`). | word-audit |
| 5 | modern-t11 | EN + AR | both | PDF (letter) | The PDF cover letter keeps a stray accent dash from the hidden summary. Word does not draw it, and the quirk is not copied. | word-audit |
| 6 | modern-t16 | EN + AR | both | PDF (letter) vs Word | With no photo, the PDF letter drops the empty photo placeholder; the Word letter keeps it. | word-audit |
| 7 | modern-t8 | AR | both | PDF + Word (letter) | The Arabic letter body runs to the page edge, in the PDF as well as in Word. | word-audit |
| 8 | modern-t8 | AR | both | Word | A 1px white hairline under the top strip. | word-audit |
| 9 | all with a photo slot | EN + AR | both | PDF | A photo the user uploads never prints in the PDF: `set_content()` has no base URL, so `/uploads/...` does not load. The audit and the lock inline their test photo, so the lock does not show this. | word-audit; memory pdf-render-base-url |
| 10 | all | EN + AR | both | Word | One page in Word for content much longer than the demo and sample CVs still depends on the page estimate. The reserves were measured on demo + sample only. | word-pages |
| 11 | modern-t22, modern-t4 | EN | both | PDF text layer | The PDF's text layer glues words (t4's name and "Contact"), and t22's rail word is a picture in Word. Nothing is visible on the page; copy/paste and ATS text extraction are affected. | word-audit ACCEPTED |

Not template defects, but listed so that nobody "fixes" them: the audit's instrument noise. Windows' PDF
renderer does not draw the conic-gradient skill rings (t12, t24). Skill bar and grid edges are read as rules.
Word ends an Arabic line with an invisible space glyph left of the page (t7, t17). The full list with reasons
is in `tests/test_word_audit_real.py` ACCEPTED.

## Fixed

| Date | Branch | Template | Issue # | Lock updated with approval |
|---|---|---|---|---|
| | | | | |
