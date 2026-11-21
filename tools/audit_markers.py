"""Are bullets and timeline dots where they belong?  (feature/defects, 2026-11-20)

The user's rule, for all 49 templates, English and Arabic, Letter and A4:
  * every BULLET is vertically centred on the FIRST line of its text;
  * a TIMELINE dot is centred ON its line (horizontally) and level with its
    entry's first text line, and the line does not stick out above the first
    dot or below the last one.

Measured on the rendered page (the preview and the PDF are the same layout):

  BULLETS   every `li` whose marker is drawn. The marker is the browser's
            ::marker, so it is painted in a probe colour (colour only - no
            `content`) and found by its pixels; its ink centre is compared
            with its first line's OPTICAL CENTRE: baseline - x-height / 2 in the
            text's own face (the typographic rule for bullets; Arabic faces
            set their tooth height to the x-height). The densest-ink band was
            tried first and rejected: in Arabic it is the baseline strokes,
            which read every correct disc as ~3px high. A template's own dot element (`.cv-dot`)
            is measured the same way, from its box.
  TIMELINE  every small round absolutely-positioned element (a dot) is matched
            to its line: the border of an ancestor list, the border of its own
            entry, or a thin absolute bar beside it. Reported: the dot centre's
            distance from the line centre (x), from its entry's first-line
            optical centre (y), and how far the line runs past the first / last dot box.

    python tools/audit_markers.py [--lang en|ar] [--paper letter|a4] [keys...]
    python tools/audit_markers.py --selftest        # the instrument, on known pages

PASS: bullet |dy| <= 1px; dot |dx| <= 0.5px, |dy| <= 1px; line inside the
first and last dot boxes (0.5px).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DPR = 2
PROBE = (255, 0, 255)
TOL_BULLET, TOL_DX, TOL_DY, TOL_LINE = 1.0, 0.5, 1.0, 0.5

_GEOMETRY = r"""() => {
  const tpl = document.querySelector('.tpl'), T = tpl.getBoundingClientRect();
  const R = (r) => ({x: r.left - T.left, y: r.top - T.top, w: r.width, h: r.height});
  const firstLine = (root, skip) => {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (!n.textContent.trim()) continue;
      if (skip && skip.some((s) => s.contains(n.parentElement))) continue;
      const cs = getComputedStyle(n.parentElement);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      const rs = [...rg.getClientRects()].filter((r) => r.width > 1);
      if (rs.length) {
        // every rect on the first line (inline runs of different faces)
        const top = rs[0].top;
        const line = rs.filter((r) => Math.abs(r.top - top) < 2);
        const l = Math.min(...line.map((r) => r.left)), rr = Math.max(...line.map((r) => r.right));
        const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
        // the line's optical centre: baseline - x-height / 2, in this text's
        // own face (Arabic faces set their tooth height to the x-height)
        const cx = document.createElement('canvas').getContext('2d');
        cx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
        const asc = cx.measureText('Hxg').fontBoundingBoxAscent;
        const xh = cx.measureText('x').actualBoundingBoxAscent;
        const base = rs[0].top + asc;
        return {x: l - T.left, y: rs[0].top - T.top, w: rr - l, h: rs[0].height, lh,
                fs: parseFloat(cs.fontSize), mid: base - xh / 2 - T.top};
      }
    }
    return null;
  };
  // ---- bullets
  const bullets = [];
  for (const li of tpl.querySelectorAll('li')) {
    const cs = getComputedStyle(li);
    const dot = li.querySelector(':scope > .cv-dot');
    if (cs.listStyleType === 'none' && !dot) continue;
    const text = firstLine(li, dot ? [dot] : null);
    if (!text) continue;
    const box = li.getBoundingClientRect();
    const rtl = cs.direction === 'rtl';
    bullets.push({li: R(box), rtl, text, dot: dot ? R(dot.getBoundingClientRect()) : null,
                  pos: cs.listStylePosition});
  }
  // ---- timeline dots
  const dots = [...tpl.querySelectorAll('*')].filter((e) => {
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    return cs.position === 'absolute' && r.width >= 6 && r.width <= 16 && cs.transform === 'none' &&
           Math.abs(r.width - r.height) < 0.6 && parseFloat(cs.borderTopLeftRadius) >= r.width / 2 - 0.6 &&
           !e.closest('li') && !e.classList.contains('cv-dot');
  });
  const out = [];
  for (const d of dots) {
    const dr = d.getBoundingClientRect();
    // the entry: the dot may sit in a zero-size anchor inside the title
    // (rendering.tl_node), so climb to the first ancestor holding text
    let entry = d.parentElement;
    for (let i = 0; i < 4 && entry && entry !== tpl && !firstLine(entry, [d]); i++) entry = entry.parentElement;
    const cx = dr.left + dr.width / 2, cy = dr.top + dr.height / 2;
    // the line: (a) a thin absolute bar under the same entry or its list;
    // (b) a side border on the entry or an ancestor (up to 3 levels)
    let line = null;
    // a bar beside the entries: inside the list, or beside the list (t2, t13)
    // the list: the nearest ancestor holding two or more of these dots
    let list = d.parentElement;
    for (let i = 0; i < 6 && list !== tpl && dots.filter((x) => list.contains(x)).length < 2; i++) list = list.parentElement;
    const isBar = (e) => {
      if (e === d) return false;
      const cs = getComputedStyle(e), r = e.getBoundingClientRect();
      return cs.position === 'absolute' && r.width > 0 && r.width <= 4 && r.height > 12 &&
             Math.abs(r.left + r.width / 2 - cx) < 12;
    };
    let bars = [...list.querySelectorAll('*')].filter(isBar);
    if (!bars.length && list.parentElement) bars = [...list.parentElement.querySelectorAll('*')].filter(isBar);
    if (bars.length) {
      const top = Math.min(...bars.map((b) => b.getBoundingClientRect().top));
      const bottom = Math.max(...bars.map((b) => b.getBoundingClientRect().bottom));
      const b0 = bars[0].getBoundingClientRect();
      line = {kind: 'bar', x: b0.left + b0.width / 2 - T.left, top: top - T.top, bottom: bottom - T.top,
              segs: bars.length, owner: bars[0].parentElement};
    } else {
      let e = entry;
      for (let i = 0; i < 4 && e && e !== tpl; i++, e = e.parentElement) {
        const cs = getComputedStyle(e), r = e.getBoundingClientRect();
        const lw = parseFloat(cs.borderLeftWidth), rw = parseFloat(cs.borderRightWidth);
        const cand = [];
        if (lw > 0 && cs.borderLeftStyle !== 'none') cand.push(r.left + lw / 2);
        if (rw > 0 && cs.borderRightStyle !== 'none') cand.push(r.right - rw / 2);
        const near = cand.filter((x) => Math.abs(x - cx) < 12);
        if (near.length) {
          line = {kind: i === 0 ? 'entry-border' : 'list-border', x: near[0] - T.left,
                  top: r.top - T.top, bottom: r.bottom - T.top, el: i,
                  owner: i === 0 ? e.parentElement : e};
          break;
        }
      }
    }
    const title = firstLine(entry, [d]);
    let gid = 'none';
    if (line) {
      if (!line.owner.dataset.auditId) line.owner.dataset.auditId = String(Math.random()).slice(2, 8);
      gid = line.kind + ':' + Math.round(line.x) + ':' + line.owner.dataset.auditId;
      delete line.owner;
    }
    out.push({dot: R(dr), cx: cx - T.left, cy: cy - T.top, line, title, group: gid});
  }
  return {bullets, dots: out, size: [T.width, T.height]};
}"""


def _ink_core(img, rect, probe_out=True):
    """Centre (css px) of the core ink band of the text inside `rect`."""
    from PIL import Image  # noqa: F401
    x0 = max(0, int(rect["x"] * DPR)); x1 = min(img.width, int((rect["x"] + rect["w"]) * DPR))
    y0 = max(0, int(rect["y"] * DPR)); y1 = min(img.height, int((rect["y"] + rect["h"]) * DPR))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    crop = img.crop((x0, y0, x1, y1))
    px = crop.load(); W, H = crop.size
    # background = the most common colour of the crop's border pixels
    from collections import Counter
    border = Counter()
    for x in range(W):
        border[px[x, 0]] += 1; border[px[x, H - 1]] += 1
    bg = border.most_common(1)[0][0]
    rows = []
    for y in range(H):
        n = 0
        for x in range(W):
            c = px[x, y]
            if probe_out and abs(c[0] - 255) < 60 and c[1] < 90 and abs(c[2] - 255) < 60:
                continue
            if abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) > 120:
                n += 1
        rows.append(n)
    peak = max(rows) if rows else 0
    if peak == 0:
        return None
    core = [y for y, n in enumerate(rows) if n >= 0.5 * peak]
    return (y0 + (core[0] + core[-1] + 1) / 2) / DPR


def _probe_centre(img, band):
    """Centre (css px) of the probe-coloured pixels in `band`, or None."""
    x0 = max(0, int(band[0] * DPR)); x1 = min(img.width, int(band[2] * DPR))
    y0 = max(0, int(band[1] * DPR)); y1 = min(img.height, int(band[3] * DPR))
    if x1 <= x0 or y1 <= y0:
        return None
    px = img.load(); ys = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = px[x, y]
            if c[0] > 200 and c[1] < 90 and c[2] > 200:
                ys.append(y)
    if not ys:
        return None
    return (min(ys) + max(ys) + 1) / 2 / DPR


def measure_html(page, html: str) -> dict:
    """Geometry + verdicts for one rendered document."""
    from PIL import Image
    page.set_content(html, wait_until="networkidle")
    page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
    page.add_style_tag(content=".tpl li::marker { color: rgb(255,0,255) !important; }"
                                " .tpl .cv-dot { background: rgb(255,0,255) !important; }")
    geo = page.evaluate(_GEOMETRY)
    shot = page.locator(".tpl").screenshot()
    img = Image.open(io.BytesIO(shot)).convert("RGB")
    res = {"bullets": [], "dots": []}
    for b in geo["bullets"]:
        t = b["text"]
        line_band = (t["y"], t["y"] + max(t["h"], t["lh"]))
        if b["dot"]:
            d = b["dot"]; mc = d["y"] + d["h"] / 2
        else:
            li = b["li"]
            if b["pos"] == "inside":
                band = (li["x"], line_band[0], li["x"] + li["w"], line_band[1])
            elif b["rtl"]:
                band = (li["x"] + li["w"], line_band[0] - 4, li["x"] + li["w"] + 30, line_band[1] + 4)
            else:
                band = (li["x"] - 30, line_band[0] - 4, li["x"], line_band[1] + 4)
            mc = _probe_centre(img, band)
        tc = t["mid"]
        if mc is None or tc is None:
            res["bullets"].append({"dy": None, "y": t["y"]})
            continue
        res["bullets"].append({"dy": round(mc - tc, 2), "y": round(t["y"], 1)})
    groups: dict = {}
    for d in geo["dots"]:
        tc = d["title"]["mid"] if d["title"] else None
        dx = round(d["cx"] - d["line"]["x"], 2) if d["line"] else None
        dy = round(d["cy"] - tc, 2) if tc is not None else None
        res["dots"].append({"dx": dx, "dy": dy, "group": d["group"], "cy": round(d["cy"], 1),
                            "dot": d["dot"], "line": d["line"]})
        groups.setdefault(d["group"], []).append(d)
    over = []
    for g, ds in groups.items():
        line = ds[0]["line"]
        if not line:
            continue
        first = min(ds, key=lambda d: d["cy"]); last = max(ds, key=lambda d: d["cy"])
        top = min(d["line"]["top"] for d in ds); bottom = max(d["line"]["bottom"] for d in ds)
        above = first["dot"]["y"] - top
        below = bottom - (last["dot"]["y"] + last["dot"]["h"])
        over.append({"group": g, "kind": line["kind"], "above": round(above, 2),
                     "below": round(below, 2), "n": len(ds)})
    res["lines"] = over
    return res


def verdict(res: dict) -> list[str]:
    bad = []
    for b in res["bullets"]:
        if b["dy"] is None:
            bad.append(f"bullet at y={b['y']}: not measurable")
        elif abs(b["dy"]) > TOL_BULLET:
            bad.append(f"bullet at y={b['y']}: {b['dy']:+.2f}px off its first line")
    for d in res["dots"]:
        if d["dx"] is None:
            bad.append(f"dot at y={d['cy']}: no line found")
            continue
        if abs(d["dx"]) > TOL_DX:
            bad.append(f"dot at y={d['cy']}: {d['dx']:+.2f}px off its line (x)")
        if d["dy"] is None or abs(d["dy"]) > TOL_DY:
            bad.append(f"dot at y={d['cy']}: {d['dy']}px off its first line (y)")
    for ln in res.get("lines", []):
        if ln["above"] > TOL_LINE:
            bad.append(f"line {ln['group']}: runs {ln['above']}px above the first dot")
        if ln["below"] > TOL_LINE:
            bad.append(f"line {ln['group']}: runs {ln['below']}px below the last dot")
    return bad


def _doc(key: str, lang: str, paper: str, cv: str = "demo") -> str:
    from app.rendering import document_html
    sfx = "_ar" if lang == "ar" else ""
    d = json.loads((ROOT / "data" / f"{cv}_resume{sfx}.json").read_text(encoding="utf-8"))
    d["paper"] = paper
    return document_html(d, key, for_pdf=True)


def audit(keys=None, langs=("en", "ar"), papers=("letter", "a4"), cv="demo"):
    from playwright.sync_api import sync_playwright
    from app import registry
    keys = keys or sorted(registry.ported_keys())
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 900, "height": 1300}, device_scale_factor=DPR)
        for lang in langs:
            for paper in papers:
                for key in keys:
                    res = measure_html(page, _doc(key, lang, paper, cv))
                    rows.append({"key": key, "lang": lang, "paper": paper,
                                 "n_bullets": len(res["bullets"]), "n_dots": len(res["dots"]),
                                 "bad": verdict(res), "res": res})
        b.close()
    return rows


_SELF = """<!doctype html><html dir="{d}"><head><style>body{{margin:0}}
.tpl{{width:850px;height:400px;position:relative;font:16px/1.5 Arial;background:#fff}}
ul{{margin:0;padding:20px 40px}} .tl{{position:absolute;top:100px;inset-inline-start:100px;
border-inline-start:2px solid #000;padding-inline-start:20px}} .e{{position:relative;margin-bottom:20px}}
.dot{{position:absolute;width:12px;height:12px;border-radius:50%;background:#000;
inset-inline-start:-27px;top:{top}px}}</style></head><body><div class="tpl">
<ul><li>{li}Good bullet text line</li></ul>
<div class="tl"><div class="e"><span class="dot"></span><b>Title one</b><div>body</div></div>
<div class="e"><span class="dot"></span><b>Title two</b><div>body</div></div></div></div></body></html>"""


def selftest() -> None:
    """The instrument on pages whose answers are known (memory:
    measurement-instrument-errors): a native disc on Arial; a dot 6px off
    its title; a dot centred on its title; the list border runs past the last
    dot in every case (body below it)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 900, "height": 500}, device_scale_factor=DPR)
        for d in ("ltr", "rtl"):
            # 16px Arial, 24px line: the first line box is 24px; centring a 12px
            # dot on the x-height core needs top ~ 7-8px; top 0 is ~-7px off
            for top, expect_ok in ((0, False), (7.5, True)):
                res = measure_html(page, _SELF.format(d=d, top=top, li=""))
                dys = [x["dy"] for x in res["dots"]]
                dxs = [x["dx"] for x in res["dots"]]
                ok = all(abs(v) <= TOL_DY for v in dys)
                print(d, "dot top", top, "dy", dys, "dx", dxs, "lines", res["lines"],
                      "bullets", res["bullets"], "PASS" if ok == expect_ok else "INSTRUMENT WRONG")
        b.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--selftest"]:
        selftest(); sys.exit(0)
    langs, papers, out = ("en", "ar"), ("letter", "a4"), None
    if "--lang" in args:
        i = args.index("--lang"); langs = (args[i + 1],); del args[i:i + 2]
    if "--paper" in args:
        i = args.index("--paper"); papers = (args[i + 1],); del args[i:i + 2]
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
    rows = audit(args or None, langs, papers)
    if out:
        Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        flag = "OK " if not r["bad"] else "BAD"
        print(flag, r["key"], r["lang"], r["paper"], f"bullets={r['n_bullets']} dots={r['n_dots']}",
              "; ".join(r["bad"][:3]))
