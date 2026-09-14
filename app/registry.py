"""Template registry — the catalogue behind the gallery and the builder.

Two categories:
  - "modern"  -> ported from `Resume Templates Coded.dc.html`      (t1..t24)
  - "ats"     -> ported from `ATS Resume Templates Coded.dc.html`  (t1..t25)

A template KEY is "<category>-<block>", e.g. "modern-t1", "ats-t3". Block ids
collide across the two source files, so the category prefix disambiguates.
The Jinja file for a key lives at `app/templates/resumes/<category>/<block>.j2`.

`ported=True` means the .j2 exists and the template is live in the app. The
rest are catalogued (title/blurb known) but not yet selectable — the gallery
shows them greyed with a "coming soon" ribbon so the roadmap is visible.

DOCX: each category maps to one Word-master family (the ~4-master Word-safe
set becomes 2 families — one per category — since ATS masters are genuinely
single-column and Modern masters carry the sidebar).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Template:
    key: str
    category: str          # "modern" | "ats"
    block: str             # "t1".."t25" — the id in the source .dc.html
    label: str             # short human name
    blurb: str             # one line for the gallery card
    skill_pattern: str     # "dot-grid" | "bars" | "rings" | "inline"
    accent: str            # representative hex, for the gallery card chip
    ported: bool = False
    docx_master: str = ""  # filename under word_masters/, "" until authored
    tags: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------
# MODERN — colour, two-column, photo-capable. Source: Resume Templates Coded.dc.html
# --------------------------------------------------------------------------
_MODERN = [
    ("t1",  "Editorial Redline",   "Pure white, hairlines only, chartreuse redline marker", "dot-grid", "#D8F035"),
    ("t2",  "Navy & Gold",         "Navy sidebar with a gold band, numeric skill bars",     "bars",     "#C8A24A"),
    ("t3",  "Yellow Photo Rail",   "Heavy display heads over a yellow photo rail",          "bars",     "#F2C200"),
    ("t4",  "Ribbon Sidebar",      "Ribbon-header sidebar, references block, dot levels",    "dot-grid", "#3A6B5C"),
    ("t5",  "Rounded Dark",        "Rounded dark sidebar, black pill headers, coral sliders","bars",    "#FF6F5E"),
    ("t6",  "Centred Symmetric",   "Centred header, symmetric two-column body, bar levels",  "bars",     "#2B6CB0"),
    ("t7",  "Poster Band",         "Poster masthead over a two-tone body, early-career",     "bars",     "#E4572E"),
    ("t8",  "Interlocking Blocks", "Navy and pale-blue interlocking blocks, dot-grid levels", "dot-grid", "#003366"),
    ("t9",  "Boxed Sections",      "Yellow boxed-section rail with boxed entries",           "bars",     "#F2C200"),
    ("t10", "FinTech Elite",       "Editorial sidebar tuned for finance leadership",         "bars",     "#A93005"),
    ("t11", "Colour Header Rail",  "Photo rail plus a colour header block, dot levels",      "dot-grid", "#2F855A"),
    ("t12", "Typographic Mono",    "Full-bleed typographic mono with ring skill diagrams",   "rings",    "#111111"),  # single-tone: ink on #f7f7f5
    ("t13", "Band Timeline",       "Colour band over a single-column timeline, finance",     "dot-grid", "#2B6CB0"),
    ("t14", "Offset Plaque",       "Offset plaque with flag headers, graphic-design",        "dot-grid", "#B83280"),
    ("t15", "Forest & Amber",      "Forest sidebar, amber band, seam photo, skill bars",     "bars",     "#2F855A"),
    ("t16", "Charcoal Rings",      "Charcoal rail with a ring cluster, circular levels",     "rings",    "#A32638"),
    ("t17", "Two-Tone Ribbon",     "Two-tone ribbon banners, photo top-right",               "rings",    "#003366"),
    ("t18", "Interlocking Block",  "Interlocking two-tone block with a straddling photo",    "bars",     "#002B66"),
    ("t19", "Label Gutter",        "Label-gutter editorial, product management",             "bars",     "#6B2A5A"),
    ("t20", "Cotton & Cherry",     "Cotton sidebar, cherry rail, dot-grid expertise",        "dot-grid", "#810100"),
    ("t21", "Rounded Card Shell",  "Rounded card shell with pill headers, dot levels",       "dot-grid", "#013F32"),
    ("t22", "Vertical Rail Rings", "Vertical RESUME rail, bold type, circular rings",        "rings",    "#CB3500"),
    ("t23", "Spine Timeline",      "Spine timeline with pill tags, software engineering",     "bars",     "#3182CE"),
    ("t24", "Hard-Edged Sidebar",  "Hard-edged sidebar, block headers, gold skill rings",    "rings",    "#FFD633"),
]

# --------------------------------------------------------------------------
# ATS — strictly single column, parse-safe. Source: ATS Resume Templates Coded.dc.html
# --------------------------------------------------------------------------
_ATS = [
    ("t1",  "Tech Lead",          "Signal blue, rule-to-margin heads, dot-grid levels",     "dot-grid", "#2563EB"),
    ("t2",  "Data Scientist",     "Teal accent, grouped skill levels, metric lines",        "inline",   "#0D9488"),
    ("t3",  "Portal Standard",    "The safest single column — dot-grid levels, plain rules","dot-grid", "#334155"),
    ("t4",  "Editorial Redline",  "Pure white, redline marker, ATS-safe port of Modern 1",  "dot-grid", "#D8F035"),
    ("t5",  "Sectioned Plum",     "Sectioned editorial, plum accent, bar levels",           "bars",     "#7C3AED"),
    ("t6",  "Rule Stack",         "Steel accent, hairline sections, quiet structure",       "inline",   "#475569"),
    ("t7",  "Accent Band",        "Full-width navy masthead over a linear body",            "inline",   "#1E3A5F"),
    ("t8",  "Big Type",           "No rules — space-only structure, inline skill run",      "inline",   "#C0392B"),
    ("t9",  "Ledger",             "Double rules, tabular dates, serif masthead",            "inline",   "#1A1A1A"),
    ("t10", "Marker",             "Pure white, hairlines only, one highlight swipe",        "dot-grid", "#FDE047"),
    ("t11", "Caps Tick",          "Teal accent, tick-marked section labels",                "dot-grid", "#0D9488"),
    ("t12", "Serif Executive",    "Ink only, executive register, generous leading",         "inline",   "#1A1A1A"),
    ("t13", "Mono Tech",          "Monospace labels, signal blue, engineering register",    "dot-grid", "#2563EB"),
    ("t14", "Numbered",           "Numbered sections, rust accent, flush-left",             "inline",   "#B45309"),
    ("t15", "Split Rule",         "Plum accent, label-then-rule section heads",             "bars",     "#7C3AED"),
    ("t16", "Fraunces Stack",     "Fraunces masthead, terracotta accent, double-rule heads","inline",   "#C2410C"),
    ("t17", "Wide Caps",          "Anton masthead, forest accent, hairline-only",           "inline",   "#166534"),
    ("t18", "Indent Rule",        "Indigo accent, left border marking each section",        "dot-grid", "#4F46E5"),
    ("t19", "Ochre Ledger",       "Mono dates, right-hand rule column, warm neutral",       "inline",   "#B45309"),
    ("t20", "Centred Serif",      "Burgundy accent, centred masthead, quiet register",      "inline",   "#8B1E3F"),
    ("t21", "Mono Label",         "Cyan on slate, monospace headings, engineering",         "dot-grid", "#06B6D4"),
    ("t22", "Accent Bar",         "One full-bleed crimson band, Archivo black masthead",    "inline",   "#DC2626"),
    ("t23", "Open Air",           "Teal accent, no rules at all, space-only structure",     "inline",   "#0F6E63"),
    ("t24", "Narrow Two-Tone",    "Olive accent, condensed type, tight rules",              "bars",     "#4D7C0F"),
    ("t25", "Dense Career",       "Steel blue, built for long multi-role histories",        "inline",   "#3B6EA5"),
]

_PORTED = {
    "modern-t1", "modern-t2", "modern-t3", "modern-t4", "modern-t5", "modern-t6",
    "modern-t7", "modern-t8", "modern-t9", "modern-t11", "modern-t14", "modern-t15",
    "modern-t10", "modern-t12", "modern-t13", "modern-t23", "modern-t16", "modern-t17", "modern-t18",
    "modern-t19", "modern-t20", "modern-t21", "modern-t22", "modern-t24",
    "ats-t1", "ats-t2", "ats-t3", "ats-t4", "ats-t5", "ats-t6", "ats-t7",
    "ats-t8", "ats-t9", "ats-t10", "ats-t11", "ats-t12", "ats-t13", "ats-t14", "ats-t15",
    "ats-t16", "ats-t17", "ats-t18", "ats-t19", "ats-t20", "ats-t21",
    "ats-t22", "ats-t23", "ats-t24", "ats-t25",
}  # complete — all 49 catalogued layouts are ported


def _build() -> "dict[str, Template]":
    out: dict[str, Template] = {}
    for cat, rows in (("modern", _MODERN), ("ats", _ATS)):
        for block, label, blurb, pattern, accent in rows:
            key = f"{cat}-{block}"
            out[key] = Template(
                key=key,
                category=cat,
                block=block,
                label=label,
                blurb=blurb,
                skill_pattern=pattern,
                accent=accent.replace(" ", ""),
                ported=key in _PORTED,
                docx_master="ats_standard.docx" if cat == "ats" else "modern_editorial.docx",
            )
    return out


TEMPLATES: "dict[str, Template]" = _build()

CATEGORIES = (
    {"id": "modern", "label": "Modern", "tagline": "Colour, structure, personality. Best as a PDF."},
    {"id": "ats", "label": "ATS-Friendly", "tagline": "Single column, parse-safe. Best for job portals."},
)


def get(key: str) -> Template | None:
    return TEMPLATES.get(key)


def ported_keys() -> list[str]:
    return [k for k, t in TEMPLATES.items() if t.ported]


def by_category(category: str | None = None) -> list[Template]:
    vals = list(TEMPLATES.values())
    if category:
        vals = [t for t in vals if t.category == category]
    return sorted(vals, key=lambda t: (0 if t.ported else 1, t.category, int(t.block[1:])))


def default_key() -> str:
    pk = ported_keys()
    return pk[0] if pk else "modern-t1"
