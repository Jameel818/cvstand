"""The public brand reaches every page, in both interface languages.

WHY THIS FILE EXISTS
    Before it, brand coverage in the suite was zero: `grep -rn "Craft" tests/`
    returned nothing and no test asserted on any `<title>`. That is how the
    app shipped sign-up and sign-in branded "Résumé Builder" -- a generic
    string -- next to the real wordmark, and in Arabic rendered a translated
    title beside a Latin logo.

    It also disarms the trap this project has now hit twice. The wordmark is
    split across tags so the two halves can be styled differently:

        CV<b>Stand</b>

    so `grep -i cvstand` DOES NOT FIND IT, exactly as `grep -i resumecraft`
    did not find `Résumé<b>Craft</b>`. On 2026-09-12 that produced a
    confidently wrong answer ("the brand slot is empty" -- it was on every
    page). The defence is not remembering the trap. It is this file plus the
    `app/brand.py` constant: the rename is greppable in Python, and the
    rendered HTML is asserted here.

WHAT IS DELIBERATELY NOT ASSERTED
    The builder has no wordmark, and that is correct: `builder.html:4-5`
    empties both the `chrome` and `footer` blocks because the builder is a
    focused workspace with its own toolbar. It carries the brand in its
    `<title>` only, and that IS asserted.
"""
from __future__ import annotations

import re

import pytest

from app import brand, create_app

# The two pages that render the full shell (header + footer). The builder is
# excluded by design -- see the module docstring.
CHROME_PAGES = ["/", "/templates", "/account/sign-in", "/account/sign-up"]
# Every page, including the chrome-less builder, must be branded in its title.
ALL_PAGES = CHROME_PAGES + ["/builder"]

# The wordmark AS RENDERED. Written out literally rather than composed from
# the constants, so that a change to brand.py which breaks the markup fails
# here instead of silently agreeing with itself.
WORDMARK = re.compile(r"CV<b>Stand</b>")
TITLE = re.compile(r"<title>(.*?)</title>", re.S)


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _page(client, path: str, lang: str) -> str:
    client.set_cookie("ui_lang", lang)
    res = client.get(path)
    assert res.status_code == 200, f"{path} ({lang}) returned {res.status_code}"
    return res.get_data(as_text=True)


def test_the_constants_agree_with_each_other():
    """`HEAD + TAIL` is what the split wordmark renders; if they drift, the
    logo and the `<title>` show two different names on the same page."""
    assert brand.HEAD + brand.TAIL == brand.NAME


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("path", CHROME_PAGES)
def test_the_wordmark_is_in_the_header_and_the_footer(client, path, lang):
    html = _page(client, path, lang)
    assert len(WORDMARK.findall(html)) == 2, (
        f"{path} ({lang}) should carry the wordmark twice -- header and footer"
    )


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("path", ALL_PAGES)
def test_every_title_carries_the_brand(client, path, lang):
    title = TITLE.search(_page(client, path, lang))
    assert title, f"{path} ({lang}) has no <title> at all"
    assert brand.NAME in title.group(1), (
        f"{path} ({lang}) title is {title.group(1).strip()!r}, which does not "
        f"name the product"
    )


@pytest.mark.parametrize("path", ALL_PAGES)
def test_the_brand_is_byte_identical_in_arabic(client, path):
    """A brand does not change script when the interface does. This is the
    assertion that lets `labels.py` keep the brand out of the catalogue: if
    anyone ever adds an "Arabic translation" of the name, this fails."""
    en, ar = _page(client, path, "en"), _page(client, path, "ar")
    assert WORDMARK.findall(en) == WORDMARK.findall(ar), path
    assert brand.NAME in TITLE.search(ar).group(1), path


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_old_brand_is_gone_everywhere(client, lang):
    """The rename is only finished when the previous name renders nowhere."""
    for path in ALL_PAGES:
        html = _page(client, path, lang)
        assert "Craft" not in html, f"{path} ({lang}) still renders the old brand"


