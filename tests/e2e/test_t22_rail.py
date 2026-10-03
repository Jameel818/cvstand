"""modern-t22's rail word is FIXED artwork (run 6, user requirement).

"RESUME" / "سيرة ذاتية": the template's red, never editable, and it never
follows the Fonts panel - font, weight and size are fixed in every case, in
the preview and in the PDF. The Arabic word fills the rail end to end like
the English one (Cairo Black: Alexandria at the same length is wider than the
215px rail - measured, docs/WORD_FIDELITY_AUDIT.md). The Word export carries
the rail as a picture rendered from this same HTML (tools/build_t22_rail.py),
so the picture must not go stale."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.rendering import document_html

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
DATA = {"en": json.loads((ROOT / "data" / "demo_resume.json").read_text(encoding="utf-8")),
        "ar": json.loads((ROOT / "data" / "demo_resume_ar.json").read_text(encoding="utf-8"))}
#: every choice the Fonts panel offers a role: font, weight and size, all three roles
CHOICES = {"en": dict(font_name="Playfair Display", font_name_weight=400, font_name_size=40,
                      font_heading="Lora", font_heading_weight=700, font_heading_size=16,
                      font_body="Inter", font_body_weight=300, font_body_size=11),
           "ar": dict(font_name="Amiri", font_name_weight=700, font_name_size=40,
                      font_heading="Lateef", font_heading_weight=400, font_heading_size=18,
                      font_body="Noto Naskh Arabic", font_body_weight=400, font_body_size=12)}
RAIL = """() => {
  const v = document.querySelector('.vrail');
  const spans = [...v.querySelectorAll('span')];
  const cs = e => { const c = getComputedStyle(e);
    return [c.fontFamily, c.fontWeight, c.fontSize, c.color, c.lineHeight].join('|'); };
  const r = [...v.querySelectorAll('span')].map(s => s.getBoundingClientRect());
  const top = Math.min(...r.map(b => b.top)), bottom = Math.max(...r.map(b => b.bottom));
  return {rail: cs(v), spans: spans.map(cs), text: v.textContent,
          editable: v.isContentEditable, top, bottom};
}"""


def _open(page, base, html):
    # the document's origin must be the server's: its fonts are same-origin
    page.goto(f"{base}/static/fonts/typography.css")
    page.set_content(html, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")


@pytest.mark.parametrize("pdf", [False, True], ids=["preview", "pdf"])
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_rail_word_never_follows_the_fonts_panel(page, live_server, lang, pdf):
    _open(page, live_server.url, document_html(DATA[lang], "modern-t22", for_pdf=pdf))
    plain = page.evaluate(RAIL)
    _open(page, live_server.url,
          document_html(dict(DATA[lang], **CHOICES[lang]), "modern-t22", for_pdf=pdf))
    chosen = page.evaluate(RAIL)
    assert page.evaluate("document.documentElement.hasAttribute('data-cvt')"), \
        "the choices did not apply at all - the test proves nothing"
    assert chosen == plain
    assert not plain["editable"]
    assert plain["rail"].split("|")[3] == "rgb(203, 53, 0)"          # #CB3500
    want = ("Archivo", "900", "214px") if lang == "en" else ('"CVT Cairo"', "900", "202px")
    fam, weight, size = plain["spans"][0].split("|")[:3]
    assert fam.startswith(want[0]) and weight == want[1] and size == want[2], plain["spans"][0]


def test_the_arabic_rail_word_fills_the_rail(page, live_server):
    """The rotated word's extent along the 1043.5px track (its box's height
    on the page) is >= 95% of the track, as 'RESUME' is."""
    for lang in ("ar", "en"):
        _open(page, live_server.url, document_html(DATA[lang], "modern-t22"))
        got = page.evaluate(RAIL)
        assert (got["bottom"] - got["top"]) >= 0.95 * 1043.5, (lang, got)


def test_the_word_pictures_match_the_template():
    r = subprocess.run([sys.executable, "tools/build_t22_rail.py", "--check"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
