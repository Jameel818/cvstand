"""Measure every template's IDENTITY for the cover letter into app/letter_themes.json.

    venv/Scripts/python tools/build_letter_themes.py          # write
    venv/Scripts/python tools/build_letter_themes.py --check  # compare, exit 1 if stale

The cover letter is ONE shared layout (app/templates/resumes/_letter.j2) that
dresses itself in the selected template's identity, so it matches all 49
without 49 designs. The identity is what a reader recognises at a glance:

    head    where the name sits - on a coloured BAND across the top, in a
            coloured SIDE column, or OPEN on the page - and that surface's colour
    side    a full-height coloured column, its colour and its side
            (inline start / end), drawn on the letter as a rail
    name    the name's colour, case and tracking (its face comes from
            word_themes.json and the font ribbon, like the CV's)
    title   the headline's colour
    heading the section titles' colour and case (the letter's subject line)
    text    the body colour
    page    the page colour (a few templates are not white)
    accent  the template's accent (registry)

MEASURED, NOT TRANSCRIBED - the same rule as tools/build_word_themes.py:
templates set colours in inline styles, so Chromium's computed style on the
rendered sample document is the only reliable answer, and `--check` is how a
test notices a template that changed after this file was written.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry  # noqa: E402
from app.letter import THEMES_PATH  # noqa: E402
from app.rendering import document_html  # noqa: E402

SAMPLES = {
    "en": ROOT / "data" / "sample_resume.json",
    "ar": ROOT / "data" / "sample_resume_ar.json",
}

_MEASURE = r"""(sample) => {
  const tpl = document.querySelector('.tpl');
  const T = tpl.getBoundingClientRect();
  const W = T.width, H = T.height;
  const hex = (c) => {
    const m = (c || '').match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map((s) => parseFloat(s));
    if (p.length === 4 && p[3] < 0.85) return null;          // see-through: not a surface
    return '#' + p.slice(0, 3).map((x) => Math.round(x).toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  const surface = (e) => {
    const c = getComputedStyle(e);
    let bg = hex(c.backgroundColor);
    if (!bg && /gradient/.test(c.backgroundImage)) {
      const m = c.backgroundImage.match(/rgba?\([^)]+\)/);
      bg = m ? hex(m[0]) : null;
    }
    return bg;
  };
  const page = surface(tpl) || '#FFFFFF';
  const panels = [...tpl.querySelectorAll('*')].map((e) => {
    const bg = surface(e);
    if (!bg || bg === page) return null;
    const r = e.getBoundingClientRect();
    return { e, bg, x: r.left - T.left, y: r.top - T.top, w: r.width, h: r.height };
  }).filter(Boolean);
  const side = panels.filter((p) => p.h >= 0.7 * H && p.w >= 40 && p.w <= 0.55 * W)
                     .sort((a, b) => b.w * b.h - a.w * a.h)[0] || null;
  const band = panels.filter((p) => p.w >= 0.8 * W && p.y <= 60 && p.h >= 60 && p.h <= 0.45 * H)
                     .sort((a, b) => a.y - b.y)[0] || null;
  const name = document.querySelector('.cv-name');
  const nr = name.getBoundingClientRect();
  const ncs = getComputedStyle(name);
  const inside = (p) => p && p.e.contains(name);
  // The surface the name is drawn on: the nearest ancestor with a colour.
  let onBg = null;
  for (let e = name; e && e !== tpl.parentElement; e = e.parentElement) {
    const bg = surface(e);
    if (bg) { onBg = bg; break; }
  }
  const head = inside(band) ? 'band' : inside(side) ? 'side' : 'open';
  const dirRtl = document.documentElement.dir === 'rtl';
  const sideAt = side ? (((side.x + side.w / 2) < W / 2) !== dirRtl ? 'start' : 'end') : null;
  const textOf = (needle) => {
    if (!needle) return null;
    // the smallest element holding it: a label or an icon often shares the line
    const all = [...tpl.querySelectorAll('*')].filter((e) => e.textContent.includes(needle.trim()))
                  .sort((a, b) => a.textContent.length - b.textContent.length);
    const e = all[0];
    return e ? hex(getComputedStyle(e).color) : null;
  };
  // The subject line borrows the section titles' look, so it must be a title
  // drawn ON THE PAGE: a white heading inside a dark sidebar or on a clay
  // ribbon would vanish on the letter's white page.
  const surfaceOf = (el) => {
    for (let e = el; e && e !== tpl.parentElement; e = e.parentElement) {
      const bg = surface(e);
      if (bg) return bg;
    }
    return page;
  };
  const sec = [...document.querySelectorAll('.cv-section')]
                .find((s) => s.textContent.trim() && surfaceOf(s) === page) || null;
  const scs = sec ? getComputedStyle(sec) : null;
  const fam = (cs) => cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
  // Centred: the name's centre sits on its surface's centre.
  let box = tpl.getBoundingClientRect();
  if (head === 'band') box = band.e.getBoundingClientRect();
  if (head === 'side') box = side.e.getBoundingClientRect();
  const centred = Math.abs((nr.left + nr.width / 2) - (box.left + box.width / 2)) < 12
                  && ncs.textAlign !== 'start' || ncs.textAlign === 'center';
  return {
    page,
    head: head === 'open' ? { kind: 'open' }
                          : { kind: head, bg: onBg, },
    side: side ? { bg: side.bg, at: sideAt } : null,
    name: { color: hex(ncs.color), caps: ncs.textTransform === 'uppercase',
            tracking: Math.round((parseFloat(ncs.letterSpacing) || 0) * 10) / 10,
            centred: !!centred, family: fam(ncs), weight: Number(ncs.fontWeight) },
    title: textOf(sample.title),
    contact: textOf((sample.contact || {}).email),
    heading: sec ? { color: hex(scs.color), caps: scs.textTransform === 'uppercase',
                     family: fam(scs), weight: Number(scs.fontWeight) } : null,
    text: hex(getComputedStyle(tpl).color),
    body: fam(getComputedStyle(tpl)),
    // Arabic section titles in Tajawal rather than Cairo (rendering.RTL_TYPOGRAPHY)
    taj: tpl.classList.contains('cv-sections-taj'),
  };
}"""


def measure() -> dict:
    from playwright.sync_api import sync_playwright

    samples = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in SAMPLES.items()}
    out: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 850, "height": 1100})
            page.route("**/*", lambda route: route.abort())     # nothing leaves the machine
            for key in registry.ported_keys():
                entry = {}
                for lang, data in samples.items():
                    page.set_content(document_html(data, key, for_pdf=True))
                    m = page.evaluate(_MEASURE, data)
                    m["accent"] = registry.get(key).accent.upper()
                    entry[lang] = m
                out[key] = entry
        finally:
            browser.close()
    return out


def render(templates: dict) -> str:
    doc = {"generated_by": "tools/build_letter_themes.py",
           "note": "Measured from the rendered templates; do not edit by hand.",
           "templates": templates}
    return json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    text = render(measure())
    if "--check" in sys.argv:
        current = THEMES_PATH.read_text(encoding="utf-8") if THEMES_PATH.exists() else ""
        if current != text:
            print(f"STALE {THEMES_PATH.name}: re-run tools/build_letter_themes.py")
            return 1
        print(f"OK  {THEMES_PATH.name} matches the templates")
        return 0
    THEMES_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {THEMES_PATH.relative_to(ROOT)} ({len(json.loads(text)['templates'])} templates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