def test_the_manifest_names_the_product_untranslated(client):
    """`routes.py` used to wrap these in `ui_t()`, which was always a no-op for
    an untranslated brand. The installed app must be one name, not two."""
    for lang in ("en", "ar"):
        client.set_cookie("ui_lang", lang)
        m = client.get("/manifest.webmanifest").get_json()
        assert m["name"] == brand.NAME, lang
        assert m["short_name"] == brand.NAME, lang


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_there_is_a_way_to_contact_us(client, lang):
    """`account.html` told locked-out people to "get in touch" while the app
    contained no address of any kind -- there was no `mailto:` anywhere under
    `app/`. Password reset still does not exist, so this sentence is the only
    route out of a locked account and the address has to be real."""
    assert brand.SUPPORT_EMAIL.endswith("@" + brand.DOMAIN)
    footer = _page(client, "/", lang)
    assert f"mailto:{brand.SUPPORT_EMAIL}" in footer, "no contact link in the footer"
    locked_out = _page(client, "/account/sign-in", lang)
    assert f"mailto:{brand.SUPPORT_EMAIL}" in locked_out, (
        "the sign-in page tells people to get in touch but offers no address"
    )


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_tagline_renders_and_is_translated(client, lang):
    """The tagline is passed to `t()` as a VARIABLE (`t(brand_tagline)`), so
    `tests/test_labels.py` cannot see it: its scan is anchored on a quoted
    literal inside the call. Without this test the Arabic row could be deleted
    and every label gate would still pass while Arabic readers got English.
    """
    from app.labels import ui_t

    html = _page(client, "/", lang)
    rendered = ui_t(brand.TAGLINE, lang)
    assert str(rendered) in html, f"the tagline is missing from the footer ({lang})"
    if lang == "ar":
        assert str(rendered) != brand.TAGLINE, "the tagline has no Arabic"
        assert "CV" not in str(rendered), "the Arabic tagline is still English"


def test_the_tagline_still_does_its_job():
    """It exists to resolve one specific ambiguity: "Stand" reads as a booth
    (جناح) as readily as "stand out". A tagline that drops the disambiguating
    verb is prettier and useless -- see app/brand.py.
    """
    from app.labels import ui_t

    assert "stand out" in brand.TAGLINE.lower(), brand.TAGLINE
    # The Arabic carries the sense rather than the words: تلفت الأنظار is
    # "catches the eye", which has no booth reading available.
    assert "تلفت الأنظار" in str(ui_t(brand.TAGLINE, "ar"))


def test_no_code_still_reads_the_old_env_namespace():
    """Phase A (2026-09-14) renamed `RESUMECRAFT_*` to `CVSTAND_*`.

    An env var that nothing reads fails SILENTLY -- you set it in the hosting
    dashboard, the app ignores it and quietly uses the default. For
    `CVSTAND_SERVER_STORE` that default is 1, which is the single setting that
    must not be wrong on a public URL: two visitors would read and overwrite
    each other's résumé. So a stray `RESUMECRAFT_` left in the code is not a
    cosmetic miss, it is a config setting that looks applied and is not.

    Prose ABOUT the old name is fine and deliberate -- `app/brand.py` explains
    why the rename happened, and `sw.js` must keep sweeping the old cache
    prefix. Only a live `os.environ` read is a defect.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    here = Path(__file__).resolve()
    offenders = []
    for f in [*root.joinpath("app").rglob("*.py"), *root.joinpath("tests").rglob("*.py")]:
        # This file necessarily CONTAINS the old prefix as a literal -- it is
        # the thing being searched for. Without this line the guard reports
        # itself, which is the same self-reference that made the dead-row
        # scan in test_labels.py pass vacuously by including labels.py.
        if "__pycache__" in str(f) or f.resolve() == here:
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.startswith("RESUMECRAFT_"):
                    offenders.append(f"{f.relative_to(root)}:{node.lineno}: {node.value}")
    assert not offenders, (
        "string literals still naming the old env namespace - these would be "
        f"set in the dashboard and silently ignored: {offenders}"
    )


def test_the_js_keys_use_the_current_namespace():
    """The browser owns the résumé, so these key names ARE the storage."""
    from pathlib import Path

    js = (Path(__file__).resolve().parent.parent
          / "app" / "static" / "js" / "builder.js").read_text(encoding="utf-8")
    assert '"cvstand:resume"' in js and '"cvstand:template"' in js
    assert "resumecraft:" not in js, "the old localStorage keys are still live"


def test_the_service_worker_still_sweeps_the_old_cache_prefix():
    """A cleanup filter only deletes keys it recognises. Renaming the prefix
    without keeping the old one strands every cache a browser already stored
    under the previous name -- permanently, since nothing will ever match it.
    """
    from pathlib import Path

    sw = (Path(__file__).resolve().parent.parent
          / "app" / "static" / "js" / "sw.js").read_text(encoding="utf-8")
    assert 'startsWith("cvstand-")' in sw
    assert 'startsWith("resumecraft-")' in sw, (
        "dropping the old prefix strands previously-cached shells forever"
    )
