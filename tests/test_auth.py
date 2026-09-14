"""Accounts and sessions — Stage 3, Phase 1.

The single most important property in this file is the one that is easiest to
lose: **anonymous use is unchanged.** All 49 templates, unlimited PDF, both
languages and the whole builder work with no account, and that is an
acquisition asset in a market saturated with free (`MONETIZATION.md` §6), not
a gap waiting to be closed. `test_anonymous_*` is the guard.
"""
import pytest

from app import InsecureDeployment, auth, create_app, db
from app.auth import SESSION_USER, SESSION_VERSION
from app.config import DEFAULT_SECRET_KEY
from app.limits import LIMITS

GOOD = "correct-horse-battery"          # 21 chars, over the floor
EMAIL = "wren@example.com"


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def ctx(app):
    """An app context, for calling auth/db functions without a request."""
    with app.app_context():
        yield


def signup(client, email=EMAIL, password=GOOD, **extra):
    return client.post("/account/sign-up",
                       data={"email": email, "password": password, **extra})


def signin(client, email=EMAIL, password=GOOD, **extra):
    return client.post("/account/sign-in",
                       data={"email": email, "password": password, **extra})


# ------------------------------------------------------------------ the module

def test_email_is_case_folded_and_stripped():
    assert auth.normalise_email("  Wren@Example.COM ") == "wren@example.com"


def test_two_cases_of_one_address_are_one_account(ctx):
    """Without folding, `Ali@x.com` and `ali@x.com` are two accounts — and one
    of them is the one that paid."""
    auth.create_user("Wren@Example.com", GOOD)
    with pytest.raises(auth.AuthError):
        auth.create_user("wren@example.com", GOOD)


@pytest.mark.parametrize("email", ["", "   ", "no-at-sign", "a@b", "a b@c.com",
                                   "a,b@c.com", "@c.com", "a@.com"])
def test_bad_emails_are_refused(email, ctx):
    with pytest.raises(auth.AuthError):
        auth.validate_credentials(email, GOOD)


def test_short_password_is_refused(ctx):
    with pytest.raises(auth.AuthError):
        auth.validate_credentials(EMAIL, "x" * (auth.MIN_PASSWORD_LENGTH - 1))
    auth.validate_credentials(EMAIL, "x" * auth.MIN_PASSWORD_LENGTH)


def test_absurdly_long_password_is_refused(ctx):
    """A cap, so a 5MB body cannot make the server scrypt-hash 5MB."""
    with pytest.raises(auth.AuthError):
        auth.validate_credentials(EMAIL, "x" * (auth.MAX_PASSWORD_LENGTH + 1))


def test_password_is_hashed_not_stored(ctx):
    auth.create_user(EMAIL, GOOD)
    row = db.query_one("SELECT * FROM users WHERE email = ?", (EMAIL,))
    stored = row["password_hash"]
    assert GOOD not in stored
    assert stored != GOOD
    # A salted hash: the same password hashed twice must not collide, or the
    # whole table falls to one rainbow table.
    auth.create_user("other@example.com", GOOD)
    other = db.query_one("SELECT * FROM users WHERE email = ?",
                         ("other@example.com",))
    assert other["password_hash"] != stored


def test_authenticate_accepts_only_the_right_password(ctx):
    auth.create_user(EMAIL, GOOD)
    assert auth.authenticate(EMAIL, GOOD) is not None
    assert auth.authenticate(EMAIL, GOOD + "x") is None
    assert auth.authenticate(EMAIL, "") is None
    assert auth.authenticate("nobody@example.com", GOOD) is None


def test_missing_account_still_pays_for_a_hash(ctx, monkeypatch):
    """Timing equalisation, asserted structurally rather than by a stopwatch.

    A wall-clock assertion here would be flaky on a loaded machine and prove
    little. What matters is that the no-such-user path performs the same
    expensive check as the wrong-password path — otherwise response time tells
    an attacker which addresses are registered.
    """
    calls = []
    real = auth.check_password_hash
    monkeypatch.setattr(auth, "check_password_hash",
                        lambda h, p: calls.append(h) or real(h, p))
    auth.authenticate("nobody@example.com", GOOD)
    assert len(calls) == 1, "no-such-user returned without hashing"
    assert calls[0] == auth._DUMMY_HASH


def test_changing_the_password_evicts_existing_sessions(ctx):
    uid = auth.create_user(EMAIL, GOOD)
    before = db.query_one("SELECT session_version FROM users WHERE id = ?",
                          (uid,))["session_version"]
    auth.change_password(uid, "a-different-long-one")
    after = db.query_one("SELECT session_version FROM users WHERE id = ?",
                         (uid,))["session_version"]
    assert after == before + 1
    assert auth.authenticate(EMAIL, GOOD) is None
    assert auth.authenticate(EMAIL, "a-different-long-one") is not None


