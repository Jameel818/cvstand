/* Auto-fit — seat a résumé of any length on one 1100px page.
 *
 * WHY NOT A TRANSFORM. Scaling `.tpl` geometrically is the obvious fix and it
 * is wrong here: `transform: scale(k)` shrinks the painted box to 850k wide, so
 * every full-bleed sidebar/band stops reaching the page edge, and widening the
 * logical canvas to 850/k instead breaks the absolutely-positioned layouts
 * (modern t7/t8/t11/t14/t15/t18/t21) whose px offsets are keyed to 850.
 *
 * So NO horizontal property is ever touched — no width, no height, no top/left
 * offset, no border. Only vertical rhythm (line-height, block margins/padding,
 * row-gap) and, as a second stage, font-size, which is horizontally safe for
 * the same reason: the text re-wraps inside boxes that have not moved.
 * Full-bleed and absolute panels come out exactly as designed.
 *
 * Two stages, tried in order of how visible they are:
 *   1. rhythm    d: 1.00 -> 0.85   recovers ~7-12%, type sizes untouched
 *   2. type      f: 1.00 -> 0.90   only after rhythm bottoms out
 *
 * This is the runtime form of a per-template `--density` variable, without the
 * 49-file edit: originals are read from computed style, cached, and re-applied
 * as `original * factor`.
 *
 * WHAT IT CANNOT DO. The two stages together recover roughly 15-20% of height.
 * Content past that still overflows at the floors; `fitted` comes back false
 * and the caller keeps warning. Auto-fit never expands — a short résumé keeps
 * its designed spacing and its whitespace.
 *
 * One implementation, three consumers: the builder preview (srcdoc), the PDF
 * exporter (Playwright awaits `ResumeAutofit.ready`) and tools/verify_autofit.py.
 * It is INLINED into the document by rendering.document_html() rather than
 * linked, for the same reason the PDF fonts are inlined: the PDF path renders
 * through `set_content()`, whose base URL is about:blank, so a `/static/...`
 * src resolves to nothing and fails silently.
 */
