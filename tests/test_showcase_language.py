"""The showcase previews follow the READER, the builder follows the DOCUMENT.

WHAT THIS PROTECTS

    `/preview` serves four surfaces, and they do not all want the same résumé:

        landing hero cards   demonstrate a layout  -> the SHOWCASE sample, in
        gallery résumé cards                          the interface language
        ------------------------------------------------------------------
        builder live preview you editing YOUR CV   -> `load_resume()`
        template drawer minis picking a layout for
                              your own content

    Before 2026-09-08 all four rendered `load_resume()`, so an Arabic visitor
    browsing the landing page saw English résumés in every card — the app
    advertising a product it does not sell. `showcase=1` splits the two jobs.

    The temptation, and the thing these tests exist to forbid, is to make the
    showcase read `resume["lang"]` instead of the interface language. That
    would look correct in every case where the two agree, and it would couple
    the two languages that `app/i18n.py` exists to keep apart. The sharp case
    is an ARABIC document read through an ENGLISH interface: the cards must be
    English.

WHY THE TEMPLATE GUARDS ARE HERE TOO

    The route can be perfectly correct while nothing asks it for a showcase,
    or while the BUILDER starts asking for one. Neither raises; the first
    silently reverts this feature and the second silently shows a stranger's
    CV to someone editing their own. Both are one careless `url_for` away, so
    they are asserted against the template source in the fast loop.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import create_app
from app.i18n import COOKIE
from app.store import load_showcase

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app" / "templates"

#: Templates that MUST ask for the showcase.
SHOWCASE_PAGES = ["landing.html", "gallery.html"]

#: Files that must NEVER mention it. `builder.js` is in the list and
#: `builder.html` alone is NOT enough: the builder does not write its preview
#: URLs in Jinja. It ships a bare `previewBase` and the JS appends the query
#: string, so the drawer minis are built in
#: `builder.js` as `${EP.previewBase}?template_key=...`. A guard that scanned
#: only the .html passed a mutation that added `showcase` to that line — it was
#: checking a file that could not fail.
OWN_RESUME_FILES = [
    TPL / "builder.html",
    ROOT / "app" / "static" / "js" / "builder.js",
]

_PREVIEW_CALL = re.compile(r"url_for\(\s*['\"]main\.preview['\"][^)]*\)")


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ------------------------------------------------------------ the loader

def test_the_showcase_sample_matches_the_language_asked_for():
    assert load_showcase("en")["name"] == "Wren Ashworth"
    assert load_showcase("ar")["lang"] == "ar"
    assert load_showcase("ar")["name"] != load_showcase("en")["name"]


@pytest.mark.parametrize("bogus", ["fr", "", "EN", None, "../../etc/passwd"])
def test_an_unknown_language_degrades_to_english(bogus):
    """A presentational choice driven by a user-editable cookie must not 500
    the landing page, and must not be able to name a file."""
    assert load_showcase(bogus) == load_showcase("en")


def test_the_caller_cannot_poison_the_cache():
    """The loader caches the sample's TEXT and re-parses, so two callers never
    share a dict. A mutation here would otherwise reach the next 48 cards on
    the same gallery load."""
    first = load_showcase("ar")
    first["name"] = "MUTATED"
    first["skills"].clear()
    second = load_showcase("ar")
    assert second["name"] != "MUTATED"
    assert second["skills"]


# ------------------------------------------------------------- the route

@pytest.mark.parametrize("lang,expect_dir", [("en", "ltr"), ("ar", "rtl")])
def test_the_showcase_follows_the_interface_language(client, lang, expect_dir):
    client.set_cookie(COOKIE, lang)
    body = client.get("/preview?template_key=ats-t1&showcase=1").get_data(as_text=True)
    assert f'dir="{expect_dir}"' in body
    assert load_showcase(lang)["title"] in body


def test_without_the_flag_the_route_still_renders_the_stored_resume(client):
    """The builder's half of the contract. `data/resume.json` is English here
    (the session's temp data dir seeds from the English sample), so an Arabic
    interface must NOT change what the builder previews."""
    client.set_cookie(COOKIE, "ar")
    body = client.get("/preview?template_key=ats-t1").get_data(as_text=True)
    assert 'dir="ltr"' in body
    assert "Ashworth" in body


def test_an_arabic_document_read_in_english_still_shows_an_english_showcase(client):
    """THE case that fails if the showcase ever reads `resume["lang"]`.

    Asserted through the route rather than the loader, because the coupling
    would be introduced in the route — one `load_resume().get("lang")` where
    `current_lang()` belongs."""
    from app.store import save_resume

    stored = client.get("/api/resume").get_json()["resume"]
    try:
        save_resume(dict(stored, lang="ar"))
        client.set_cookie(COOKIE, "en")
        body = client.get("/preview?template_key=ats-t1&showcase=1").get_data(as_text=True)
        assert 'dir="ltr"' in body
        assert load_showcase("en")["title"] in body
    finally:
        save_resume(stored)


def test_the_showcase_never_writes_anything(client):
    """It is a read of a repo file. A showcase render must not seed, touch or
    reorder the user's résumé — `load_resume()` DOES write on first read
    (it seeds from the sample), which is exactly the sort of thing that could
    creep in here."""
    before = client.get("/api/resume").get_json()["resume"]
    client.set_cookie(COOKIE, "ar")
    for key in ("ats-t1", "modern-t1", "modern-t11"):
        assert client.get(f"/preview?template_key={key}&showcase=1").status_code == 200
    assert client.get("/api/resume").get_json()["resume"] == before


# --------------------------------------------------- who asks for what

@pytest.mark.parametrize("name", SHOWCASE_PAGES)
def test_the_showcase_pages_ask_for_it(name):
    """Otherwise the route is right and the feature is off."""
    src = (TPL / name).read_text(encoding="utf-8")
    calls = _PREVIEW_CALL.findall(src)
    assert calls, f"{name} no longer renders a preview at all"
    for call in calls:
        assert "showcase" in call, (
            f"{name} renders a preview WITHOUT showcase=1, so it will show the "
            f"user's own résumé instead of the sample: {call}")


@pytest.mark.parametrize("path", OWN_RESUME_FILES, ids=lambda p: p.name)
def test_the_builder_never_asks_for_it(path):
    """The inverse, and the more damaging direction: a builder that previewed
    stock content would show someone a résumé that is not theirs while they
    typed into the form beside it.

    Asserted as a plain absence of the word across the whole file rather than
    against `url_for` calls, because the builder assembles these URLs in
    JavaScript where no `url_for` appears."""
    src = path.read_text(encoding="utf-8")
    assert "showcase" not in src, (
        f"{path.name} mentions `showcase`; every builder surface — the live "
        f"preview and the drawer minis — must render the user's own résumé")
