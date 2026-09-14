"""Invariants of the test harness itself.

These run in the FAST loop on purpose. What they guard against is a gate that
stops running — a failure that shows up as green, so the slow opt-in suite is
exactly the wrong place to catch it.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"


def _sync_playwright_calls(src: str):
    """Line numbers where `sync_playwright(...)` is actually CALLED.

    Parsed rather than grepped: this file, tests/conftest.py and
    tests/test_golden_pixels.py all *discuss* sync_playwright in prose, and a
    regex flags every one of those. A guard that cries wolf on its own
    docstring is a guard someone deletes.
    """
    return [
        node.lineno
        for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sync_playwright"
    ]


def test_only_one_place_enters_sync_playwright():
    """`sync_playwright()` may be entered ONCE per session, in tests/conftest.py.

    Two gates need a browser: `tests/e2e/` and `tests/test_golden_pixels.py`.
    They each used to open their own, and Playwright's sync API cannot be
    entered twice in a thread — the second raises "Playwright Sync API inside
    the asyncio loop".

    The damage was invisible in the shape this project keeps finding. Running
    `pytest --e2e tests/test_golden_pixels.py` alone: 50 passed. Running the
    documented full `pytest --e2e`: all 50 errored AT SETUP, every run, because
    a tests/e2e/ test had already opened one. Setup errors are not failures, so
    pytest could still exit 0 and the summary still read "935 passed" — and the
    pixel gate, which is the only proof that English APPEARANCE does not move
    under the bilingual work, had never once run in that command.

    So the guard is static and fast rather than a browser test: a second
    `sync_playwright()` anywhere under tests/ is the bug, whatever it is for.
    """
    offenders = []
    for f in sorted(TESTS.rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if rel == "tests/conftest.py":
            continue
        for line in _sync_playwright_calls(f.read_text(encoding="utf-8")):
            offenders.append(f"{rel}:{line}")

    assert not offenders, (
        "sync_playwright() is entered outside tests/conftest.py, which makes "
        "every browser test collected after it error at setup:\n  "
        + "\n  ".join(offenders)
        + "\nDepend on the session-scoped `_playwright` fixture instead."
    )


def test_the_pixel_gate_uses_the_shared_playwright():
    """The other half: the pixel gate must actually take the shared fixture.

    Asserted separately because dropping `_playwright` from its signature would
    not reintroduce a second `sync_playwright()` call — it would just fail to
    launch a browser, in a file the fast loop never runs.
    """
    src = (TESTS / "test_golden_pixels.py").read_text(encoding="utf-8")
    assert "def browser(_playwright):" in src, (
        "tests/test_golden_pixels.py's browser fixture no longer depends on the "
        "session-wide _playwright fixture from tests/conftest.py"
    )
