"""Cairo one step lighter in the Arabic interface (user, 2026-10-07).

"Make Cairo less bold everywhere it is used in the WEBSITE INTERFACE":
800 -> 600, 700 -> 600, 600 -> 500, 500 -> 400 (regular stays regular).
Measured, not assumed: every visible shell element whose text renders in
Cairo is collected from each Arabic page, and none may be heavier than 600.
The CV templates (iframes) and the t22 rail word are out of scope by
construction - the collector skips iframes - and English, which never
reaches the `[dir=rtl]` rules, keeps its weights exactly.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PAGES = ("/", "/templates", "/builder")

COLLECT = """() => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('iframe, svg')) continue;
    const own = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const fam = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    out.push({tag: el.tagName.toLowerCase(), cls: String(el.className || ''), fam, w: +cs.fontWeight});
  }
  return out;
}"""


def _collect(page, server, lang, path):
    page.goto(f"{server.url}/lang/{lang}?next={path}")
    page.wait_for_load_state("networkidle")
    if path == "/builder":
        page.click("#open-drawer")                 # the drawer's own heading
        expect(page.locator("#drawer")).to_have_class("drawer is-open")
    return page.evaluate(COLLECT)


@pytest.mark.parametrize("path", PAGES)
def test_no_arabic_interface_text_is_heavier_than_cairo_semibold(page, live_server, path):
    cairo = [e for e in _collect(page, live_server, "ar", path) if e["fam"] == "Cairo"]
    assert cairo, "no Cairo text found - the collector measured nothing"
    heavy = [e for e in cairo if e["w"] > 600]
    assert not heavy, f"Cairo still heavier than 600: {heavy[:5]}"


def test_each_role_moved_exactly_one_step(page, live_server):
    """The table, pinned: headings 700 -> 600, figures and section numbers
    800 -> 600, FAQ questions 600 -> 500, navigation 500 -> 400."""
    got = {}
    for path in ("/", "/builder"):
        for e in _collect(page, live_server, "ar", path):
            if e["fam"] == "Cairo":
                got.setdefault((e["tag"], e["cls"].split(" ")[0] if e["cls"] else ""), set()).add(e["w"])
    assert got[("h2", "")] == {600}
    assert got[("h3", "")] == {600}
    assert got[("b", "")] == {600}                 # .stat-strip figures
    assert got[("div", "eyebrow")] == {600}
    assert got[("summary", "")] == {500}           # FAQ questions
    assert got[("span", "num")] == {600}           # builder section numbers
    assert 500 not in got[("a", "")] and 700 not in got[("a", "")]


@pytest.mark.parametrize("path", PAGES)
def test_english_weights_are_unchanged(page, live_server, path):
    """English never reaches the rules; pinned at what shipped before."""
    els = _collect(page, live_server, "en", path)
    assert not [e for e in els if e["fam"] == "Cairo"]
    pinned = {
        "/": {("h2", ""): 800, ("summary", ""): 600, ("div", "eyebrow"): 700},   # FAQ questions
        "/templates": {("h4", ""): None},
        "/builder": {("summary", ""): 700, ("span", "num"): 800},                # form sections
    }[path]
    for e in els:
        key = (e["tag"], e["cls"].split(" ")[0] if e["cls"] else "")
        if pinned.get(key) is not None:
            assert e["w"] == pinned[key], (path, key, e["w"])
