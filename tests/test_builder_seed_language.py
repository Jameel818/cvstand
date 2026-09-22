"""An Arabic visitor must open the builder onto an ARABIC document.

The seed is the one place where the interface language may decide what the
document says: a résumé that does not exist yet has no language of its own to
respect. Everything past that moment follows the DOCUMENT (app/i18n.py), and
`tests/test_showcase_language.py` guards that half.

WHAT WENT WRONG, AND WHY NOTHING CAUGHT IT

`load_resume()` seeded from the right sample and then WROTE it to
`data/resume.json`. That file is one file for the whole server. With
`CVSTAND_SERVER_STORE=0` nothing ever rewrites it, so whichever language the
FIRST request to reach the container happened to carry became everyone's: an
Arabic reader got the English builder, and switching the header changed
nothing, because by then the file existed and the seed was never consulted
again.

It is invisible in the two places you would look. Locally you are the first
visitor and the language is yours. And a single-request test passes either
way — the bug needs TWO visitors in one process, which is what
`test_the_first_visitor_does_not_fix_everyone_elses_language` is.

EVERY TEST HERE OWNS ITS OWN `RESUME_PATH`. The suite shares one temp data dir
for the whole session (tests/conftest.py), so seeding an Arabic file into it
would reach into another module and fail it on test ORDER.
"""
from __future__ import annotations

import json
import re

import pytest

from app import create_app
from app.i18n import COOKIE
from app.store import seed_resume

_SEED = re.compile(r'<script id="resume-data" type="application/json">(.*?)</script>', re.S)


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture()
def own_resume_file(tmp_path, monkeypatch):
    """A `RESUME_PATH` this test alone can create, patched where it is USED.

    `app.store` reads the module global inside the function, so patching it
    here is enough; patching `app.config` alone would leave the already-bound
    name pointing at the session's shared file — the test would pass and prove
    nothing. Same trap `tests/test_stateless.py::no_server_store` documents.
    """
    path = tmp_path / "resume.json"
    monkeypatch.setattr("app.store.RESUME_PATH", path)
    return path


@pytest.fixture()
def deployment(monkeypatch, own_resume_file):
    """A multi-visitor deployment: the browser owns the résumé, not the server."""
    monkeypatch.setattr("app.store.SERVER_STORE", False)
    return own_resume_file


def seed_of(client, lang):
    client.set_cookie(COOKIE, lang)
    body = client.get("/builder").get_data(as_text=True)
    return json.loads(_SEED.search(body).group(1))


# ------------------------------------------------------- the reported bug

@pytest.mark.parametrize("lang,expect", [("en", None), ("ar", "ar")])
def test_a_new_visitor_starts_in_their_interface_language(deployment, client, lang, expect):
    """English carries no `lang` key at all — absent means English, and
    stamping one on would be a change to the sample, not to the behaviour."""
    assert seed_of(client, lang).get("lang") == expect


def test_the_first_visitor_does_not_fix_everyone_elses_language(deployment, client):
    """THE regression. Two visitors, one process, no write in between.

    This is the whole file: with the seed persisted, the second assertion got
    the first visitor's sample and an Arabic reader read English.
    """
    english = seed_of(client, "en")
    arabic = seed_of(client, "ar")

    assert english.get("lang") is None
    assert arabic["lang"] == "ar"
    assert arabic["name"] != english["name"]

    # …and back again, because a seed that merely alternates would also pass
    # the two assertions above.
    assert seed_of(client, "en")["name"] == english["name"]


def test_the_arabic_seed_renders_as_an_arabic_document(deployment, client):
    """The seed is only half of it — the page the visitor actually looks at is
    the preview, which must come back RTL with Arabic text in it."""
    client.set_cookie(COOKIE, "ar")
    body = client.get("/preview?template_key=ats-t1").get_data(as_text=True)

    assert 'dir="rtl"' in body
    assert seed_resume("ar")["name"] in body


def test_a_deployment_render_writes_nothing(deployment, client):
    """No file, and therefore no shared state to go stale — the same claim
    `tests/test_stateless.py` makes for the export routes, for the three GETs
    that can still reach `load_resume()`.

    It also means the app no longer needs a writable data dir to render a
    page.
    """
    client.set_cookie(COOKIE, "ar")
    client.get("/builder")
    client.get("/api/resume")
    client.get("/preview?template_key=ats-t1")

    assert not deployment.exists()


def test_a_leftover_file_on_the_volume_is_ignored(deployment, client):
    """`/data` is a PERSISTENT volume (DEPLOY.md §C3, for the accounts DB), so
    the file the old seed wrote outlives every deploy.

    Two things ride on ignoring it. The fix has to arrive by itself — a build
    that stopped writing but still read would ship green and change nothing on
    the live site, needing a manual deletion on the volume that nothing would
    remind anyone to do. And whatever is in that file came from SOME earlier
    visitor's request; serving it to everyone who arrives later is the leak
    `tests/test_stateless.py` exists to make unreachable.
    """
    deployment.write_text(
        json.dumps({"name": "Leftover Visitor", "lang": "en"}), encoding="utf-8")

    assert seed_of(client, "ar")["name"] != "Leftover Visitor"
    assert seed_of(client, "ar")["lang"] == "ar"


@pytest.mark.parametrize("bogus", ["fr", "", "EN", "../../etc/passwd"])
def test_an_unknown_language_seeds_english(deployment, client, bogus):
    """The cookie is user-editable, so it must not 500 the builder and must
    not be able to name a file. Same degrade rule as `load_showcase`."""
    assert seed_of(client, bogus).get("lang") is None


# ------------------------------------------- what must NOT have changed

def test_the_local_workflow_still_keeps_the_resume_on_disk(own_resume_file, client):
    """`SERVER_STORE=1` is your own machine, where `data/resume.json` IS the
    store and the builder's autosave mirrors into it. The seed must still land
    there on first run, or a local user's résumé would not survive a restart.
    """
    assert not own_resume_file.exists()
    seed_of(client, "ar")
    assert json.loads(own_resume_file.read_text(encoding="utf-8"))["lang"] == "ar"


def test_a_document_that_exists_ignores_the_interface(own_resume_file, client):
    """The other half of the contract, at the seed level: once a document
    exists, its language is its own and no cookie may overwrite it. An Arabic
    reader editing an English résumé is an ordinary case.
    """
    seed_of(client, "en")                      # writes the English sample
    assert seed_of(client, "ar").get("lang") is None


# ------------------------------------------- every template, not a sample

def test_every_live_template_opens_in_the_selected_language(deployment, client):
    """"The whole opened templates", asserted over the whole catalogue.

    `tests/e2e/test_selected_language_everywhere.py` walks the real journey in
    a browser but can only afford to look at a handful of gallery cards. The
    claim is about all 49, and at request level it costs a second: a template
    that hard-codes an English heading, or renders `dir` from something other
    than the document, fails here and nowhere else.
    """
    from app import registry

    client.set_cookie(COOKIE, "ar")
    arabic_name = seed_resume("ar")["name"]

    for key in registry.ported_keys():
        body = client.get(f"/preview?template_key={key}").get_data(as_text=True)
        assert 'dir="rtl"' in body, key
        assert arabic_name.split()[0] in body, key
