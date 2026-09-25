"""Typography registry — the ONE list of fonts, weights, roles and sizes.

Spec: docs/CVSTAND_FONT_CONTROLS.md §3 (fonts, weights) and §4 (sizes). The
builder's dropdowns, server validation, the CSS, the PDF check and the Word
mapping all read from here; nothing else may carry a font list (hard rule 4).

What is typed in by hand is only what a font IS: the weights it ships and its
category. What a dropdown OFFERS is computed — (the role's weight range) ∩
(the weights the font has), falling back to the font's single nearest weight
when that is empty — so a table and its arithmetic can never drift apart.
`tests/test_typography_registry.py` pins the result against the spec's tables
cell by cell.

The "weights the font has" are the spec's figures (Fontsource, 2026-09-25).
They are not verified against files here: step 2's build script asserts every
offered weight really exists in the downloaded fonts and fails loudly if not.
"""
from __future__ import annotations

from dataclasses import dataclass

LANGS = ("en", "ar")
ROLES = ("heading", "body")

# The six résumé keys (spec §2), by role. Fonts are family names, weights are
# CSS numeric weights, sizes are points.
FONT_KEY = {"heading": "font_heading", "body": "font_body"}
WEIGHT_KEY = {"heading": "font_heading_weight", "body": "font_body_weight"}
SIZE_KEY = {"heading": "font_heading_size", "body": "font_body_size"}
TYPOGRAPHY_KEYS = tuple(
    k for role in ROLES for k in (FONT_KEY[role], WEIGHT_KEY[role], SIZE_KEY[role])
)

# Every @font-face the typography build writes (tools/build_fonts.py) uses
# this prefix, so a family a template already names ('Montserrat', 'Inter')
# can never resolve to one of the new files and change an existing render.
CSS_FAMILY_PREFIX = "CVT "

# §3: headlines are heavy, details are light.
WEIGHT_RANGE = {"heading": (700, 900), "body": (200, 400)}

# Details text the TEMPLATE set bold (a job title at 900, a company at 600)
# keeps its emphasis under a chosen Details font: it renders in that family's
# real 700, not at the chosen light weight. Not a user choice - it is never in
# a dropdown - but it is a built face for every Details family, so nothing is
# synthesised (hard rule 1). EMPHASIS_FROM is the template weight at which
# text counts as emphasis.
EMPHASIS_WEIGHT = 700
EMPHASIS_FROM = 600

# §4 derived size: section titles = clamp(name size x 0.42, lo, hi) pt.
SECTION_RATIO = 0.42
SECTION_CLAMP_PT = {"en": (11, 18), "ar": (12, 20)}

# §3.5 light-weight hint: Details at weight 200 below this size (pt) may print
# faint. Informational only.
LIGHT_WEIGHT = 200
LIGHT_WARNING_PT = {"en": 10, "ar": 11}

# Eight Arabic families stop at Latin-1 upstream (measured, build.json
# `latin_ext`), so a rare Latin letter (Ł, ř, Ş) needs a Latin family that has
# it. Chosen by the family's generic, and built at every weight 200-900 so the
# fallback never has to synthesise either. Loaded by the browser only when a
# glyph actually falls through.
LATIN_EXT_FALLBACK = {"sans-serif": "Work Sans", "serif": "Source Serif 4"}

# Dropdown group keys (§3.5). Display text belongs to the label catalogue.
SANS, SERIF, DISPLAY = "sans", "serif", "display"
KUFI, NASKH, CALLIGRAPHIC, STYLISED = "kufi", "naskh", "calligraphic", "stylised"
PLAYFUL = "playful"

# §3.5 <optgroup> order per language, and each group's label (an English msgid,
# translated by the builder's T(); Arabic in labels._UI_AR).
GROUP_ORDER = {"en": (SANS, SERIF, DISPLAY),
               "ar": (KUFI, STYLISED, NASKH, CALLIGRAPHIC, PLAYFUL)}