# ------------------------------------------------------------------- the routes

def test_sign_up_creates_an_account_and_signs_in(client):
    res = signup(client)
    assert res.status_code == 302
    with client.session_transaction() as s:
        assert s[SESSION_USER]
    assert client.get("/").status_code == 200


def test_sign_up_rejects_a_duplicate_with_400(client):
    signup(client)
    client.post("/account/sign-out")
    res = signup(client)
    assert res.status_code == 400
    with client.session_transaction() as s:
        assert SESSION_USER not in s


def test_sign_up_rejects_a_short_password_with_400(client):
    res = signup(client, password="short")
    assert res.status_code == 400
    with client.session_transaction() as s:
        assert SESSION_USER not in s


def test_sign_in_round_trip(client):
    signup(client)
    client.post("/account/sign-out")
    res = signin(client)
    assert res.status_code == 302
    with client.session_transaction() as s:
        assert s[SESSION_USER]


def test_wrong_password_and_missing_account_say_the_same_thing(client):
    """Different messages let a stranger enumerate who has an account here.

    Compares the ERROR, not the whole page: the form legitimately echoes the
    address back so the person does not retype it, and that is their own
    input, not a disclosure. A first cut of this test compared whole bodies
    and failed on exactly that difference.
    """
    import re

    def error_of(res):
        html = res.data.decode("utf-8")
        found = re.search(r'class="form-errors show"[^>]*>(.*?)</div>', html, re.S)
        return found.group(1).strip() if found else None

    signup(client)
    client.post("/account/sign-out")
    wrong = signin(client, password=GOOD + "x")
    missing = signin(client, email="nobody@example.com")
    assert wrong.status_code == missing.status_code == 401
    assert error_of(wrong) and error_of(wrong) == error_of(missing)
    # And it must not hint at which half was wrong.
    assert "password" not in error_of(wrong).lower().replace("and password", "")


def test_sign_out_clears_the_session(client):
    signup(client)
    assert client.post("/account/sign-out").status_code == 302
    with client.session_transaction() as s:
        assert SESSION_USER not in s


def test_sign_out_refuses_GET(client):
    """A GET that changes state is CSRF-able from any <img>, and browsers
    prefetch GET links — a sign-out link would log people out as they read."""
    signup(client)
    assert client.get("/account/sign-out").status_code == 405
    with client.session_transaction() as s:
        assert SESSION_USER in s


@pytest.mark.parametrize("evil", [
    "//evil.example.com", "https://evil.example.com", "http://evil.example.com",
])
def test_open_redirect_is_refused(client, evil):
    """An open redirect ON A SIGN-IN PAGE is the classic phishing setup: the
    user checks the domain, signs in for real, and is bounced to a lookalike
    that asks again."""
    res = signup(client, next=evil)
    assert res.status_code == 302
    assert "evil.example.com" not in res.headers["Location"]


def test_a_safe_next_is_honoured(client):
    res = signup(client, next="/templates?cat=ats")
    assert res.headers["Location"].endswith("/templates?cat=ats")


def test_password_never_appears_in_a_response(client):
    for res in (signup(client, password="a-very-distinctive-passphrase"),
                client.get("/account/sign-in")):
        assert b"a-very-distinctive-passphrase" not in res.data


def test_session_dies_when_the_password_changes_elsewhere(client, app):
    """The cookie is a claim the user holds; only something they do not
    control can retire it."""
    signup(client)
    with app.app_context():
        row = db.query_one("SELECT id FROM users WHERE email = ?", (EMAIL,))
        auth.change_password(row["id"], "another-long-password")
    assert client.get("/").status_code == 200
    with client.session_transaction() as s:
        assert SESSION_USER not in s, "a stale session survived a password change"


def test_session_dies_when_the_account_is_deleted(client, app):
    signup(client)
    with app.app_context():
        db.execute("DELETE FROM users WHERE email = ?", (EMAIL,))
    client.get("/")
    with client.session_transaction() as s:
        assert SESSION_USER not in s


def test_a_forged_session_version_does_not_authenticate(client, app):
    signup(client)
    with client.session_transaction() as s:
        s[SESSION_VERSION] = 999
    res = client.get("/")
    assert EMAIL.encode() not in res.data


def test_signed_in_pages_show_who_you_are(client):
    assert EMAIL.encode() not in client.get("/").data
    signup(client)
    assert EMAIL.encode() in client.get("/").data


def test_sign_in_is_rate_limited(client):
    for _ in range(int(LIMITS["auth"].capacity)):
        signin(client, email="nobody@example.com")
    assert signin(client, email="nobody@example.com").status_code == 429


# ----------------------------------------------------- anonymous use is intact

@pytest.mark.parametrize("path", ["/", "/templates", "/builder",
                                  "/templates?cat=modern", "/account/sign-in"])
