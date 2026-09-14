"""HORIZONTAL overflow across all 49 templates. The other axis.

WHY THIS EXISTS

    Auto-fit solves the VERTICAL axis: content longer than one page is
    compressed until it seats, and `tools/verify_autofit.py` plus
    `tests/e2e/test_autofit_gate.py` gate that for the whole catalogue. Nothing
    has ever looked at the horizontal one, and several layouts use fixed `px`
    column widths, so a value wider than its column has never been measured.

    That matters because the horizontal failure is SILENT in a way the vertical
    one is not. Too-tall content pushes past 1100px, auto-fit reports
    `fitted: false` and the builder raises a banner the user can act on. Too-wide
    content just... goes. It is painted outside the 850px canvas (and the PDF
    page is exactly the canvas, so it is simply absent from the export), or it
    is cut by an `overflow: hidden` on an ancestor. Either way nothing throws,
    nothing warns, and the résumé looks fine on screen while the email address
    on it is missing its last nine characters.

WHAT IS MEASURED, AND WHY ONLY THESE

    Two checks, both unambiguous:

    PAINTED OUTSIDE THE CANVAS. Every text node's client rects, compared with
    the `.tpl` box. A rect that starts before the left edge or ends after the
    right one is text that does not exist in the PDF. There is no reading of
    the layout under which that is intended.

    CLIPPED BY AN ANCESTOR. Any element whose own `overflow-x` is hidden/clip
    and whose `scrollWidth` exceeds its `clientWidth`. That is the browser
    telling us it had more content than it drew.

    Deliberately NOT measured: text that WRAPS to more lines (that is the
    vertical axis, and auto-fit owns it), and two columns whose text rects
    overlap. Overlap sounds like the obvious third check and is not usable —
    an inline element's rect legitimately sits inside its parent's, and a
    negative-margin decoration overlapping body text is a design choice several
    of these templates make on purpose. Measuring it produces a list dominated
    by false positives, which is the mistake `tests/test_bidi_mixed.py`
    documents from the other direction.

TWO TIERS, BECAUSE THEY DESERVE DIFFERENT ANSWERS

    `wide_sample()`  values that are long but entirely ordinary — a university
                     email address, a full department name, a real URL. A
                     template that loses text here is broken for a real person.

    `extreme_sample()` a single unbroken 120-character token. Nobody types this
                     by hand, but a paste does it, and it is the shape that
                     proves whether a fix is a fix or a coincidence: a value
                     with spaces in it can always be rescued by wrapping.

Usage:
    venv/Scripts/python tools/verify_overflow.py                # all 49, wide
    venv/Scripts/python tools/verify_overflow.py --extreme      # all 49, extreme
    venv/Scripts/python tools/verify_overflow.py --lang ar      # the Arabic sample
    venv/Scripts/python tools/verify_overflow.py modern-t1 ats-t5
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry                       # noqa: E402
from app.rendering import document_html        # noqa: E402

SAMPLES = {
    "en": json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8")),
    "ar": json.loads((ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8")),
}

#: A pixel of slack. Sub-pixel layout means a rect can land at 850.0004 without
#: anything being wrong; a real overflow is tens of pixels, never one.
TOLERANCE = 1.0


# --------------------------------------------------------------- the samples

#: Long but entirely ordinary values. Every one of these is a shape a real
#: applicant produces: a university address, a department's full name, a
#: hyphenated double-barrelled surname, a skill written out rather than
#: abbreviated. None is a stunt.
_WIDE_EN = {
    "name": "Wren Alexandra Ashworth-Fairweather",
    "title": "Creative Lead, Brand Systems & Editorial Direction",
    "email": "wren.alexandra.ashworth@postgraduate-communications.example-university.edu",
    "site": "https://www.wren-ashworth-portfolio.example.com/case-studies/brand-systems",
    "company": "Halden & Row Integrated Communications Group",
    "school": "Northfield University School of Art, Media and Design",
    "skill": "Cross-functional Stakeholder Communication",
    "tool": "Adobe Creative Cloud (InDesign)",
    "language": "Brazilian Portuguese",
    "chip_label": "Annual production budget owned",
}

_WIDE_AR = {
    "name": "أحمد عبد الرحمن الفارسي القحطاني",
    "title": "رئيس قسم المحاسبة والتخطيط المالي والرقابة الداخلية",
    "email": "ahmed.abdulrahman.alfarisi@almuhasaba-wa-altakhtit.example.com",
    "site": "https://www.ahmed-alfarisi-portfolio.example.com/dirasat-halat",
    "company": "مجموعة الشركات المتحدة للاستشارات المالية والإدارية",
    "school": "كلية الإدارة والاقتصاد بجامعة الشمال الوطنية",
    "skill": "التواصل مع أصحاب المصلحة عبر الإدارات",
    "tool": "برنامج التخطيط لموارد المؤسسات",
    "language": "البرتغالية البرازيلية",
    "chip_label": "الميزانية الإنتاجية السنوية المُدارة",
}

#: One unbroken token, 120 characters, no space and no hyphen to break at.
#: `overflow-wrap: break-word` does NOT rescue this — it only breaks a word
#: that has nowhere else to go, and several of these fields sit in a flex
#: child, which by default refuses to shrink below its content. That is why
#: this tier exists: it separates a real fix from a lucky one.
_TOKEN = "wrenashworthbrandsystemseditorialdirectionportfoliocasestudiesnorthfieldstudiopracticeandhandoverdocumentationx"
_TOKEN_AR = "الاستشاراتالماليةوالإداريةوالتخطيطالاستراتيجيوالرقابةالداخليةوإعدادالتقاريرالمحاسبيةالشهريةوالسنويةللمجموعةالموحدة"


def _plant(data: dict, v: dict) -> dict:
    """Write the long values into every field that has a column of its own."""
    d = copy.deepcopy(data)
    d["name"] = v["name"]
    d["title"] = v["title"]
    d.setdefault("contact", {})
    d["contact"]["email"] = v["email"]
    d["contact"]["site"] = v["site"]
    if d.get("experience"):
        d["experience"][0]["company"] = v["company"]
    if d.get("education"):
        d["education"][0]["school"] = v["school"]
    if d.get("skills"):
        d["skills"][0] = dict(d["skills"][0], name=v["skill"])
    if d.get("tools"):
        d["tools"][0] = v["tool"]
    if d.get("languages"):
        d["languages"][0] = dict(d["languages"][0], name=v["language"])
    if d.get("achievements"):
        d["achievements"][0] = dict(d["achievements"][0], label=v["chip_label"])
    return d


def wide_sample(lang: str = "en") -> dict:
    """Long but ordinary. A template that loses text here is broken for a
    real person, not for a stress test."""
    return _plant(SAMPLES[lang], _WIDE_EN if lang == "en" else _WIDE_AR)


def extreme_sample(lang: str = "en") -> dict:
    """One 120-character unbroken token in each column-bound field."""
    tok = _TOKEN if lang == "en" else _TOKEN_AR
    v = dict((_WIDE_EN if lang == "en" else _WIDE_AR),
             **{k: tok for k in ("name", "title", "email", "site", "company",
                                 "school", "skill", "tool", "language")})
    return _plant(SAMPLES[lang], v)


# ----------------------------------------------------------------- the scan

#: Runs in the page. Returns every text run painted outside the canvas, and
#: every element the browser had to clip horizontally.
SCAN_JS = r"""
(tol) => {
  const tpl = document.querySelector('.tpl');
  const box = tpl.getBoundingClientRect();
  const out = { canvas: {w: box.width, h: box.height}, outside: [], clipped: [], ellipsised: [] };

  /* 1. TEXT PAINTED OUTSIDE THE CANVAS.
     Measured per text node with a Range, not per element: an element's border
     box can sit inside the page while the text inside it spills, and a Range
     sees through `overflow:hidden` and absolute placement to where the glyphs
     actually are. */
  /* 2. CLIPPED BY AN ANCESTOR — measured the SAME way, against the nearest
     ancestor that clips horizontally, so the two checks share one frame of
     reference (viewport coordinates, after transforms).

     The obvious implementation is `el.scrollWidth > el.clientWidth`, and it is
     wrong here. Those are untransformed, element-local numbers, so
     `modern-t22`'s rotated "RESUME" rail reports +20px of clipped text on the
     SHIPPED sample while every glyph is drawn exactly where it was designed to
     be. A check that fails on the résumé this project ships is not measuring
     the thing it is named after — which is why the plain sample is run as a
     control before any of this is believed. Comparing rects places the rotated
     case correctly at zero, because both rects are post-transform. */
  const clipperOf = (el) => {
    for (let a = el; a && a !== tpl.parentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (/hidden|clip|scroll|auto/.test(cs.overflowX)) return a;
    }
    return null;
  };

  /* A Range's rects are NOT transform-aware in Chromium, and an element's are.
     Measured on `modern-t22`, whose "RESUME" rail is rotated -90deg: the rail's
     own box is 153px wide (67..220), while a Range over the same glyph returns
     233px (27..260) — the UNROTATED run, in a frame nothing is painted in.
     That is what made the shipped sample look like it lost 20px of text.

     So inside a transformed subtree the range is abandoned and the parent
     element's own rect is used instead. Coarser — it is the whole element, not
     the run — and correct, which is the trade to make in a check whose entire
     output is "this text is not where it should be". */
  const transformed = (el) => {
    for (let a = el; a && a !== tpl.parentElement; a = a.parentElement) {
      if (getComputedStyle(a).transform !== 'none') return true;
    }
    return false;
  };

  const walk = document.createTreeWalker(tpl, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    const text = n.nodeValue.trim();
    if (!text || !n.parentElement) continue;
    let rects;
    if (transformed(n.parentElement)) {
      rects = [n.parentElement.getBoundingClientRect()];
    } else {
      const rng = document.createRange();
      rng.selectNodeContents(n);
      rects = Array.from(rng.getClientRects());
    }
    rects = rects.filter((r) => r.width > 0 && r.height > 0);
    if (!rects.length) continue;

    /* Compare what is PAINTED, not what the Range reports. A Range returns the
       full extent of the run even when an ancestor clips it: `modern-t21`'s
       contact pill ellipsises a long email at 670px, and the Range still hands
       back 869px — 19px "outside" an 850px canvas where the glyphs stop well
       inside it. So the rect is first intersected with every clipping ancestor
       BETWEEN the text and the canvas. The canvas itself is excluded, because
       it is the thing being compared against — most templates set
       `overflow:hidden` on `.tpl`, and intersecting with that would make this
       check unable to fire at all. */
    let lo = -Infinity, hi = Infinity;
    for (let a = n.parentElement; a && a !== tpl; a = a.parentElement) {
      if (!/hidden|clip|scroll|auto/.test(getComputedStyle(a).overflowX)) continue;
      const ab = a.getBoundingClientRect();
      lo = Math.max(lo, ab.left); hi = Math.min(hi, ab.right);
    }
    for (const r of rects) {
      const l = Math.max(r.left, lo), rt = Math.min(r.right, hi);
      if (rt <= l) continue;                       // clipped away entirely
      const left = box.left - l, right = rt - box.right;
      const over = Math.max(left, right);
      if (over > tol) {
        out.outside.push({
          px: +over.toFixed(1),
          side: left > right ? 'start' : 'end',
          text: text.slice(0, 60),
          tag: n.parentElement ? n.parentElement.tagName.toLowerCase() : '?',
          cls: n.parentElement ? (n.parentElement.className || '') : '',
        });
      }
    }

    const clip = n.parentElement && clipperOf(n.parentElement);
    if (!clip || clip === tpl) continue;   // the canvas is check 1's job
    /* SIGNALLED loss is not silent loss, and the whole audit is about the
       silent kind. `text-overflow: ellipsis` puts a "…" where the text stopped,
       so the reader knows something was cut and can go and shorten it.
       `modern-t21`'s contact pill does exactly that, deliberately. Counting it
       as a defect would push us to "fix" a design that is already honest. */
    const ell = /ellipsis/.test(getComputedStyle(n.parentElement).textOverflow)
             || /ellipsis/.test(getComputedStyle(clip).textOverflow);
    const cb = clip.getBoundingClientRect();
    for (const r of rects) {
      const over = Math.max(cb.left - r.left, r.right - cb.right);
      if (over > tol) {
        (ell ? out.ellipsised : out.clipped).push({
          px: +over.toFixed(1),
          text: text.slice(0, 60),
          tag: clip.tagName.toLowerCase(),
          cls: clip.className || '',
        });
      }
    }
  }

  return out;
}
"""


def scan(page, data: dict, key: str) -> dict:
    # for_pdf=True embeds the fonts. set_content()'s base URL is about:blank, so
    # a linked stylesheet resolves to nothing and every width below would be
    # measured in a fallback face — silently wrong, no error. Same trap as
    # tools/verify_height.py.
    page.set_content(document_html(data, key, for_pdf=True), wait_until="networkidle")
    # Auto-fit changes the type scale, which changes every width. Measure the
    # settled layout, not one halfway through a fit.
    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
    return page.evaluate(SCAN_JS, TOLERANCE)


def worst(result: dict) -> float:
    """The worst SILENT loss. `ellipsised` is deliberately excluded: a "..."
    tells the reader text was cut, which is the opposite of the failure this
    tool is named after."""
    px = [f["px"] for f in result["outside"]] + [c["px"] for c in result["clipped"]]
    return max(px) if px else 0.0


def run(keys: list[str], data: dict, label: str) -> int:
    from playwright.sync_api import sync_playwright

    bad = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 900, "height": 1200})
        page = ctx.new_page()
        for key in keys:
            r = scan(page, data, key)
            w = worst(r)
            if w:
                bad.append((key, w, r))
                print(f"\n{key}: worst +{w:.1f}px")
                for f in sorted(r["outside"], key=lambda x: -x["px"])[:4]:
                    print(f"    outside {f['side']:>5} +{f['px']:>6.1f}px  "
                          f"{f['tag']}.{f['cls'][:28]:<28} {f['text']!r}")
                for c in sorted(r["clipped"], key=lambda x: -x["px"])[:4]:
                    print(f"    clipped       +{c['px']:>6.1f}px  "
                          f"{c['tag']}.{c['cls'][:28]:<28} {c['text']!r}")
            else:
                note = (f"  (+{max(e['px'] for e in r['ellipsised']):.0f}px ellipsised)"
                        if r["ellipsised"] else "")
                print(f"{key}: clean{note}")
        ctx.close()
        browser.close()

    print(f"\n{label}: {len(keys) - len(bad)}/{len(keys)} clean, {len(bad)} losing text")
    if bad:
        print("  " + ", ".join(f"{k} (+{w:.0f})" for k, w, _ in
                               sorted(bad, key=lambda x: -x[1])))
    return len(bad)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--extreme", action="store_true",
                    help="one unbroken 120-character token per field")
    ap.add_argument("--lang", default="en", choices=("en", "ar"))
    ap.add_argument("--plain", action="store_true",
                    help="the shared sample, unmodified (should always be clean)")
    a = ap.parse_args()

    keys = a.keys or sorted(registry.ported_keys())
    if a.plain:
        data, label = SAMPLES[a.lang], f"plain/{a.lang}"
    elif a.extreme:
        data, label = extreme_sample(a.lang), f"extreme/{a.lang}"
    else:
        data, label = wide_sample(a.lang), f"wide/{a.lang}"
    return 1 if run(keys, data, label) else 0


if __name__ == "__main__":
    raise SystemExit(main())
