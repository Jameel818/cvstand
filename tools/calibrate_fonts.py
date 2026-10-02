"""Typography step 7 (spec §4.1): measure every offered face's optical size and
line height, so "10 pt" looks the same size whichever font is chosen.

    venv/Scripts/python tools/calibrate_fonts.py               # measure + write
    venv/Scripts/python tools/calibrate_fonts.py --check       # numbers current?
    venv/Scripts/python tools/calibrate_fonts.py --instrument  # the known answer

Writes app/typography/calibration.json (generated, never hand-edited):
{lang: {family: {"optical_scale", "ink", "ink_headline", "spread", "weight",
"line_height", "clamped"}}}.

optical_scale = reference ink / face ink, reference Inter (EN) / Cairo (AR) at
the same weight, clamped to 0.85-1.8 (spec); a face beyond the clamp is
listed (`clamped`), never silently bent. The ink is the MEAN over several
strings the templates really print: the spec's single word (EN "Hxpg", AR
"محمد") is kept as `ink_headline`, but one word is dominated by its own
letters (Amiri reads 126 % of the mean on "محمد", 111 % on real headings) -
`spread` is the min/max ratio across the strings, the measurement's own noise.

Weight: each face at its role's default (Details 400 if the family is offered
for Details, else Headings 700), the offered weight nearest to it.

line_height: max(hhea ascender - descender + lineGap, OS/2 winAscent +
winDescent) / unitsPerEm - the line a browser (hhea / typo) or Word (win)
gives the face at line-height: normal.

--instrument: SIZE_ADJUST in tools/fetch_fonts_ar.py came from the same
canvas measure over Arabic headings (raw 100px ink: Tajawal 90.6, Amiri
112.8); this tool must reproduce both within 1 % before its numbers count.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from _ink import ink_heights, ink_page  # noqa: E402

from app.typography import built_faces  # noqa: E402
from app.typography.faces import FONT_DIR  # noqa: E402
from app.typography.registry import OFFERED, nearest_weight  # noqa: E402

OUT = ROOT / "app" / "typography" / "calibration.json"
CLAMP = (0.85, 1.8)
REFERENCE = {"en": "Inter", "ar": "Cairo"}
HEADLINE = {"en": "Hxpg", "ar": "محمد"}
STRINGS = {
    "en": ["Wren Ashworth", "Experience", "Creative Lead", "Northfield University",
           "Brand systems that survive handover"],
    "ar": ["الخبرة العملية", "التعليم", "المهارات", "نبذة عني", "ليلى خليل",
           "مديرة إبداعية", "تدير استوديو من أربعة عشر شخصاً", "ديوان للتصميم",
           "اللغة الأم", "الهاتف"],
}
#: the instrument check: raw ink at 100px, weight 400, Arabic headings
KNOWN = {"Tajawal": 90.6, "Amiri": 112.8}


def _families(lang: str) -> dict[str, str]:
    """family -> the role whose default weight it is measured at."""
    out = {}
    for role in ("heading", "body"):
        for f in OFFERED[(lang, role)]:
            out[f] = "body" if f in OFFERED[(lang, "body")] else "heading"
    return out


def _weight(lang: str, role: str, family: str) -> int:
    return nearest_weight(lang, role, family, 400 if role == "body" else 700)


def _built(family: str, weight: int) -> int:
    have = sorted(w for f, w in built_faces() if f == family)
    return min(have, key=lambda w: (abs(w - weight), -w))


def line_height(family: str, weight: int) -> float:
    from fontTools.ttLib import TTFont
    face = built_faces()[(family, _built(family, weight))]
    font = TTFont(FONT_DIR / face["ttf"], lazy=True)
    upm, hh, os2 = font["head"].unitsPerEm, font["hhea"], font["OS/2"]
    hhea = hh.ascent - hh.descent + hh.lineGap
    win = os2.usWinAscent + os2.usWinDescent
    return round(max(hhea, win) / upm, 4)


def _ink(page, family, weight, texts):
    got = ink_heights(page, family, weight, texts)
    if not got:
        raise SystemExit(f"{family} {weight} did not load - refusing a fallback's number")
    return got


def measure() -> dict:
    out: dict = {}
    with ink_page() as page:
        for lang in ("en", "ar"):
            out[lang] = {}
            ref_cache: dict[int, float] = {}
            for family, role in sorted(_families(lang).items()):
                w = _built(family, _weight(lang, role, family))
                hs = _ink(page, family, w, STRINGS[lang])
                ink = sum(hs) / len(hs)
                rw = _built(REFERENCE[lang], w)
                if rw not in ref_cache:
                    r = _ink(page, REFERENCE[lang], rw, STRINGS[lang])
                    ref_cache[rw] = sum(r) / len(r)
                ref = ref_cache[rw]
                rhs = _ink(page, REFERENCE[lang], rw, STRINGS[lang])
                ratios = [a / b for a, b in zip(rhs, hs) if b]
                raw = ref / ink
                scale = min(max(raw, CLAMP[0]), CLAMP[1])
                out[lang][family] = {
                    "weight": w,
                    "ink": round(ink, 2),
                    "ink_headline": round(_ink(page, family, w, [HEADLINE[lang]])[0], 2),
                    "optical_scale": round(scale, 3),
                    "spread": [round(min(ratios), 3), round(max(ratios), 3)],
                    "clamped": round(raw, 3) if scale != raw else None,
                    "line_height": line_height(family, w),
                }
    return out


def instrument() -> int:
    with ink_page() as page:
        bad = 0
        for family, want in KNOWN.items():
            hs = _ink(page, family, 400, STRINGS["ar"][:5])
            got = sum(hs) / len(hs)
            off = 100 * (got - want) / want
            ok = abs(off) <= 1.0
            bad += not ok
            print(f"{'ok ' if ok else 'BAD'} {family}: {got:.1f} vs SIZE_ADJUST's {want} ({off:+.1f} %)")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--instrument" in argv:
        return instrument()
    data = {"generated_by": "tools/calibrate_fonts.py", "clamp": list(CLAMP),
            "reference": REFERENCE, **measure()}
    if "--check" in argv:
        old = json.loads(OUT.read_text(encoding="utf-8"))
        drift = [f"{lang}/{f}" for lang in ("en", "ar") for f in data[lang]
                 if abs(old.get(lang, {}).get(f, {}).get("optical_scale", -9)
                        - data[lang][f]["optical_scale"]) > 0.01]
        print("calibration current" if not drift else f"STALE: {drift}")
        return 1 if drift else 0
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for lang in ("en", "ar"):
        for f, v in data[lang].items():
            flag = f"  CLAMPED (raw {v['clamped']})" if v["clamped"] else ""
            print(f"{lang} {f:22} w{v['weight']} scale {v['optical_scale']:.3f} "
                  f"spread {v['spread']} lh {v['line_height']}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