def test_anonymous_pages_still_work(client, path):
    assert client.get(path).status_code == 200


def test_anonymous_can_still_render(client):
    import json, pathlib
    data = json.loads(pathlib.Path("data/sample_resume.json").read_text("utf-8"))
    res = client.post("/api/render", json={"data": data})
    assert res.status_code == 200 and res.get_json()["ok"]


def test_the_header_does_not_nag_anonymous_visitors(client):
    """No "Sign in" link for a signed-out visitor, on purpose. The free tier
    needs no account, and a prominent sign-in invites people to think it does
    — which is the promise `MONETIZATION.md` §6 says is worth protecting."""
    body = client.get("/").data.decode("utf-8")
    assert "/account/sign-in" not in body
    assert "/account/sign-up" not in body


# ------------------------------------------------------------------- deployment

def test_a_deployment_refuses_to_boot_with_the_default_secret_key(monkeypatch):
    """Before accounts, the session cookie carried nothing worth forging. It
    now carries WHO YOU ARE, so a known signing key mints a session as any
    user — including one holding a paid pass — without touching the database.
    Fail at startup: a warning in a log nobody reads ships anyway."""
    import app as app_pkg

    monkeypatch.setattr(app_pkg, "SERVER_STORE", False)
    with pytest.raises(InsecureDeployment):
        create_app()


def test_a_deployment_boots_with_a_real_secret_key(monkeypatch):
    import app as app_pkg
    from app.config import Config

    class Real(Config):
        SECRET_KEY = "a-long-random-value-from-secrets-token-urlsafe"

    monkeypatch.setattr(app_pkg, "SERVER_STORE", False)
    assert create_app(Real) is not None


def test_the_local_default_is_still_allowed():
    """The single-user local workflow must not need a key ceremony."""
    assert create_app().config["SECRET_KEY"] == DEFAULT_SECRET_KEY


def test_password_hint_matches_the_constant():
    """The sign-up copy names a number, and the number is a literal in the
    msgid because the catalogue has no interpolation precedent. Pin the two
    together so they cannot drift into a lie."""
    import pathlib
    page = pathlib.Path("app/templates/account.html").read_text("utf-8")
    assert f"At least {auth.MIN_PASSWORD_LENGTH} characters" in page


# --------------------------------------------------- the interface translates

def _ar(client, path):
    client.set_cookie("ui_lang", "ar")
    return client.get(path).data.decode("utf-8")


@pytest.mark.parametrize("path", ["/account/sign-up", "/account/sign-in"])
def test_the_account_pages_are_translated(client, path):
    """The bug this catches actually shipped, and `test_labels.py` passed.

    The route pre-translated the heading and button with `ui_t(...)` — whose
    signature is `ui_t(text, lang="en")` — so with no language argument the
    Arabic page rendered a mirrored, fully-Arabic form under an English
    heading with an English button. The catalogue rows existed the whole time;
    nothing was reading them. Translation now happens in the template, where
    `t()` knows the reader's language.
    """
    html = _ar(client, path)
    assert "Create your account" not in html
    assert "Create account" not in html
    assert ">Sign in<" not in html
    assert "إنشاء حساب" in html or "تسجيل الدخول" in html


def test_the_sign_in_error_is_translated(client):
    signup(client)
    client.post("/account/sign-out")
    client.set_cookie("ui_lang", "ar")
    html = signin(client, password=GOOD + "x").data.decode("utf-8")
    assert "That email and password do not match." not in html
    assert "غير متطابقين" in html


def test_auth_messages_are_all_translated():
    """Every string `auth.py` can raise must exist in the catalogue.

    Read out of the module source rather than listed here, so a new `raise
    AuthError("...")` that nobody translated fails this test instead of
    silently rendering English to an Arabic reader. It also catches an
    f-string msgid, which can never match a catalogue key.
    """
    import ast
    import pathlib

    from app.labels import ui_t

    tree = ast.parse(pathlib.Path("app/auth.py").read_text(encoding="utf-8"))
    raised = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        if getattr(node.exc.func, "id", "") != "AuthError" or not node.exc.args:
            continue
        arg = node.exc.args[0]
        assert not isinstance(arg, ast.JoinedStr), (
            "an f-string AuthError message can never match a catalogue key"
        )
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            raised.append(arg.value)

    assert len(raised) >= 7, f"only found {len(raised)} messages — parser drifted?"
    missing = [m for m in raised if ui_t(m, "ar") == m]
    assert not missing, f"untranslated AuthError messages: {missing}"


def test_the_password_message_matches_the_constant():
    """The copy names a number and the constant defines it. Pin them."""
    import pathlib

    src = pathlib.Path("app/auth.py").read_text(encoding="utf-8")
    assert f"Use at least {auth.MIN_PASSWORD_LENGTH} characters" in src
