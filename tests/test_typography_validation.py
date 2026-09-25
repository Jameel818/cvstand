"""Server-side whitelist for the typography keys (docs/CVSTAND_FONT_CONTROLS.md §7.2).

Agreed behaviour: a value the registry does not offer is RESET to null
("template default") and reported, never refused; only a wrong JSON type is a
422. And a résumé with no typography keys must normalise exactly as it did
before the feature — the goldens in tests/golden/normalize/ were captured from
`normalize()` BEFORE the six keys existed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import create_app
from app.config import RESUME_PATH
from app.schema import ResumeValidationError, normalize, validate
from app.typography import NO_FONT, NOT_OFFERED, TYPOGRAPHY_KEYS, clean_typography
from tests import samples

GOLDEN = Path(__file__).resolve().parent / "golden" / "normalize"
NONE6 = dict.fromkeys(TYPOGRAPHY_KEYS)


def _clean(lang="en", **kw):
    return clean_typography(kw, lang)


# ---- backward compatibility (§1.7, §7.9 at the data layer) -------------------

@pytest.mark.parametrize("name, data", [
    ("english", samples.ENGLISH), ("arabic", samples.ARABIC), ("mixed", samples.MIXED),
    ("reversed", samples.REVERSED), ("minimal", {"name": "A", "title": "B"}),
])
def test_normalize_is_unchanged_apart_from_six_none_keys(name, data):
    before = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    after = normalize(data)
    assert {k: after[k] for k in TYPOGRAPHY_KEYS} == NONE6
    assert {k: v for k, v in after.items() if k not in TYPOGRAPHY_KEYS} == before


def test_the_samples_carry_no_typography():
    """If a sample ever gains a font, the golden test above stops testing the
    no-typography case while still passing."""
    for data in (samples.ENGLISH, samples.ARABIC, samples.MIXED, samples.REVERSED):
        assert not set(TYPOGRAPHY_KEYS) & data.keys()


def test_missing_and_null_both_mean_template_default():
    assert _clean() == (NONE6, [])
    assert _clean(**NONE6) == (NONE6, [])


# ---- valid values survive ---------------------------------------------------

def test_a_full_valid_english_choice_survives_unchanged():
    choice = {"font_heading": "Montserrat", "font_heading_weight": 800,
              "font_heading_size": 32, "font_body": "Inter",
              "font_body_weight": 400, "font_body_size": 10}
    assert _clean(**choice) == (choice, [])


def test_a_full_valid_arabic_choice_survives_unchanged():
    choice = {"font_heading": "Almarai", "font_heading_weight": 800,
              "font_heading_size": 34, "font_body": "Readex Pro",
              "font_body_weight": 200, "font_body_size": 11.5}
    assert _clean("ar", **choice) == (choice, [])


def test_size_without_a_font_is_kept():
    """Size does not depend on the face, so "template font, bigger" is valid."""
    values, resets = _clean(font_body_size=11)
    assert values["font_body_size"] == 11 and resets == []


def test_whole_number_floats_are_stored_as_ints():
    values, _ = _clean(font_heading="Montserrat", font_heading_weight=800.0,
                       font_heading_size=32.0)
    assert values["font_heading_weight"] == 800 and type(values["font_heading_weight"]) is int
    assert values["font_heading_size"] == 32 and type(values["font_heading_size"]) is int


# ---- invalid values reset ---------------------------------------------------

def _reset_keys(resets):
    return {r["key"]: r["reason"] for r in resets}


@pytest.mark.parametrize("family", [
    "Comic Sans MS", "montserrat", " Montserrat", "Montserrat; } body { color:red",
    "", 42, ["Montserrat"],
])
def test_unknown_or_malformed_font_resets(family):
    values, resets = _clean(font_heading=family)
    assert values["font_heading"] is None
    assert _reset_keys(resets) == {"font_heading": NOT_OFFERED}


def test_arabic_font_on_an_english_cv_is_rejected():
    values, resets = _clean("en", font_body="Amiri")
    assert values["font_body"] is None
    assert _reset_keys(resets) == {"font_body": NOT_OFFERED}


def test_english_font_on_an_arabic_cv_is_rejected():
    values, _ = _clean("ar", font_heading="Montserrat")
    assert values["font_heading"] is None


def test_font_in_the_wrong_role_is_rejected():
    """Inter is an English DETAILS font only."""
    values, _ = _clean("en", font_heading="Inter")
    assert values["font_heading"] is None


@pytest.mark.parametrize("weight", [900, 300, 850, 800.5, True, "800", float("nan")])
def test_weight_the_font_does_not_offer_resets(weight):
    values, resets = _clean("ar", font_heading="Almarai", font_heading_weight=weight)
    assert values["font_heading"] == "Almarai"
    assert values["font_heading_weight"] is None
    assert _reset_keys(resets) == {"font_heading_weight": NOT_OFFERED}


def test_anton_only_takes_400():
    assert _clean(font_heading="Anton", font_heading_weight=400)[0]["font_heading_weight"] == 400
    assert _clean(font_heading="Anton", font_heading_weight=700)[0]["font_heading_weight"] is None


def test_weight_without_a_font_resets():
    """The template's own face is outside the registry; a weight it may not
    have would be faux bold (hard rule 1)."""
    values, resets = _clean(font_body_weight=300)
    assert values["font_body_weight"] is None
    assert _reset_keys(resets) == {"font_body_weight": NO_FONT}


def test_weight_is_dropped_with_an_invalid_font():
    values, resets = _clean(font_heading="Nope", font_heading_weight=800)
    assert values["font_heading"] is None and values["font_heading_weight"] is None
    assert _reset_keys(resets) == {"font_heading": NOT_OFFERED, "font_heading_weight": NO_FONT}


@pytest.mark.parametrize("size", [9.7, 9.25, 12.5, 8.5, 0, -10, True, "10",
                                  float("inf"), 10 ** 400])
def test_off_grid_or_out_of_range_body_size_resets(size):
    values, resets = _clean(font_body_size=size)
    assert values["font_body_size"] is None
    assert _reset_keys(resets) == {"font_body_size": NOT_OFFERED}


@pytest.mark.parametrize("lang, size, ok", [
    ("en", 32, True), ("en", 33, False), ("en", 46, False),
    ("ar", 48, True), ("ar", 24, False),
])
def test_heading_size_grid_is_even_points(lang, size, ok):
    assert (_clean(lang, font_heading_size=size)[0]["font_heading_size"] is not None) is ok


def test_arabic_body_size_uses_the_arabic_range():
    """10 pt: bottom of AR details, but 9 pt is EN-only."""
    assert _clean("ar", font_body_size=9)[0]["font_body_size"] is None
    assert _clean("ar", font_body_size=14)[0]["font_body_size"] == 14


def test_resets_echo_the_rejected_value():
    _, resets = _clean(font_heading="Nope")
    assert resets == [{"key": "font_heading", "value": "Nope", "reason": NOT_OFFERED}]


# ---- normalize() --------------------------------------------------------------

def test_normalize_applies_the_whitelist_for_the_documents_language():
    en = {"name": "A", "title": "B", "font_heading": "Cairo", "font_body": "Inter"}
    out = normalize(en)
    assert out["font_heading"] is None and out["font_body"] == "Inter"
    out = normalize({**en, "lang": "ar"})
    assert out["font_heading"] == "Cairo" and out["font_body"] is None


def test_normalize_never_passes_raw_input_through():
    out = normalize({"name": "A", "title": "B", "font_heading": "x</style><script>"})
    assert out["font_heading"] is None


# ---- schema: only a wrong JSON TYPE is refused ------------------------------

@pytest.mark.parametrize("key, value", [
    ("font_heading", 5), ("font_heading", {"a": 1}), ("font_body_weight", "400"),
    ("font_body_size", "10"), ("font_heading_size", [32]),
])
def test_schema_rejects_the_wrong_json_type(key, value):
    with pytest.raises(ResumeValidationError):
        validate({"name": "A", "title": "B", key: value})


@pytest.mark.parametrize("key, value", [
    ("font_heading", "Comic Sans MS"), ("font_heading_weight", 850),
    ("font_body_size", 9.7), ("font_body", None),
])
def test_schema_accepts_the_right_type_even_off_the_whitelist(key, value):
    validate({"name": "A", "title": "B", key: value})


# ---- PUT /api/resume ----------------------------------------------------------

@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    before = RESUME_PATH.read_bytes() if RESUME_PATH.exists() else None
    try:
        yield app.test_client()
    finally:
        # One data dir per session (tests/conftest.py): leave the store as found.
        if before is None:
            RESUME_PATH.unlink(missing_ok=True)
        else:
            RESUME_PATH.write_bytes(before)


def test_put_returns_resets_and_stores_the_cleaned_values(client, caplog):
    caplog.set_level("INFO")
    body = {"name": "A", "title": "B", "font_heading": "Montserrat",
            "font_heading_weight": 850, "font_body": "Amiri", "font_body_size": 10}
    res = client.put("/api/resume", json=body)
    assert res.status_code == 200
    got = res.get_json()
    assert got["ok"] is True
    assert _reset_keys(got["resets"]) == {"font_heading_weight": NOT_OFFERED,
                                         "font_body": NOT_OFFERED}
    assert "typography reset on save" in caplog.text
    stored = json.loads(RESUME_PATH.read_text(encoding="utf-8"))
    assert stored["font_heading"] == "Montserrat"
    assert stored["font_heading_weight"] is None and stored["font_body"] is None
    assert stored["font_body_size"] == 10
    # A second save of what was stored reports nothing: the reset is one-off.
    assert client.put("/api/resume", json=stored).get_json()["resets"] == []


def test_put_without_typography_stores_the_resume_as_sent(client):
    res = client.put("/api/resume", json=samples.ENGLISH)
    assert res.status_code == 200 and res.get_json() == {"ok": True, "resets": []}
    assert json.loads(RESUME_PATH.read_text(encoding="utf-8")) == samples.ENGLISH


def test_put_with_a_wrong_type_is_422(client):
    res = client.put("/api/resume", json={"name": "A", "title": "B", "font_body_size": "10"})
    assert res.status_code == 422
    assert any("font_body_size" in e for e in res.get_json()["errors"])
