"""Import my CV (2026-10-18), server side: reading untrusted uploads, the AI
step with a MOCKED client (no network, no cost), the word-for-word guard,
the daily limit, the monthly budget, and "Coming soon" without a key.

The files are real: CVStand's own PDF and Word exports of the demo CVs, in
English and Arabic, plus a .txt and pasted text. The fake client answers with
what a perfect reader would copy out of them - plus, where a test says so,
something invented, which must not survive.
"""
from __future__ import annotations

import copy
import io
import json
import zipfile
from types import SimpleNamespace

import pytest

from app import ai_quota, create_app, importer
from app.exporters.docx import render_docx
from tests import letter_samples as LS

CONTENT = ("name", "title", "summary", "contact", "experience", "education", "skills", "tools",
           "languages", "recognition", "references")


# ---- the fake model ---------------------------------------------------------------

class FakeClient:
    def __init__(self, payload=None, *, stop="end_turn", raise_exc=None, text=None):
        self.payload, self.stop, self.raise_exc, self.text = payload, stop, raise_exc, text
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self.raise_exc:
            raise self.raise_exc
        body = self.text if self.text is not None else json.dumps(self.payload, ensure_ascii=False)
        return SimpleNamespace(stop_reason=self.stop,
                               content=[SimpleNamespace(type="text", text=body)],
                               usage=SimpleNamespace(input_tokens=3000, output_tokens=1500,
                                                     cache_read_input_tokens=0,
                                                     cache_creation_input_tokens=1200))


def perfect(lang: str) -> dict:
    """What a faithful reader copies out of the demo CV."""
    d = LS.resume(lang)
    out = {k: copy.deepcopy(d.get(k, [] if k not in ("name", "title", "summary", "contact") else ""))
           for k in CONTENT}
    out["contact"] = {k: d["contact"].get(k, "") for k in ("email", "phone", "address", "site")}
    out["contact"]["social"] = []
    out["skills"] = [{"name": s["name"], "level": s.get("level", "")} for s in d.get("skills", [])]
    for e in out["experience"]:
        e.setdefault("location", "")
        e.setdefault("bullets", [])
    for e in out["education"]:
        for k in ("start", "end", "gpa"):
            e.setdefault(k, "")
        e.setdefault("bullets", [])
    out["lang"] = lang
    return out


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture()
def ai(monkeypatch):
    """The server 'has a key' and the model is a fake. Nothing reads or sets
    an environment variable."""
    import app.routes as routes
    fake = FakeClient()
    monkeypatch.setattr(routes, "assist_configured", lambda: True)
    monkeypatch.setattr(importer, "client", lambda: fake)
    return fake


@pytest.fixture(scope="module")
def files():
    """Real CVStand exports of the demo CVs (PDF via Chromium, once)."""
    from concurrent.futures import ThreadPoolExecutor

    from app.exporters.pdf import render_pdf
    out = {}
    for lang in ("en", "ar"):
        d = LS.resume(lang)
        # In a worker thread: under --e2e the browser suite's event loop may
        # already run in this thread, and Playwright's sync API refuses to
        # start inside one.
        with ThreadPoolExecutor(1) as pool:
            out[(lang, "pdf")] = pool.submit(render_pdf, d, "modern-t13").result()
        out[(lang, "docx")] = render_docx(d, "ats-t1")
        out[(lang, "txt")] = importer.extract_text("cv.docx", out[(lang, "docx")]).encode("utf-8")
    return out


def _upload(client, name, blob):
    return client.post("/api/import", data={"file": (io.BytesIO(blob), name)},
                       content_type="multipart/form-data")


# ---- without a key ------------------------------------------------------------------

def test_without_a_key_the_route_answers_503_before_reading_anything(client, monkeypatch):
    called = []
    monkeypatch.setattr(importer, "extract_text", lambda *a: called.append(1))
    r = client.post("/api/import", json={"text": "x" * 100})
    assert r.status_code == 503 and r.get_json()["reason"] == "not_configured"
    assert not called


