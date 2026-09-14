"""App configuration. Single-user v1 — no DB, no auth."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The working data dir. Overridable so a test run (tests/e2e) can drive the
# real server against a throwaway directory instead of the user's live
# resume.json -- the browser suite autosaves on every keystroke.
DATA_DIR = Path(os.environ.get("CVSTAND_DATA_DIR") or (ROOT / "data"))
UPLOADS_DIR = DATA_DIR / "uploads"
WORD_MASTERS_DIR = ROOT / "word_masters"

# The one working resume for v1. Copied from sample_resume.json on first run.
RESUME_PATH = DATA_DIR / "resume.json"
SAMPLE_RESUME_PATH = ROOT / "data" / "sample_resume.json"

# The SHOWCASE samples, one per interface language. These are what the landing
# hero and the gallery cards render - a demonstration of the layout, not the
# user's own document - so they follow the reader's interface language. Keyed
# by the `ui_lang` cookie's value; see app/store.py::load_showcase.
SAMPLE_RESUME_PATHS = {
    "en": SAMPLE_RESUME_PATH,
    "ar": ROOT / "data" / "sample_resume_ar.json",
}

# Template catalogue + which are live lives in app/registry.py.
# DOCX master families (one per category) live under word_masters/.

MAX_UPLOAD_BYTES = 4 * 1024 * 1024  # 4 MB photo cap

# Does the SERVER keep the résumé?
#
# `RESUME_PATH` is one global file. That is exactly right for the tool this
# started as -- your machine, your résumé, no account to make -- and it is the
# single thing that cannot survive a public URL: two visitors would read and
# overwrite each other's document, with no bug anywhere in the code. It is not
# an authz gap that accounts would close; it is one file where there needs to
# be one per person.
#
# So the browser owns the résumé (localStorage) and the server became a pure
# render-and-export service: POST it a document, get a PDF or a .docx back,
# nothing kept. That works for any number of simultaneous visitors with no
# accounts at all -- and it means a person's CV never touches the server's
# disk, which is worth saying out loud in a market where it is a real concern.
#
# This flag keeps the old behaviour available for the local single-user
# workflow and for the browser suite, which is built on it:
#
#   1 (default)  /api/resume PUT, /api/template POST and GET /export/* work
#                against data/resume.json, as they always have
#   0            those refuse; the browser is the only store
#
# Set it to 0 for any deployment more than one person can reach.
class AmbiguousFlag(RuntimeError):
    """A deployment flag whose value does not clearly mean anything."""


def _flag(name: str, default: str) -> bool:
    """Read a 0/1 deployment flag, refusing anything ambiguous.

    `!= "0"` is the historical test, and it has a trap that is invisible until
    it has already cost you: `CVSTAND_SERVER_STORE=false` is TRUE. So is `no`,
    and so is `off`. An operator who types the word they mean gets the exact
    opposite of it, silently, on the one setting where being wrong means two
    visitors read and overwrite each other's résumé.

    Nothing in the app can detect that mistake later -- the wrong value is a
    perfectly valid configuration -- so it is refused at import, which is the
    only moment anyone is looking.
    """
    raw = os.environ.get(name)
    if raw is None or raw == "":
        raw = default
    value = raw.strip().lower()
    if value in ("0", "false", "no", "off"):
        return False
    if value in ("1", "true", "yes", "on"):
        return True
    raise AmbiguousFlag(
        f"{name}={raw!r} is not a yes/no value. Use 1 or 0 "
        f"(true/false/yes/no/on/off are also accepted). Refusing to guess: "
        f"for {name} the two answers are not equally safe."
    )


# Does the SERVER keep the résumé? See the long comment above. Set it to 0 for
# any deployment more than one person can reach.
SERVER_STORE = _flag("CVSTAND_SERVER_STORE", "1")


# The shipped placeholder. `app/__init__.py` refuses to start a DEPLOYMENT
# that still has it, because the session cookie now carries the signed-in
# user and a known signing key forges accounts. Named rather than repeated as
# a literal so the check and the default cannot drift apart.
DEFAULT_SECRET_KEY = "dev-only-not-secret"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    JSON_SORT_KEYS = False
