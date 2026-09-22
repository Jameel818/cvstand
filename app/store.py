"""The single working resume, persisted as one JSON file (v1, no DB).

On first read, seeds from the sample matching the reader's interface
language (data/sample_resume.json for English) — see load_resume, which only
persists that seed where the server is the store.
Selection state (chosen template) lives in a separate data/meta.json so the
resume file stays a clean instance of the locked schema.
"""
from __future__ import annotations

import json
from typing import Any

from functools import lru_cache

from . import registry
from .config import (
    RESUME_PATH,
    SAMPLE_RESUME_PATH,
    SAMPLE_RESUME_PATHS,
    SERVER_STORE,
)

_META_PATH = RESUME_PATH.parent / "meta.json"


def _read_json(path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    tmp.replace(path)


def seed_resume(lang: str = "en") -> dict[str, Any]:
    """The sample a visitor with no document of their own starts from.

    A pure read of a repo file, keyed by the READER's interface language. No
    disk write: see load_resume for why that matters.

    An unknown language falls back to English rather than raising — the same
    degrade rule `load_showcase` follows, and for the same reason: the value
    comes from a user-editable cookie.
    """
    return _read_json(SAMPLE_RESUME_PATHS.get(lang, SAMPLE_RESUME_PATH))


def load_resume(seed_lang: str = "en") -> dict[str, Any]:
    """The user's OWN résumé, seeded in the reader's language when there is none.

    `seed_lang` applies at exactly one moment — when no document exists yet —
    and never to one that does. An existing document's language is a property
    of the document (app/i18n.py) and no cookie may overwrite it; that is what
    `tests/test_showcase_language.py` and the phase-6 tests protect, and
    nothing here weakens it.

    WHY THE SEED IS THE EXCEPTION

        A new résumé has no language of its own to respect yet. Seeding it
        from the English sample regardless of the interface meant an Arabic
        visitor opened the builder onto an English document and had to find
        `Résumé language` in Basics to fix it — a control they may never
        notice, and whose purpose is not obvious if they do. The default now
        follows the choice they already made in the header.

        Session 24 declined to default `lang` from the interface, and was
        right to: stamping `lang: "ar"` onto the ENGLISH sample's text renders
        worse than leaving it absent. That objection was about the sample, not
        the principle. Seeding from the Arabic sample carries Arabic text AND
        `lang: "ar"` together, so the pair stays consistent.

    WHY `SERVER_STORE=0` NEITHER READS NOR WRITES THE FILE

        There the browser owns the résumé (app/config.py) and nothing may
        write `resume.json`: `PUT /api/resume` refuses, the exports take the
        document in the body. So the file can only ever hold a leftover — and
        reading one means handing whatever some earlier visitor's request left
        behind to everybody who arrives after, which is the leak
        `tests/test_stateless.py` exists to make unreachable.

        That is not hypothetical, and it is the bug reported from production
        on 2026-09-22. Seeding used to WRITE, so the language of the first
        request to reach the container became everyone's: an Arabic reader got
        the English builder and no amount of switching the header changed it,
        because by then the file existed. Measured on the live site the same
        day — shell `dir="rtl"`, document "Wren Ashworth".

        Not reading it is what makes the fix arrive on its own. `/data` is a
        PERSISTENT VOLUME (DEPLOY.md §C3, for the accounts DB), so the stale
        file outlives every deploy; a version that stopped writing but still
        read would ship green and change nothing anyone could see, and would
        need a manual file deletion on the volume that nothing in the repo
        would ever remind you to do again.

        It was invisible in both places you would look. Locally you ARE the
        first visitor and the language is yours; and one request passes either
        way — the bug needs two. `tests/test_builder_seed_language.py`.

    Where the server IS the store, none of that applies: `data/resume.json` is
    the user's own document on their own machine, it must win over the seed,
    and the seed must land on disk so it survives a restart.
    """
    if SERVER_STORE:
        if RESUME_PATH.exists():
            return _read_json(RESUME_PATH)
        data = seed_resume(seed_lang)
        _write_json(RESUME_PATH, data)
        return data
    return seed_resume(seed_lang)


def save_resume(data: dict[str, Any]) -> None:
    _write_json(RESUME_PATH, data)


@lru_cache(maxsize=len(SAMPLE_RESUME_PATHS))
def _sample_text(lang: str) -> str:
    """The raw JSON of a showcase sample, read once per process.

    Cached as TEXT rather than as a parsed dict on purpose: a gallery page
    issues one /preview request per card, so this is read ~49 times per load,
    and handing every caller the same dict would let one of them mutate the
    copy the next 48 receive. Re-parsing 3KB is cheaper than that class of bug.
    These are repo files, not user data, so they cannot change under the cache.
    """
    return SAMPLE_RESUME_PATHS[lang].read_text(encoding="utf-8")


def load_showcase(lang: str) -> dict[str, Any]:
    """The résumé the LANDING HERO and the GALLERY CARDS render.

    Not `load_resume()`. Those two surfaces are a demonstration of what a
    layout looks like, so they follow the READER's interface language: an
    Arabic visitor should see Arabic résumés on the landing page even though
    the document sitting in `data/resume.json` is English, and vice versa.

    Everything else - the builder's live preview and the template drawer -
    deliberately keeps rendering `load_resume()`, because there you are
    choosing a layout for YOUR OWN content and stock text would be a lie.

    An unknown language falls back to English rather than raising: this is a
    presentational choice driven by a user-editable cookie, and the same
    degrade rule the label catalogue follows.
    """
    if lang not in SAMPLE_RESUME_PATHS:
        lang = "en"
    return json.loads(_sample_text(lang))


def load_meta() -> dict[str, Any]:
    default = registry.default_key()
    if not _META_PATH.exists():
        return {"template_key": default}
    meta = _read_json(_META_PATH)
    key = meta.get("template_key")
    tpl = registry.get(key) if key else None
    if tpl is None or not tpl.ported:
        meta["template_key"] = default
    return meta


def set_template(template_key: str) -> None:
    meta = load_meta()
    meta["template_key"] = template_key
    _write_json(_META_PATH, meta)
