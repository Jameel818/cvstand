"""The typography registry against the spec (docs/CVSTAND_FONT_CONTROLS.md §7.1).

The registry COMPUTES what each dropdown offers from what each font has. The
tables below are the spec's §3.1-3.4 typed out once, here, so a slip in that
arithmetic — or in a font's weight list — fails against an independent copy
instead of agreeing with itself.
"""
from __future__ import annotations

import math

import pytest

from app.typography import (
    FONTS, LANGS, OFFERED, ROLES, SIZES, WEIGHT_RANGE,
    fonts_for, is_single_weight, nearest_weight, offered_weights, size_scale,
)

SPEC_OFFERED = {
    ("en", "heading"): {
        "Anton": (400,), "Anton SC": (400,), "Archivo": (700, 800, 900),
        "Archivo Black": (400,), "Bebas Neue": (400,), "Montserrat": (700, 800, 900),
        "Raleway": (700, 800, 900), "Playfair Display": (700, 800, 900),
        "Source Serif 4": (700, 800, 900), "Work Sans": (700, 800, 900),
    },
    ("en", "body"): {
        "Poppins": (200, 300, 400), "Montserrat": (200, 300, 400), "Inter": (200, 300, 400),
        "Lora": (400,), "Source Serif 4": (200, 300, 400), "Work Sans": (200, 300, 400),
        "Archivo": (200, 300, 400),
    },
    ("ar", "heading"): {
        "Tajawal": (700, 800, 900), "Cairo": (700, 800, 900), "Almarai": (700, 800),
        "Alexandria": (700, 800, 900), "Noto Kufi Arabic": (700, 800, 900),
        "Mada": (700, 800, 900), "Readex Pro": (700,), "El Messiri": (700,),
        "Noto Naskh Arabic": (700,), "Markazi Text": (700,), "Scheherazade New": (700,),
        "Lateef": (700, 800), "Aref Ruqaa": (700,), "Lalezar": (400,), "Jomhuria": (400,),
        "Rakkas": (400,), "Marhey": (700,), "Baloo Bhaijaan 2": (700, 800),
        "Lemonada": (700,),
    },
    ("ar", "body"): {
        "Markazi Text": (400,), "Noto Naskh Arabic": (400,), "Readex Pro": (200, 300, 400),
        "Amiri": (400,), "Scheherazade New": (400,), "Noto Kufi Arabic": (200, 300, 400),
        "IBM Plex Sans Arabic": (200, 300, 400), "Noto Sans Arabic": (200, 300, 400),
        "Lateef": (200, 300, 400), "Mada": (200, 300, 400), "Baloo Bhaijaan 2": (400,),
        "Tajawal": (200, 300, 400), "Cairo": (200, 300, 400), "Alexandria": (200, 300, 400),
        "El Messiri": (400,),
    },
}

# §3.5: the six fonts that carry the "creative roles" tag.
SPEC_PLAYFUL = {"Marhey", "Baloo Bhaijaan 2", "Lemonada", "Jomhuria", "Rakkas", "Lalezar"}

SLOTS = [(lang, role) for lang in LANGS for role in ROLES]


def test_the_spec_table_covers_every_slot():
    """Guards the guard: an empty or partial SPEC_OFFERED would pass vacuously."""
    assert set(SPEC_OFFERED) == set(OFFERED) == set(SLOTS)
    assert sum(len(v) for v in SPEC_OFFERED.values()) == 51


@pytest.mark.parametrize("slot", SLOTS)
def test_each_dropdown_lists_exactly_the_spec_fonts_in_order(slot):
    assert OFFERED[slot] == tuple(SPEC_OFFERED[slot])


@pytest.mark.parametrize("slot", SLOTS)
def test_offered_weights_match_the_spec_cell_by_cell(slot):
    got = {f.family: offered_weights(*slot, f.family) for f in fonts_for(*slot)}
    assert got == SPEC_OFFERED[slot]


@pytest.mark.parametrize("slot", SLOTS)
def test_every_font_offers_at_least_one_real_weight(slot):
    for font in fonts_for(*slot):
        weights = offered_weights(*slot, font.family)
        assert weights, f"{font.family} offers nothing in {slot}"
        assert set(weights) <= set(font.weights), f"{font.family} offers a weight it lacks"