@pytest.mark.parametrize("lang,soon", [("en", "Coming soon"), ("ar", "قريباً")])
def test_without_a_key_the_button_is_disabled_and_says_coming_soon(client, lang, soon):
    client.get(f"/lang/{lang}")
    html = client.get("/builder").get_data(as_text=True)
    btn = html[html.index('id="import-btn"') - 60: html.index('id="import-btn"') + 600]
    assert "disabled" in btn and soon in btn


def test_with_a_key_the_button_is_enabled(client, ai):
    html = client.get("/builder").get_data(as_text=True)
    btn = html[html.index('id="import-btn"') - 60: html.index('id="import-btn"') + 400]
    assert "disabled" not in btn and "Coming soon" not in btn


# ---- reading every kind of input, EN + AR -------------------------------------------

@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("kind", ["pdf", "docx", "txt", "paste"])
def test_every_input_reaches_the_model_and_comes_back_reviewed(client, ai, files, lang, kind):
    ai.payload = perfect(lang)
    if kind == "paste":
        r = client.post("/api/import", json={"text": files[(lang, "txt")].decode("utf-8")})
    else:
        r = _upload(client, f"my cv.{kind}", files[(lang, kind)])
    j = r.get_json()
    assert r.status_code == 200, j
    assert j["ok"] and j["lang"] == lang
    d = LS.resume(lang)
    assert j["resume"]["name"] == d["name"]
    assert j["resume"]["experience"][0]["role"] == d["experience"][0]["role"]
    assert j["left_today"] == ai_quota.DAILY_LIMITS["import"] - 1
    # what went to the model: Haiku 5.5, structured output, the CV's text,
    # no sampling parameters (Haiku 5.5 refuses non-defaults), no thinking
    (call,) = ai.calls
    assert call["model"] == "claude-haiku-5-5"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert not {"temperature", "top_p", "top_k"} & set(call)
    assert call["thinking"] == {"type": "disabled"}
    sent = call["messages"][0]["content"][0]["text"]
    assert d["experience"][0]["company"].split()[0] in sent


def test_invented_values_never_reach_the_review(client, ai, files):
    p = perfect("en")
    p["name"] = "Jordan Example"                                  # not in the CV
    p["experience"].append({"role": "Chief Executive", "company": "Made Up Ltd", "location": "",
                            "start": "1999", "end": "2001", "bullets": []})
    p["experience"][0]["bullets"].append("Grew revenue by 900%")
    p["skills"].append({"name": "Quantum Basket Weaving", "level": "Expert"})
    p["contact"]["email"] = "someone.else@example.org"
    ai.payload = p
    j = _upload(client, "cv.docx", files[("en", "docx")]).get_json()
    R = j["resume"]
    assert R["name"] == "" and R["contact"]["email"] == ""
    assert all(e["role"] != "Chief Executive" for e in R["experience"])
    assert "Grew revenue by 900%" not in R["experience"][0]["bullets"]
    assert all(s["name"] != "Quantum Basket Weaving" for s in R["skills"])
    assert j["dropped"] >= 5


def test_levels_outside_cvstands_lists_are_cleared(client, ai, files):
    p = perfect("en")
    p["skills"][0]["level"] = "Godlike"
    ai.payload = p
    R = _upload(client, "cv.docx", files[("en", "docx")]).get_json()["resume"]
    assert R["skills"][0]["level"] == ""


def test_an_arabic_cv_comes_back_arabic_even_from_the_english_builder(client, ai, files):
    ai.payload = perfect("ar")
    j = _upload(client, "cv.docx", files[("ar", "docx")]).get_json()
    assert j["lang"] == "ar"          # the builder then asks to switch, it does not translate


def test_the_cv_text_is_never_logged(client, ai, files, caplog):
    ai.payload = perfect("en")
    with caplog.at_level("DEBUG"):
        _upload(client, "cv.docx", files[("en", "docx")])
    logs = "\n".join(r.getMessage() for r in caplog.records)
    for secret in ("Wren", "Ashworth", "Halden", "examplemail"):
        assert secret not in logs


