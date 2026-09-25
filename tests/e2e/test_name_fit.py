"""The name must fit its width: shrunk, never clipped, never below 70%.

autofit.js shrinks a `.cv-name` whose text reaches past the room it has (the
padding boxes of its ancestors and the canvas), in font-size only, down to
NAME_FLOOR = 0.70 of its designed or chosen size. It never wraps.

Measured BEFORE the fit existed (same-origin, fonts loaded):

    long name, no typography     modern-t2 +9.8px, modern-t3 +17.9, modern-t9 +18.6
    max headline size (44pt)     modern-t3 +41.5, modern-t9 +33.7
    Arabic, either case          nothing clipped

HOW THIS IS MEASURED. Documents are served from the live server's ORIGIN
(page.route). `set_content()` with a <base> looks equivalent and is not: its
origin is about:blank, every linked font is then a blocked cross-origin fetch,
and the page silently renders in system fallbacks (Arial Black for Montserrat
900). That mistake was made once while building this, and every number it
produced was wrong. `test_fonts_really_load` guards it. The clipping probe is
tools/verify_overflow.py's own SCAN_JS, calibrated here on a known clip.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import registry
from app.rendering import document_html

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
EN = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
AR = json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))
BASE = {"en": EN, "ar": AR}
LONG = {"en": "Mohammed Abdulrahman Al-Hashimi", "ar": "محمد عبدالرحمن الهاشمي"}
MAX_HEADLINE = {"en": 44, "ar": 48}
TEMPLATES = [t.key for t in registry.by_category() if t.ported]
FLOOR = 0.70


def _scan_js():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import verify_overflow as vo
    return vo.SCAN_JS, vo.TOLERANCE


@pytest.fixture(scope="module")
def doc_page(browser, live_server):
    """One page serving whatever document `load` hands it, same-origin."""
    ctx = browser.new_context(viewport={"width": 900, "height": 1200})
    pg = ctx.new_page()
    cur = {"doc": ""}
    pg.route(live_server.url + "/__doc", lambda route, _r: route.fulfill(
        body=cur["doc"], content_type="text/html; charset=utf-8"))

    def load(data: dict, key: str) -> dict:
        cur["doc"] = document_html(data, key)
        pg.goto(live_server.url + "/__doc", wait_until="networkidle")
        return pg.evaluate("window.ResumeAutofit.ready")
    yield pg, load
    ctx.close()


def _name_clip(pg, name: str) -> float:
    js, tol = _scan_js()
    r = pg.evaluate(js, tol)
    words = set(name.split())
    hits = [x["px"] for x in r["outside"] + r["clipped"]
            if "cv-name" in x.get("cls", "") or any(w in x.get("text", "") for w in words)]
    return max(hits, default=0.0)


def test_fonts_really_load(doc_page):
    pg, load = doc_page
    load(EN, "modern-t17")
    assert pg.evaluate("[...document.fonts].filter(f => f.status === 'error').length") == 0


def test_the_probe_sees_a_known_clip(doc_page):
    """Calibration: undo the fit on modern-t3's long name and the probe must
    report the ~18px it measured before the fit existed."""
    pg, load = doc_page
    r = load(dict(EN, name=LONG["en"]), "modern-t3")
    assert r["namesShrunk"] == 1
    assert _name_clip(pg, LONG["en"]) == 0
    # Undo exactly the fit's factor (removing the property would also drop
    # the template's own inline size and read a smaller, inherited one).
    pg.evaluate("""k => document.querySelectorAll('.cv-name, .cv-name *').forEach(e =>
                   e.style.setProperty('font-size',
                     parseFloat(getComputedStyle(e).fontSize) / k + 'px', 'important'))""",
                r["nameScaleMin"])
    assert _name_clip(pg, LONG["en"]) > 10


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("case", ["long-name", "max-headline"])
@pytest.mark.parametrize("key", TEMPLATES)
def test_the_name_never_clips(doc_page, key, case, lang):
    pg, load = doc_page
    if case == "long-name":
        data = dict(BASE[lang], name=LONG[lang])
    else:
        data = dict(BASE[lang], font_heading_size=MAX_HEADLINE[lang])
    r = load(data, key)
    assert r["nameScaleMin"] >= FLOOR - 1e-9, r
    clip = _name_clip(pg, data["name"])
    assert clip == 0, (f"{key}/{lang}/{case}: name still loses {clip:.1f}px "
                       f"at scale {r['nameScaleMin']}")


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", TEMPLATES)
def test_a_normal_name_is_never_touched(doc_page, key, lang):
    """No typography, the shipped sample's name: the fit must not engage at
    all - the pixel goldens prove the same for the English PDF render; this
    covers the preview render and Arabic too."""
    _pg, load = doc_page
    r = load(BASE[lang], key)
    assert r["namesShrunk"] == 0, r