@pytest.mark.parametrize("slot", SLOTS)
def test_weights_outside_the_role_range_appear_only_as_the_lone_fallback(slot):
    lo, hi = WEIGHT_RANGE[slot[1]]
    for font in fonts_for(*slot):
        weights = offered_weights(*slot, font.family)
        if any(not lo <= w <= hi for w in weights):
            assert len(weights) == 1 and is_single_weight(*slot, font.family)


def test_no_font_crosses_languages():
    """An Arabic dropdown listing an English-only face (or the reverse) would
    render Arabic text in a fallback font (§3.4)."""
    en = set(OFFERED[("en", "heading")]) | set(OFFERED[("en", "body")])
    ar = set(OFFERED[("ar", "heading")]) | set(OFFERED[("ar", "body")])
    assert not en & ar


def test_every_offered_family_is_registered_and_every_registered_family_offered():
    offered = {f for fams in OFFERED.values() for f in fams}
    assert offered == set(FONTS)


def test_family_names_and_slugs_are_unique():
    slugs = [f.slug for f in FONTS.values()]
    assert len(slugs) == len(set(slugs))


def test_playful_tag_is_exactly_the_spec_list():
    assert {f.family for f in FONTS.values() if f.playful} == SPEC_PLAYFUL


def test_font_weights_are_real_css_weights():
    for font in FONTS.values():
        assert font.weights == tuple(sorted(set(font.weights)))
        assert all(w in range(100, 1000, 100) for w in font.weights)


# ---- sizes (§4) -------------------------------------------------------------

SPEC_SIZES = {
    ("en", "heading"): (24, 44, 2, 32),
    ("en", "body"): (9, 12, 0.5, 10),
    ("ar", "heading"): (26, 48, 2, 34),
    ("ar", "body"): (10, 14, 0.5, 11.5),
}


@pytest.mark.parametrize("slot", SLOTS)
def test_size_scales_match_the_spec(slot):
    s = size_scale(*slot)
    assert (s.min, s.max, s.step, s.default) == SPEC_SIZES[slot]


@pytest.mark.parametrize("slot", SLOTS)
def test_size_default_is_on_the_grid_and_in_range(slot):
    s = size_scale(*slot)
    assert s.allows(s.default)
    assert s.default in s.options()


@pytest.mark.parametrize("slot", SLOTS)
def test_size_steps_are_powers_of_two(slot):
    """`allows()` divides by the step and asks `.is_integer()`. That is exact
    ONLY for power-of-two steps; a 0.1 step would make 0.3 / 0.1 = 2.9999...
    and silently reject a size the dropdown itself offers."""
    step = size_scale(*slot).step
    assert math.log2(step).is_integer()


@pytest.mark.parametrize("slot", SLOTS)
def test_every_dropdown_size_is_accepted_and_the_ends_are_exact(slot):
    s = size_scale(*slot)
    opts = s.options()
    assert opts[0] == s.min and opts[-1] == s.max
    assert all(s.allows(v) for v in opts)


def test_size_grid_checks_are_exact_multiples():
    body, head = size_scale("en", "body"), size_scale("en", "heading")
    assert body.allows(9.5) and body.allows(12)
    assert not body.allows(9.7) and not body.allows(9.25) and not body.allows(12.5)
    assert head.allows(32) and not head.allows(33) and not head.allows(32.5)
    assert not head.allows(22) and not head.allows(46)


def test_sizes_cover_both_roles_in_both_languages():
    assert set(SIZES) == set(SLOTS)


# ---- weight carry-over (§3.5) ----------------------------------------------

def test_montserrat_900_to_almarai_keeps_800():
    assert nearest_weight("ar", "heading", "Almarai", 900) == 800


def test_single_weight_fonts_are_flagged_for_a_disabled_dropdown():
    assert is_single_weight("en", "heading", "Anton")
    assert offered_weights("en", "heading", "Anton") == (400,)
    assert not is_single_weight("en", "heading", "Montserrat")


def test_nearest_weight_ties_go_heavier_and_unknown_fonts_give_none():
    # 750 is equidistant from 700 and 800
    assert nearest_weight("en", "heading", "Montserrat", 750) == 800
    assert nearest_weight("en", "body", "Inter", 900) == 400
    assert nearest_weight("en", "heading", "Amiri", 700) is None
