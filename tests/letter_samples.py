"""Cover-letter fixtures shared by the fast and the browser tests.

LONGEST is the most the builder's form lets a user type - every field at its
schema cap, the maximum number of paragraphs, each at its cap - in words
rather than one repeated letter, because a run of "xxxx" wraps nothing like
prose. It is what proves "the letter is one page" for every template.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from app import schema

ROOT = Path(__file__).resolve().parent.parent
EN_WORDS = ("We built the brand system that four product lines now share, wrote the "
            "rules that kept two hundred assets consistent, and trained the team to own "
            "it after the launch. ")
AR_WORDS = ("بنينا نظام الهوية الذي تتشاركه أربعة خطوط منتجات، وكتبنا القواعد التي حافظت "
            "على اتساق مئتي مادة، ودرّبنا الفريق على إدارته بعد الإطلاق. ")


def _fill(words: str, n: int) -> str:
    out = (words * (n // len(words) + 2))[:n]
    return out.rsplit(" ", 1)[0] if " " in out[-12:] else out


def resume(lang: str) -> dict:
    name = "demo_resume_ar.json" if lang == "ar" else "demo_resume.json"
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def demo_letter(lang: str) -> dict:
    name = "demo_letter_ar.json" if lang == "ar" else "demo_letter.json"
    cl = json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
    cl["date"] = "18 October 2026" if lang == "en" else "١٨ أكتوبر ٢٠٢٦"
    return cl


def with_letter(lang: str, letter: dict | None = None) -> dict:
    d = resume(lang)
    d["cover_letter"] = copy.deepcopy(letter if letter is not None else demo_letter(lang))
    return d


def longest(lang: str) -> dict:
    w = AR_WORDS if lang == "ar" else EN_WORDS
    f, a = schema.LETTER_FIELD_MAX, schema.LETTER_ADDRESS_MAX
    return {
        "enabled": True,
        "recipient_name": _fill(w, f), "recipient_title": _fill(w, f), "company": _fill(w, f),
        "company_address": _fill(w, a), "date": _fill(w, f), "subject": _fill(w, f),
        "greeting": _fill(w, f),
        "paragraphs": [_fill(w, schema.LETTER_PARAGRAPH_MAX)] * schema.LETTER_MAX_PARAGRAPHS,
        "closing": _fill(w, f), "signature": _fill(w, 40),
    }
