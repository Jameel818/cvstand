"""The font ribbon is interface: choosing a font never changes its OWN font
(user, 2026-10-18).

Its labels (Section / Font / Weight / Size, القسم / الخط / السماكة / الحجم),
its buttons, its selects and the options inside their menus stay in the
face of the form fields beside them - Inter in English, IBM Plex Sans Arabic
in Arabic. Only the preview, the PDF and the Word file follow the choice.

The bug: the Font select drew its value (and so its options) in the chosen
face as a sample. Every font in every section's list is tried here, not a
handful: one family with an odd stack would be enough to bring it back.
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

#: Every text-bearing node of the ribbon, with its computed face and weight.
RIBBON_FACES = """() => {
  const out = {};
  document.querySelectorAll('#ribbon label, #ribbon .rb-lbl, #ribbon button, #ribbon select, #ribbon option, #ribbon optgroup')
    .forEach((e, i) => {
      const key = (e.id || e.getAttribute('for') || e.className || e.tagName) + ':' + e.tagName;
      const fam = getComputedStyle(e).fontFamily;
      out[key] = out[key] || new Set();
      out[key].add(fam);
    });
  const flat = {};
  Object.keys(out).forEach((k) => { flat[k] = Array.from(out[k]); });
  return flat;
}"""

FIELD_FACE = "() => getComputedStyle(document.querySelector('#resume-form .field input')).fontFamily"


def _on(page, role):
    if page.locator("#ty_section").input_value() != role:
        page.select_option("#ty_section", role)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_choosing_any_font_never_changes_the_ribbons_own_font(page, deployed_server, lang):
    page.goto(f"{deployed_server.url}/lang/{lang}?next=/builder")
    expect(page.frame_locator("#preview-frame").locator(".tpl")).to_be_visible()
    field = page.evaluate(FIELD_FACE)
    assert ("IBM Plex Sans Arabic" if lang == "ar" else "Inter") in field.split(",")[0]

    def check(context):
        faces = page.evaluate(RIBBON_FACES)
        wrong = {k: v for k, v in faces.items() if v != [field]}
        assert not wrong, f"{context}: ribbon text not in the form-field face {field!r}: {wrong}"
        # no inline style can bring a face back onto a select
        styled = page.locator("#ribbon select[style*='font'], #ribbon option[style*='font']")
        assert styled.count() == 0, f"{context}: an inline font style is back in the ribbon"

    check("on load")
    tried = 0
    for role in ("name", "heading", "body"):
        _on(page, role)
        values = page.locator(f"#ty_{role}_font option").evaluate_all(
            "os => os.map(o => o.value).filter(v => v && v !== 'template')")
        assert values, f"no fonts offered for {role}"
        for v in values:
            _on(page, role)
            page.select_option(f"#ty_{role}_font", v)
            check(f"{lang} {role} = {v}")
            tried += 1
    assert tried > 20


def test_the_preview_still_follows_the_choice(page, deployed_server):
    """The other half of the rule: the ribbon stopped following the font,
    the résumé did not."""
    page.goto(f"{deployed_server.url}/builder")
    name = page.frame_locator("#preview-frame").locator(".cv-name").first
    expect(name).to_be_visible()
    _on(page, "heading")
    page.select_option("#ty_heading_font", "Montserrat")
    expect(name).to_have_css("font-family", re.compile(r"CVT Montserrat"))
    expect(page.locator("#ty_heading_font")).not_to_have_css("font-family", re.compile(r"CVT"))
