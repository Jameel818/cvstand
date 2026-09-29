"""Measure every Modern template's LAYOUT for the Word export into
app/word_layouts.json.

    venv/Scripts/python tools/build_word_layouts.py          # write
    venv/Scripts/python tools/build_word_layouts.py --check  # compare, exit 1 if stale

The Word layouts (docs/WORD_LAYOUTS_PLAN.md) rebuild each Modern template's
SHAPE in Word: a side column, a header band, which sections sit where and in
what order, their headings, and the colours of each zone. None of that is
transcribed by hand. It is read from the rendered template in Chromium, the
same document the PDF prints, in English AND Arabic, so a template change
shows up in `--check` (and in the e2e test that runs it).

WHAT IS MEASURED, per template and language
  zones     side column (tall narrow coloured column, or the split line of an
            open layout), band (the coloured block the name sits in), main.
  items     where the sample's own content lands: name, title, contact,
            photo, and every section (summary, achievements, experience,
            education, skills, recognition, tools, languages). Found by the
            sample's TEXT, not by class names, so it works on all 24.
            Each gets its zone and, from the .cv-section just above it in the
            same zone, its heading label and whether it is set in capitals.
  colours   each zone's background, body text, heading and name colour, and a
            heading's own fill (ribbon / pill headings).
  photo     size and whether it is round, from a real <img> (the sample is
            rendered WITH a photo for this).

WHAT IS DECIDED, not measured (HINTS): the archetype of each template (the
plan's mapping, approved 2026-09-29), which side the side column sits on in
English, and the timeline flag. The measurement confirms the side and fails
loudly when it disagrees.
"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry  # noqa: E402
from app.rendering import document_html  # noqa: E402

OUT = ROOT / "app" / "word_layouts.json"
SAMPLES = {"en": ROOT / "data" / "sample_resume.json",
           "ar": ROOT / "data" / "sample_resume_ar.json"}

# archetype, English side of the side column (None: no side column), timeline.
# From docs/WORD_LAYOUTS_PLAN.md §3 (user-approved 2026-09-29).
HINTS = {
    "modern-t1": ("open", "right", False),
    "modern-t2": ("sidebar", "left", False),
    "modern-t3": ("sidebar", "left", False),
    "modern-t4": ("sidebar", "left", True),
    "modern-t5": ("sidebar", "left", True),
    "modern-t6": ("open", "right", False),
    "modern-t7": ("band", "right", False),
    "modern-t8": ("band", "left", False),
    "modern-t9": ("sidebar", "left", False),
    "modern-t10": ("sidebar", "left", False),
    "modern-t11": ("band", "left", False),
    "modern-t12": ("open", "right", True),
    "modern-t13": ("band", None, True),
    "modern-t14": ("band", "left", True),
    "modern-t15": ("sidebar", "left", False),
    "modern-t16": ("sidebar", "left", False),
    "modern-t17": ("sidebar", "left", False),
    "modern-t18": ("band", "left", False),
    "modern-t19": ("gutter", None, False),
    "modern-t20": ("sidebar", "left", False),
    "modern-t21": ("band", "left", False),
    "modern-t22": ("open", "right", True),
    "modern-t23": ("sidebar", "left", True),
    "modern-t24": ("sidebar", "left", True),
}

SKILLS = {"bars": "bars", "dot-grid": "dots", "rings": "dots", "inline": "dots"}


def _photo_uri() -> str:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (60, 60), (120, 120, 120)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _needles(d: dict) -> dict:
    c = d.get("contact") or {}
    return {
        "summary": (d["summary"].split(d.get("summary_highlight") or "\0")[0])[:18],
        "achievements": d["achievements"][0]["label"],
        "experience": d["experience"][0]["bullets"][0][:18],
        "education": d["education"][0]["degree"],
        "skills": d["skills"][0]["name"],
        "recognition": d["recognition"][0]["title"],
        "tools": d["tools"][0],
        "languages": d["languages"][0]["name"],
        "email": c.get("email", ""),
        "phone": c.get("phone", ""),
        "title": d["title"],
    }


_MEASURE = r"""(arg) => {
  const {needles, side, split} = arg;
  const tpl = document.querySelector('.tpl');
  const R = tpl.getBoundingClientRect(), W = R.width, H = R.height;
  const rel = r => ({x: (r.left - R.left) / W, y: (r.top - R.top) / H,
                     w: r.width / W, h: r.height / H,
                     cx: (r.left + r.width / 2 - R.left) / W, cy: (r.top + r.height / 2 - R.top) / H});
  const opaque = c => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent';
  const hex = c => { const m = c.match(/\d+(\.\d+)?/g); if (!m) return null;
    if (m.length > 3 && +m[3] === 0) return null;
    return m.slice(0, 3).map(v => (+v).toString(16).padStart(2, '0')).join('').toUpperCase(); };
  const bgOf = e => { const c = getComputedStyle(e).backgroundColor; return opaque(c) ? hex(c) : null; };
  const own = e => [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();

  // --- side column
  let sideR = null, sideBg = null;
  if (side) {
    let best = null;
    for (const e of tpl.querySelectorAll('*')) {
      const r = rel(e.getBoundingClientRect());
      if (r.h < 0.55 || r.w < 0.15 || r.w > 0.49) continue;
      const onSide = side === 'left' ? r.x < 0.12 : r.x + r.w > 0.88;
      if (!onSide) continue;
      const score = (bgOf(e) ? 2 : 0) + r.h;
      if (!best || score > best.score) best = {r, bg: bgOf(e), score};
    }
    if (best) { sideR = best.r; sideBg = best.bg; }
  }
  const splitX = sideR ? (side === 'left' ? sideR.x + sideR.w : sideR.x) : split;

  // --- band: the coloured block holding the name (not the side column)
  const name = document.querySelector('.cv-name');
  const nr0 = rel(name.getBoundingClientRect());
  let bandR = null, bandBg = null;
  for (const e of tpl.querySelectorAll('*')) {   // the coloured block BEHIND the name,
    const r = rel(e.getBoundingClientRect()); const bg = bgOf(e);   // parent or not
    if (!bg || bg === 'FFFFFF' || r.h >= 0.5 || r.y >= 0.15 || r.w <= 0.25) continue;
    if (nr0.cx < r.x || nr0.cx > r.x + r.w || nr0.cy < r.y || nr0.cy > r.y + r.h) continue;
    if (!bandR || r.w * r.h < bandR.w * bandR.h) { bandR = r; bandBg = bg; }
  }

  let headOK = true;
  const zoneOf = (r, blockW) => {
    if (bandR && r.cy >= bandR.y && r.cy <= bandR.y + bandR.h && r.cx >= bandR.x && r.cx <= bandR.x + bandR.w) return 'band';
    // full width, above where the columns start: a plain header over both
    if (headOK && blockW > 0.6 && (!sideR || r.y + r.h <= sideR.y + 0.01) && side) return 'head';
    if (side && splitX != null) {
      if (side === 'left' ? r.cx < splitX : r.cx > splitX) return 'side';
    }
    return 'main';
  };

  // --- find the sample's content
  const all = [...tpl.querySelectorAll('*')];
  const findEls = (needle, exact) => all.filter(e => { const t = own(e);
      return t && (exact ? t === needle : t.includes(needle)); });
  const items = [];
  const blockW = el => { let e = el; while (e && e !== tpl && getComputedStyle(e).display.startsWith('inline')) e = e.parentElement;
    return rel(e.getBoundingClientRect()).w; };
  // an item's OWN ground: a small filled element around it (modern-t21's
  // contact pill). None when the colour behind it is a separate block, as
  // modern-t11's yellow band is: then the zone's colour is the ground.
  const localBg = el => { for (let e = el; e && e !== tpl; e = e.parentElement) {
      const r = rel(e.getBoundingClientRect()); if (r.w * r.h > 0.12) return null;
      const b = bgOf(e); if (b) return b; } return null; };
  const push = (kind, el) => { if (!el) return;
    const r = rel(el.getBoundingClientRect());
    items.push({kind, el, r, zone: zoneOf(r, blockW(el)), color: hex(getComputedStyle(el).color), bg: localBg(el)}); };
  push('name', name);
  // an open layout's full-width header exists only if the NAME is in it;
  // otherwise full-width text (t12's summary) belongs to its column
  if (items[0].zone !== 'head') headOK = false;
  const nr = nr0;
  const nz = items[0].zone;
  const titles = findEls(needles.title, true).filter(e => !e.closest('.cv-name'))
      .map(e => { const r = rel(e.getBoundingClientRect());
                  return {e, d: Math.abs(r.cy - nr.cy) + (zoneOf(r, blockW(e)) === nz ? 0 : 0.1)}; })
      .sort((a, b) => a.d - b.d);
  if (titles.length && titles[0].d < 0.2) push('title', titles[0].e);
  for (const k of ['summary', 'achievements', 'experience', 'education', 'skills',
                   'recognition', 'tools', 'languages']) {
    const els = findEls(needles[k], k === 'education' || k === 'skills' || k === 'recognition' || k === 'achievements');
    const hit = els.length ? els : findEls(needles[k], false);
    push(k, hit[0]);
  }
  const em = findEls(needles.email, false)[0], ph = findEls(needles.phone, false)[0];
  push('contact', em || ph);
  const img = tpl.querySelector('img');
  if (img) push('photo', img);

  // headings: the nearest .cv-section above an item, in the same zone
  // a heading is a .cv-section, or an element styled EXACTLY like one in its
  // zone (modern-t3's "Software" lacks the class but is the same heading)
  const sig = e => { const c = getComputedStyle(e);
      return [c.fontSize, c.fontWeight, c.color, c.textTransform, c.fontFamily].join('|'); };
  const marked = [...tpl.querySelectorAll('.cv-section')];
  const zOf = e => zoneOf(rel(e.getBoundingClientRect()), blockW(e));
  const sigs = new Set(marked.map(e => zOf(e) + '#' + sig(e)));
  const alike = all.filter(e => !marked.includes(e) && !e.closest('.cv-section, .cv-name')
      && own(e) && own(e).length <= 40
      && (sigs.has(zOf(e) + '#' + sig(e))
          // a short label on its own coloured fill: t4's ribbons
          || (bgOf(e) && rel(e.getBoundingClientRect()).h < 0.05 && rel(e.getBoundingClientRect()).w > 0.08
              && !/\d/.test(own(e)))));
  const heads = [...marked, ...alike].map(e => { const r = rel(e.getBoundingClientRect());
      return {e, r, zone: zOf(e)}; });
  const used = new Set();
  const caps = e => getComputedStyle(e).textTransform === 'uppercase' ||
      (/[A-Za-z]/.test(e.textContent) && e.textContent === e.textContent.toUpperCase());
  const headFill = e => { for (let p = e, i = 0; p && i < 3 && p !== tpl; p = p.parentElement, i++) {
      const bg = bgOf(p); const r = rel(p.getBoundingClientRect());
      if (bg && r.h < 0.08) return bg; } return null; };
  // a rule under the heading: its own bottom border or a thin parent's
  const ruleOf = e => { for (let p = e, i = 0; p && i < 3 && p !== tpl; p = p.parentElement, i++) {
      const c = getComputedStyle(p); if (rel(p.getBoundingClientRect()).h > 0.08) break;
      if (parseFloat(c.borderBottomWidth) >= 0.5 && c.borderBottomStyle !== 'none') return true; }
      return false; };
  // the heading's words as written, a <br> read as a space (modern-t15's
  // "Personal<br>Information"); the capitals are the `caps` flag's job
  const labelOf = e => { const c = e.cloneNode(true);
      c.querySelectorAll('br').forEach(b => b.replaceWith(' '));
      return c.textContent.replace(/\s+/g, ' ').trim(); };
  items.sort((a, b) => a.r.y - b.r.y || a.r.x - b.r.x);
  for (const it of items) {
    // these never show a heading in Word; they must not claim one either (the
    // chips beside t5's "Contact" pill took it from the contact lines)
    if (['name', 'title', 'photo', 'achievements'].includes(it.kind)) continue;
    const cands = heads.filter(h => h.zone === it.zone && h.r.y + h.r.h <= it.r.y + 0.004
                                     && it.r.y - (h.r.y + h.r.h) < 0.16 && !used.has(h.e)
                                     && Math.abs(h.r.cx - it.r.cx) < 0.45)
                       .sort((a, b) => (b.r.y + b.r.h) - (a.r.y + a.r.h));
    // a heading belongs to the FIRST item below it: skip one that has a
    // closer item between them
    const above = cands.find(c => !items.some(o => o !== it && o.zone === it.zone && o.kind !== 'name'
            && o.r.y > c.r.y + c.r.h - 0.002 && o.r.y < it.r.y - 0.002 && !['title', 'photo'].includes(o.kind)));
    const starts = c => it.el.textContent.trim().startsWith(c.e.textContent.trim());
    // a label BESIDE its content: inline in the same line (t4's "Tools"), or
    // in a gutter (t19), level with the entry's first line
    const beside = heads.filter(c => !used.has(c.e) && c.zone === it.zone
            && ((c.e !== it.el && it.el.contains(c.e) && starts(c))
                || ((arg.rtl ? c.r.cx > it.r.x + it.r.w - 0.01 : c.r.cx < it.r.x + 0.01)
                    && c.r.y <= it.r.y + 0.01
                    && it.r.y - c.r.y < (arg.gutter ? 0.07 : 0.012))))
        .sort((a, b) => b.r.y - a.r.y)[0];
    // a label INSIDE the item's own line wins: t8's "Also" block holds
    // "<b>Tools</b> — Figma ..." under one "Also" heading
    // (only at the START of the line: modern-t1's summary highlights a phrase
    // mid-sentence in the heading style, and that is no label)
    const inline = heads.find(c => !used.has(c.e) && c.e !== it.el && it.el.contains(c.e) && starts(c));
    // contact lines take only a real heading above them: t22 labels each
    // line ("Email", "Phone"), which is not the section's heading
    const FIELD = /^(e-?mail|phone|mobile|tel|address|location|web(site)?|site|البريد|الهاتف|الجوال|العنوان|الموقع)/i;
    const h = it.kind === 'contact' ? (above && !FIELD.test(labelOf(above.e)) ? above : null)
            : inline || (arg.gutter ? (beside || above) : (above || beside));
    if (h) { used.add(h.e); it.label = labelOf(h.e); it.caps = caps(h.e);
             it.fill = headFill(h.e); it.hcolor = hex(getComputedStyle(h.e).color); it.rule = ruleOf(h.e); }
  }
  // contact: one line, or stacked lines
  const contactStacked = !!(em && ph && Math.abs(em.getBoundingClientRect().top - ph.getBoundingClientRect().top) > 6);

  // colours per zone: most characters wins
  const tally = (els) => { const t = {}; for (const e of els) { const s = own(e); if (!s) continue;
      const k = hex(getComputedStyle(e).color); if (k) t[k] = (t[k] || 0) + s.length; }
      const b = Object.entries(t).sort((a, b) => b[1] - a[1])[0]; return b ? b[0] : null; };
  const inZone = (e, z) => zOf(e) === z;
  const body = all.filter(e => !e.closest('.cv-name, .cv-section'));
  const zones = {};
  for (const z of ['side', 'band', 'head', 'main']) {
    zones[z] = {text: tally(body.filter(e => inZone(e, z))),
                heading: tally(heads.filter(h => h.zone === z).map(h => h.e))};
  }
  const nameStyle = getComputedStyle(name);
  const headPx = heads.length ? parseFloat(getComputedStyle(heads[0].e).fontSize) : 14;
  const imgR = img ? rel(img.getBoundingClientRect()) : null;
  const radOf = e => { const v = getComputedStyle(e).borderTopLeftRadius;
      return v.endsWith('%') ? parseFloat(v) / 100 * e.getBoundingClientRect().width : parseFloat(v); };
  let radius = img ? radOf(img) : 0;
  for (let p = img && img.parentElement, i = 0; p && i < 3 && p !== tpl; p = p.parentElement, i++) {
    const pr = p.getBoundingClientRect(), ir = img.getBoundingClientRect();
    if (getComputedStyle(p).overflow !== 'visible' && Math.abs(pr.width - ir.width) < 0.25 * ir.width)
      radius = Math.max(radius, radOf(p) * ir.width / pr.width);
  }
  return {
    side: sideR ? {x: sideR.x, w: sideR.w, bg: sideBg} : (side ? {x: null, w: side === 'left' ? split : 1 - split, bg: null} : null),
    band: bandR ? {x: bandR.x, y: bandR.y, w: bandR.w, h: bandR.h, bg: bandBg} : null,
    zones,
    name: {color: hex(nameStyle.color), px: parseFloat(nameStyle.fontSize),
           centred: nameStyle.textAlign === 'center' && Math.abs(nr.cx - 0.5) < 0.06, zone: items[0].zone},
    heading_px: headPx,
    contact_stacked: contactStacked,
    photo: imgR ? {zone: items.find(i => i.kind === 'photo').zone, w: imgR.w, round: radius >= 0.4 * img.getBoundingClientRect().width} : null,
    band_span: !bandR ? null : (() => { if (!sideR) return 'full';
        const ov = (a0, a1, b0, b1) => Math.max(0, Math.min(a1, b1) - Math.max(a0, b0));
        const onSide = ov(bandR.x, bandR.x + bandR.w, sideR.x, sideR.x + sideR.w) / sideR.w;
        const mx0 = side === 'left' ? sideR.x + sideR.w : 0, mx1 = side === 'left' ? 1 : sideR.x;
        const onMain = ov(bandR.x, bandR.x + bandR.w, mx0, mx1) / (mx1 - mx0);
        return onSide > 0.6 && onMain > 0.6 ? 'full' : onSide > 0.6 ? 'side' : 'main'; })(),
    side_top: sideR ? sideR.y : null,
    items: items.map(i => ({kind: i.kind, zone: i.zone, y: +i.r.y.toFixed(3), label: i.label || null,
                            caps: !!i.caps, fill: i.fill || null, hcolor: i.hcolor || null, rule: !!i.rule,
                            color: i.color, bg: i.bg})),
  };
}"""


def _side_to_logical(en_side: str | None) -> str | None:
    """Word keeps ONE logical order; the RTL twin mirrors it (w:bidiVisual)."""
    return None if en_side is None else ("start" if en_side == "left" else "end")


def measure_one(page, key: str, lang: str, data: dict) -> dict:
    arche, en_side, timeline = HINTS[key]
    # In Arabic every column mirrors (measured 2026-09-29), so look for the
    # side column on the other physical side.
    side = en_side if lang == "en" or en_side is None else ("right" if en_side == "left" else "left")
    split = 0.34 if side == "left" else 0.66
    data = dict(data, photo_url=_photo_uri())
    page.set_content(document_html(data, key, for_pdf=True))
    m = page.evaluate(_MEASURE, {"needles": _needles(data), "side": side, "split": split,
                                 "gutter": arche == "gutter", "rtl": lang == "ar"})
    # Instrument check: every section the template's SOURCE uses must be
    # found, and nothing the template never shows (it is not in its PDF, so
    # it is not in its Word file either - decision 2026-09-29).
    src = (ROOT / "app" / "templates" / "resumes" / "modern" / f"{tpl_block(key)}.j2").read_text(
        encoding="utf-8")
    shown = {k for k in SECTIONS if f"r.{k}" in src} | {"name"}
    found = {i["kind"] for i in m["items"]} - {"photo", "contact", "title"}
    if shown != found:
        raise SystemExit(f"{key} ({lang}): template shows {sorted(shown)}, "
                         f"measured {sorted(found)}")
    return m


SECTIONS = ("summary", "achievements", "experience", "education", "skills",
            "recognition", "tools", "languages")


def tpl_block(key: str) -> str:
    return registry.get(key).block


def _px_pt(px: float) -> float:
    return round(px * 0.75 * 2) / 2   # CSS px -> pt, to the half point


DEFAULT_LABELS = {"summary": "Profile", "experience": "Experience", "education": "Education",
                  "skills": "Skills", "recognition": "Certifications", "tools": "Tools",
                  "languages": "Languages", "contact": "Contact"}
UNLABELLED = {"name", "title", "photo", "contact_line", "achievements"}


def _default_label(kind: str, lang: str) -> str:
    from app.labels import reset_lang, set_lang, t
    token = set_lang(lang)
    try:
        return str(t(DEFAULT_LABELS[kind]))
    finally:
        reset_lang(token)


def compile_lang(key: str, m: dict, lang: str, other: dict) -> dict:
    """One language's Word structure: which cell each item goes in, and the
    colours of each zone. See app/exporters/docx_layout.py for how it is drawn.

    CELLS
      top_full   a row across both columns: a full-width band (t13, t21) or
                 the plain header of an open layout (t6)
      top_side / top_main
                 the tops of the two columns when a band covers only one of
                 them (t2, t8, t14, t17, t18), with whatever sits beside it
      side, main the two columns below
    """
    band, side = m["band"], m["side"]
    span = m["band_span"]
    band_bottom = band["y"] + band["h"] if band else None
    cells = {"top_full": [], "top_side": [], "top_main": [], "side": [], "main": []}
    for it in m["items"]:
        kind = it["kind"]
        if kind == "contact" and not m["contact_stacked"] and it["zone"] != "side":
            kind = "contact_line"
        entry = {"k": kind}
        # the other language's heading for this section, if the template
        # gives it one there: then a missing one here is a measuring gap
        # (t6's tools in Arabic), not the design (t1's summary has none)
        twin = next((o for o in other["items"] if o["kind"] == it["kind"]), None)
        if kind not in UNLABELLED and (it["label"] or (twin and twin["label"])):
            entry["label"] = it["label"] or _default_label(kind, lang)
            entry["caps"] = bool(it["caps"]) if it["label"] else lang == "en"
            if it["fill"]:
                entry["fill"] = it["fill"]
                entry["hcolor"] = it["hcolor"]
            entry["rule"] = bool(it["rule"])
        if kind == "contact_line" and it["bg"]:
            entry["bg"], entry["color"] = it["bg"], it["color"]
        zone = it["zone"]
        if zone == "band":
            cell = {"full": "top_full", "main": "top_main", "side": "top_side"}[span]
        elif zone == "head":
            cell = "top_full"
        elif band and span != "full" and it["y"] < band_bottom - 0.01:
            cell = "top_side" if zone == "side" else "top_main"   # level with the band
        else:
            cell = zone
        cells[cell].append(entry)
    zc = m["zones"]
    colours = {z: {"text": zc[z]["text"], "heading": zc[z]["heading"]} for z in zc}
    return {
        "cells": cells,
        "side_w": None if side is None else round(side["w"], 3),
        "side_bg": None if side is None else side["bg"],
        "band": None if band is None else {"span": span, "bg": band["bg"]},
        "colours": colours,
        "name": {"color": m["name"]["color"], "pt": min(40.0, max(18.0, _px_pt(m["name"]["px"]))),
                 "centred": m["name"]["centred"]},
        "heading_pt": min(13.0, max(8.5, _px_pt(m["heading_px"]))),
        "photo": None if m["photo"] is None else {
            "mm": int(min(45, max(20, round(m["photo"]["w"] * 215.9)))),
            "round": m["photo"]["round"]},
    }


def compile_entry(key: str, en: dict, ar: dict) -> dict:
    arche, en_side, timeline = HINTS[key]
    tpl = registry.get(key)
    return {"archetype": arche, "side": _side_to_logical(en_side), "timeline": timeline,
            "skills": SKILLS[tpl.skill_pattern],
            "en": compile_lang(key, en, "en", ar), "ar": compile_lang(key, ar, "ar", en)}


def measure() -> dict:
    from playwright.sync_api import sync_playwright
    samples = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in SAMPLES.items()}
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 850, "height": 1100})
            page.route("**/*", lambda route: route.abort())   # nothing leaves the machine
            for key in HINTS:
                got = {lang: measure_one(page, key, lang, samples[lang]) for lang in samples}
                out[key] = compile_entry(key, got["en"], got["ar"])
        finally:
            browser.close()
    return out


def render(layouts: dict) -> str:
    doc = {"generated_by": "tools/build_word_layouts.py",
           "note": "Measured from the rendered Modern templates; do not edit by hand. "
                   "See docs/WORD_LAYOUTS_PLAN.md.",
           "templates": layouts}
    return json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    if "--raw" in sys.argv:   # debugging: print the raw measurement of given keys
        from playwright.sync_api import sync_playwright
        keys = [a for a in sys.argv[1:] if a in HINTS]
        samples = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in SAMPLES.items()}
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 850, "height": 1100})
            pg.route("**/*", lambda route: route.abort())
            for k in keys:
                for lang in ("en", "ar"):
                    print(k, lang, json.dumps(measure_one(pg, k, lang, samples[lang]), ensure_ascii=False))
            b.close()
        return 0
    text = render(measure())
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"STALE {OUT.name}: re-run tools/build_word_layouts.py")
            return 1
        print(f"OK  {OUT.name} matches the templates")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(json.loads(text)['templates'])} templates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
