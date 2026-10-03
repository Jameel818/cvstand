"""Measure every template's Word theme into app/word_themes.json.

    venv/Scripts/python tools/build_word_themes.py          # write
    venv/Scripts/python tools/build_word_themes.py --check  # compare, exit 1 if stale

For each template and language: the face (family, weight) that carries the
most text in the NAME (.cv-name) and in the SECTION TITLES (.cv-section), the
family that carries the most of everything else (the body), and the
template's accent (registry). Read by app/exporters/docx_theme.py.

MEASURED, NOT TRANSCRIBED. Templates set their fonts in inline styles, and in
Arabic the font policy (RTL_TYPOGRAPHY) overrides them with !important, so
the only reliable answer is Chromium's computed style on the rendered
document - the same document the PDF prints. Hand-copying the fonts would
drift the first time a template changed, and `--check` is how a test catches
that.

WORD_SUBSTITUTES is applied here (DM Sans -> Poppins for modern-t10).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry  # noqa: E402
from app.exporters.docx_theme import THEMES_PATH, WORD_SUBSTITUTES  # noqa: E402
from app.rendering import document_html  # noqa: E402
from app.typography import CSS_FAMILY_PREFIX  # noqa: E402

SAMPLES = {
    "en": ROOT / "data" / "sample_resume.json",
    "ar": ROOT / "data" / "sample_resume_ar.json",
}

# Per role, the (family, weight) carrying the most characters. Only an
# element's OWN text nodes count, so a wrapper is not credited with its
# children's text.
_MEASURE = r"""() => {
  const fam = cs => cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
  const own = e => [...e.childNodes].filter(n => n.nodeType === 3)
                     .map(n => n.textContent.trim().length).reduce((a, b) => a + b, 0);
  const top = (els) => {
    const t = {};
    for (const e of els) { const n = own(e); if (!n) continue;
      const c = getComputedStyle(e); const k = fam(c) + '|' + c.fontWeight;
      t[k] = (t[k] || 0) + n; }
    const best = Object.entries(t).sort((a, b) => b[1] - a[1])[0];
    return best ? best[0] : null;
  };
  const within = sel => [...document.querySelectorAll(sel)]
      .flatMap(r => [r, ...r.querySelectorAll('*')]);
  const rest = [...document.querySelectorAll('.tpl *')]
      .filter(e => !e.closest('.cv-name, .cv-section'));
  return {name: top(within('.cv-name')), heading: top(within('.cv-section')),
          body: top(rest)};
}"""


def _face(measured: str) -> dict:
    family, weight = measured.split("|")
    # The browser reports the CSS name; Word needs the face's own name. The
    # Arabic policy faces are declared as 'CVT <family>' since run 4 item 3.
    family = family.removeprefix(CSS_FAMILY_PREFIX)
    return {"family": WORD_SUBSTITUTES.get(family, family), "weight": int(weight)}


def measure() -> dict:
    from playwright.sync_api import sync_playwright

    samples = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in SAMPLES.items()}
    out: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 850, "height": 1100})
            # Computed style needs no font file; nothing may leave the machine.
            page.route("**/*", lambda route: route.abort())
            for key in registry.ported_keys():
                entry = {}
                for lang, data in samples.items():
                    page.set_content(document_html(data, key, for_pdf=True))
                    m = page.evaluate(_MEASURE)
                    missing = [r for r, v in m.items() if not v]
                    if missing:
                        raise SystemExit(f"{key} ({lang}): no text found for {missing}")
                    entry[lang] = {"accent": registry.get(key).accent.upper(),
                                   "name": _face(m["name"]),
                                   "heading": _face(m["heading"]),
                                   "body": _face(m["body"])["family"]}
                out[key] = entry
        finally:
            browser.close()
    return out


def render(templates: dict) -> str:
    doc = {"generated_by": "tools/build_word_themes.py",
           "note": "Measured from the rendered templates; do not edit by hand.",
           "templates": templates}
    return json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    text = render(measure())
    if "--check" in sys.argv:
        current = THEMES_PATH.read_text(encoding="utf-8") if THEMES_PATH.exists() else ""
        if current != text:
            print(f"STALE {THEMES_PATH.name}: re-run tools/build_word_themes.py")
            return 1
        print(f"OK  {THEMES_PATH.name} matches the templates")
        return 0
    THEMES_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {THEMES_PATH.relative_to(ROOT)} ({len(json.loads(text)['templates'])} templates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
