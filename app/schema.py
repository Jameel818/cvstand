"""Resume JSON Schema + validation.

The shape is the locked data model from
`design_handoff_resume_templates/README.md`. Both the HTML (Jinja2) and the
DOCX (docxtpl) renderers read exactly this dict, so it is the single contract
between the editor, the preview, and both exporters.

Notes from the handoff that the schema enforces or preserves:
- `achievements[].metric` is a STRING ("$4.1M", "95%", "2x") — formatting is
  the user's choice, never re-computed.
- `skills[].level` / `languages[].level` is a word, not only a number.
- Every optional field has a defined empty-value degrade path (see
  `normalize()` and the templates), so a missing field never 500s a render.
"""
from __future__ import annotations

import copy
from typing import Any

from jsonschema import Draft202012Validator

from .typography import clean_typography, migrate_typography
from .typography.registry import FONT_KEY, TYPOGRAPHY_KEYS

_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": {"type": "string"}}

RESUME_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Resume",
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "title"],
    "properties": {
        "name": _STR,
        "title": _STR,
        # Document language. OPTIONAL and absent-means-"en", so every resume
        # written before bilingual support stays valid and renders unchanged.
        # An enum rather than a free string: a typo here would silently fall
        # back to English layout, which is precisely the class of failure this
        # project keeps finding (a wrong render that raises nothing).
        "lang": {"type": "string", "enum": ["en", "ar"]},
        # Typography choices (docs/CVSTAND_FONT_CONTROLS.md §2). OPTIONAL;
        # null or absent means "template default". The schema checks the JSON
        # TYPE only — a wrong type is a 422. Whether a value is on the
        # registry's whitelist depends on `lang`, so that is `normalize()`'s
        # job, and it resets rather than refuses (app/typography/validate.py).
        # Weights are "number", not "integer": 800.5 is the right type and
        # simply not offered, so it is reset like any other off-list value.
        **{key: {"type": ["string" if key in FONT_KEY.values() else "number", "null"]}
           for key in TYPOGRAPHY_KEYS},
        "photo_url": _STR,
        "summary": _STR,
        # A short highlighted phrase inside the summary (the marker swipe in
        # editorial templates). Optional; templates that don't use it ignore it.
        "summary_highlight": _STR,
        "contact": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "email": _STR,
                "phone": _STR,
                "address": _STR,
                "site": _STR,
                "social": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "url"],
                        "properties": {"label": _STR, "url": _STR},
                    },
                },
            },
        },
        "achievements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["metric", "label"],
                "properties": {
                    "metric": _STR,  # STRING — keep formatting the user chose
                    "label": _STR,
                },
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["role"],
                "properties": {
                    "company": _STR,
                    "role": _STR,
                    "location": _STR,
                    "start": _STR,
                    "end": _STR,
                    "bullets": _STR_LIST,
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["degree"],
                "properties": {
                    "school": _STR,
                    "degree": _STR,
                    "start": _STR,
                    "end": _STR,
                    "gpa": _STR,
                    "bullets": _STR_LIST,
                },
            },
        },
        "recognition": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title"],
                "properties": {"title": _STR, "detail": _STR},
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "level"],
                "properties": {
                    "name": _STR,
                    "level": _STR,  # word: Expert / Advanced / Proficient / Foundational
                    # optional numeric 0-100 for bar/ring templates; dot-grid
                    # derives dots from `level` alone.
                    "percent": {"type": "integer", "minimum": 0, "maximum": 100},
                },
            },
        },
        "tools": _STR_LIST,
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "level"],
                "properties": {"name": _STR, "level": _STR},
            },
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name"],
                "properties": {
                    "name": _STR,
                    "title": _STR,
                    "phone": _STR,
                    "email": _STR,
                },
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(RESUME_SCHEMA)

# Dot-grid mapping — fixed and identical everywhere (brief, PART 1).
#
# The Arabic words map to the SAME counts rather than replacing anything, which
# is why bilingual support needs no data migration: `level` stays the free
# string the user typed, and an existing "Expert" keeps resolving exactly as it
# did. A résumé switched to Arabic simply starts producing Arabic level words,
# and both vocabularies resolve for the lifetime of the file.
LEVEL_DOTS = {
    # English
    "foundational": 2,
    "proficient": 3,
    "advanced": 4,
    "expert": 5,
    # Arabic — the words the builder offers under lang="ar"
    "أساسي": 2,
    "متمكن": 3,
    "متقدم": 4,
    "خبير": 5,
}
DOT_TOTAL = 5

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "ar")
_RTL_LANGS = frozenset({"ar"})


def lang_of(data: dict[str, Any]) -> str:
    """The document language, defaulting to English for anything unrecognised."""
    lang = (data.get("lang") or DEFAULT_LANG)
    lang = lang.strip().lower() if isinstance(lang, str) else DEFAULT_LANG
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def dir_of(data: dict[str, Any]) -> str:
    """The writing direction for a résumé: "rtl" or "ltr"."""
    return "rtl" if lang_of(data) in _RTL_LANGS else "ltr"


