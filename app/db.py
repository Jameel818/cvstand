"""SQLite. The first persistent server-side state this project has ever had.

WHY A DATABASE AT ALL, WHEN THE BROWSER OWNS THE RÉSUMÉ

    It still does, and that does not change here. `data/resume.json` was one
    global file and the browser took over precisely because one file cannot
    serve two visitors (`app/config.py::SERVER_STORE`). The server remained a
    pure render-and-export service, and for the FREE tier it stays exactly
    that — no account, nothing stored, nothing to leak.

    What a database is for is the things you cannot sell without it: who has
    paid, until when, and — for the multi-résumé line in `MONETIZATION.md` §7
    — a place to keep more than one document per person. "Unlimited stored
    résumés" is not a feature if storage is the visitor's own localStorage,
    because that is already unlimited and already free.

    So: anonymous use touches none of this. The tables below exist only for
    people who make an account, which only happens when they buy something.

WHY sqlite3 AND NOT AN ORM

    The whole schema is two tables and one of them has four columns. An ORM
    would be more code to read than the SQL it hides. `MONETIZATION.md` §10.1
    says SQLite → Postgres when it matters; the `_connect()` seam below is
    where that swap happens, and keeping the queries as visible SQL is what
    makes the swap a small job rather than an archaeology exercise.

WHERE THE FILE LIVES

    `DATA_DIR`, which `CVSTAND_DATA_DIR` overrides — so the test session
    already points at a throwaway directory (`tests/conftest.py`) and gets an
    isolated database for free, the same way it gets an isolated résumé.
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Any, Iterable

from flask import g

from .config import DATA_DIR

DB_PATH = DATA_DIR / "cvstand.db"

# One schema statement per entry, applied in order and idempotent. This is
# deliberately NOT a migration framework: there is no production database yet,
# so there is nothing to migrate FROM. The moment one exists, this list is
# where a real migration tool replaces it — and that is a better time to
# choose one than now, when the choice would be uninformed.
_SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        email           TEXT    NOT NULL UNIQUE,
        password_hash   TEXT    NOT NULL,
        created_at      TEXT    NOT NULL,
        -- Bumped on password change so every existing session dies. The
        -- session cookie carries this number; a mismatch is a signed-out
        -- user. Without it, "I changed my password" does not evict whoever
        -- was already signed in as them, which is the one thing a password
        -- change is for.
        session_version INTEGER NOT NULL DEFAULT 1,
        -- Phase 2 fills this in. It is here from the start because a column
        -- that arrives with the feature that needs it is a migration; a
        -- column that is already there is an UPDATE.
        pass_expires_at TEXT
    )
    """,
    # Email is compared lower-cased everywhere (see auth.normalise_email), so
    # the UNIQUE constraint above is enough — but the index makes the lookup
    # on every sign-in an index seek rather than a scan.
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
)

_init_lock = threading.Lock()
_initialised = False

# Set by `execute()`. Only the test-reset path reads it — see
# `reset_for_tests`. Every write in this app goes through `execute()`; a
# future one that opens its own connection must set this too, or the wipe it
# needs will be skipped.
_dirty = False


def _connect() -> sqlite3.Connection:
    """A connection with the settings this app actually needs.

    `check_same_thread=False` because Flask serves requests on threads and the
    connection is stored per-request in `g`, never shared across one.

    **WAL matters here specifically.** Every `/export/pdf` launches a whole
    Chromium (`app/exporters/pdf.py`), so several requests can be in flight for
    seconds at a time. In SQLite's default rollback-journal mode a single
    writer blocks every reader; in WAL, readers and one writer proceed
    concurrently. Without it an entitlement check could sit behind somebody
    else's sign-up.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init() -> None:
    """Create the schema if it is not there. Safe to call repeatedly."""
    global _initialised
    with _init_lock:
        conn = _connect()
        try:
            for statement in _SCHEMA:
                conn.execute(statement)
            conn.commit()
        finally:
            conn.close()
        _initialised = True


def get() -> sqlite3.Connection:
    """The connection for this request, opened on first use and closed by the
    teardown registered in `register()`."""
    if not _initialised:
        init()
    conn = getattr(g, "_db", None)
    if conn is None:
        conn = g._db = _connect()
    return conn


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return get().execute(sql, tuple(params)).fetchall()


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    return get().execute(sql, tuple(params)).fetchone()


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    """Write and commit.

    Committing per statement rather than per request is the right default for
    this app: there is no multi-statement business operation yet, and an
    implicit transaction spanning a request would hold a write lock across a
    PDF render.
    """
    global _dirty
    conn = get()
    cur = conn.execute(sql, tuple(params))
    conn.commit()
    _dirty = True
    return cur


def close(_exc: BaseException | None = None) -> None:
    conn = g.pop("_db", None)
    if conn is not None:
        conn.close()


def register(app) -> None:
    app.teardown_appcontext(close)


_test_conn: sqlite3.Connection | None = None


def reset_for_tests() -> None:
    """Empty every table. For tests, which share one data dir per session.

    The suite already resets rate-limit buckets between tests for exactly this
    reason (`tests/conftest.py`) — module and file state outlives a Flask test
    client, and a fixture that leaks makes the NEXT test fail based on ORDER,
    which is the worst shape of flake to chase. A user row left behind would
    do the same to any test that signs up with the same address.

    **Holds ONE connection for the whole session, deliberately.** This runs
    autouse, twice per test, across ~1650 tests. The first cut opened two
    fresh connections per call — `init()` plus the wipe — and took the fast
    loop from 22s to 70s. The fast loop is what this project runs on every
    edit, so tripling it is not a rounding error; it is the difference between
    a test suite you run and one you skip. Connection setup was the whole cost
    (file open, WAL pragma, two CREATE TABLE statements), not the DELETE.
    """
    global _test_conn, _dirty
    # The overwhelming majority of this suite never touches the database at
    # all — it renders templates and measures geometry. A DELETE plus a commit
    # is an fsync, and paying it twice for each of ~1600 tests that wrote
    # nothing cost another 8 seconds of the fast loop on top of the connection
    # churn described above. Skipping the no-op case is what keeps this
    # fixture close to free.
    if not _dirty:
        return
    if _test_conn is None:
        init()
        _test_conn = _connect()
    _test_conn.execute("DELETE FROM users")
    _test_conn.commit()
    _dirty = False
