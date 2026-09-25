"""The typography choices, as the browser actually resolves them.

Every rendered document is served from the live server's origin (via
page.route), so `/static/...` resolves exactly as it does in the builder's
preview iframe.

WHAT IS PROVED, over all 49 templates in both languages

    ROLES     every text element in .cv-name / .cv-section resolves to the
              chosen headline family, every other one to the chosen details
              family - through the templates' inline styles and, in Arabic,
              through the font policy's own !important rules.
    WEIGHTS   "weight None" is registry.nearest_weight() of the element's OWN
              weight, measured on the same template rendered without choices;
              template-bold details text (>= 600) is the 700 emphasis face.
    GLYPHS    the face that actually drew the text (CDP
              CSS.getPlatformFontsForNode) is the chosen family - computed
              style says what was ASKED for, this says what was USED.
              Calibrated on a default render whose answer is known.
    NETWORK   the typography files requested are exactly the faces the text
              uses - nothing unchosen - and a résumé with no choices requests
              no typography file at all.

Sizes, and the Latin-Ext fallback, are proved on a few templates below.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import registry
from app.rendering import document_html
from app.typography import CSS_FAMILY_PREFIX, face, nearest_weight

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
EN = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
AR = json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8"))
TEMPLATES = [t.key for t in registry.by_category() if t.ported]

#: One choice per language, weights left None so the nearest-weight path runs.
#: Each language pairs an unmodified reserved-name family (served as .ttf)
#: with a built one (served as .woff2), so both delivery paths are exercised.
CHOICE = {
    "en": {"font_heading": "Playfair Display", "font_body": "Poppins"},
    "ar": {"font_heading": "Cairo", "font_body": "Lateef"},
}
BASE = {"en": EN, "ar": AR}

FONT_FILE = re.compile(r"/static/fonts/((?:web|ttf)/[^?#]+)")

COLLECT = """() => {
  const tpl = document.querySelector('.tpl');
  return [tpl, ...tpl.querySelectorAll('*')].map((el, i) => {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim());
    const cs = getComputedStyle(el);
    return {
      i, own,
      role: el.closest('.cv-name') ? 'heading' : el.closest('.cv-section') ? 'heading' : 'body',
      family: cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, ''),
      weight: parseInt(cs.fontWeight, 10),
      size: parseFloat(cs.fontSize),
    };
  });
}"""


def _open(ctx, url, doc):
    pg = ctx.new_page()
    requests: list[str] = []
    pg.on("request", lambda r: requests.append(r.url))
    pg.route(url + "/__doc", lambda route, _req: route.fulfill(
        body=doc, content_type="text/html; charset=utf-8"))
    pg.goto(url + "/__doc")
    pg.evaluate("window.ResumeAutofit.ready")
    pg.evaluate("document.fonts.ready")
    return pg, requests


def _hundred(w: int) -> int:
    return min(900, max(100, round(w / 100) * 100))


def _platform_fonts(ctx, pg, selector: str) -> list[dict]:
    cdp = ctx.new_cdp_session(pg)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    root = cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    assert node, selector
    return cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]


def _probe(pg, role: str) -> str:
    """Mark the first element of `role` that owns text; return its selector."""
    sel = {"name": ".cv-name", "body": None}[role]
    ok = pg.evaluate("""([sel]) => {
      const tpl = document.querySelector('.tpl');
      const pool = sel ? [...tpl.querySelectorAll(sel + ', ' + sel + ' *')]
                       : [...tpl.querySelectorAll('*')].filter(e => !e.closest('.cv-name, .cv-section'));
      const el = pool.find(e => [...e.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim()));
      if (!el) return false;
      el.setAttribute('data-probe', sel ? 'name' : 'body');
      return true;
    }""", [sel])
    return f"[data-probe={'name' if sel else 'body'}]" if ok else ""


def test_the_glyph_instrument_reads_a_known_answer(browser, live_server):
    """Calibration first: ats-t1 with no choices draws its name in Archivo.
    If this reads anything else, every GLYPHS assertion below means nothing."""
    ctx = browser.new_context()
    try:
        pg, _ = _open(ctx, live_server.url, document_html(EN, "ats-t1"))
        fonts = _platform_fonts(ctx, pg, _probe(pg, "name"))
        # The instrument reports the FILE's own family name, not the CSS name:
        # Google's variable Archivo calls itself "Archivo SemiBold". So the
        # reading is "starts with the family, and is a web font" - measured
        # here, on an answer known in advance, before it is trusted below.
        assert len(fonts) == 1, fonts
        assert fonts[0]["familyName"].startswith("Archivo"), fonts
        assert fonts[0]["isCustomFont"] is True, fonts
    finally:
        ctx.close()


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", TEMPLATES)
def test_choices_apply_to_every_role(browser, live_server, key, lang):
    choice = CHOICE[lang]
    ctx = browser.new_context()
    try:
        base_pg, base_req = _open(ctx, live_server.url, document_html(BASE[lang], key))
        before = base_pg.evaluate(COLLECT)
        # NO choices -> no typography file of any kind.
        assert not [u for u in base_req if FONT_FILE.search(u) or "typography.css" in u]
        base_pg.close()

        pg, requests = _open(ctx, live_server.url,
                             document_html(dict(BASE[lang], **choice), key))
        after = pg.evaluate(COLLECT)
        assert len(after) == len(before)

        used: set[tuple[str, int]] = set()
        wrong = []
        for b, a in zip(before, after):
            if not a["own"]:
                continue
            fam = choice["font_heading" if a["role"] == "heading" else "font_body"]
            own = _hundred(b["weight"])
            if a["role"] == "body" and own >= 600:
                want = 700
            else:
                want = nearest_weight(lang, a["role"], fam, own)
            got = (a["family"], a["weight"])
            if got != (CSS_FAMILY_PREFIX + fam, want):
                wrong.append(f"#{a['i']} {a['role']} own={own}: got {got}, want "
                             f"{(CSS_FAMILY_PREFIX + fam, want)}")
            used.add((fam, a["weight"]))
        assert not wrong, f"{len(wrong)} element(s):\n  " + "\n  ".join(wrong[:12])

        # Only what the text uses is fetched.
        expected = {face(f, w)["woff2"] or face(f, w)["ttf"] for f, w in used}
        fetched = {FONT_FILE.search(u).group(1) for u in requests if FONT_FILE.search(u)}
        assert fetched == expected, (f"fetched {sorted(fetched)}, text uses {sorted(expected)}")

        # And the glyphs really came from the chosen faces.
        for role, fam in (("name", choice["font_heading"]), ("body", choice["font_body"])):
            sel = _probe(pg, role)
            if not sel:
                continue
            fonts = _platform_fonts(ctx, pg, sel)
            top = max(fonts, key=lambda x: x["glyphCount"])
            assert top["familyName"].startswith(fam) and top["isCustomFont"], (
                f"{role}: drawn in {fonts}")
    finally:
        ctx.close()


# ---- sizes ---------------------------------------------------------------------

#: Inside each language's own range (Arabic runs one step larger, §4) - an
#: out-of-range size is reset to template default by the validator.
SIZED = {"en": {"font_heading_size": 32, "font_body_size": 9.5},
         "ar": {"font_heading_size": 34, "font_body_size": 10.5}}
SIZE_CASES = [("ats-t1", "en"), ("ats-t1", "ar"), ("modern-t1", "en"),
              # ats-t13 carries the Arabic `.sec-head` 14px !important rescue:
              # the section size must still win.
              ("ats-t13", "ar")]

SIZES_JS = """() => {
  const tpl = document.querySelector('.tpl');
  const own = el => [...el.childNodes].filter(n => n.nodeType === 3)
                     .reduce((s, n) => s + n.nodeValue.trim().length, 0);
  const all = [tpl, ...tpl.querySelectorAll('*')].map(el => ({
    el, text: own(el), size: parseFloat(getComputedStyle(el).fontSize),
    role: el.closest('.cv-name') ? 'name' : el.closest('.cv-section') ? 'section' : 'body'}));
  const name = Math.max(...all.filter(x => x.role === 'name' && x.text).map(x => x.size));
  const sections = [...tpl.querySelectorAll('.cv-section')]
    .filter(s => !s.parentElement.closest('.cv-section'))
    .map(s => Math.max(...all.filter(x => x.text && (x.el === s || s.contains(x.el))).map(x => x.size)));
  const body = all.filter(x => x.role === 'body' && x.text).map(x => [x.size, x.text]);
  return {name, sections, body, f: window.ResumeAutofit.result().typeScale};
}"""


@pytest.mark.parametrize("key,lang", SIZE_CASES)
def test_sizes_scale_each_role_and_keep_the_hierarchy(browser, live_server, key, lang):
    from app.typography.render import section_size_pt
    ctx = browser.new_context()
    try:
        pg, _ = _open(ctx, live_server.url, document_html(BASE[lang], key))
        before = pg.evaluate(SIZES_JS)
        pg, _ = _open(ctx, live_server.url, document_html(dict(BASE[lang], **SIZED[lang]), key))
        after = pg.evaluate(SIZES_JS)
    finally:
        ctx.close()
    f = after["f"]                                   # autofit's own type scale
    px = 4 / 3
    sized = SIZED[lang]
    assert after["name"] == pytest.approx(sized["font_heading_size"] * px * f, rel=1e-3)
    sec = section_size_pt(sized["font_heading_size"], lang) * px * f
    assert after["sections"] and all(s == pytest.approx(sec, rel=1e-3) for s in after["sections"])

    # Details: the dominant size lands on the target, every other size keeps
    # its ratio to it - the template's hierarchy survives.
    def dominant(rows):
        chars: dict[float, int] = {}
        for size, n in rows:
            chars[size] = chars.get(size, 0) + n
        return max(chars, key=chars.get)
    d0, d1 = dominant(before["body"]), dominant(after["body"])
    assert d1 == pytest.approx(sized["font_body_size"] * px * f, rel=1e-3)
    for (s0, _), (s1, _) in zip(before["body"], after["body"]):
        assert s1 / d1 == pytest.approx(s0 / d0, rel=1e-3)


# ---- Latin-Ext fallback ---------------------------------------------------------

def _ar_with_summary(summary: str) -> dict:
    return dict(AR, summary=summary, font_body="Tajawal")


def test_rare_latin_letters_fall_back_to_a_real_latin_face(browser, live_server):
    """Tajawal lacks `ř` and `Ş` (measured: it does have `Ł`). In an Arabic CV
    those two must come from the stack's Work Sans - fetched for exactly
    that - not from the OS, while every other glyph stays Tajawal."""
    ctx = browser.new_context()
    try:
        pg, requests = _open(ctx, live_server.url, document_html(
            _ar_with_summary("مهندس عمل مع Dvořák و Şahin في وارسو."), "ats-t1"))
        sel = pg.evaluate("""() => {
          const p = [...document.querySelectorAll('.tpl *')]
            .find(e => [...e.childNodes].some(n => n.nodeType === 3 && n.nodeValue.includes('Dvo')));
          p.setAttribute('data-probe', 'ext'); return '[data-probe=ext]';
        }""")
        fonts = {f["familyName"]: f["glyphCount"] for f in _platform_fonts(ctx, pg, sel)}
        assert any(n.startswith("Tajawal") for n in fonts), fonts
        assert fonts.get("Work Sans", 0) == 2, fonts          # ř and Ş, nothing else
        assert any("work-sans" in u for u in requests)
    finally:
        ctx.close()


def test_the_fallback_is_not_fetched_when_nothing_needs_it(browser, live_server):
    ctx = browser.new_context()
    try:
        _pg, requests = _open(ctx, live_server.url, document_html(
            _ar_with_summary("مهندس عمل مع Dvorak و Sahin في وارسو."), "ats-t1"))
        assert not [u for u in requests if "work-sans" in u], requests
        assert [u for u in requests if "tajawal" in u and FONT_FILE.search(u)]
    finally:
        ctx.close()


# ---- one role chosen leaves the other alone --------------------------------------

@pytest.mark.parametrize("chosen", ["body", "heading"])
@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", TEMPLATES)
def test_one_role_chosen_leaves_the_other_alone(browser, live_server, key, lang, chosen):
    """Choosing only a Details font must not touch the name or the section
    titles, and choosing only a Headlines font must not touch the details -
    in Arabic the untouched role keeps the font policy's faces, in English
    the template's own.

    Found by this test: a headline that sets no font-family of its own
    INHERITS it (ats-t1's name inherits Archivo from .tpl), so overriding .tpl
    for Details silently restyled the name. typography.js now pins the
    unchosen headlines to their pre-switch family."""
    fam = CHOICE[lang]["font_body" if chosen == "body" else "font_heading"]
    key_name = "font_body" if chosen == "body" else "font_heading"
    ctx = browser.new_context()
    try:
        pg, _ = _open(ctx, live_server.url, document_html(BASE[lang], key))
        before = pg.evaluate(COLLECT)
        pg, _ = _open(ctx, live_server.url, document_html(dict(BASE[lang], **{key_name: fam}), key))
        after = pg.evaluate(COLLECT)
    finally:
        ctx.close()
    other = [(b, a) for b, a in zip(before, after) if a["own"] and a["role"] != chosen]
    moved = [(b["i"], b["family"], a["family"]) for b, a in other
             if (a["family"], a["weight"]) != (b["family"], b["weight"])]
    assert not moved, moved[:8]
    assert any(a["family"] == CSS_FAMILY_PREFIX + fam
               for a in after if a["own"] and a["role"] == chosen)
