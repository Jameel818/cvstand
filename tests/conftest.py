"""Shared pytest configuration.

The browser suite under `tests/e2e/` is **opt-in**. `pytest -q` stays the ~3s
unit loop this project runs on every edit; `pytest --e2e` adds the Playwright
journeys, which boot a real server and drive Chromium.

    venv/Scripts/python -m pytest -q                # unit + contract, ~3s
    venv/Scripts/python -m pytest --e2e -q          # everything
    venv/Scripts/python -m pytest --e2e -q -m e2e   # only the browser suite
"""
import atexit
import os
import shutil
import tempfile

import pytest

# Point the WHOLE test session at a throwaway data dir, before `app.config` is
# imported (it reads this once, at import time). Without it the suite writes
# into the user's own data/: `tests/test_smoke.py::uploaded_photo` POSTs a real
# upload, which landed a stray .jpg in data/uploads/ on every single run, and a
# test that saved a résumé would overwrite the one in the builder.
# data/sample_resume.json is still read from the repo, so seeding is unaffected.
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="cvstand-tests-")
os.environ["CVSTAND_DATA_DIR"] = _TEST_DATA_DIR
atexit.register(shutil.rmtree, _TEST_DATA_DIR, True)


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test starts with a full token bucket.

    `app/limits.py` keeps its buckets in module state, so they outlive a Flask
    test client and accumulate across a session. Without this, the suite's own
    volume would eventually spend an endpoint's allowance and the NEXT test to
    touch that route would fail with a 429 that has nothing to do with what it
    is testing — and it would fail based on test ORDER, which is the worst
    shape of flake to chase.

    Deliberately a reset rather than disabling the limiter under TESTING: the
    limits are a security control, and a control that is off in the test suite
    is a control nothing proves. `tests/test_limits.py` exercises them for real.
    """
    from app.limits import reset_all

    reset_all()
    yield
    reset_all()


@pytest.fixture(autouse=True)
def _fresh_db():
    """Every test starts with an empty user table.

    Same reasoning as `_fresh_rate_limits` above, and the same failure it
    prevents: the whole session shares ONE `CVSTAND_DATA_DIR`, so the
    SQLite file outlives a Flask test client exactly the way the rate-limit
    buckets do. A user row left behind makes the NEXT test that signs up with
    the same address fail on "already registered" — a failure that depends on
    test ORDER, which is the worst shape of flake to chase.

    Deliberately a wipe rather than an in-memory database: `:memory:` is
    per-connection, and this app opens one connection per request, so the
    schema would vanish between the sign-up POST and the redirect that reads
    it back. The suite must exercise the real file the app actually uses.
    """
    from app import db

    db.reset_for_tests()
    yield
    db.reset_for_tests()


@pytest.fixture(scope="session")
def _playwright():
    """The ONE Playwright instance for the whole session.

    It lives here, not in tests/e2e/conftest.py, because two gates need a
    browser and `sync_playwright()` cannot be entered twice in a thread: the
    second call raises "Playwright Sync API inside the asyncio loop".

    That is not hypothetical. `tests/e2e/conftest.py` held a session-scoped
    instance open for the whole run while `tests/test_golden_pixels.py` opened
    its own, so in a full `pytest --e2e` EVERY pixel test errored at setup --
    all 50, every run -- while the file passed when run alone. And because
    those were setup ERRORS rather than failures, pytest could still exit 0
    (see the warning in RESUME_HERE.md about reading "N passed" alone). The
    pixel gate is the proof that English appearance does not move under the
    bilingual work; it had been silently absent from the documented command
    since it was written.

    Session-scoped and lazy, so `pytest -q` never starts a browser.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


def pytest_addoption(parser):
    parser.addoption(
        "--e2e", action="store_true", default=False,
        help="run the Playwright end-to-end suite (slow; needs Chromium installed)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: browser journey test — opt in with --e2e")
    config.addinivalue_line(
        "markers", "slow: runs the whole 49-template catalogue through Chromium")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--e2e"):
        return
    skip = pytest.mark.skip(reason="browser suite: pass --e2e to run it")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Expose the phase reports so the `page` fixture can tell, at teardown,
    whether the test failed — that is when a screenshot and trace are worth
    keeping."""
    outcome = yield
    setattr(item, "rep_" + call.when, outcome.get_result())