(function () {
  "use strict";

  var MAX_H = 1100;   // the page box

  /* Near zero, and deliberately so. Chromium paginates on ANY overflow past the
   * page box: ats-t15 ended at 1100.453 and modern-t13 at 1100.250, and both
   * shipped a 2-page PDF. Integer `scrollHeight` rounds those away, which is
   * why the old `scrollHeight <= 1102` check passed them for months. This is a
   * float-noise epsilon only — never a tolerance. */
  var SLACK = 0.05;

  /* Stage 1 — rhythm. Preferred, because it leaves the designer's type sizes
   * exactly as drawn. Recovers roughly 7-12% of height depending on how much of
   * the layout is leading rather than glyphs. */
  var FLOOR = 0.85;
  var STEP = 0.03;

  /* Stage 2 — type scale, only once rhythm has bottomed out and the page is
   * still over. Shrinking font-size is safe horizontally for the same reason
   * rhythm is: no width, offset or border is touched, so full-bleed panels and
   * the absolute Modern layouts keep their geometry — the text simply re-wraps
   * inside boxes that have not moved. Held at 0.90 because below that the
   * designed type hierarchy visibly flattens. */
  var TYPE_FLOOR = 0.90;
  var TYPE_STEP = 0.02;

  /* Vertical-only. Deliberately excludes width/height, top/left and border
   * widths — see the header note. font-size is handled separately, by stage 2. */
  var PROPS = ["marginTop", "marginBottom", "paddingTop", "paddingBottom", "rowGap"];

  var origins = new WeakMap();
  var lastResult = null;

  function tplEl() { return document.querySelector(".tpl"); }

  function px(v) {
    var n = parseFloat(v);
    return isFinite(n) ? n : null;
  }

  function elements() {
    var t = tplEl();
    if (!t) return [];
    var out = [t];                       // .tpl's own top/bottom page insets count
    var all = t.querySelectorAll("*");
    for (var i = 0; i < all.length; i++) out.push(all[i]);
    return out;
  }

  function capture(el) {
    if (origins.has(el)) return;
    var cs = getComputedStyle(el);
    var o = {};
    for (var i = 0; i < PROPS.length; i++) {
      var n = px(cs[PROPS[i]]);
      if (n) o[PROPS[i]] = n;            // 0 and NaN ("normal" row-gap) both skip
    }
    if (cs.lineHeight !== "normal") {
      var lh = px(cs.lineHeight);
      if (lh) o.lineHeight = lh;
    }
    var fs = px(cs.fontSize);
    if (fs) o.fontSize = fs;
    origins.set(el, o);
  }

  /* Capture every element BEFORE writing any of them. line-height and font-size
   * both inherit, so writing a parent first would make the child capture the
   * already-scaled value and compound the compression on the next pass.
   *
   * `d` scales rhythm, `f` scales type. Leading is a product of both: at type
   * scale f the line boxes must come down with the glyphs or the text floats in
   * its own leading. */
  /* The user's size choice, as a per-element factor from typography.js (only
   * present when the résumé chose a size). Multiplied into what this file
   * already writes, because autofit OWNS inline font-size: a size written
   * anywhere else would be cleared by reset() on the next fit. Written
   * !important where it applies, since an !important stylesheet size (the
   * Arabic `.sec-head` rescue) would otherwise swallow it. Absent, k is 1 and
   * every write below is exactly what it was before this hook existed. */
  function typeScale(el) {
    var T = window.CVTypography;
    return T ? T.scale(el) : 1;
  }

  function apply(d, f) {
    var els = elements(), i, k, o, el, s;
    for (i = 0; i < els.length; i++) capture(els[i]);
    for (i = 0; i < els.length; i++) {
      el = els[i];
      o = origins.get(el);
      s = typeScale(el);
      for (k in o) {
        if (k === "fontSize") {
          if (s === 1) el.style.fontSize = (o[k] * f) + "px";
          else el.style.setProperty("font-size", (o[k] * f * s) + "px", "important");
        } else if (k === "lineHeight") {
          if (s === 1) el.style.lineHeight = (o[k] * d * f) + "px";
          else el.style.setProperty("line-height", (o[k] * d * f * s) + "px", "important");
        } else el.style[k] = (o[k] * d) + "px";
      }
    }
  }

  function reset() {
    var els = elements();
    for (var i = 0; i < els.length; i++) {
      var o = origins.get(els[i]);
      if (!o) continue;
      for (var k in o) els[i].style[k] = "";
    }
  }

  /* How far down the page the content actually reaches.
   *
   * `.tpl.scrollHeight` is the obvious measure and it is wrong in both
   * directions here:
   *   too low  — absolutely-placed panels (modern t7/t8/t11/t14/t15/t18/t21)
   *              never grow it, and an overflow:hidden box swallows its own
   *              overrun, so real spill reads as a clean 1100;
   *   too high — a fixed-height clipped box whose scrollHeight counts trailing
   *              padding reads as overflowing while every glyph is visible. That
   *              false positive made ats-t7 and modern-t22 compress themselves
   *              on the shared sample, which they fit perfectly well.
   *
   * So measure the TEXT, not the boxes: walk the text nodes and take the lowest
   * Range rect. A Range rect is pure layout geometry — an ancestor's
   * `overflow: hidden` clips what is painted but never moves it — so this sees
   * through clipping and absolute placement alike, and counts only ink that a
   * reader would actually lose. Images are included; anything with no text and
   * no image is decoration and is deliberately ignored. */
  function measure() {
    var t = tplEl();
    if (!t) return 0;
    var top = t.getBoundingClientRect().top;
    var h = 0;

    var walker = document.createTreeWalker(t, NodeFilter.SHOW_TEXT, null, false);
    var rng = document.createRange();
    var n;
    while ((n = walker.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      rng.selectNodeContents(n);
      var rc = rng.getBoundingClientRect();
      if (!rc.height) continue;                     // display:none / empty line box
      h = Math.max(h, rc.bottom - top);
    }

    var media = t.querySelectorAll("img, svg, canvas");
    for (var i = 0; i < media.length; i++) {
      var mr = media[i].getBoundingClientRect();
      if (mr.height) h = Math.max(h, mr.bottom - top);
    }

    /* Text is not the only thing that paginates. A box whose trailing padding
     * or margin runs past 1100 puts a second page in the PDF even though every
     * glyph sits inside the first — ats-t7, ats-t15 and modern-t13 all shipped
     * a 2-page export that way, with no visible symptom on screen.
     *
     * `.tpl.scrollHeight` is exactly that overflow, and it is the right term
     * ONLY when `.tpl` does not clip: with `overflow: hidden` nothing escapes
     * the page box, so Chromium emits one page and the number would be a false
     * positive (it is what made modern-t22 compress itself for nothing). */
    if (getComputedStyle(t).overflowY !== "hidden") {
      var kids = t.querySelectorAll("*");
      for (var j = 0; j < kids.length; j++) {
        var kr = kids[j].getBoundingClientRect();
        if (kr.height || kr.width) h = Math.max(h, kr.bottom - top);
      }
      h = Math.max(h, t.scrollHeight);
    }
    /* Returned unrounded: a 0.45px overrun is a whole extra page. */
    return h;
  }

  function fit() {
    reset();
    // A chosen size is part of the design, not a compression: apply it
    // before measuring, and keep it even when nothing needs fitting.
    var scaled = !!(window.CVTypography && window.CVTypography.active);
    if (scaled) apply(1, 1);
    var natural = measure();
    var d = 1, f = 1, h = natural;

    while (h > MAX_H + SLACK && d > FLOOR + 1e-9) {          // stage 1: rhythm
      d = Math.max(FLOOR, Number((d - STEP).toFixed(4)));
      apply(d, f);
      h = measure();
    }
    while (h > MAX_H + SLACK && f > TYPE_FLOOR + 1e-9) {     // stage 2: type
      f = Math.max(TYPE_FLOOR, Number((f - TYPE_STEP).toFixed(4)));
      apply(d, f);
      h = measure();
    }

    if (d === 1 && f === 1 && !scaled) reset();   // nothing was needed; leave the DOM clean
    lastResult = {
      natural: natural,
      height: h,
      density: d,
      typeScale: f,
      fitted: h <= MAX_H + SLACK,
      compressed: d < 1 || f < 1
    };
    var root = document.documentElement;
    root.setAttribute("data-autofit", String(d));
    root.setAttribute("data-autofit-type", String(f));
    root.setAttribute("data-autofit-fitted", lastResult.fitted ? "1" : "0");
    try {
      window.dispatchEvent(new CustomEvent("resume-autofit", { detail: lastResult }));
    } catch (e) { /* CustomEvent unavailable — the ready promise still carries it */ }
    return lastResult;
  }

  var fontsReady = (document.fonts && document.fonts.ready)
    ? document.fonts.ready
    : Promise.resolve();

  /* Fonts first: measuring in a fallback face measures the wrong document. */
  var ready = fontsReady.then(fit).catch(function () {
    lastResult = { natural: 0, height: 0, density: 1, typeScale: 1,
                   fitted: true, compressed: false, error: true };
    return lastResult;
  });

  window.ResumeAutofit = {
    fit: fit,
    reset: reset,
    measure: measure,
    ready: ready,
    result: function () { return lastResult; },
    MAX_H: MAX_H,
    FLOOR: FLOOR
  };
})();