GROUP_LABEL = {SANS: "Sans", SERIF: "Serif", DISPLAY: "Display",
               KUFI: "Kufi / Sans", STYLISED: "Modern / stylised", NASKH: "Naskh",
               CALLIGRAPHIC: "Calligraphic", PLAYFUL: "Display / Playful"}

# Weight names as the dropdown shows them ("800 — ExtraBold"). msgids too.
WEIGHT_LABEL = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
                500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold",
                900: "Black"}


@dataclass(frozen=True)
class Font:
    family: str
    weights: tuple[int, ...]   # every weight the font ships
    category: str              # dropdown group key
    generic: str = "sans-serif"
    playful: bool = False      # §3.5 "Creative, best for design/creative roles"

    @property
    def slug(self) -> str:
        return self.family.lower().replace(" ", "-")


def _span(lo: int, hi: int) -> tuple[int, ...]:
    return tuple(range(lo, hi + 1, 100))


FONTS: dict[str, Font] = {f.family: f for f in (
    # ---- English -------------------------------------------------------
    Font("Anton", (400,), DISPLAY),
    Font("Anton SC", (400,), DISPLAY),
    Font("Archivo", _span(100, 900), SANS),
    Font("Archivo Black", (400,), DISPLAY),
    Font("Bebas Neue", (400,), DISPLAY),
    Font("Montserrat", _span(100, 900), SANS),
    Font("Raleway", _span(100, 900), SANS),
    Font("Playfair Display", _span(400, 900), SERIF, "serif"),
    Font("Source Serif 4", _span(200, 900), SERIF, "serif"),
    Font("Work Sans", _span(100, 900), SANS),
    Font("Poppins", _span(100, 900), SANS),
    Font("Inter", _span(100, 900), SANS),
    Font("Lora", _span(400, 700), SERIF, "serif"),
    # ---- Arabic --------------------------------------------------------
    Font("Tajawal", (200, 300, 400, 500, 700, 800, 900), KUFI),
    Font("Cairo", _span(200, 900), KUFI),
    Font("Almarai", (300, 400, 700, 800), KUFI),
    Font("Alexandria", _span(100, 900), KUFI),
    Font("Noto Kufi Arabic", _span(100, 900), KUFI),
    Font("Mada", _span(200, 900), KUFI),
    Font("Readex Pro", _span(200, 700), KUFI),
    Font("IBM Plex Sans Arabic", _span(100, 700), KUFI),
    Font("Noto Sans Arabic", _span(100, 900), KUFI),
    Font("El Messiri", _span(400, 700), STYLISED),
    Font("Noto Naskh Arabic", _span(400, 700), NASKH, "serif"),
    Font("Markazi Text", _span(400, 700), NASKH, "serif"),
    Font("Scheherazade New", _span(400, 700), NASKH, "serif"),
    Font("Lateef", _span(200, 800), NASKH, "serif"),
    Font("Amiri", (400, 700), NASKH, "serif"),
    Font("Aref Ruqaa", (400, 700), CALLIGRAPHIC, "serif"),
    Font("Lalezar", (400,), PLAYFUL, playful=True),
    Font("Jomhuria", (400,), PLAYFUL, playful=True),
    Font("Rakkas", (400,), PLAYFUL, playful=True),
    Font("Marhey", _span(300, 700), PLAYFUL, playful=True),
    Font("Baloo Bhaijaan 2", _span(400, 800), PLAYFUL, playful=True),
    Font("Lemonada", _span(300, 700), PLAYFUL, playful=True),
)}

