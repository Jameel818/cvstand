"""The real-Word audit as a test (opt in: `pytest --word`).

Runs tools/word_audit.py in a subprocess: every Word download of the chosen
templates (demo + sample + photo CV x EN/AR x Letter/A4 x cv/letter/both)
built, converted in REAL Microsoft Word (its own WINWORD process only - the
user's Word is never touched; tools/word_com.ps1), rasterised and checked
against the PDF of the same CV: page count, columns and bands to the page
foot on every page, stray / missing lines, text cut off or moved, photo frame
(PDF and CV = letter), letterhead = CV header.

The whole catalogue takes ~80 minutes; choose templates with
    CVSTAND_WORD_AUDIT_KEYS=modern-t21,ats-t18 pytest --word tests/test_word_audit_real.py
Accepted rows (instrument limits and decisions, docs/CVSTAND_TEMPLATES_GUIDE.md
§8.21) are listed in ACCEPTED; anything else fails the test.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: (template, check) pairs that are known and agreed, with the reason - each
#: was inspected on the contact sheets (feature/word-audit, 2026-11-25)
ACCEPTED = {
    # the PDF shrinks this flex photo to a 6px strip on the Arabic Letter CV;
    # Word stops at 22px (a thinner picture saves no height: its paragraph
    # keeps a text line)
    ("modern-t20", "photo"),
    # the photo is partly under the orange panel in the PDF; Word shows the
    # visible part beside the panel (documented simplification, t14.py), and
    # the panel's edge differs by a few px in the Arabic letter
    ("modern-t14", "photo"), ("modern-t14", "letterhead-fill"),
    # Windows.Data.Pdf does not draw the PDF's conic-gradient skill rings;
    # the ring grid's cell borders reflow
    ("modern-t12", "line-missing"), ("modern-t24", "line-stray"), ("modern-t24", "dash-stray"),
    # PDF text-layer artefacts: t22's rail word is a picture in Word; t4's
    # name and "Contact" extract glued in the PDF
    ("modern-t22", "text-missing"), ("modern-t4", "text-missing"),
    # Word ends an Arabic line with an invisible space glyph left of the page
    # (x -6.6pt): nothing visible is off the page
    ("modern-t17", "text-offpage"), ("modern-t7", "text-offpage"),
    # modern-t8's Arabic letter body runs to the page edge in the PDF too
    ("modern-t8", "text-offpage"),
    # skill bars / slider grids / track ends: the bar edges are read as rules
    # and the rows reflow (the bars match by eye)
    ("modern-t15", "line-missing"), ("modern-t23", "line-missing"), ("modern-t7", "line-stray"),
    ("modern-t6", "line-stray"), ("modern-t5", "line-stray"), ("modern-t5", "line-missing"),
    ("modern-t5", "dash-stray"), ("ats-t7", "dash-stray"), ("ats-t6", "line-missing"),
    # a glyph stem (the T of ASHWORTH) read as a rule
    ("ats-t8", "line-stray"),
    # the PDF letter keeps a stray accent dash of the hidden summary; Word
    # does not draw it (a PDF-side quirk, not copied)
    ("modern-t11", "line-missing"),
    # a 1px white hairline under the top strip of the Arabic page
    ("modern-t8", "line-stray"),
    # the PDF letter drops the side "Contact" pill that its CV has; the Word
    # letter keeps the CV's header (owner's call, RESUME_HERE); the Arabic
    # Letter CV's side content ends higher in Word (empty column foot)
    ("modern-t5", "fill-top"), ("modern-t5", "fill-bottom"),
    # the letter's contact column starts a few px lower than the PDF letter's
    ("modern-t22", "letterhead-fill"),
    # the navy rail begins under the photo's white frame (334px), not beside
    # it at 312px - the simplification documented in t18.py
    ("modern-t18", "fill-top"),
}


@pytest.mark.word
def test_every_word_download_matches_its_pdf(tmp_path):
    keys = os.environ.get("CVSTAND_WORD_AUDIT_KEYS", "")
    cmd = [sys.executable, str(ROOT / "tools" / "word_audit.py"), "all", str(tmp_path)]
    if keys:
        cmd += ["--keys", keys]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr[-2000:]
    rows = list(csv.DictReader(open(tmp_path / "failures.csv", encoding="utf-8")))
    bad = [x for x in rows if (x["key"], x["check"]) not in ACCEPTED]
    assert not bad, "\n".join(" ".join(x.values()) for x in bad[:40])
