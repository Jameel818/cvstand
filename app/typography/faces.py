"""What the font build produced, per (family, weight).

`build.json` is written by `tools/build_fonts.py` and committed beside the
registry. The registry says what a font IS and what a dropdown offers; this
says which file serves each offered face and what that file measured as -
`word_family_name` and `word_bold` for the Word mapping (§6.2), `fs_type` and
`ttf` for embedding (§6.3), `css_family` for the stylesheet. Read it; never
rebuild those values by hand.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BUILD_JSON = Path(__file__).with_name("build.json")
FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"


@lru_cache(maxsize=1)
def built_faces() -> dict[tuple[str, int], dict]:
    data = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    return {(f["family"], f["weight"]): f for f in data["faces"]}


def face(family: str, weight: int) -> dict | None:
    return built_faces().get((family, weight))


def ttf_path(family: str, weight: int) -> Path | None:
    f = face(family, weight)
    return FONT_DIR / f["ttf"] if f else None
