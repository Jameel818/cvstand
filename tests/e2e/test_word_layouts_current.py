"""app/word_layouts.json must describe the Modern templates as they render today.

It is MEASURED from the rendered templates (tools/build_word_layouts.py):
which items sit in which column, their order, the templates' own headings,
the zone colours. A template changed without re-measuring would keep
exporting its old shape to Word. Run as a subprocess: the tool opens its own
Playwright, which cannot share this session's thread (tests/conftest.py
`_playwright`).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]


def test_word_layouts_match_the_rendered_templates():
    res = subprocess.run([sys.executable, "tools/build_word_layouts.py", "--check"],
                         cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stdout + res.stderr
