"""Typography step 7 data (tools/calibrate_fonts.py -> calibration.json).

What these pin is the GENERATED file's shape and the facts measured on
2026-10-02; `calibrate_fonts.py --check` re-measures in Chromium, and
`--instrument` re-derives tools/fetch_fonts_ar.py's SIZE_ADJUST first."""
from __future__ import annotations

import json
from pathlib import Path

from app.typography.registry import OFFERED, line_height, optical_scale

DATA = json.loads(Path("app/typography/calibration.json").read_text(encoding="utf-8"))


def test_every_offered_family_is_calibrated_within_the_clamp():
    lo, hi = DATA["clamp"]
    for (lang, _role), fams in OFFERED.items():
        for f in fams:
            v = DATA[lang][f]
            assert lo <= v["optical_scale"] <= hi, (lang, f)
            assert v["line_height"] >= 1.0, (lang, f)
            assert v["spread"][0] <= v["spread"][1]


def test_the_references_are_exactly_one():
    assert optical_scale("en", "Inter") == 1.0 and optical_scale("ar", "Cairo") == 1.0


def test_it_agrees_with_the_older_size_adjust_measurement():
    # fetch_fonts_ar.py: Tajawal 114.2 % of the mean of five faces (Cairo ~100 %)
    assert abs(optical_scale("ar", "Tajawal") - 1.142) < 0.03


def test_naskh_faces_need_taller_lines_than_cairo_except_markazi():
    # the plan expected all five; measured: Markazi Text's own line is SHORT
    # (1.30 em, smaller ascenders) - recorded, not hidden
    for f in ("Amiri", "Scheherazade New", "Lateef", "Noto Naskh Arabic"):
        assert line_height("ar", f) > line_height("ar", "Cairo"), f
    assert line_height("ar", "Markazi Text") < line_height("ar", "Cairo")


def test_uncalibrated_means_unscaled():
    assert optical_scale("en", "No Such Font") == 1.0
    assert line_height("en", "No Such Font") is None


def test_the_calibration_page_exists_only_in_debug():
    from app import create_app
    app = create_app()
    assert app.test_client().get("/dev/typography").status_code == 404
    app.debug = True
    r = app.test_client().get("/dev/typography")
    assert r.status_code == 200 and "CVT Jomhuria" in r.get_data(as_text=True)


def test_the_optical_scale_is_off_unless_enabled(monkeypatch):
    from app.schema import normalize, typography_of
    from app.typography.render import config
    ar = json.loads(Path("data/demo_resume_ar.json").read_text(encoding="utf-8"))
    vals, _ = typography_of(normalize(dict(ar, font_body="Lateef")))
    monkeypatch.delenv("CVSTAND_OPTICAL_SCALE", raising=False)
    assert config(vals, "ar")["body"]["optical"] == 1.0
    monkeypatch.setenv("CVSTAND_OPTICAL_SCALE", "1")
    assert config(vals, "ar")["body"]["optical"] == optical_scale("ar", "Lateef") != 1.0
