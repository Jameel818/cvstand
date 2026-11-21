"""No PDF content leaves the page (user, 2026-11-20).

The user's A4 Arabic PDF of modern-t21 was cut off on the LEFT on both pages.
Cause (app/exporters/pdf.py PRINT_ORIGIN): Chromium printed every right-to-left
document 850 x (1 - scale) px too far left - 34px on Letter, 57px on A4 - and
every A4 document 1px too far right. Neither is visible to a layout check: it
happens in the print step, after layout. So this reads the real PDFs.

tools/pdf_bounds.py --sweep prints the CV AND the cover letter of all 49
templates, English and Arabic, Letter and A4 (392 documents), through the
exporter's own `_print`, and checks every page: page-wide fills must span
exactly the page, and every text origin must be inside it. It runs in a
subprocess because this process may enter sync_playwright() only once
(tests/conftest.py; tests/test_suite_invariants.py).

The check was proven on known input before it was trusted
(memory: measurement-instrument-errors): it flags a bare 850px RTL page and
the shipped sample's modern-t21 Arabic PDF from before the fix, and passes the
same pages after it. `test_the_check_can_fail` keeps that proof in the suite.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "pdf_bounds.py"


def _sweep(tmp_path, *keys) -> list[dict]:
    out = tmp_path / "bounds.json"
    res = subprocess.run([sys.executable, str(TOOL), "--sweep", "--json", str(out), *keys],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                         stdin=subprocess.DEVNULL, timeout=1800)
    assert out.exists(), f"the sweep did not finish:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}"
    return json.loads(out.read_text(encoding="utf-8"))


def test_every_template_pdf_stays_on_the_page(tmp_path):
    rows = _sweep(tmp_path)
    assert len(rows) == 49 * 2 * 2 * 2, len(rows)
    # the walk must have SEEN content, or "no problems" proves nothing
    blind = [(r["key"], r["lang"], r["paper"], r["part"]) for r in rows
             if r["counts"][0] < 1 or r["counts"][1] < 20]
    assert not blind, f"pages the check could not read: {blind[:6]}"
    bad = [f'{r["key"]} {r["lang"]} {r["paper"]} {r["part"]}: {r["problems"][0]}'
           for r in rows if r["problems"]]
    assert not bad, f"{len(bad)} PDF(s) with content off the page:\n" + "\n".join(bad[:20])


def test_the_check_can_fail():
    """A right-to-left 850px page printed the way the exporter printed it
    before the fix (no PRINT_ORIGIN) must be reported."""
    sys.path.insert(0, str(ROOT / "tools"))
    from pdf_bounds import problems
    script = r'''
import sys
from playwright.sync_api import sync_playwright
html = ('<!doctype html><html dir="rtl"><head><style>html,body{margin:0} .tpl{margin:0 auto}'
        '@page{size:8.5in 11in;margin:0}</style></head><body><div class="tpl" '
        'style="width:850px;height:1100px;background:#eee"><p>مرحبا</p></div></body></html>')
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_page(); pg.set_content(html)
    pg.emulate_media(media="print")
    sys.stdout.buffer.write(pg.pdf(format="Letter", scale=0.96, print_background=True,
        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True))
    b.close()
'''
    pdf = subprocess.run([sys.executable, "-c", script], capture_output=True,
                         stdin=subprocess.DEVNULL, timeout=120, check=True).stdout
    assert pdf.startswith(b"%PDF")
    assert problems(pdf), "the check passed a page that is shifted 34px left"
