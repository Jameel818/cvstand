"""Download file names: the person's real name, in any script.

Until 2026-10 both the server (werkzeug's secure_filename) and the builder
(`[^\\w\\-]` in builder.js) kept ASCII letters only, so an Arabic name
downloaded as "_.pdf" / "_cover_letter.pdf". Now:

    ليلى خليل        -> ليلى_خليل.pdf
    Wren Ashworth   -> Wren_Ashworth.pdf          (the header, as werkzeug sent it;
                                                   the builder lower-cases, as it did)
    letter / both   -> <name>_cover_letter.pdf / <name>_cv_and_cover_letter.pdf

What is removed is exactly what Windows or macOS refuse in a file name:
< > : " / \\ | ? * and control characters, a leading dot, trailing dots and
spaces, and the reserved Windows device names (CON, NUL, COM1...). Runs of
spaces become one "_". Nothing else is touched - an Arabic, Cyrillic or
accented name keeps every letter.

Old browsers read only the plain `filename=` parameter, which must be ASCII:
it carries a transliteration when one exists (José -> jose) and "resume"
otherwise. Every current browser reads `filename*=UTF-8''...` (RFC 6266 /
RFC 5987) and gets the real name. The builder downloads through fetch() and
reads the same header (static/js/builder.js), so both paths agree.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

SUFFIX = {"cv": "", "letter": "_cover_letter", "both": "_cv_and_cover_letter"}
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f‎‏‪-‮⁦-⁩]')
_RESERVED = re.compile(r"(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\..*)?", re.IGNORECASE)
#: a long name stays well inside every file system's 255-byte limit
MAX_CHARS = 80
FALLBACK = "resume"


def base_name(name: str | None) -> str:
    """The person's name as a safe file-name stem ("resume" when nothing is left)."""
    s = unicodedata.normalize("NFC", (name or "").strip())
    s = _FORBIDDEN.sub(" ", s)
    s = "_".join(s.split())
    s = s.strip(". _")[:MAX_CHARS].rstrip(". _")
    if not s or _RESERVED.fullmatch(s):
        return FALLBACK
    return s


def ascii_name(stem: str) -> str:
    """An ASCII stand-in for `stem` for old browsers: José -> jose; a name with
    no Latin letters at all -> "resume"."""
    s = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("._-")
    return s if re.search(r"[A-Za-z0-9]", s) else FALLBACK


def download_name(name: str | None, part: str, ext: str) -> str:
    return f"{base_name(name)}{SUFFIX[part]}.{ext}"


def content_disposition(name: str | None, part: str, ext: str) -> str:
    """`attachment; filename="<ascii>"; filename*=UTF-8''<real name>`."""
    real = download_name(name, part, ext)
    plain = f"{ascii_name(base_name(name))}{SUFFIX[part]}.{ext}"
    # unquoted when it is a plain token, as werkzeug wrote it before
    shown = plain if re.fullmatch(r"[A-Za-z0-9._-]+", plain) else f'"{plain}"'
    if real == plain:
        return f"attachment; filename={shown}"
    return f"attachment; filename={shown}; filename*=UTF-8''{quote(real, safe='')}"
