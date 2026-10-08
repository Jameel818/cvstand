"""Stat chips that stack the number above its label are centred - both
lines - in every template, English and Arabic (user, 2026-10-08, mockup
stat-chips-centre.png).

Measured, not grepped: for each of the sample's chips, the number's and the
label's TEXT boxes (Range rects) against the chip's centre. A chip counts as
stacked when its label starts below its number. The ATS templates write
their chips inline ("14 - designers led") and are not stacked, so they are
out of scope by measurement, not by a list.

Changed on 2026-10-08 (were start-aligned): modern-t1 t3 t4 t7 t9 t11 t13 t16
t18 t19 t21 t23. Already centred: t2 t5 t6 t8 t10 t12 t15 t17 t20 t22 t24.
Word: tests/test_stat_chips_word.py.
"""
from __future__ import annotations

import pytest

from app import registry
from app.store import load_showcase

pytestmark = pytest.mark.e2e

JS = r"""(ach) => {
  const leaf = (txt) => [...document.querySelectorAll('.tpl *')].filter(e =>
      e.children.length === 0 ? e.textContent.trim() === txt
      : [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim() === txt));
  const out = [];
  for (const a of ach) {
    const m = leaf(a.metric)[0], l = leaf(a.label)[0];
    if (!m || !l) { out.push({metric: a.metric, missing: !m ? 'metric' : 'label'}); continue; }
    let c = m.parentElement; while (c && !c.contains(l)) c = c.parentElement;
    const rm = m.getBoundingClientRect(), rl = l.getBoundingClientRect(), rc = c.getBoundingClientRect();
    const range = (el) => { const r = document.createRange(); r.selectNodeContents(el); const b = r.getBoundingClientRect(); return b; };
    const im = range(m), il = range(l);   // the TEXT's own box, not the element's
    const cx = rc.left + rc.width / 2;
    out.push({metric: a.metric, stacked: il.top >= im.bottom - 2,
              dm: +((im.left + im.width / 2) - cx).toFixed(1), dl: +((il.left + il.width / 2) - cx).toFixed(1),
              chipW: Math.round(rc.width), mAlign: getComputedStyle(m).textAlign, lAlign: getComputedStyle(l).textAlign,
              chip: c.tagName + '.' + (c.className || '').toString().slice(0, 20)});
  }
  return out;
}"""


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_stacked_stat_chips_are_centred(page, deployed_server, lang):
    page.context.add_cookies([{"name": "ui_lang", "value": lang, "url": deployed_server.url}])
    ach = [{"metric": a["metric"], "label": a["label"]} for a in load_showcase(lang)["achievements"][:4]]
    off, stacked_templates = {}, []
    for key in registry.ported_keys():
        page.goto(f"{deployed_server.url}/preview?template_key={key}&showcase=1")
        page.wait_for_load_state("networkidle")
        res = [r for r in page.evaluate(JS, ach) if r.get("stacked")]
        if res:
            stacked_templates.append(key)
        bad = [r for r in res if abs(r["dm"]) > 1.5 or abs(r["dl"]) > 1.5]
        if bad:
            off[key] = bad
    assert len(stacked_templates) >= 23, f"the instrument found too few stacked chips: {stacked_templates}"
    assert not off, f"stacked stat chips not centred: {off}"