def typography_of(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The résumé's whitelisted typography for its own language, plus what had
    to be reset to reach it. See app/typography/validate.py."""
    return clean_typography(data, lang_of(data))


def typography_migrations(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Keys a pre-step-3c résumé must rewrite to keep its look (validate.py
    ::migrate_typography). Empty for anything saved since."""
    return migrate_typography(data, lang_of(data))[1]


class ResumeValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate(data: Any) -> None:
    """Raise ResumeValidationError with every problem found, or return None."""
    errs = sorted(_VALIDATOR.iter_errors(data), key=lambda e: list(e.path))
    if errs:
        raise ResumeValidationError(
            [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in errs]
        )


def dots_for(level: str) -> int:
    """Filled-dot count for a skill level word. Unknown -> 0 (renders as text only)."""
    return LEVEL_DOTS.get((level or "").strip().lower(), 0)


_EMPTY: dict[str, Any] = {
    "photo_url": "",
    "summary": "",
    "summary_highlight": "",
    "contact": {},
    "achievements": [],
    "experience": [],
    "education": [],
    "recognition": [],
    "skills": [],
    "tools": [],
    "languages": [],
    "references": [],
}


def _blank_for(spec: dict[str, Any]) -> Any:
    """The empty value a template can safely read for one schema property.

    Numeric properties are deliberately absent from the result. `percent` is the
    only one, and the macros already read it as `skill.get('percent')` — the one
    field with an explicit guard — because "no percent given" and "0%" have to
    stay distinguishable. Defaulting it would erase that distinction."""
    kind = spec.get("type")
    if kind == "array":
        return []
    if kind == "object":
        return {}
    return "" if kind == "string" else None


def _entry_blanks(item: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for name, spec in item.get("properties", {}).items():
        blank = _blank_for(spec)
        if blank is not None:
            out[name] = blank
    return out


# Per-entry defaults derived from the schema itself, so adding a field there can
# never leave `normalize()` behind (see the regression note in `normalize`).
_LIST_BLANKS: dict[str, dict[str, Any]] = {
    key: _entry_blanks(spec["items"])
    for key, spec in RESUME_SCHEMA["properties"].items()
    if spec.get("type") == "array" and spec.get("items", {}).get("type") == "object"
}
_CONTACT_BLANKS: dict[str, Any] = _entry_blanks(RESUME_SCHEMA["properties"]["contact"])
_SOCIAL_BLANKS: dict[str, Any] = _entry_blanks(
    RESUME_SCHEMA["properties"]["contact"]["properties"]["social"]["items"])


def _fill(entry: dict[str, Any], blanks: dict[str, Any]) -> None:
    if not isinstance(entry, dict):
        return
    for key, blank in blanks.items():
        entry.setdefault(key, copy.deepcopy(blank))


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with every optional key present and defaulted, so a
    template can iterate/read any field without a guard. Also caps the stat-chip
    row at 4 and drops chips whose metric is blank (Scope Section Spec).

    REGRESSION (2026-09-04). This used to default only `bullets`, so it did not
    honour the contract above — and the Jinja env runs `StrictUndefined`. The
    builder's "+ Add role" pushes `{bullets: []}`; the moment the user typed the
    job title (making it schema-valid, since only `role` is required) the entry
    reached a template that reads `job.start`, and `/api/render` answered 500.
    Adding a role and naming it is the most ordinary edit there is. The blanks
    are now derived from RESUME_SCHEMA rather than listed by hand, so a new
    optional field cannot reintroduce this."""
    out = copy.deepcopy(_EMPTY)
    out.update(copy.deepcopy(data))
    out.setdefault("name", "")
    out.setdefault("title", "")
    # Derived, like `dots` below: templates read r.lang / r.dir directly, and
    # StrictUndefined means anything they read must always be present.
    out["lang"] = lang_of(out)
    out["dir"] = dir_of(out)
    # All six typography keys, always present (None = template default), and
    # only ever registry values for THIS language — never the raw input.
    out.update(typography_of(out)[0])

    contact = out.get("contact") or {}
    _fill(contact, _CONTACT_BLANKS)
    out["contact"] = contact
    for social in contact["social"]:
        _fill(social, _SOCIAL_BLANKS)

    out["achievements"] = [
        a for a in out.get("achievements", []) if (a.get("metric") or "").strip()
    ][:4]

    for key, blanks in _LIST_BLANKS.items():
        for entry in out.get(key, []) or []:
            _fill(entry, blanks)

    for sk in out.get("skills", []):
        sk["dots"] = dots_for(sk.get("level", ""))
        sk["dot_total"] = DOT_TOTAL

    return out
