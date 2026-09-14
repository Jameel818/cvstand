"""Two visitors must not be able to export each other's résumé.

`data/resume.json` is ONE file. That is right for the tool this started as and
it is the one thing that cannot survive a public URL — not an authz gap that
accounts would close, just one file where there needs to be one per person.
`GET /export/docx` reading it is fine on your laptop and is a data leak the
moment two people can reach the same server.

So the export routes learned POST: the client sends the document, the server
renders it and keeps nothing. `app/config.py::SERVER_STORE` switches the old
GET behaviour off for a deployment that more than one person can reach.

`test_two_visitors_get_their_own_document` is the point of the file. Everything
else here supports it: a route that reads the body but ALSO falls back to the
stored file would pass a naive "does POST work" test while still leaking.
"""
from __future__ import annotations

import copy
import io

import pytest

from app import create_app
from app.config import RESUME_PATH
from tests import samples

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.fixture()
def no_server_store(monkeypatch):
    """Simulate a multi-visitor deployment.

    `routes` binds SERVER_STORE at import, so the flag is patched where it is
    USED, not where it is defined — patching `app.config` alone would leave the
    already-imported name pointing at the old value and the test would pass
    while proving nothing.
    """
    monkeypatch.setattr("app.routes.SERVER_STORE", False)


def _named(sample: dict, name: str) -> dict:
    r = copy.deepcopy(sample)
    r["name"] = name
    return r


def _text(blob: bytes) -> str:
    from docx import Document

    return "\n".join(p.text for p in Document(io.BytesIO(blob)).paragraphs)


# ---------------------------------------------------------------- the claim

def test_two_visitors_get_their_own_document(client):
    """The whole reason this module exists.

    Two POSTs, no save in between, no shared state touched. If the route ever
    reads `load_resume()` again — as a fallback, as a merge, as a default for a
    missing field — one of these two people gets the other's name on their CV.
    """
    a = client.post("/export/docx", json={
        "data": _named(samples.ENGLISH, "Visitor Alpha"), "template_key": "ats-t1"})
    b = client.post("/export/docx", json={
        "data": _named(samples.ENGLISH, "Visitor Beta"), "template_key": "ats-t1"})

    assert a.status_code == b.status_code == 200
    text_a, text_b = _text(a.data), _text(b.data)
    assert "Visitor Alpha" in text_a
    assert "Visitor Beta" in text_b
    assert "Visitor Beta" not in text_a, "one visitor's export leaked another's data"
    assert "Visitor Alpha" not in text_b, "one visitor's export leaked another's data"


def test_posting_does_not_write_the_shared_file(client):
    """Export is a read. A POST that persisted would reintroduce the collision
    it was built to remove — and would do it invisibly, since the response
    would still look correct to the person who sent it."""
    before = RESUME_PATH.read_bytes() if RESUME_PATH.exists() else None
    client.post("/export/docx", json={
        "data": _named(samples.ENGLISH, "Passing Through"), "template_key": "ats-t1"})
    after = RESUME_PATH.read_bytes() if RESUME_PATH.exists() else None
    assert after == before, "an export mutated the stored résumé"


@pytest.mark.parametrize("lang,sample", samples.BOTH)
def test_posted_export_works_in_both_languages(client, lang, sample):
    """An Arabic résumé takes a different Word master, and a missing one raises
    rather than falling back (phase 7). The body path must reach that too."""
    res = client.post("/export/docx", json={"data": sample, "template_key": "ats-t1"})
    assert res.status_code == 200
    assert res.mimetype == DOCX_MIME
    assert res.data[:2] == b"PK"


# ---------------------------------------------------------------- bad bodies

@pytest.mark.parametrize("route", ["/export/docx", "/export/pdf"])
def test_a_body_that_is_not_a_resume_is_refused(client, route):
    """422 with the schema's own errors, not a 500 from deep inside a renderer.

    Checked on the PDF route too, and it is the cheap half of that route: a
    rejected body must never reach `render_pdf`, which would launch a whole
    Chromium to fail.
    """
    res = client.post(route, json={"data": {"nope": True}})
    assert res.status_code == 422
    assert res.get_json()["ok"] is False
    assert res.get_json()["errors"]


@pytest.mark.parametrize("route", ["/export/docx", "/export/pdf"])
@pytest.mark.parametrize("body", [{}, {"data": None}, {"data": "a string"}, {"data": []}])
def test_a_missing_or_wrong_typed_body_is_refused(client, route, body):
    assert client.post(route, json=body).status_code == 422


# ---------------------------------------------------------------- the switch

def test_server_store_off_refuses_the_shared_file_routes(client, no_server_store):
    """The routes that read or write the ONE file must be unreachable.

    Turning the builder's calls off in JavaScript is not the same as turning
    the route off: the route is the thing on the internet.
    """
    # 403 for the two writes: the route exists, this deployment does not do
    # that. 405 + `Allow: POST` for the export, where there IS a right method.
    assert client.put("/api/resume", json=samples.ENGLISH).status_code == 403
    assert client.post("/api/template", json={"template_key": "ats-t1"}).status_code == 403

    res = client.get("/export/docx?template_key=ats-t1")
    assert res.status_code == 405
    assert res.headers["Allow"] == "POST", (
        "Allow must name the method that works. `abort(405, text)` puts the "
        "TEXT here one character at a time — see routes._store_disabled."
    )
    assert res.is_json


def test_server_store_off_still_exports_what_you_send(client, no_server_store):
    """Switching the store off must not switch the product off."""
    res = client.post("/export/docx", json={
        "data": _named(samples.ENGLISH, "Deployed User"), "template_key": "ats-t1"})
    assert res.status_code == 200
    assert "Deployed User" in _text(res.data)


def test_server_store_on_keeps_the_local_workflow(client):
    """The default is unchanged: `curl localhost/export/docx` still works, and
    so does the browser suite, which is built on the stored résumé.

    Snapshots and restores the file, per `test_smoke.py::stored_resume`: the
    whole session shares one data dir, so a test that writes the store and
    walks away changes what every later test reads — which shows up as a
    failure somewhere else, dependent on collection order.
    """
    before = RESUME_PATH.read_bytes() if RESUME_PATH.exists() else None
    try:
        assert client.put("/api/resume", json=samples.ENGLISH).status_code == 200
        assert client.get("/export/docx?template_key=ats-t1").status_code == 200
    finally:
        if before is None:
            RESUME_PATH.unlink(missing_ok=True)
        else:
            RESUME_PATH.write_bytes(before)
