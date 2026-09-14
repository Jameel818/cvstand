"""Accounts and sessions. Password sign-in, chosen 2026-09-11.

**Anonymous use is not affected by anything in this file.** All 49 templates,
unlimited PDF, both languages and the whole builder work with no account, and
that stays true — it is an acquisition asset in a market saturated with free
(`MONETIZATION.md` §6), not an oversight waiting to be closed. An account is
what you make when you BUY something, and nothing else requires one.

WHY PASSWORDS AND NOT A MAGIC LINK

    A magic link is nicer and needs an email provider, which is an external
    dependency this track was picked specifically to avoid. Passwords are
    self-contained. The cost is that password RESET also needs email — so
    there is no reset flow here, and that is a known gap written down rather
    than forgotten (see MISSING, below).

WHAT IS DELIBERATELY NOT HAND-ROLLED

    Hashing. `werkzeug.security` ships with Flask and defaults to scrypt with
    a per-password salt. Writing anything else here — a fast hash, a shared
    salt, a "clever" scheme — is how password databases become worthless the
    day they leak.

MISSING, ON PURPOSE, AND TRACKED

    * **Password reset.** Needs email. Until then a locked-out user has to be
      helped by hand. Acceptable while the only people with accounts are
      people who bought a 30-day pass.
    * **Email verification.** Same reason. The address is an identifier here,
      not a proven channel — so do not build anything that assumes mail sent
      to it arrives.
    * **Per-session revocation.** `session_version` evicts ALL of a user's
      sessions at once, which is what a password change needs. Signing out one
      device while leaving others is a session table, and there is no demand
      for it yet.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import wraps

from flask import g, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

SESSION_USER = "uid"
SESSION_VERSION = "sv"

# Length beats composition. Enforcing an uppercase-digit-symbol rule pushes
# people towards `Password1!` — memorably worse than a long passphrase — and
# current guidance has moved away from it. A floor with no character classes
# is the deliberate choice.
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256  # a bcrypt-style cap; also stops a 5MB hash request

# Not RFC 5322. A full-grammar regex is famously enormous and still accepts
# addresses no mail server will take, and this address is an IDENTIFIER, not a
# proven channel (see MISSING above) — so the only job here is to reject
# obvious nonsense and anything with whitespace or a comma that would make a
# later mail merge ambiguous.
_EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]{2,}$")


class AuthError(Exception):
    """Something the caller did wrong. The message is safe to show a user."""


def normalise_email(raw: str) -> str:
    """Lower-cased and stripped.

    Case-folding matters: without it `Ali@x.com` and `ali@x.com` are two
    accounts, one of which paid. The UNIQUE constraint in the schema only
    helps if everything that touches the column has been through here.
    """
    return (raw or "").strip().lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_credentials(email: str, password: str) -> str:
    """Check and return the normalised email, or raise `AuthError`."""
    email = normalise_email(email)
    if not email:
        raise AuthError("Enter your email address.")
    if not _EMAIL_RE.match(email):
        raise AuthError("That does not look like an email address.")
    if len(email) > 320:
        raise AuthError("That email address is too long.")
    if not password:
        raise AuthError("Choose a password.")
    if len(password) < MIN_PASSWORD_LENGTH:
        # A LITERAL, not an f-string. Every message raised here is a msgid
        # that the template looks up in the catalogue, and an interpolated
        # msgid never matches a catalogue key — it would silently render in
        # English for Arabic readers. `test_auth_messages_are_all_translated`
        # pins the number to MIN_PASSWORD_LENGTH.
        raise AuthError(
            "Use at least 10 characters — a short phrase is easier to "
            "remember and harder to guess than a short password."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise AuthError("That password is too long.")
    return email


def create_user(email: str, password: str) -> int:
    """Make an account. Returns the new user id."""
    email = validate_credentials(email, password)
    if db.query_one("SELECT id FROM users WHERE email = ?", (email,)):
        # Saying "that address is already registered" tells an unauthenticated
        # stranger who has an account here. That is a real disclosure, and it
        # is accepted rather than overlooked: hiding it means a sign-up form
        # that silently does nothing, which is worse for the far more common
        # case of a person who simply forgot they had registered.
        raise AuthError("There is already an account with that email.")
    cur = db.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (email, generate_password_hash(password), _now()),
    )
    return int(cur.lastrowid)


# A real hash of a value nobody can log in with. Verifying against this when
# the account does not exist keeps sign-in the same COST whether or not the
# address is registered — otherwise the response time tells an attacker which
# addresses have accounts, which is the disclosure the error message above
# deliberately accepts on sign-UP but should not leak silently on sign-IN.
_DUMMY_HASH = generate_password_hash("not-a-real-password-timing-equaliser")


def authenticate(email: str, password: str):
    """The user row for these credentials, or None. Constant-ish time."""
    row = db.query_one(
        "SELECT * FROM users WHERE email = ?", (normalise_email(email),)
    )
    if row is None:
        check_password_hash(_DUMMY_HASH, password or "")
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None
    return row


def sign_in(row) -> None:
    session.clear()
    session[SESSION_USER] = int(row["id"])
    session[SESSION_VERSION] = int(row["session_version"])
    session.permanent = True


def sign_out() -> None:
    session.clear()
    g.pop("_current_user", None)


def change_password(user_id: int, new_password: str) -> None:
    """Set a new password and evict every existing session for that user."""
    if len(new_password or "") < MIN_PASSWORD_LENGTH:
        raise AuthError("Use at least 10 characters.")
    db.execute(
        "UPDATE users SET password_hash = ?, session_version = session_version + 1 "
        "WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )


def current_user():
    """The signed-in user row, or None. Cached per request.

    Re-reads `session_version` from the database on every request rather than
    trusting the cookie alone. That is the point: a cookie is a claim the user
    holds, and the only thing that can retire it is a value they do not
    control.
    """
    if "_current_user" in g:
        return g._current_user
    user = None
    uid = session.get(SESSION_USER)
    if uid is not None:
        row = db.query_one("SELECT * FROM users WHERE id = ?", (uid,))
        if row is not None and session.get(SESSION_VERSION) == row["session_version"]:
            user = row
        else:
            # Deleted account, or a password changed elsewhere. Drop the cookie
            # rather than leaving a session that half-works.
            session.clear()
    g._current_user = user
    return user


def login_required(fn):
    """Send a browser to sign-in; answer an API caller with JSON 401.

    Two shapes because the two callers are different: a person following a
    link should land on a form that returns them where they were, and
    `builder.js` should get a body it can read. Answering a fetch with an HTML
    redirect is how a client ends up guessing from a status code — the failure
    mode this project has hit repeatedly.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({
                    "ok": False,
                    "error": "Sign in to continue.",
                    "sign_in": url_for("main.sign_in_page"),
                }), 401
            return redirect(url_for("main.sign_in_page", next=request.full_path))
        return fn(*args, **kwargs)

    return wrapper
