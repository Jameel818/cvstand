"""User typography choices: the font registry and its whitelist.

Spec: docs/CVSTAND_FONT_CONTROLS.md. Import from here, not the submodules.
"""
from .registry import (
    FONTS, LANGS, OFFERED, ROLES, SIZES, TYPOGRAPHY_KEYS, WEIGHT_RANGE,
    Font, SizeScale,
    fonts_for, is_offered, is_single_weight, nearest_weight, offered_weights, size_scale,
)
from .validate import NO_FONT, NOT_OFFERED, clean_typography

__all__ = [
    "FONTS", "LANGS", "OFFERED", "ROLES", "SIZES", "TYPOGRAPHY_KEYS", "WEIGHT_RANGE",
    "Font", "SizeScale",
    "fonts_for", "is_offered", "is_single_weight", "nearest_weight", "offered_weights",
    "size_scale",
    "NO_FONT", "NOT_OFFERED", "clean_typography",
]
