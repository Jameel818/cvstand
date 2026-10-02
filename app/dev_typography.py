"""/dev/typography - the step 7 calibration page (spec §7.4). Debug only.

One row per offered (language, family, weight): a sample name, a heading and
a body line at the role's DEFAULT size, drawn twice - as typed (the size the
user picks) and multiplied by the face's measured optical_scale - with the
scale, its spread and the face's own line height beside them. It exists so a
person can judge the calibration by eye; tests/e2e/
test_typography_calibration_page.py screenshots it into tests/e2e/artifacts/
and checks every face loaded.

Answers 404 unless the app runs in debug mode (checked per request:
app.run(debug=True) sets debug only after create_app() has returned).
"""
from __future__ import annotations

from flask import Blueprint, abort, current_app
from markupsafe import escape

from .typography.registry import OFFERED, SIZES, line_height, offered_weights, optical_scale
from .typography.render import PT_TO_PX, TYPOGRAPHY_CSS_URL

bp = Blueprint("dev_typography", __name__)

SAMPLE = {
    "en": ("Wren Ashworth", "Experience", "Brand systems that survive handover: fourteen "
           "designers, four launches."),
    "ar": ("ليلى خليل", "الخبرة العملية", "مديرة إبداعية تبني أنظمة هوية تصمد بعد التسليم."),
}


def _rows(lang: str) -> list[str]:
    from .typography.registry import _calibration
    cal = _calibration().get(lang, {})
    name, head, body = SAMPLE[lang]
    out = []
    for role, text in (("name", name), ("heading", head), ("body", body)):
        size = SIZES[(lang, role)].default
        for family in OFFERED[(lang, role)]:
            k = optical_scale(lang, family)
            spread = cal.get(family, {}).get("spread", ["?", "?"])
            for w in offered_weights(lang, role, family):
                style = f"font-family:'CVT {family}'; font-weight:{w};"
                px = size * PT_TO_PX
                out.append(
                    f'<tr data-family="{escape(family)}" data-weight="{w}">'
                    f"<td>{role}</td><td>{escape(family)} {w}</td>"
                    f'<td class="s" style="{style} font-size:{px:.2f}px">{escape(text)}</td>'
                    f'<td class="s" style="{style} font-size:{px * k:.2f}px">{escape(text)}</td>'
                    f"<td>{k:.3f}<br><small>{spread[0]}-{spread[1]}</small></td>"
                    f"<td>{line_height(lang, family) or '?'}</td></tr>")
    return out


@bp.get("/dev/typography")
def calibration_page():
    if not current_app.debug:
        abort(404)
    parts = []
    for lang in ("en", "ar"):
        d = "rtl" if lang == "ar" else "ltr"
        parts.append(
            f'<h2>{lang.upper()}</h2><table dir="{d}" lang="{lang}"><tr><th>role</th>'
            "<th>face</th><th>default size</th><th>x optical_scale</th><th>scale (spread)</th>"
            "<th>line</th></tr>" + "".join(_rows(lang)) + "</table>")
    return (
        '<!doctype html><meta charset="utf-8"><title>Typography calibration</title>'
        f'<link rel="stylesheet" href="{TYPOGRAPHY_CSS_URL}">'
        "<style>body{font:13px system-ui,sans-serif;margin:16px}table{border-collapse:collapse;"
        "margin-bottom:24px}td,th{border:1px solid #ddd;padding:4px 8px;vertical-align:middle}"
        "td.s{white-space:nowrap}</style>"
        "<h1>Typography calibration (step 7)</h1><p>Each sample at the role's default "
        "size, then multiplied by the measured optical_scale (tools/calibrate_fonts.py). "
        "The scale is OFF in documents until approved (CVSTAND_OPTICAL_SCALE=1).</p>"
        + "".join(parts))
