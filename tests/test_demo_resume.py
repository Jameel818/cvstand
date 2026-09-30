"""The builder's DEMO résumé (data/demo_resume*.json): the example a visitor's
builder opens on. It must fit ONE page in every Modern template, in the PDF
and in Word, so its content is kept short - but every section stays, so the
example still shows the whole design (docs/WORD_FIDELITY_AUDIT.md, item 2).

The test fixtures and the showcase keep data/sample_resume*.json, unchanged."""
import json

import pytest

from app import schema
from app.config import DEMO_RESUME_PATHS, SAMPLE_RESUME_PATHS
from app.store import seed_resume


@pytest.fixture(params=["en", "ar"])
def demo(request):
    return request.param, json.loads(DEMO_RESUME_PATHS[request.param].read_text(encoding="utf-8"))


def test_demo_is_schema_valid(demo):
    schema._VALIDATOR.validate(demo[1])


def test_demo_content_is_short(demo):
    lang, d = demo
    assert len(d["summary"]) <= 130            # two lines in the narrowest summary column
    assert len(d["experience"]) == 3
    assert all(len(j["bullets"]) <= 2 for j in d["experience"])
    assert len(d["skills"]) == 5
    assert len(d["languages"]) == 2
    assert 1 <= len(d["recognition"]) <= 2


def test_demo_keeps_every_section(demo):
    """Short, but nothing a template draws is left out - References included."""
    _, d = demo
    for key in ("name", "title", "summary", "achievements", "experience", "education",
                "skills", "tools", "languages", "recognition", "references"):
        assert d[key], key
    assert all(c["email"] for c in [d["contact"]])


def test_builder_seeds_from_the_demo():
    for lang in ("en", "ar"):
        assert seed_resume(lang) == json.loads(DEMO_RESUME_PATHS[lang].read_text(encoding="utf-8"))


def test_the_fixtures_are_not_the_demo():
    """The showcase / test samples stay separate files."""
    for lang in ("en", "ar"):
        assert DEMO_RESUME_PATHS[lang] != SAMPLE_RESUME_PATHS[lang]
