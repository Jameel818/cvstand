"""app/word_themes.json must describe the templates as they render today.

It is MEASURED from the rendered templates (tools/build_word_themes.py), so a
template whose fonts change would otherwise keep exporting its old look to
Word. Run as a subprocess: the tool opens its own Playwright, which cannot
share this session's thread (see tests/conftest.py `_playwright`).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]


def test_word_themes_match_the_rendered_templates():
    res = subprocess.run([sys.executable, "tools/build_word_themes.py", "--check"],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stdout + res.stderr
