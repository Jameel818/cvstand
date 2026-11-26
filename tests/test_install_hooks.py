"""The pre-commit hook that runs the download lock (tools/hooks/pre-commit,
tools/install_hooks.py; feature/download-lock 2026-11-26).

Fast: a throwaway git repo whose "venv python" is a stub that passes or fails,
and a real `git commit` in it - git must run the hook and refuse the commit
when the lock test fails.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import install_hooks  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _git(repo, *a, check=True):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env=env,
                          stdin=subprocess.DEVNULL, check=check)


def _repo(tmp_path, lock_exit: int) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    stub = repo / "venv" / "bin" / "python"
    stub.parent.mkdir(parents=True)
    # the stub records how it was called and exits like the lock test would
    stub.write_bytes(f'#!/bin/sh\necho "$@" > called.txt\nexit {lock_exit}\n'.encode())
    stub.chmod(0o755)
    install_hooks.install(repo)
    (repo / "a.txt").write_text("x")
    _git(repo, "add", "a.txt")
    return repo


def test_the_hook_is_installed_and_runs_the_download_lock_test(tmp_path):
    repo = _repo(tmp_path, 0)
    assert install_hooks.install(repo, check=True) == 0
    r = _git(repo, "commit", "-q", "-m", "ok", check=False)
    assert r.returncode == 0, r.stderr
    assert "tests/test_download_lock.py" in (repo / "called.txt").read_text()
    assert _git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "1"


def test_a_failing_download_lock_refuses_the_commit(tmp_path):
    repo = _repo(tmp_path, 1)
    r = _git(repo, "commit", "-q", "-m", "moved a download", check=False)
    assert r.returncode != 0
    assert "DOWNLOAD LOCK FAILED" in r.stderr and "commit refused" in r.stderr
    assert _git(repo, "rev-parse", "--verify", "HEAD", check=False).returncode != 0   # nothing committed


def test_reinstall_is_a_no_op_and_a_foreign_hook_is_backed_up(tmp_path):
    repo = _repo(tmp_path, 0)
    hook = install_hooks.hooks_dir(repo) / "pre-commit"
    before = hook.read_bytes()
    assert install_hooks.install(repo) == 0 and hook.read_bytes() == before
    assert not (hook.parent / "pre-commit.local-backup").exists()
    hook.write_text("#!/bin/sh\nexit 0\n")
    assert install_hooks.install(repo, check=True) == 1
    install_hooks.install(repo)
    assert hook.read_bytes() == before
    assert (hook.parent / "pre-commit.local-backup").read_text() == "#!/bin/sh\nexit 0\n"
