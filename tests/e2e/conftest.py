"""Fixtures for the browser suite: a real server on a throwaway data dir.

WHY A SUBPROCESS, NOT `app.test_client()`. Everything these tests exist to
cover — autosave, the live preview iframe, the template drawer, auto-fit, the
blob downloads — is JavaScript. A test client never runs any of it, which is
exactly the gap the other 99 tests leave.

WHY A THROWAWAY DATA DIR. The app is single-user: one `data/resume.json`, and
the builder autosaves on every keystroke. Driving the real builder against the
real data dir would overwrite the user's résumé. `CVSTAND_DATA_DIR` (see
app/config.py) points the server somewhere disposable; `data/sample_resume.json`
is still read from the repo, so each session seeds from the shared sample.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    yield from _serve(tmp_path_factory, "e2e-data", server_store=True)


@pytest.fixture()
def deployed_server(tmp_path_factory):
    """A server configured the way a PUBLIC one is: CVSTAND_SERVER_STORE=0.

    Not a variant for completeness — it is the only configuration in which the
    multi-visitor claim is true, and finding that out is what this fixture is
    for. With the default server store ON, visitor A's autosave mirrors into
    `data/resume.json` and `/builder` seeds `#resume-data` from that file, so
    visitor B opens the builder and finds A's name already typed in. The
    browser-side store does not fix that by itself: the leak is in the SEED.

    Measured 2026-09-10, and it is the reason the flag exists rather than the
    migration simply being "the browser stores it now".
    """
    yield from _serve(tmp_path_factory, "e2e-deployed", server_store=False)


def _serve(tmp_path_factory, slug, *, server_store):
    data_dir = tmp_path_factory.mktemp(slug)
    log_path = data_dir / "server.log"
    port = _free_port()
    env = dict(os.environ, CVSTAND_DATA_DIR=str(data_dir), PYTHONUTF8="1",
               CVSTAND_SERVER_STORE=("1" if server_store else "0"))
    if not server_store:
        # A deployment-mode server REFUSES TO BOOT with the shipped default
        # SECRET_KEY (app/__init__.py): the session cookie carries the
        # signed-in user, so a known signing key mints a session as anybody.
        # Setting one here is not a workaround — it is the fixture doing what
        # a real deployment has to do, and it is why the guard gates on
        # `SERVER_STORE` rather than on something a test could forget.
        env["SECRET_KEY"] = "test-only-key-not-the-shipped-default"

    # Log to a file, not a pipe: the gallery alone issues 49 /preview requests
    # and a full pipe buffer would deadlock the server mid-test.
    log = open(log_path, "wb")
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "from app import create_app; "
         f"create_app().run(host='127.0.0.1', port={port}, threaded=True)"],
        cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
    )

    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while True:
        if proc.poll() is not None:
            log.close()
            raise RuntimeError(
                "server exited during startup:\n"
                + log_path.read_text(encoding="utf-8", errors="replace"))
        try:
            urllib.request.urlopen(base + "/", timeout=2).read()
            break
        except Exception:
            if time.time() > deadline:
                proc.kill()
                log.close()
                raise RuntimeError(
                    "server never answered on " + base + "\n"
                    + log_path.read_text(encoding="utf-8", errors="replace"))
            time.sleep(0.25)

    yield SimpleNamespace(url=base, data_dir=data_dir, log=log_path)

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover
        proc.kill()
    log.close()


def _despite_the_server(op, *, attempts: int = 40, delay: float = 0.05):
    """Retry a file op that the live server may momentarily be holding open.

    WINDOWS SHARING SEMANTICS. Opening a file for writing (or unlinking it)
    fails with PermissionError while another process has it open — there is no
    POSIX-style "last writer wins" here, and `app/store.py::_write_json` ends in
    `tmp.replace(path)`, which is atomic on POSIX but ALSO denied on Windows if
    the destination is open.

    That collides with this fixture because the builder autosaves on a 900ms
    debounce: a test that edits a field and then ends can leave a
    `PUT /api/resume` in flight, which lands inside the NEXT test's reset. The
    window is small and CPU-load dependent, which is what makes it a
    once-in-many-runs flake rather than an outright break — observed
    2026-09-01 as `PermissionError: [Errno 13] ... e2e-data0/resume.json`
    aborting `test_zoom_controls_scale_the_stage` in setup.

    Retrying is the right shape of fix: the server's write is legitimate and
    short-lived, and this fixture only needs to land last."""
    last = None
    for _ in range(attempts):
        try:
            return op()
        except PermissionError as exc:      # server holds it; it will let go
            last = exc
            time.sleep(delay)
    raise AssertionError(
        f"data dir still locked by the server after {attempts * delay:.1f}s: {last}")


@pytest.fixture(autouse=True)
def clean_state(live_server):
    """Every test starts from the shared sample and the default template.

    Written straight to disk rather than through the API: the store reads the
    file on each request, so there is no cache to invalidate."""
    resume = live_server.data_dir / "resume.json"
    payload = json.dumps(SAMPLE, indent=2, ensure_ascii=False)
    _despite_the_server(lambda: resume.write_text(payload, encoding="utf-8"))
    meta = live_server.data_dir / "meta.json"
    if meta.exists():
        _despite_the_server(lambda: meta.unlink(missing_ok=True))
    yield


@pytest.fixture()
def seed_resume(live_server):
    """Write a résumé straight into the live server's data dir, retry-guarded.

    Same job as `clean_state`, exposed for tests that need a *different*
    starting résumé (a heavy one, say). Going through `PUT /api/resume` instead
    would be slower and would couple the fixture to the autosave path several of
    those tests are there to exercise."""
    def _seed(data: dict):
        path = live_server.data_dir / "resume.json"
        payload = json.dumps(data, indent=2, ensure_ascii=False)
        _despite_the_server(lambda: path.write_text(payload, encoding="utf-8"))
    return _seed


# `_playwright` now lives in tests/conftest.py: the pixel gate needs a browser
# too, and a second sync_playwright() in the same thread raises.

@pytest.fixture(scope="session")
def browser(_playwright):
    b = _playwright.chromium.launch()
    yield b
    b.close()


@pytest.fixture()
def page(browser, request):
    ctx = browser.new_context(viewport={"width": 1440, "height": 950},
                              accept_downloads=True)
    ctx.tracing.start(screenshots=True, snapshots=True)
    pg = ctx.new_page()
    pg.set_default_timeout(20_000)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    yield pg

    rep = getattr(request.node, "rep_call", None)
    failed = rep is not None and rep.failed
    if failed:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        stem = request.node.name.replace("/", "_").replace("[", "_").replace("]", "")
        try:
            pg.screenshot(path=str(ARTIFACTS / f"{stem}.png"), full_page=True)
        except Exception:  # pragma: no cover — page may already be gone
            pass
        ctx.tracing.stop(path=str(ARTIFACTS / f"{stem}-trace.zip"))
        if errors:
            print("\nconsole page errors:\n  " + "\n  ".join(errors))
    else:
        ctx.tracing.stop()
    ctx.close()
    # An uncaught JS exception is a failure even when the assertions passed:
    # the builder swallows fetch errors, so a broken listener can look green.
    assert not errors, "uncaught JS error(s): " + " | ".join(errors)