# Which families each dropdown lists, in the spec's order (§3.1-3.4).
OFFERED: dict[tuple[str, str], tuple[str, ...]] = {
    ("en", "heading"): ("Anton", "Anton SC", "Archivo", "Archivo Black", "Bebas Neue",
                        "Montserrat", "Raleway", "Playfair Display", "Source Serif 4",
                        "Work Sans"),
    ("en", "body"): ("Poppins", "Montserrat", "Inter", "Lora", "Source Serif 4",
                     "Work Sans", "Archivo"),
    ("ar", "heading"): ("Tajawal", "Cairo", "Almarai", "Alexandria", "Noto Kufi Arabic",
                        "Mada", "Readex Pro", "El Messiri", "Noto Naskh Arabic",
                        "Markazi Text", "Scheherazade New", "Lateef", "Aref Ruqaa",
                        "Lalezar", "Jomhuria", "Rakkas", "Marhey", "Baloo Bhaijaan 2",
                        "Lemonada"),
    ("ar", "body"): ("Markazi Text", "Noto Naskh Arabic", "Readex Pro", "Amiri",
                     "Scheherazade New", "Noto Kufi Arabic", "IBM Plex Sans Arabic",
                     "Noto Sans Arabic", "Lateef", "Mada", "Baloo Bhaijaan 2", "Tajawal",
                     "Cairo", "Alexandria", "El Messiri"),
}


@dataclass(frozen=True)
class SizeScale:
    """A dropdown of point sizes: min..max in `step` increments (§4).

    The grid check is "an exact whole number of steps", never float equality.
    Every step is a power of two (0.5, 2), so `size / step` is computed
    exactly in binary floating point and `.is_integer()` is a true test:
    9.5 / 0.5 == 19.0, while 9.7 / 0.5 == 19.4. A test pins the power-of-two
    property, because a 0.1 step would silently break it."""
    min: float
    max: float
    step: float
    default: float

    def options(self) -> tuple[float, ...]:
        n = int((self.max - self.min) / self.step)
        return tuple(self.min + i * self.step for i in range(n + 1))

    def allows(self, size: float) -> bool:
        return self.min <= size <= self.max and (size / self.step).is_integer()


SIZES: dict[tuple[str, str], SizeScale] = {
    ("en", "heading"): SizeScale(24, 44, 2, 32),
    ("en", "body"): SizeScale(9, 12, 0.5, 10),
    ("ar", "heading"): SizeScale(26, 48, 2, 34),
    ("ar", "body"): SizeScale(10, 14, 0.5, 11.5),
}


def fonts_for(lang: str, role: str) -> tuple[Font, ...]:
    return tuple(FONTS[f] for f in OFFERED[(lang, role)])


def is_offered(lang: str, role: str, family: str) -> bool:
    return family in OFFERED.get((lang, role), ())


def offered_weights(lang: str, role: str, family: str) -> tuple[int, ...]:
    """(role range) ∩ (weights the font has); if empty, the single nearest
    weight — e.g. Anton's only 400 in a 700-900 headline slot (§3)."""
    if not is_offered(lang, role, family):
        return ()
    lo, hi = WEIGHT_RANGE[role]
    have = FONTS[family].weights
    inside = tuple(w for w in have if lo <= w <= hi)
    if inside:
        return inside
    return (min(have, key=lambda w: (min(abs(w - lo), abs(w - hi)), w)),)


def is_single_weight(lang: str, role: str, family: str) -> bool:
    """Only one choice exists, so the builder shows the weight dropdown disabled."""
    return len(offered_weights(lang, role, family)) == 1


def nearest_weight(lang: str, role: str, family: str, wanted: int) -> int | None:
    """The offered weight closest to `wanted`, ties going heavier. Used when
    the font changes and the old weight should carry over (§3.5: Montserrat
    900 -> Almarai gives 800)."""
    weights = offered_weights(lang, role, family)
    if not weights:
        return None
    return min(weights, key=lambda w: (abs(w - wanted), -w))


def size_scale(lang: str, role: str) -> SizeScale:
    return SIZES[(lang, role)]


def built_weights(lang: str, role: str, family: str) -> tuple[int, ...]:
    """Every weight of `family` a document can request in this role: the
    offered ones, plus the emphasis face for Details (see EMPHASIS_WEIGHT)."""
    weights = set(offered_weights(lang, role, family))
    if weights and role == "body":
        weights.add(EMPHASIS_WEIGHT)
    return tuple(sorted(weights))
