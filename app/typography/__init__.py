"""User typography choices: the font registry and its whitelist.

Spec: docs/CVSTAND_FONT_CONTROLS.md. Import from here, not the submodules.
"""
from .faces import built_faces, face, ttf_path
from .registry import (
    CSS_FAMILY_PREFIX, EMPHASIS_FROM, EMPHASIS_WEIGHT, LATIN_EXT_FALLBACK,
    LIGHT_WARNING_PT, LIGHT_WEIGHT, built_weights, FONTS, LANGS, OFFERED, ROLES, SIZES, TYPOGRAPHY_KEYS, WEIGHT_RANGE,
    Font, SizeScale,
    fonts_for, is_offered, is_single_weight, nearest_weight, offered_weights, size_scale,
)
from .validate import NO_FONT, NOT_OFFERED, clean_typography

__all__ = [
    "built_faces", "face", "ttf_path", "CSS_FAMILY_PREFIX",
    "EMPHASIS_FROM", "EMPHASIS_WEIGHT", "LATIN_EXT_FALLBACK", "LIGHT_WARNING_PT",
    "LIGHT_WEIGHT", "built_weights",
    "FONTS", "LANGS", "OFFERED", "ROLES", "SIZES", "TYPOGRAPHY_KEYS", "WEIGHT_RANGE",
    "Font", "SizeScale",
    "fonts_for", "is_offered", "is_single_weight", "nearest_weight", "offered_weights",
    "size_scale",
    "NO_FONT", "NOT_OFFERED", "clean_typography",
]
