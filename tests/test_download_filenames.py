"""Download file names keep the person's real name in any script
(app/filenames.py). Until 2026-10 an Arabic name downloaded as "_.pdf".

The routes send `filename="<ASCII>"` for old browsers and
`filename*=UTF-8''<real name>` for every current one; the builder reads the
same header (tests/e2e/test_download_filenames_builder.py)."""
from __future__ import annotations

from urllib.parse import unquote

import pytest

from app import filenames as F
from tests.samples import ARABIC, ENGLISH


@pytest.mark.parametrize("name,want", [
    ("Wren Ashworth", "Wren_Ashworth"),
    ("ليلى خليل", "ليلى_خليل"),
    ("  ليلى   خليل  ", "ليلى_خليل"),
    ("José Núñez", "José_Núñez"),
    ("Anna-Maria O'Neil", "Anna-Maria_O'Neil"),
    ('A<b>c:d"e/f\\g|h?i*j', "A_b_c_d_e_f_g_h_i_j"),
    ("name.", "name"),
    ("..hidden", "hidden"),
    ("CON", "resume"),
    ("nul.txt", "resume"),
    ("", "resume"),
    (None, "resume"),
    ("???", "resume"),
    ("⁦555⁩ Laila", "555_Laila"),
])
def test_base_name(name, want):
    assert F.base_name(name) == want


def test_base_name_is_bounded():
    assert len(F.base_name("x" * 500)) == F.MAX_CHARS


@pytest.mark.parametrize("stem,want", [
    ("Wren_Ashworth", "Wren_Ashworth"),
    ("José_Núñez", "Jose_Nunez"),
    ("ليلى_خليل", "resume"),
])
def test_ascii_fallback(stem, want):
    assert F.ascii_name(stem) == want


def _cd(name, part, ext):
    return F.content_disposition(name, part, ext)


def test_english_header_is_plain():
    assert _cd("Wren Ashworth", "cv", "pdf") == "attachment; filename=Wren_Ashworth.pdf"


@pytest.mark.parametrize("part,suffix", [("cv", ""), ("letter", "_cover_letter"),
                                         ("both", "_cv_and_cover_letter")])
@pytest.mark.parametrize("ext", ["pdf", "docx"])
def test_arabic_header_carries_the_real_name(part, suffix, ext):
    cd = _cd("ليلى خليل", part, ext)
    assert f"filename=resume{suffix}.{ext};" in cd
    star = cd.split("filename*=UTF-8''", 1)[1]
    assert unquote(star) == f"ليلى_خليل{suffix}.{ext}"
    assert all(ord(c) < 128 for c in cd), "a header must be ASCII"


# ---- through the routes (the Flask test client) ----------------------------------

@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _post(client, kind, data, part="cv"):
    body = {"data": data, "template_key": "ats-t1"}
    if part != "cv":
        body["part"] = part
    return client.post(f"/export/{kind}", json=body)


@pytest.mark.parametrize("part", ["cv", "letter", "both"])
@pytest.mark.parametrize("data,want", [(ENGLISH, None), (ARABIC, "ar")], ids=["en", "ar"])
def test_word_download_names(client, data, want, part):
    from tests import letter_samples as LS
    if part != "cv":
        data = LS.with_letter("ar" if want else "en")
    res = _post(client, "docx", data, part)
    assert res.status_code == 200, res.data[:300]
    cd = res.headers["Content-Disposition"]
    assert cd == F.content_disposition(data.get("name"), part, "docx")
    if want:
        real = unquote(cd.split("filename*=UTF-8''", 1)[1])
        assert real.startswith(F.base_name(data["name"])) and real.endswith(".docx")
        assert not real.startswith("_")
