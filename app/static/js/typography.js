/* Typography runtime — the user's weight and size choices, per element.
 *
 * Inlined into the document by app/typography/render.py, only when the résumé
 * chose something, right after the canvas and BEFORE autofit.js. The family
 * is plain CSS (render.py); this does the two things CSS cannot:
 *
 * WEIGHT. Each element's own weight is read from computed style - the
 * template's inline weight, or the Arabic policy's 800 on the name - and
 * replaced, inline and !important, by:
 *   headlines                  the chosen weight, else nearest[own weight]
 *   details, own weight < 600  the chosen weight, else nearest[own weight]
 *   details, own weight >= 600 the emphasis face (700): template-bold text
 *                              such as a job title stays bold
 * `nearest` is computed by the server's registry.nearest_weight(), so the rule
 * lives in one place. Every weight written is a built face, and
 * font-synthesis is none, so nothing is ever faked.
 *
 * SIZE. autofit.js owns inline font-size (it clears and rewrites it on every
 * fit), so sizes are not written here. This computes a factor per element,
 * and autofit multiplies it into what it writes (`scale(el)`):
 *   name       target / the largest size inside .cv-name
 *   section    target / the largest size inside that .cv-section
 *   details    target / the template's dominant details size - the size
 *              carrying the most characters
 * One factor per role keeps the template's own hierarchy: a job title that
 * was 1.17x body stays 1.17x body.
 *
 * Then `data-cvt` goes on <html>, which is what switches the family rules on.
 * Until that moment nothing can lay out in a chosen family, so no face is
 * fetched at a weight nobody chose.
 */
(function () {
  "use strict";

  var cfgEl = document.getElementById("cv-typography-config");
  var tpl = document.querySelector(".tpl");
  if (!cfgEl || !tpl) return;
  var C = JSON.parse(cfgEl.textContent);

  var els = [tpl].concat(Array.prototype.slice.call(tpl.querySelectorAll("*")));

  function roleOf(el) {
    if (el.closest(".cv-name")) return "name";
    if (el.closest(".cv-section")) return "section";
    return "body";
  }

  function ownText(el) {
    var n = 0;
    for (var c = el.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) n += c.nodeValue.trim().length;
    }
    return n;
  }

  function hundred(w) {
    var n = Math.round(parseFloat(w) / 100) * 100;
    return Math.min(900, Math.max(100, n || 400));
  }

  // ---- read everything first: weight and size are inherited, so writing a
  // parent before reading its child would read our own value back.
  var info = els.map(function (el) {
    var cs = getComputedStyle(el);
    return { el: el, role: roleOf(el), weight: hundred(cs.fontWeight),
             size: parseFloat(cs.fontSize) || 0, text: ownText(el),
             family: cs.fontFamily };
  });

  // ---- headlines left on "Template default" keep the template's face.
  // A name or section title that sets no font-family of its own INHERITS it
  // (ats-t1's name inherits Archivo from .tpl), and the Details rule
  // overrides .tpl and every wrapper - so without this, choosing only a
  // Details font would silently restyle the headlines too. Each is pinned to
  // the family it had before the rules switch on (read above, while
  // data-cvt is still absent), which in Arabic is the font policy's own face.
  if (C.body.family && !C.heading.family) {
    info.forEach(function (i) {
      if (i.role !== "body") i.el.style.setProperty("font-family", i.family, "important");
    });
  }

  // ---- weight
  info.forEach(function (i) {
    var c = i.role === "body" ? C.body : C.heading;
    if (!c.family) return;
    var w;
    if (i.role === "body" && c.emphasis && i.weight >= c.emphasis_from) w = c.emphasis;
    else w = c.weight || c.nearest[String(i.weight)];
    i.el.style.setProperty("font-weight", String(w), "important");
  });

  // ---- size factors
  var factor = new WeakMap();
  var active = false;

  function largest(list) {
    return list.reduce(function (m, i) { return i.text && i.size > m ? i.size : m; }, 0);
  }
  function setRole(list, target) {
    if (!target) return;
    var ref = largest(list);
    if (!ref) return;
    var k = target / ref;
    list.forEach(function (i) { factor.set(i.el, k); });
    if (Math.abs(k - 1) > 1e-9) active = true;
  }

  setRole(info.filter(function (i) { return i.role === "name"; }), C.heading.size_px);

  if (C.heading.section_px) {
    var roots = Array.prototype.slice.call(tpl.querySelectorAll(".cv-section"))
      .filter(function (s) { return !s.parentElement.closest(".cv-section"); });
    roots.forEach(function (root) {
      setRole(info.filter(function (i) {
        return i.el === root || root.contains(i.el);
      }), C.heading.section_px);
    });
  }

  if (C.body.size_px) {
    var body = info.filter(function (i) { return i.role === "body"; });
    var chars = {};
    body.forEach(function (i) { if (i.text) chars[i.size] = (chars[i.size] || 0) + i.text; });
    var dominant = 0, most = -1;
    Object.keys(chars).forEach(function (s) {
      if (chars[s] > most) { most = chars[s]; dominant = parseFloat(s); }
    });
    if (dominant) {
      var k = C.body.size_px / dominant;
      body.forEach(function (i) { factor.set(i.el, k); });
      if (Math.abs(k - 1) > 1e-9) active = true;
    }
  }

  window.CVTypography = {
    active: active,
    scale: function (el) { var k = factor.get(el); return k === undefined ? 1 : k; }
  };

  document.documentElement.setAttribute("data-cvt", "");
})();
