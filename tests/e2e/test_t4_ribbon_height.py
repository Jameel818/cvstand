"""modern-t4 "Ribbon Sidebar": every Arabic ribbon is as tall as the English
ones (user, 2026-10-08) - measured on the rendered page the PDF prints.

Before: English 41px, Arabic 49px (the Arabic label's own line). The
template is served from the app (/preview) so its fonts load as in the PDF.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

CLAY = "rgb(196, 86, 47)"
JS = f"""() => [...document.querySelectorAll('.tpl div')]
  .filter(d => getComputedStyle(d).backgroundColor === '{CLAY}' && d.offsetWidth >= 300)
  .map(d => d.getBoundingClientRect().height)"""


def _heights(page, server, lang):
    page.context.add_cookies([{"name": "ui_lang", "value": lang, "url": server.url}])
    page.goto(server.url + "/preview?template_key=modern-t4&showcase=1")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => document.fonts.ready")
    return page.evaluate(JS)


def test_arabic_ribbons_match_the_english_height(page, deployed_server):
    en = _heights(page, deployed_server, "en")
    ar = _heights(page, deployed_server, "ar")
    assert len(en) == 4 and len(ar) == 4, (en, ar)
    assert max(en) - min(en) < 0.5, en
    for h in ar:
        assert abs(h - en[0]) <= 1.0, f"Arabic ribbon {h:.1f}px, English {en[0]:.1f}px"