def test_the_upload_is_kept_in_memory_never_spooled_to_disk(client, ai, files, monkeypatch):
    """werkzeug writes a multipart file over 500 KB to a temporary FILE unless
    told otherwise. The route swaps that for memory; prove the default
    factory is never used, with a file well over the threshold."""
    import werkzeug.wrappers.request as wreq

    def boom(*a, **k):
        raise AssertionError("the upload was spooled to a temporary file")
    monkeypatch.setattr(wreq, "default_stream_factory", boom)
    ai.payload = perfect("en")
    big = files[("en", "pdf")] + b"\n%" + b"x" * (900 * 1024)     # a PDF may carry trailing junk
    r = _upload(client, "cv.pdf", big)
    assert r.status_code == 200, r.get_json()


# ---- untrusted files are refused ---------------------------------------------------

def _docx_with(extra: dict[str, bytes], base: bytes) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(base))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in src.namelist():
            z.writestr(n, src.read(n))
        for n, b in extra.items():
            z.writestr(n, b)
    return buf.getvalue()


@pytest.mark.parametrize("name,make,status,reason", [
    ("cv.pdf", lambda f: b"Just some text pretending to be a PDF" * 3, 415, "type"),
    ("cv.exe", lambda f: b"MZ\x90\x00" + b"\x00" * 200, 415, "type"),
    ("cv.docx", lambda f: f[("en", "pdf")], 415, "type"),                 # renamed PDF
    ("cv.docm", lambda f: f[("en", "docx")], 415, "macro"),
    ("cv.docx", lambda f: _docx_with({"word/vbaProject.bin": b"\x00" * 64}, f[("en", "docx")]),
     415, "macro"),
    ("cv.docx", lambda f: _docx_with({"word/media/bomb.bin": b"\x00" * (41 * 1024 * 1024)},
                                      f[("en", "docx")]), 413, "size"),
    ("cv.docx", lambda f: b"PK\x03\x04 this is not really a zip", 422, "broken"),
    ("cv.pdf", lambda f: b"%PDF-1.7\n this is not really a pdf", 422, "broken"),
    ("cv.txt", lambda f: b"", 400, "empty"),
])
def test_untrusted_uploads_are_refused_before_the_model(client, ai, files, name, make, status,
                                                        reason):
    r = _upload(client, name, make(files))
    assert (r.status_code, r.get_json()["reason"]) == (status, reason)
    assert not ai.calls


def test_a_file_over_5_mb_is_refused(client, ai):
    r = _upload(client, "cv.txt", b"a" * (5 * 1024 * 1024 + 10))
    assert r.status_code == 413 and r.get_json()["reason"] == "size"
    assert not ai.calls


def test_a_scanned_pdf_says_it_has_no_readable_text(client, ai):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(612, 792)
    buf = io.BytesIO()
    w.write(buf)
    r = _upload(client, "scan.pdf", buf.getvalue())
    j = r.get_json()
    assert r.status_code == 422 and j["reason"] == "scanned"
    assert "no readable text" in j["error"]
    assert not ai.calls


def test_a_password_protected_pdf_is_refused(client, ai, files):
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for p in PdfReader(io.BytesIO(files[("en", "pdf")])).pages:
        w.add_page(p)
    w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    r = _upload(client, "cv.pdf", buf.getvalue())
    assert r.get_json()["reason"] == "encrypted"


