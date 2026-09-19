"""The Arabic font policy applies to the shell, and ONLY in Arabic.

WHAT THIS PROTECTS

    Two halves, and the second is the one that matters.

    In ARABIC the shell must actually use the policy's faces (FONTS.md): body
    in IBM Plex Sans Arabic, headings in Cairo, hero and CTA in Tajawal. Before
    this, `base.html` linked `fonts.css` (Latin) and nothing else, so an Arabic
    interface fell back to whatever the OS supplied — Segoe UI on Windows,
    Geeza Pro on macOS, anything at all on Android. The faces were vendored;
    the interface never asked for them.

    In ENGLISH nothing may move. The request was explicitly "apply it when
    Arabic is selected, not English", and the whole change is one `[dir="rtl"]`
    block plus a conditional `<link>`. That is easy to state and easy to get
    wrong — a stray media query, a class applied on both, a `:root` value
    edited instead of added. So English is asserted against the computed style
    the browser actually resolves, not against the CSS source.

WHY COMPUTED STYLE AND NOT THE STYLESHEET

    Reading app.css tells you what was written. `getComputedStyle` tells you
    what the cascade produced, which is the only thing a reader sees. This
    project has been caught twice believing a stylesheet over a rendered page.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e]

#: What English resolved to before this change. Any drift here is a regression
#: in the half of the app that was supposed to be untouched.
ENGLISH_BODY_FONT = "Inter"

PAGES = ["/", "/templates", "/builder"]


def _fonts(page, base, lang, path):
    page.context.clear_cookies()
    page.context.add_cookies([{"name": "ui_lang", "value": lang,
                               "domain": "127.0.0.1", "path": "/"}])
    page.goto(f"{base.url}{path}", wait_until="networkidle")
    page.wait_for_timeout(400)
    return page.evaluate("""() => {
      const f = el => el ? getComputedStyle(el).fontFamily : null;
      // The HERO and a section HEADING are different roles in the policy —
      // hero is Tajawal (standing in for Thmanyah), headings are Cairo. A
      // plain `querySelector('h1,h2,h3')` finds the hero h1 on the landing
      // page and then reports the hero's font as the heading's.
      const hero = document.querySelector('.hero h1');
      const heading = [...document.querySelectorAll('h1, h2, h3')]
        .find(el => !el.closest('.hero'));
      const btn = document.querySelector('.btn, button');
      return {
        dir: document.documentElement.getAttribute('dir'),
        body: f(document.body),
        leading: getComputedStyle(document.body).lineHeight,
        hero: f(hero),
        heading: f(heading),
        cta: f(btn),
      };
    }""")


@pytest.mark.parametrize("path", PAGES)
def test_english_typography_is_untouched(page, live_server, path):
    got = _fonts(page, live_server, "en", path)
    assert got["dir"] in (None, "ltr"), got["dir"]
    assert got["body"].startswith(ENGLISH_BODY_FONT), (
        f"English body font moved to {got['body']!r} — the Arabic policy was "
        "supposed to apply only under [dir=rtl]")
    for role in ("hero", "heading", "cta"):
        if got[role]:
            assert "Cairo" not in got[role] and "Tajawal" not in got[role], (
                f"an Arabic face leaked into the English {role}: {got[role]!r}")


@pytest.mark.parametrize("path", PAGES)
def test_arabic_uses_the_policy_faces(page, live_server, path):
    got = _fonts(page, live_server, "ar", path)
    assert got["dir"] == "rtl"
    assert "IBM Plex Sans Arabic" in got["body"], (
        f"Arabic body should lead with IBM Plex Sans Arabic, got {got['body']!r}")
    if got["hero"]:
        # Thmanyah Serif Display per the policy, Tajawal ExtraBold by its own
        # stated fallback — the licence forbids shipping Thmanyah. FONTS.md.
        assert "Tajawal" in got["hero"], (
            f"the Arabic hero should lead with Tajawal, got {got['hero']!r}")
    if got["heading"]:
        assert "Cairo" in got["heading"], (
            f"Arabic headings should lead with Cairo, got {got['heading']!r}")
    if got["cta"]:
        assert "Tajawal" in got["cta"], (
            f"Arabic buttons should lead with Tajawal, got {got['cta']!r}")


def test_the_arabic_stylesheet_is_not_sent_to_english_readers(page, live_server):
    """An English visitor must not pay for a render-blocking stylesheet whose
    every rule is unreachable. `unicode-range` already stops the .woff2 files
    downloading; the stylesheet itself is a separate cost."""
    page.context.clear_cookies()
    page.context.add_cookies([{"name": "ui_lang", "value": "en",
                               "domain": "127.0.0.1", "path": "/"}])
    page.goto(f"{live_server.url}/", wait_until="networkidle")
    links = page.evaluate(
        "() => [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href)")
    assert not any("fonts_ar_shell" in h for h in links), links

    page.context.clear_cookies()
    page.context.add_cookies([{"name": "ui_lang", "value": "ar",
                               "domain": "127.0.0.1", "path": "/"}])
    page.goto(f"{live_server.url}/", wait_until="networkidle")
    links = page.evaluate(
        "() => [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href)")
    assert any("fonts_ar_shell" in h for h in links), (
        f"the Arabic page did not link fonts_ar_shell.css: {links}")


def test_the_resume_templates_are_not_affected(page, live_server):
    """Scope boundary. The policy's roles are INTERFACE roles; the 49 templates
    are locked designs with their own pixel and HTML gates, and their Arabic
    already resolves through the unicode-range aliases in fonts_ar.css. A
    preview is a separate document in an iframe, so `[dir=rtl]` on the shell
    cannot reach it — this asserts that rather than assuming it."""
    page.context.clear_cookies()
    page.context.add_cookies([{"name": "ui_lang", "value": "ar",
                               "domain": "127.0.0.1", "path": "/"}])
    page.goto(f"{live_server.url}/preview?template_key=modern-t2&showcase=1",
              wait_until="networkidle")
    page.wait_for_timeout(600)
    fam = page.evaluate(
        "() => getComputedStyle(document.querySelector('.tpl')).fontFamily")
    assert "Archivo" in fam, (
        f"modern-t2 should still declare Archivo (Arabic arrives via the "
        f"unicode-range alias), got {fam!r}")
