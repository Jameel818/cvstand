"""Phase 8: MIXED content — an Arabic résumé naming English employers.

WHAT THIS PROTECTS

    Phases 1-7 each proved one layer bilingual. Every one of them tested a
    page that was Arabic all the way down, or English all the way down. The
    case left over is the one a real bilingual applicant actually produces: an
    Arabic CV that names `Halden & Row`, or an English CV that names
    `هالدن آند رو`. There the two directions meet INSIDE a line, and the
    Unicode bidi algorithm — not the template, not the schema — decides where
    each character lands.

    It decides using the neighbours of every NEUTRAL character. Letters are
    strong: a Latin word cannot be reordered into Arabic, and vice versa. What
    can move is punctuation: `&`, `+`, `(`, `-`, `,`, `|`. This is why the
    fixtures in tests/samples.py are neutral-heavy and why `Halden & Row` is
    the recurring probe — if that run is resolved right-to-left it reads
    `Row & Halden`, which is wrong, silent, and looks like a typo rather than
    a rendering bug.

WHAT WAS MEASURED, AND THE VERDICT

    The phase-8 plan assumed the bidi-isolation trap would be sprung and that
    the fix would be `<bdi>` (or `unicode-bidi: isolate`) around every user
    field. Measured across all 49 templates in Chromium, and per-character in
    real Word, IT IS NOT. Nothing is torn, nothing overlaps, no separator
    escapes the pair it separates, and every Latin island inside Arabic prose
    still reads left-to-right:

        Chromium, 49/49 templates, the MIXED résumé ....... 0 findings
        Word, ats-t1, per-character `Information(5)` ...... `Halden & Row,`
            advances 152.65 -> 204.70pt, a clean left-to-right island inside a
            right-to-left paragraph

    That is the same shape as phase 4, where the letter-spacing purge was
    measured to fix nothing and was dropped rather than shipped. Isolation was
    therefore NOT added: it would be markup in all 50 files, in service of a
    defect that does not exist, and `<bdi>` is not free — it pins a field's
    direction to its own first strong character, which changes how an
    all-neutral field (a bare phone number, a date) resolves.

    So this file is a GATE, not a fix. What it holds still is the property the
    algorithm currently gives us for free, because the things that would take
    it away are ordinary edits: a template wrapping a field in an element with
    an explicit `dir`, a `unicode-bidi: bidi-override` added to make one
    stubborn line look right, an isolate introduced for one field and not its
    neighbour.

WHY THE ASSERTIONS ARE SHAPED THE WAY THEY ARE

    "The earlier field must be drawn further right in RTL" is the obvious
    check and it is WRONG. An LTR island inside an RTL line is read
    left-to-right, so two fields that both resolve LTR are correctly drawn
    earlier-on-the-left. Written that way the check reports 33 of 49 templates
    as broken, all of them false. What is asserted here instead is only what
    is unambiguous whichever way a reader scans the line:

      * a field's glyphs stay CONTIGUOUS — nothing else is drawn inside them;
      * two inline elements on one line do not OVERLAP;
      * a separator stays BETWEEN the two fields it separates;
      * a Latin run reads left-to-right and an Arabic run right-to-left.

    Each of those is false only if the text is genuinely mangled.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from markupsafe import escape

from app import registry
from app.rendering import canvas_html, document_html

from tests import samples

ROOT = Path(__file__).resolve().parents[1]
TPL_DIR = ROOT / "app" / "templates" / "resumes"

# Templates the browser gate runs on by default. Chosen for the shape of their
# contact block, which is where the neutrals cluster: t1/t3/t8/t22 join every
# contact bit into ONE text node with a separator between each pair, which is
# the only place a separator can escape; modern-t1/t5 give each bit its own
# element, which is the cross-element case. The `slow` test below sweeps all 49.
PROBE_KEYS = ["ats-t1", "ats-t3", "ats-t8", "ats-t22", "modern-t1", "modern-t5"]

#: A gap wider than this between two rects of the SAME text node, on the same
#: visual line, means something else got drawn in the middle. Runs that merely
#: sit next to each other are contiguous to within a fraction of a pixel; the
#: threshold is loose enough that a wide inter-word space cannot trip it.
GAP_PX = 6


# --------------------------------------------------------------- static gates

def test_the_mixed_samples_really_are_mixed():
    """If this fails the rest of the file is testing single-direction text.

    Cheap, and it has to exist: every assertion below is about the meeting
    point of two scripts, and a fixture edit that dropped the Latin employer
    would leave them all passing on an all-Arabic page.
    """
    arabic = re.compile(r"[؀-ۿ]")
    latin = re.compile(r"[A-Za-z]")
    for value in samples.MIXED_LATIN:
        assert latin.search(value), value
    for value in samples.MIXED_NEUTRAL:
        assert not latin.search(value) and not arabic.search(value), (
            f"{value!r} is in MIXED_NEUTRAL but carries a strong character; "
            "the direction check excludes it on the grounds that it has none")
    for value in samples.REVERSED_ARABIC:
        assert arabic.search(value), value
    blob = str(samples.MIXED)
    assert arabic.search(blob) and latin.search(blob)
    blob = str(samples.REVERSED)
    assert arabic.search(blob) and latin.search(blob)
    # and the neutrals that make the case a case
    assert "&" in samples.MIXED["experience"][0]["company"]
    assert "(" in samples.MIXED["contact"]["phone"]


@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_every_template_renders_mixed_content(key):
    """StrictUndefined smoke over the whole catalogue, both mixtures.

    Rendering is where a bilingual assumption becomes a 500 — `dots_for` on a
    level word in the other language, a `|join` on a list of mixed types. All
    49 have only ever been rendered with a single-script résumé."""
    assert canvas_html(samples.MIXED, key)
    assert canvas_html(samples.REVERSED, key)


@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_planted_values_survive_as_real_text(key):
    """The employer named in the other script must reach the page as text.

    Not a formality: a template that decided to `upper()` a company name, or
    to slice it to fit, would drop or corrupt a script it was never tested
    with. Templates that have no slot for a field are not blamed for it — the
    assertion is per value, only where the same field renders in the
    single-script résumé.

    Compared against the ESCAPED value, because `Halden & Row` reaches the
    page as `Halden &amp; Row`. That is correct and load-bearing — the same
    `&` the DOCX smoke test pins — but it means a naive `in` check fails on
    exactly the field this file cares most about."""
    mixed = canvas_html(samples.MIXED, key)
    plain = canvas_html(samples.ARABIC, key)
    for value, plain_value in (
        (samples.MIXED["experience"][0]["company"], samples.ARABIC["experience"][0]["company"]),
        (samples.MIXED["contact"]["phone"], samples.ARABIC["contact"]["phone"]),
        (samples.MIXED["education"][0]["school"], samples.ARABIC["education"][0]["school"]),
        (samples.MIXED["skills"][0]["name"], samples.ARABIC["skills"][0]["name"]),
    ):
        if str(escape(plain_value)) not in plain:
            continue          # this layout has no slot for that field
        assert str(escape(value)) in mixed, (
            f"{key}: {value!r} did not reach the page")


def test_no_template_pins_a_direction_by_hand():
    """A hardcoded `dir=` or a `bidi-override` in a template is the edit that
    would break mixed content — and it would look like a fix while doing it.

    `dir` belongs on `<html>`, set from the document language by
    `rendering.document_html()`. A template that sets its own overrides the
    reader's whole page for that subtree; `unicode-bidi: bidi-override` goes
    further and disables the algorithm outright, which forces Latin text to be
    laid out right-to-left — the exact mangling this file exists to catch.
    """
    offenders = []
    for path in sorted(TPL_DIR.rglob("*.j2")):
        src = path.read_text(encoding="utf-8")
        for pattern in (r"\bdir\s*=\s*[\"'](?:rtl|ltr)[\"']",
                        r"unicode-bidi\s*:\s*bidi-override",
                        r"direction\s*:\s*(?:rtl|ltr)"):
            for m in re.finditer(pattern, src):
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{line}: {m.group(0)}")
    assert not offenders, (
        "a template pins text direction by hand; direction comes from the "
        "document language on <html>:\n  " + "\n  ".join(offenders))


@pytest.mark.parametrize("key", ["modern-t1", "ats-t1"])
def test_the_word_export_carries_both_scripts(key):
    """The DOCX path is a different renderer with a different bidi engine, and
    phase 7 marks EVERY run `w:rtl` — including the runs that end up holding
    a Latin employer, because the masters are built before any content exists.

    Measured in real Word per character (see the module docstring): `w:rtl` on
    a run does not reorder strong Latin letters, so `Halden & Row,` still
    advances left-to-right. What is asserted here, in the fast loop, is the
    part that can be checked without Word: both scripts arrive intact, in one
    paragraph, with the neutral still between the two Latin words."""
    from docx import Document

    from app.exporters import render_docx

    paras = [p.text for p in
             Document(io.BytesIO(render_docx(samples.MIXED, key))).paragraphs]
    body = "\n".join(paras)
    assert "Halden & Row" in body, "the Latin employer did not survive the export"
    assert "بورتسايد" in body, "the Arabic city did not survive the export"
    assert samples.MIXED["contact"]["phone"] in body
    # the employer and the Arabic city share one line — that is the mixed run
    assert any("Halden & Row" in p and "بورتسايد" in p for p in paras)


# ------------------------------------------------------- the browser measurement

#: Returns a list of findings; an empty list is a clean page. Everything it
#: looks at is a rendered geometric fact — none of it can be asserted against
#: the CSS, because the bidi algorithm runs after layout has been described.
_PROBE = r"""(args) => {
  const { values, rtl } = args;
  const tpl = document.querySelector('.tpl');
  const GAP = args.gap;
  const found = [];

  const linesOf = (node, a, b) => {
    const r = document.createRange();
    r.setStart(node, a); r.setEnd(node, b);
    const rects = [...r.getClientRects()].filter(x => x.width > 0.5);
    const by = new Map();
    for (const x of rects) {
      const top = Math.round(x.top);
      if (!by.has(top)) by.set(top, []);
      by.get(top).push(x);
    }
    return [...by.entries()].map(([top, rs]) => ({
      top, n: rs.length,
      rects: rs.slice().sort((p, q) => p.left - q.left),
      left: Math.min(...rs.map(x => x.left)),
      right: Math.max(...rs.map(x => x.right)),
    }));
  };

  // ---- 1. a field's glyphs stay contiguous -------------------------------
  const walk = document.createTreeWalker(tpl, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let node;
  while ((node = walk.nextNode())) if (/\S/.test(node.nodeValue)) nodes.push(node);

  for (const n of nodes) {
    for (const line of linesOf(n, 0, n.nodeValue.length)) {
      for (let i = 0; i + 1 < line.rects.length; i++) {
        const gap = line.rects[i + 1].left - line.rects[i].right;
        if (gap > GAP)
          found.push({ kind: 'TORN', gap: +gap.toFixed(1),
                       text: n.nodeValue.trim().slice(0, 80) });
      }
    }
  }

  // ---- 2. inline siblings on one line do not overlap ---------------------
  const byLine = new Map();
  for (const el of tpl.querySelectorAll('*')) {
    if (el.children.length || !(el.textContent || '').trim()) continue;
    const cs = getComputedStyle(el);
    if (!cs.display.startsWith('inline')) continue;
    if (cs.position === 'absolute' || cs.position === 'fixed') continue;
    if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 0.5) continue;
    const top = Math.round(r.top);
    if (!byLine.has(top)) byLine.set(top, []);
    byLine.get(top).push({ t: el.textContent.trim().slice(0, 40),
                           l: r.left, r: r.right });
  }
  for (const [top, els] of byLine) {
    for (let i = 0; i < els.length; i++)
      for (let j = i + 1; j < els.length; j++)
        if (els[i].l < els[j].r - 1 && els[j].l < els[i].r - 1)
          found.push({ kind: 'OVERLAP', a: els[i].t, b: els[j].t, top });
  }

  // ---- 3. a separator stays between the pair it separates ----------------
  for (const n of nodes) {
    const s = n.nodeValue;
    const spans = [];
    const taken = new Array(s.length).fill(false);
    for (const v of values) {
      let i = s.indexOf(v);
      while (i >= 0) {
        let free = true;
        for (let k = i; k < i + v.length; k++) if (taken[k]) { free = false; break; }
        if (free) {
          for (let k = i; k < i + v.length; k++) taken[k] = true;
          spans.push({ v, a: i, b: i + v.length });
        }
        i = s.indexOf(v, i + 1);
      }
    }
    spans.sort((p, q) => p.a - q.a);
    for (let i = 0; i + 1 < spans.length; i++) {
      const A = spans[i], B = spans[i + 1];
      if (!s.slice(A.b, B.a).trim()) continue;         // whitespace only
      const la = linesOf(n, A.a, A.b), lb = linesOf(n, B.a, B.b);
      const ls = linesOf(n, A.b, B.a);
      if (la.length !== 1 || lb.length !== 1 || ls.length !== 1) continue;  // wrapped
      if (la[0].top !== lb[0].top || ls[0].top !== la[0].top) continue;
      const lo = Math.min(la[0].left, lb[0].left);
      const hi = Math.max(la[0].right, lb[0].right);
      if (ls[0].left < lo - 0.5 || ls[0].right > hi + 0.5)
        found.push({ kind: 'SEPARATOR-ESCAPED', a: A.v, b: B.v,
                     sep: s.slice(A.b, B.a),
                     sepx: [ls[0].left, ls[0].right], pair: [lo, hi] });
    }
  }

  // ---- 4. each planted run reads in its OWN direction --------------------
  // A Latin island inside Arabic must still advance left-to-right, and an
  // Arabic island inside Latin right-to-left. Compared first-vs-last
  // character per visual line, which shaping and ligatures cannot upset.
  for (const probe of args.runs) {
    for (const n of nodes) {
      const at = n.nodeValue.indexOf(probe.text);
      if (at < 0) continue;
      const chars = [];
      for (let i = 0; i < probe.text.length; i++) {
        const r = document.createRange();
        r.setStart(n, at + i); r.setEnd(n, at + i + 1);
        const b = r.getBoundingClientRect();
        if (b.width > 0.2) chars.push({ i, mid: b.left + b.width / 2,
                                        top: Math.round(b.top) });
      }
      const by = new Map();
      for (const c of chars) {
        if (!by.has(c.top)) by.set(c.top, []);
        by.get(c.top).push(c);
      }
      for (const [top, cs] of by) {
        if (cs.length < 2) continue;
        const first = cs[0], last = cs[cs.length - 1];
        const advancesRight = last.mid > first.mid;
        if (advancesRight !== probe.ltr)
          found.push({ kind: 'RUN-REVERSED', text: probe.text,
                       want: probe.ltr ? 'left-to-right' : 'right-to-left',
                       firstMid: first.mid, lastMid: last.mid, top });
      }
      break;
    }
  }
  return found;
}"""


def _measure(playwright, data, key, *, values, runs):
    browser = playwright.chromium.launch(args=["--no-sandbox"])
    try:
        page = browser.new_page(viewport={"width": 850, "height": 1100})
        page.set_content(document_html(data, key, for_pdf=True), wait_until="networkidle")
        page.evaluate("document.fonts && document.fonts.ready")
        return page.evaluate(_PROBE, {
            "values": list(values), "runs": runs,
            "rtl": data.get("lang") == "ar", "gap": GAP_PX,
        })
    finally:
        browser.close()


def _mixed_probe():
    """The Latin runs planted into the Arabic résumé, plus one Arabic run, so
    both directions are asserted on the same page."""
    return [{"text": v, "ltr": True} for v in samples.MIXED_LATIN] + [
        {"text": samples.MIXED["contact"]["address"], "ltr": False}]


def _reversed_probe():
    return [{"text": v, "ltr": False} for v in samples.REVERSED_ARABIC] + [
        {"text": samples.REVERSED["experience"][0]["location"], "ltr": True}]


def _values(data):
    """Every field value long enough to be located unambiguously in a text
    node. Used to find the field PAIRS a separator sits between."""
    out = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k not in ("lang", "dir", "photo_url", "summary_highlight"):
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str) and len(obj.strip()) >= 3:
            out.add(obj.strip())

    walk(data)
    return sorted(out, key=len, reverse=True)


@pytest.mark.e2e
@pytest.mark.parametrize("key", PROBE_KEYS)
def test_mixed_arabic_page_is_not_mangled(_playwright, key):
    """An Arabic résumé naming English employers: nothing torn, nothing
    overlapping, no separator adrift, and `Halden & Row` still reads
    `Halden & Row`."""
    found = _measure(_playwright, samples.MIXED, key,
                     values=_values(samples.MIXED), runs=_mixed_probe())
    assert not found, f"{key}: mixed-content bidi damage: {found}"


@pytest.mark.e2e
@pytest.mark.parametrize("key", PROBE_KEYS)
def test_mixed_english_page_is_not_mangled(_playwright, key):
    """The mirror: an English résumé naming Arabic employers. The document has
    no `lang` key at all, which is what a bilingual user actually produces —
    they type a company name in Arabic without ever setting a language."""
    found = _measure(_playwright, samples.REVERSED, key,
                     values=_values(samples.REVERSED), runs=_reversed_probe())
    assert not found, f"{key}: mixed-content bidi damage: {found}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_single_script_arabic_page_is_not_mangled(_playwright, key):
    """The same measurement over the whole catalogue with the plain Arabic
    résumé. `slow`, like every other 49-template browser sweep here, so
    `-m "e2e and not slow"` stays the quick subset.

    Not redundant with the mixed pages: this is the baseline that says the
    probe's own thresholds are right. A finding here would mean the check is
    too tight, not that Arabic is broken — which is worth knowing before a
    mixed-content failure is believed."""
    found = _measure(_playwright, samples.ARABIC, key,
                     values=_values(samples.ARABIC), runs=[])
    assert not found, f"{key}: {found}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("key", sorted(registry._PORTED))
def test_every_template_survives_mixed_content(_playwright, key):
    """The whole catalogue, mixed both ways. Marked `slow` because it is 98
    browser renders; the six in PROBE_KEYS carry the day-to-day signal."""
    for data, runs in ((samples.MIXED, _mixed_probe()),
                       (samples.REVERSED, _reversed_probe())):
        found = _measure(_playwright, data, key, values=_values(data), runs=runs)
        assert not found, f"{key} ({data.get('lang', 'en')}): {found}"