def test_a_word_file_declaring_xml_entities_is_refused(client, ai, files):
    """Word never writes a DOCTYPE; one in document.xml is there to declare
    entities (billion laughs, external files) - refused before parsing."""
    evil = (b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x "EXPANDED-ENTITY">]>'
            b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            b'<w:body><w:p><w:r><w:t>&x; Wren Ashworth, creative lead with fourteen designers'
            b'</w:t></w:r></w:p></w:body></w:document>')
    src = zipfile.ZipFile(io.BytesIO(files[("en", "docx")]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in src.namelist():
            z.writestr(n, evil if n == "word/document.xml" else src.read(n))
    r = _upload(client, "cv.docx", buf.getvalue())
    assert r.status_code == 422 and r.get_json()["reason"] == "broken"
    assert not ai.calls


def test_pasted_text_that_is_too_short_or_too_long_is_refused(client, ai):
    assert client.post("/api/import", json={"text": "hi"}).get_json()["reason"] == "empty"
    r = client.post("/api/import", json={"text": "word " * 7000})
    assert r.status_code == 413 and r.get_json()["reason"] == "long"
    assert not ai.calls


def test_cp1256_and_utf16_text_files_are_read():
    ar = "ليلى خليل - مديرة إبداعية في ديوان للتصميم منذ عام 2021 حتى الآن"
    assert ar in importer.extract_text("cv.txt", ar.encode("cp1256"))
    assert ar in importer.extract_text("cv.txt", ar.encode("utf-16"))


def test_arabic_pdf_text_is_folded_out_of_presentation_forms(files):
    text = importer.extract_text("cv.pdf", files[("ar", "pdf")])
    assert not any("ﭐ" <= ch <= "﻿" for ch in text)
    assert LS.resume("ar")["name"].split()[0] in text


# ---- the model failing ---------------------------------------------------------------

def test_a_provider_failure_does_not_cost_the_user_a_use(client, ai, files):
    ai.raise_exc = ConnectionError("boom - with the CV in it")
    r = _upload(client, "cv.docx", files[("en", "docx")])
    j = r.get_json()
    assert r.status_code == 502 and j["reason"] == "ai_failed"
    assert "boom" not in j["error"]                      # never echoed
    with client.application.test_request_context():
        assert ai_quota.used_today("import") == 0


@pytest.mark.parametrize("fake", [dict(stop="refusal"), dict(text="not json"),
                                  dict(stop="max_tokens")])
def test_a_refusal_or_a_malformed_reply_is_reported(client, ai, files, fake):
    for k, v in fake.items():
        setattr(ai, k, v)
    ai.payload = perfect("en")
    r = _upload(client, "cv.docx", files[("en", "docx")])
    assert r.status_code == 502 and r.get_json()["reason"] == "ai_failed"


# ---- limits ------------------------------------------------------------------------

def test_ten_imports_a_day_then_429(client, ai, monkeypatch):
    from app.limits import LIMITS
    monkeypatch.setattr(LIMITS["import"], "check", lambda key: 0.0)   # the per-minute guard
    ai.payload = perfect("en")
    text = importer.extract_text("cv.docx", render_docx(LS.resume("en"), "ats-t1"))
    for i in range(10):
        assert client.post("/api/import", json={"text": text}).status_code == 200, i
    r = client.post("/api/import", json={"text": text})
    assert r.status_code == 429 and r.get_json()["reason"] == "daily_limit"
    assert len(ai.calls) == 10


def test_the_monthly_budget_stops_imports_before_the_model(client, ai, monkeypatch):
    monkeypatch.setattr(ai_quota, "monthly_budget", lambda: 0.0)
    r = client.post("/api/import", json={"text": "x" * 200})
    assert r.status_code == 503 and r.get_json()["reason"] == "budget"
    assert not ai.calls


def test_spend_is_recorded_from_the_usage_counters(client, ai, files):
    ai.payload = perfect("en")
    _upload(client, "cv.docx", files[("en", "docx")])
    with client.application.test_request_context():
        spent = ai_quota.month_spend()
    assert spent == pytest.approx(3000 * 0.10e-6 + 1500 * 0.50e-6 + 1200 * 0.125e-6)


def test_the_schema_sent_is_strict_and_matches_the_resume_fields():
    s = importer.output_schema()

    def walk(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
            for v in node["properties"].values():
                walk(v)
        if node.get("type") == "array":
            walk(node["items"])
    walk(s)
    assert set(CONTENT) | {"lang"} == set(s["properties"])
